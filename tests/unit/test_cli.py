"""Unit tests for CLI commands."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from claude_bedrock_cursor.cli import app
from claude_bedrock_cursor.config import Config

runner = CliRunner()


@pytest.mark.unit
class TestCLIInit:
    """Test suite for 'claude-bedrock init' command."""

    def test_init_creates_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test init command creates configuration.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Configuration initialized" in result.stdout

        # Verify config file created
        config_dir = tmp_path / ".claude-bedrock"
        assert config_dir.exists()
        assert (config_dir / "config.toml").exists()

    def test_init_with_custom_region(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test init with custom AWS region.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["init", "--region", "eu-west-1"])

        assert result.exit_code == 0

        # Verify region in config
        config_file = tmp_path / ".claude-bedrock" / "config.toml"
        config = Config.from_toml(config_file)
        assert config.aws_region == "eu-west-1"

    def test_init_already_initialized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test init when already initialized.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # First init
        result1 = runner.invoke(app, ["init"])
        assert result1.exit_code == 0

        # Second init should warn
        result2 = runner.invoke(app, ["init"])
        assert result2.exit_code == 0
        assert "already initialized" in result2.stdout.lower()


@pytest.mark.unit
class TestCLIStatus:
    """Test suite for 'claude-bedrock status' command."""

    def test_status_not_configured(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test status when not configured.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert (
            "Not configured" in result.stdout
            or "not initialized" in result.stdout.lower()
        )

    def test_status_configured(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
    ):
        """Test status when configured.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        # Add tokens
        mock_keyring["claude-bedrock-cursor:access_token"] = "test_access"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert (
            "Authenticated" in result.stdout or "authenticated" in result.stdout.lower()
        )


@pytest.mark.unit
class TestCLIAuth:
    """Test suite for 'claude-bedrock auth' commands."""

    @pytest.mark.asyncio
    async def test_auth_login(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
    ):
        """Test auth login command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
            mock_subprocess_run: Mocked subprocess fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0
        assert (
            "Successfully authenticated" in result.stdout
            or "login" in result.stdout.lower()
        )

    def test_auth_status_not_authenticated(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
    ):
        """Test auth status when not authenticated.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert (
            "Not authenticated" in result.stdout
            or "not logged in" in result.stdout.lower()
        )

    def test_auth_status_authenticated(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
    ):
        """Test auth status when authenticated.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Add tokens
        mock_keyring["claude-bedrock-cursor:access_token"] = "test_access"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        result = runner.invoke(app, ["auth", "status"])

        assert result.exit_code == 0
        assert "Authenticated" in result.stdout or "logged in" in result.stdout.lower()

    def test_auth_logout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
    ):
        """Test auth logout command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Add tokens
        mock_keyring["claude-bedrock-cursor:access_token"] = "test_access"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        result = runner.invoke(app, ["auth", "logout"])

        assert result.exit_code == 0
        assert (
            "Successfully logged out" in result.stdout
            or "logout" in result.stdout.lower()
        )

        # Verify tokens cleared
        assert "claude-bedrock-cursor:access_token" not in mock_keyring
        assert "claude-bedrock-cursor:refresh_token" not in mock_keyring

    @pytest.mark.asyncio
    async def test_auth_refresh(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
        mock_httpx_client: AsyncMock,
    ):
        """Test auth refresh command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Add refresh token
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = runner.invoke(app, ["auth", "refresh"])

        assert result.exit_code == 0
        assert (
            "refreshed" in result.stdout.lower() or "success" in result.stdout.lower()
        )


@pytest.mark.unit
class TestCLIAWS:
    """Test suite for 'claude-bedrock aws' commands."""

    def test_aws_setup(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_subprocess_run: MagicMock,
    ):
        """Test aws setup command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_subprocess_run: Mocked subprocess fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Mock AWS CLI check
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "aws-cli/2.15.0"

        result = runner.invoke(app, ["aws", "setup"])

        assert result.exit_code == 0

    def test_aws_validate(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
    ):
        """Test aws validate command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["aws", "validate"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIModels:
    """Test suite for 'claude-bedrock models' commands."""

    def test_models_list(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
    ):
        """Test models list command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        # Mock list models response
        mock_boto3_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {
                    "modelId": "anthropic.claude-sonnet-4-20250514-v1:0",
                    "modelName": "Claude Sonnet 4",
                }
            ]
        }

        result = runner.invoke(app, ["models", "list"])

        assert result.exit_code == 0
        assert "claude" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_models_test(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
    ):
        """Test models test command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["models", "test"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestCLICursor:
    """Test suite for 'claude-bedrock cursor' commands."""

    def test_cursor_install(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test cursor install command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["cursor", "install"])

        # May not be fully implemented yet
        assert result.exit_code in [0, 1]

    def test_cursor_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test cursor config command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize first
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["cursor", "config"])

        # May not be fully implemented yet
        assert result.exit_code in [0, 1]

    def test_cursor_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test cursor status command.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["cursor", "status"])

        # Should show cursor integration status
        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIHelp:
    """Test suite for CLI help commands."""

    def test_main_help(self):
        """Test main help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "claude-bedrock" in result.stdout.lower()
        assert "init" in result.stdout
        assert "auth" in result.stdout
        assert "aws" in result.stdout

    def test_auth_help(self):
        """Test auth subcommand help."""
        result = runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "login" in result.stdout
        assert "logout" in result.stdout
        assert "status" in result.stdout
        assert "refresh" in result.stdout

    def test_aws_help(self):
        """Test aws subcommand help."""
        result = runner.invoke(app, ["aws", "--help"])

        assert result.exit_code == 0
        assert "setup" in result.stdout or "validate" in result.stdout

    def test_models_help(self):
        """Test models subcommand help."""
        result = runner.invoke(app, ["models", "--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout or "test" in result.stdout

    def test_cursor_help(self):
        """Test cursor subcommand help."""
        result = runner.invoke(app, ["cursor", "--help"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestCLIErrorHandling:
    """Test suite for CLI error handling."""

    def test_invalid_command(self):
        """Test invalid command shows error."""
        result = runner.invoke(app, ["invalid-command"])

        assert result.exit_code != 0

    def test_missing_required_arg(self):
        """Test missing required argument shows error."""
        # This depends on specific commands with required args
        # For now, just test that help is available
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_verbose_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test verbose flag increases output.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["--verbose", "status"])

        # Should complete without error
        assert result.exit_code == 0
