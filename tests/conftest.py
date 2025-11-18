"""Pytest configuration and shared fixtures."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_bedrock_cursor.config import Config


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Create temporary config directory for tests.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path: Path to test config directory
    """
    config_dir = tmp_path / ".claude-bedrock"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def test_config_file(test_config_dir: Path) -> Path:
    """Create test configuration file.

    Args:
        test_config_dir: Test config directory fixture

    Returns:
        Path: Path to test config.toml
    """
    config_file = test_config_dir / "config.toml"
    config_file.write_text(
        """
[aws]
region = "us-east-1"
profile = "default"

[bedrock]
model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
max_output_tokens = 4096
max_thinking_tokens = 1024
enable_prompt_caching = true
enable_streaming = true

[cursor]
integration_mode = "both"
auto_update_rules = true
"""
    )
    return config_file


@pytest.fixture
def sample_config(test_config_file: Path) -> Config:
    """Load sample configuration for tests.

    Args:
        test_config_file: Test config file fixture

    Returns:
        Config: Pydantic configuration instance
    """
    return Config.from_toml(test_config_file)


@pytest.fixture
def mock_keyring(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Mock keyring for testing token storage.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        dict: In-memory token storage
    """
    storage: dict[str, str] = {}

    def mock_set_password(service: str, username: str, password: str) -> None:
        storage[f"{service}:{username}"] = password

    def mock_get_password(service: str, username: str) -> str | None:
        return storage.get(f"{service}:{username}")

    def mock_delete_password(service: str, username: str) -> None:
        storage.pop(f"{service}:{username}", None)

    import keyring

    monkeypatch.setattr(keyring, "set_password", mock_set_password)
    monkeypatch.setattr(keyring, "get_password", mock_get_password)
    monkeypatch.setattr(keyring, "delete_password", mock_delete_password)

    return storage


@pytest.fixture
def mock_httpx_client() -> Generator[AsyncMock, None, None]:
    """Mock httpx AsyncClient for testing OAuth.

    Yields:
        AsyncMock: Mocked AsyncClient
    """
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 300,
    }
    mock_client.post.return_value = mock_response
    yield mock_client


@pytest.fixture
def mock_boto3_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock boto3 client for testing Bedrock.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        MagicMock: Mocked boto3 bedrock-runtime client
    """
    mock_client = MagicMock()

    # Mock successful streaming response
    mock_stream = [
        {
            "chunk": {
                "bytes": b'{"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}'
            }
        },
        {
            "chunk": {
                "bytes": b'{"type":"content_block_delta","delta":{"type":"text_delta","text":" World"}}'
            }
        },
        {"chunk": {"bytes": b'{"type":"message_stop"}'}},
    ]

    mock_response = {"body": iter(mock_stream)}
    mock_client.invoke_model_with_response_stream.return_value = mock_response

    def mock_boto3_client_func(service_name: str, **kwargs):
        if service_name == "bedrock-runtime":
            return mock_client
        raise ValueError(f"Unexpected service: {service_name}")

    import boto3

    monkeypatch.setattr(boto3, "client", mock_boto3_client_func)

    return mock_client


@pytest.fixture
def sample_oauth_token() -> str:
    """Generate sample OAuth token for testing.

    Returns:
        str: Base64-encoded sample token
    """
    import base64
    import json

    token_data = {
        "user_id": "test_user",
        "email": "test@example.com",
        "subscription": "MAX",
        "exp": 1735689600,  # 2025-01-01
    }
    return base64.b64encode(json.dumps(token_data).encode()).decode()


@pytest.fixture
def sample_access_token() -> str:
    """Generate sample access token for testing.

    Returns:
        str: Sample JWT access token
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJleHAiOjE3MzU2ODk2MDB9.test_signature"


@pytest.fixture
def sample_refresh_token() -> str:
    """Generate sample refresh token for testing.

    Returns:
        str: Sample refresh token
    """
    return "refresh_token_test_1234567890abcdef"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean environment variables for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Remove AWS environment variables
    for var in [
        "AWS_REGION",
        "AWS_PROFILE",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)

    # Remove application environment variables
    for var in [
        "BEDROCK_MODEL_ID",
        "CLAUDE_CODE_USE_BEDROCK",
        "ENABLE_PROMPT_CACHING",
        "ENABLE_STREAMING",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_subprocess_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock subprocess.run for testing CLI commands.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        MagicMock: Mocked subprocess.run
    """
    import subprocess

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "test_oauth_token_from_claude_setup"
    mock_result.stderr = ""

    mock_run = MagicMock(return_value=mock_result)
    monkeypatch.setattr(subprocess, "run", mock_run)

    return mock_run
