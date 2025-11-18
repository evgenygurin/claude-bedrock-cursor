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

        with pytest.raises(ConfigError, match="not found"):
            Config.from_toml(nonexistent)

    def test_config_from_invalid_toml(self, tmp_path: Path):
        """Test loading from invalid TOML raises error.

        Args:
            tmp_path: Pytest temporary directory
        """
        invalid_toml = tmp_path / "invalid.toml"
        invalid_toml.write_text("this is not valid toml [[[")

        with pytest.raises(ConfigError, match="Failed to parse"):
            Config.from_toml(invalid_toml)

    def test_save_to_toml(self, tmp_path: Path):
        """Test saving config to TOML file.

        Args:
            tmp_path: Pytest temporary directory
        """
        config = Config(
            aws_region="us-west-2",
            bedrock_model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            max_output_tokens=8192,
        )

        output_file = tmp_path / "output.toml"
        config.save_to_toml(output_file)

        assert output_file.exists()

        # Load and verify
        loaded_config = Config.from_toml(output_file)
        assert loaded_config.aws_region == "us-west-2"
        assert loaded_config.max_output_tokens == 8192

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

    def test_config_get_config_dir(self):
        """Test getting config directory path."""
        config = Config()
        config_dir = config.get_config_dir()

        assert isinstance(config_dir, Path)
        assert config_dir.name == ".claude-bedrock"

    def test_config_ensure_config_dir_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test ensuring config directory is created.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        test_home = tmp_path / "home"
        monkeypatch.setenv("HOME", str(test_home))

        config = Config()
        config_dir = config.ensure_config_dir_exists()

        assert config_dir.exists()
        assert config_dir.is_dir()
        assert config_dir == test_home / ".claude-bedrock"

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
        with pytest.raises(ValidationError, match="String should match pattern"):
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

    def test_config_immutability_after_save(self, tmp_path: Path):
        """Test config can be modified and re-saved.

        Args:
            tmp_path: Pytest temporary directory
        """
        config_file = tmp_path / "config.toml"

        # Save initial config
        config1 = Config(aws_region="us-east-1")
        config1.save_to_toml(config_file)

        # Modify and save again
        config2 = Config(aws_region="us-west-2")
        config2.save_to_toml(config_file)

        # Verify latest values persisted
        loaded = Config.from_toml(config_file)
        assert loaded.aws_region == "us-west-2"

    def test_config_partial_toml(self, tmp_path: Path):
        """Test loading partial TOML with defaults.

        Args:
            tmp_path: Pytest temporary directory
        """
        partial_toml = tmp_path / "partial.toml"
        partial_toml.write_text(
            """
[aws]
region = "eu-central-1"
"""
        )

        config = Config.from_toml(partial_toml)

        # Specified value
        assert config.aws_region == "eu-central-1"

        # Default values should still apply
        assert config.bedrock_model_id == "anthropic.claude-sonnet-4-20250514-v1:0"
        assert config.max_output_tokens == 4096
