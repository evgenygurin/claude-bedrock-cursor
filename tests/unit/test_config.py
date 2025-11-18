"""Unit tests for configuration management."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_bedrock_cursor.config import Config
from claude_bedrock_cursor.utils.errors import ConfigError


@pytest.mark.unit
class TestConfig:
    """Test suite for Config class."""

    def test_default_config(self):
        """Test creating config with default values."""
        config = Config()

        assert config.aws_region == "us-east-1"
        assert config.bedrock_model_id == "anthropic.claude-sonnet-4-20250514-v1:0"
        assert config.max_output_tokens == 4096
        assert config.max_thinking_tokens == 1024
        assert config.enable_prompt_caching is True
        assert config.enable_streaming is True
        assert config.cursor_integration_mode == "both"

    def test_config_from_toml(self, test_config_file: Path):
        """Test loading config from TOML file.

        Args:
            test_config_file: Test config file fixture
        """
        config = Config.from_toml(test_config_file)

        assert config.aws_region == "us-east-1"
        assert config.bedrock_model_id == "anthropic.claude-sonnet-4-20250514-v1:0"
        assert config.max_output_tokens == 4096
        assert config.max_thinking_tokens == 1024
        assert config.enable_prompt_caching is True
        assert config.cursor_integration_mode == "both"

    def test_config_from_nonexistent_file(self, tmp_path: Path):
        """Test loading from non-existent file raises error.

        Args:
            tmp_path: Pytest temporary directory
        """
        nonexistent = tmp_path / "nonexistent.toml"

        with pytest.raises(FileNotFoundError, match="not found"):
            Config.from_toml(nonexistent)

    def test_config_from_invalid_toml(self, tmp_path: Path):
        """Test loading from invalid TOML raises error.

        Args:
            tmp_path: Pytest temporary directory
        """
        invalid_toml = tmp_path / "invalid.toml"
        invalid_toml.write_text("this is not valid toml [[[")

        with pytest.raises(Exception):  # tomllib.TOMLDecodeError or tomli.TOMLDecodeError
            Config.from_toml(invalid_toml)

    def test_max_output_tokens_validation(self):
        """Test MAX_OUTPUT_TOKENS must be at least 4096."""
        # Valid: 4096
        config = Config(max_output_tokens=4096)
        assert config.max_output_tokens == 4096

        # Valid: more than 4096
        config = Config(max_output_tokens=8192)
        assert config.max_output_tokens == 8192

        # Invalid: less than 4096
        with pytest.raises(ValidationError, match="greater than or equal to 4096"):
            Config(max_output_tokens=2048)

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config(aws_region="eu-west-1")
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["aws_region"] == "eu-west-1"
        assert config_dict["max_output_tokens"] == 4096

    def test_config_from_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading config from environment variables.

        Args:
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-opus-20240229")
        monkeypatch.setenv("MAX_OUTPUT_TOKENS", "8192")
        monkeypatch.setenv("ENABLE_PROMPT_CACHING", "false")

        config = Config()

        # Environment variables should override defaults
        assert config.aws_region == "ap-southeast-1"
        assert config.bedrock_model_id == "anthropic.claude-3-opus-20240229"
        assert config.max_output_tokens == 8192
        assert config.enable_prompt_caching is False

    def test_config_validation_invalid_region(self):
        """Test validation rejects invalid AWS region."""
        with pytest.raises(ValidationError, match="Invalid AWS region"):
            Config(aws_region="invalid-region-123")

    def test_config_model_id_pattern(self):
        """Test Bedrock model ID pattern validation."""
        # Valid Claude model ID
        config = Config(bedrock_model_id="anthropic.claude-sonnet-4-20250514-v1:0")
        assert config.bedrock_model_id.startswith("anthropic.claude-")

        # Valid alternative model
        config = Config(bedrock_model_id="anthropic.claude-3-opus-20240229")
        assert config.bedrock_model_id.startswith("anthropic.claude-")

    def test_config_cursor_integration_mode_validation(self):
        """Test cursor integration mode validation."""
        # Valid modes
        for mode in ["cli", "extension", "both"]:
            config = Config(cursor_integration_mode=mode)
            assert config.cursor_integration_mode == mode

        # Invalid mode
        with pytest.raises(ValidationError, match="Input should be"):
            Config(cursor_integration_mode="invalid")

    def test_config_partial_toml(self, tmp_path: Path):
        """Test loading partial TOML with defaults.

        Args:
            tmp_path: Pytest temporary directory
        """
        partial_toml = tmp_path / "partial.toml"
        partial_toml.write_text(
            """
aws_region = "eu-central-1"
"""
        )

        config = Config.from_toml(partial_toml)

        # Specified value
        assert config.aws_region == "eu-central-1"

        # Default values should still apply
        assert config.bedrock_model_id == "anthropic.claude-sonnet-4-20250514-v1:0"
        assert config.max_output_tokens == 4096
