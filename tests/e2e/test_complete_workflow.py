"""End-to-end tests for complete workflows."""

from datetime import UTC
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from claude_bedrock_cursor.auth.oauth import OAuthManager
from claude_bedrock_cursor.bedrock.client import BedrockClient
from claude_bedrock_cursor.cli import app
from claude_bedrock_cursor.config import Config

runner = CliRunner()


@pytest.mark.e2e
class TestCompleteSetupWorkflow:
    """End-to-end tests for initial setup workflow."""

    @pytest.mark.asyncio
    async def test_fresh_install_to_first_query(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
        mock_boto3_client: MagicMock,
    ):
        """Test complete workflow from fresh install to first query.

        Workflow:
        1. Initialize configuration
        2. Login with OAuth
        3. Validate AWS setup
        4. Make first Bedrock query

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
            mock_subprocess_run: Mocked subprocess fixture
            mock_httpx_client: Mocked httpx client fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Step 1: Initialize configuration
        result = runner.invoke(app, ["init", "--region", "us-east-1"])
        assert result.exit_code == 0
        assert "initialized" in result.stdout.lower()

        # Verify config file created
        config_file = tmp_path / ".claude-bedrock" / "config.toml"
        assert config_file.exists()

        # Step 2: Login with OAuth
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0

        # Verify authentication
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0

        # Step 3: Validate AWS setup
        result = runner.invoke(app, ["aws", "validate"])
        assert result.exit_code == 0

        # Step 4: Make first Bedrock query
        config = Config.from_toml(config_file)
        client = BedrockClient(config=config)

        chunks = []
        async for chunk in client.invoke_streaming("Hello, Claude!"):
            chunks.append(chunk)

        assert len(chunks) > 0

    def test_initialization_with_custom_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test initialization with custom configuration.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize with custom settings
        result = runner.invoke(
            app,
            [
                "init",
                "--region",
                "eu-west-1",
                "--model",
                "anthropic.claude-3-opus-20240229",
            ],
        )

        assert result.exit_code == 0

        # Verify custom config
        config_file = tmp_path / ".claude-bedrock" / "config.toml"
        config = Config.from_toml(config_file)

        assert config.aws_region == "eu-west-1"
        assert config.bedrock_model_id == "anthropic.claude-3-opus-20240229"


@pytest.mark.e2e
class TestAuthenticationWorkflow:
    """End-to-end tests for authentication workflows."""

    @pytest.mark.asyncio
    async def test_login_refresh_logout_cycle(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
    ):
        """Test complete authentication cycle.

        Workflow:
        1. Login
        2. Check status (authenticated)
        3. Refresh token
        4. Check status (still authenticated)
        5. Logout
        6. Check status (not authenticated)

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

        # Step 1: Login
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = runner.invoke(app, ["auth", "login"])

        assert result.exit_code == 0

        # Step 2: Check authenticated
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "authenticated" in result.stdout.lower()

        # Step 3: Refresh token
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "refreshed_access",
            "refresh_token": "refreshed_refresh",
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = runner.invoke(app, ["auth", "refresh"])

        assert result.exit_code == 0

        # Step 4: Still authenticated
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0

        # Step 5: Logout
        result = runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0

        # Step 6: Not authenticated anymore
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "not authenticated" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_automatic_token_refresh_on_expiry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
        mock_httpx_client: AsyncMock,
    ):
        """Test automatic token refresh when making requests.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        from datetime import datetime, timedelta

        monkeypatch.setenv("HOME", str(tmp_path))

        # Setup expired token
        mock_keyring["claude-bedrock-cursor:access_token"] = "expired_token"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "valid_refresh"

        # Set expiry to past
        past_timestamp = int(
            (datetime.now(UTC) - timedelta(minutes=5)).timestamp()
        )
        mock_keyring["claude-bedrock-cursor:access_token_expires_at"] = str(
            past_timestamp
        )

        # Setup auto-refresh
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 300,
        }

        manager = OAuthManager()

        # Should auto-refresh
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            token = await manager.get_valid_access_token()

        assert token == "new_access_token"


@pytest.mark.e2e
class TestBedrockQueryWorkflow:
    """End-to-end tests for Bedrock query workflows."""

    @pytest.mark.asyncio
    async def test_simple_query_workflow(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
        sample_config: Config,
    ):
        """Test simple query workflow.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        client = BedrockClient(config=sample_config)

        # Make query
        response = []
        async for chunk in client.invoke_streaming("What is Python?"):
            response.append(chunk)

        # Verify got response
        assert len(response) > 0
        full_response = "".join(response)
        assert isinstance(full_response, str)

    @pytest.mark.asyncio
    async def test_query_with_prompt_caching(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
    ):
        """Test query workflow with prompt caching enabled.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        # Initialize with caching enabled
        runner.invoke(app, ["init"])

        config_file = tmp_path / ".claude-bedrock" / "config.toml"
        config = Config.from_toml(config_file)
        config.enable_prompt_caching = True

        client = BedrockClient(config=config)

        system_context = "You are a helpful Python programming assistant."

        # First query (establishes cache)
        response1 = []
        async for chunk in client.invoke_streaming(
            "Explain decorators", system_context=system_context
        ):
            response1.append(chunk)

        # Second query (uses cache)
        response2 = []
        async for chunk in client.invoke_streaming(
            "Explain generators", system_context=system_context
        ):
            response2.append(chunk)

        # Both should succeed
        assert len(response1) > 0
        assert len(response2) > 0

    @pytest.mark.asyncio
    async def test_multiple_concurrent_queries(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
        sample_config: Config,
    ):
        """Test handling multiple concurrent queries.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        import asyncio

        monkeypatch.setenv("HOME", str(tmp_path))

        client = BedrockClient(config=sample_config)

        async def make_query(prompt: str):
            chunks = []
            async for chunk in client.invoke_streaming(prompt):
                chunks.append(chunk)
            return "".join(chunks)

        # Make 5 concurrent queries
        prompts = [f"Query {i}" for i in range(5)]
        results = await asyncio.gather(*[make_query(p) for p in prompts])

        # All should succeed
        assert len(results) == 5
        assert all(isinstance(r, str) for r in results)


@pytest.mark.e2e
class TestErrorRecoveryWorkflow:
    """End-to-end tests for error recovery workflows."""

    @pytest.mark.asyncio
    async def test_recovery_from_throttling(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
        sample_config: Config,
    ):
        """Test automatic recovery from throttling errors.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        from botocore.exceptions import ClientError

        monkeypatch.setenv("HOME", str(tmp_path))

        # Simulate throttling on first call, success on retry
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ClientError(
                    error_response={"Error": {"Code": "ThrottlingException"}},
                    operation_name="InvokeModel",
                )
            return mock_boto3_client.invoke_model_with_response_stream.return_value

        mock_boto3_client.invoke_model_with_response_stream.side_effect = side_effect

        client = BedrockClient(config=sample_config)

        # Should succeed after retry
        chunks = []
        async for chunk in client.invoke_streaming("test query"):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_recovery_from_token_expiry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_keyring: dict[str, str],
        mock_httpx_client: AsyncMock,
        mock_boto3_client: MagicMock,
    ):
        """Test automatic recovery from expired tokens.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        from datetime import datetime, timedelta

        monkeypatch.setenv("HOME", str(tmp_path))

        # Setup expired token
        mock_keyring["claude-bedrock-cursor:access_token"] = "expired_token"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "valid_refresh"

        past_timestamp = int(
            (datetime.now(UTC) - timedelta(minutes=5)).timestamp()
        )
        mock_keyring["claude-bedrock-cursor:access_token_expires_at"] = str(
            past_timestamp
        )

        # Setup auto-refresh
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 300,
        }

        manager = OAuthManager()

        # Should auto-refresh and succeed
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            token = await manager.get_valid_access_token()

        assert token == "new_access_token"


@pytest.mark.e2e
@pytest.mark.slow
class TestProductionScenarios:
    """End-to-end tests for production scenarios."""

    @pytest.mark.asyncio
    async def test_long_running_session(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
        sample_config: Config,
    ):
        """Test long-running session with multiple queries.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        monkeypatch.setenv("HOME", str(tmp_path))

        client = BedrockClient(config=sample_config)

        # Simulate 20 queries in a session
        for i in range(20):
            chunks = []
            async for chunk in client.invoke_streaming(f"Query {i}"):
                chunks.append(chunk)

            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_metrics_tracking_across_session(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_boto3_client: MagicMock,
        sample_config: Config,
    ):
        """Test metrics tracking across multiple queries.

        Args:
            tmp_path: Pytest temporary directory
            monkeypatch: Pytest monkeypatch fixture
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        from claude_bedrock_cursor.bedrock.client import BedrockClientWithMetrics

        monkeypatch.setenv("HOME", str(tmp_path))

        client = BedrockClientWithMetrics(config=sample_config)

        # Make 10 queries
        for i in range(10):
            async for _ in client.invoke_streaming(f"Query {i}"):
                pass

        # Verify metrics
        metrics = client.get_metrics()
        assert metrics["total_requests"] == 10
        assert metrics["successful_requests"] == 10
        assert metrics["failed_requests"] == 0
