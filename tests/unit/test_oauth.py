"""Unit tests for OAuth authentication manager."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_bedrock_cursor.auth.oauth import OAuthManager, TokenPair
from claude_bedrock_cursor.utils.errors import (
    AuthenticationError,
    NotAuthenticatedError,
    TokenRefreshError,
)


@pytest.mark.unit
class TestTokenPair:
    """Test suite for TokenPair class."""

    def test_token_pair_creation(
        self, sample_access_token: str, sample_refresh_token: str
    ):
        """Test creating TokenPair instance.

        Args:
            sample_access_token: Sample access token fixture
            sample_refresh_token: Sample refresh token fixture
        """
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        pair = TokenPair(
            access_token=sample_access_token,
            refresh_token=sample_refresh_token,
            expires_at=expires_at,
        )

        assert pair.access_token == sample_access_token
        assert pair.refresh_token == sample_refresh_token
        assert pair.expires_at == expires_at

    def test_token_pair_is_expired(self):
        """Test checking if token pair is expired."""
        # Not expired (5 minutes from now)
        future = datetime.now(UTC) + timedelta(minutes=5)
        pair = TokenPair(access_token="test", refresh_token="test", expires_at=future)
        assert not pair.is_expired()

        # Expired (5 minutes ago)
        past = datetime.now(UTC) - timedelta(minutes=5)
        pair = TokenPair(access_token="test", refresh_token="test", expires_at=past)
        assert pair.is_expired()

    def test_token_pair_needs_refresh(self):
        """Test checking if token needs refresh (within 1 minute of expiry)."""
        # Doesn't need refresh (5 minutes remaining)
        future = datetime.now(UTC) + timedelta(minutes=5)
        pair = TokenPair(access_token="test", refresh_token="test", expires_at=future)
        assert not pair.needs_refresh()

        # Needs refresh (30 seconds remaining)
        soon = datetime.now(UTC) + timedelta(seconds=30)
        pair = TokenPair(access_token="test", refresh_token="test", expires_at=soon)
        assert pair.needs_refresh()

        # Already expired
        past = datetime.now(UTC) - timedelta(minutes=1)
        pair = TokenPair(access_token="test", refresh_token="test", expires_at=past)
        assert pair.needs_refresh()


@pytest.mark.unit
class TestOAuthManager:
    """Test suite for OAuthManager class."""

    @pytest.mark.asyncio
    async def test_get_oauth_token_from_claude_cli(
        self, mock_subprocess_run: MagicMock, mock_keyring: dict[str, str]
    ):
        """Test getting OAuth token from Claude CLI.

        Args:
            mock_subprocess_run: Mocked subprocess.run fixture
            mock_keyring: Mocked keyring fixture
        """
        manager = OAuthManager()

        token = await manager._get_oauth_token_from_claude_cli()

        assert token == "test_oauth_token_from_claude_setup"
        mock_subprocess_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_oauth_token_cli_failure(
        self, mock_subprocess_run: MagicMock, mock_keyring: dict[str, str]
    ):
        """Test OAuth token retrieval fails when CLI command fails.

        Args:
            mock_subprocess_run: Mocked subprocess.run fixture
            mock_keyring: Mocked keyring fixture
        """
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stderr = "Command failed"

        manager = OAuthManager()

        with pytest.raises(AuthenticationError, match="Failed to get OAuth token"):
            await manager._get_oauth_token_from_claude_cli()

    @pytest.mark.asyncio
    async def test_exchange_oauth_token_for_tokens(
        self, mock_httpx_client: AsyncMock, mock_keyring: dict[str, str]
    ):
        """Test exchanging OAuth token for access + refresh tokens.

        Args:
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
        """
        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair = await manager._exchange_oauth_token("test_oauth_token")

        assert pair.access_token == "test_access_token"
        assert pair.refresh_token == "test_refresh_token"
        assert not pair.is_expired()

    @pytest.mark.asyncio
    async def test_exchange_oauth_token_failure(
        self, mock_httpx_client: AsyncMock, mock_keyring: dict[str, str]
    ):
        """Test OAuth exchange fails with invalid response.

        Args:
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
        """
        mock_httpx_client.post.return_value.status_code = 401
        mock_httpx_client.post.return_value.json.return_value = {
            "error": "invalid_token"
        }

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with pytest.raises(
                AuthenticationError, match="Failed to exchange OAuth token"
            ):
                await manager._exchange_oauth_token("invalid_oauth_token")

    @pytest.mark.asyncio
    async def test_login_flow(
        self,
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
        mock_keyring: dict[str, str],
    ):
        """Test complete login flow.

        Args:
            mock_subprocess_run: Mocked subprocess.run fixture
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
        """
        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair = await manager.login()

        assert pair.access_token == "test_access_token"
        assert pair.refresh_token == "test_refresh_token"

        # Verify tokens were stored
        assert mock_keyring["claude-bedrock-cursor:access_token"] == "test_access_token"
        assert (
            mock_keyring["claude-bedrock-cursor:refresh_token"] == "test_refresh_token"
        )

    @pytest.mark.asyncio
    async def test_refresh_access_token(
        self, mock_httpx_client: AsyncMock, mock_keyring: dict[str, str]
    ):
        """Test refresh token rotation.

        Args:
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
        """
        # Setup: store initial refresh token
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "old_refresh_token"

        # Mock refresh response with NEW refresh token
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",  # Important: rotated!
            "expires_in": 300,
        }

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair = await manager.refresh_access_token()

        # Verify new tokens
        assert pair.access_token == "new_access_token"
        assert pair.refresh_token == "new_refresh_token"

        # Verify tokens were updated in storage
        assert mock_keyring["claude-bedrock-cursor:access_token"] == "new_access_token"
        assert (
            mock_keyring["claude-bedrock-cursor:refresh_token"] == "new_refresh_token"
        )

    @pytest.mark.asyncio
    async def test_refresh_token_not_found(self, mock_keyring: dict[str, str]):
        """Test refresh fails when no refresh token stored.

        Args:
            mock_keyring: Mocked keyring fixture
        """
        manager = OAuthManager()

        with pytest.raises(NotAuthenticatedError, match="No refresh token found"):
            await manager.refresh_access_token()

    @pytest.mark.asyncio
    async def test_refresh_token_failure(
        self, mock_httpx_client: AsyncMock, mock_keyring: dict[str, str]
    ):
        """Test refresh fails with invalid refresh token.

        Args:
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
        """
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "invalid_refresh"
        mock_httpx_client.post.return_value.status_code = 401

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with pytest.raises(
                TokenRefreshError, match="Failed to refresh access token"
            ):
                await manager.refresh_access_token()

    @pytest.mark.asyncio
    async def test_logout(self, mock_keyring: dict[str, str]):
        """Test logout clears all tokens.

        Args:
            mock_keyring: Mocked keyring fixture
        """
        # Setup: store tokens
        mock_keyring["claude-bedrock-cursor:access_token"] = "test_access"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        manager = OAuthManager()
        await manager.logout()

        # Verify tokens cleared
        assert "claude-bedrock-cursor:access_token" not in mock_keyring
        assert "claude-bedrock-cursor:refresh_token" not in mock_keyring

    def test_is_authenticated(self, mock_keyring: dict[str, str]):
        """Test checking authentication status.

        Args:
            mock_keyring: Mocked keyring fixture
        """
        manager = OAuthManager()

        # Initially not authenticated
        assert not manager.is_authenticated()

        # Store tokens
        mock_keyring["claude-bedrock-cursor:access_token"] = "test_access"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        # Now authenticated
        assert manager.is_authenticated()

    @pytest.mark.asyncio
    async def test_get_valid_access_token_cached(
        self, mock_keyring: dict[str, str], sample_access_token: str
    ):
        """Test getting valid cached access token.

        Args:
            mock_keyring: Mocked keyring fixture
            sample_access_token: Sample access token fixture
        """
        # Store valid token with future expiry
        mock_keyring["claude-bedrock-cursor:access_token"] = sample_access_token
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        # Store expiry timestamp (5 minutes from now)
        future_timestamp = int(
            (datetime.now(UTC) + timedelta(minutes=5)).timestamp()
        )
        mock_keyring["claude-bedrock-cursor:access_token_expires_at"] = str(
            future_timestamp
        )

        manager = OAuthManager()
        token = await manager.get_valid_access_token()

        assert token == sample_access_token

    @pytest.mark.asyncio
    async def test_get_valid_access_token_auto_refresh(
        self,
        mock_httpx_client: AsyncMock,
        mock_keyring: dict[str, str],
        sample_access_token: str,
    ):
        """Test auto-refresh when access token expired.

        Args:
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
            sample_access_token: Sample access token fixture
        """
        # Store expired token
        mock_keyring["claude-bedrock-cursor:access_token"] = "expired_token"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        # Store past expiry timestamp
        past_timestamp = int(
            (datetime.now(UTC) - timedelta(minutes=5)).timestamp()
        )
        mock_keyring["claude-bedrock-cursor:access_token_expires_at"] = str(
            past_timestamp
        )

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            token = await manager.get_valid_access_token()

        # Should return refreshed token
        assert token == "test_access_token"

    @pytest.mark.asyncio
    async def test_token_rotation_security(
        self, mock_httpx_client: AsyncMock, mock_keyring: dict[str, str]
    ):
        """Test that refresh token is rotated on every use.

        Args:
            mock_httpx_client: Mocked httpx client fixture
            mock_keyring: Mocked keyring fixture
        """
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "refresh_v1"

        # First refresh
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "access_v2",
            "refresh_token": "refresh_v2",
            "expires_in": 300,
        }

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair1 = await manager.refresh_access_token()

        assert pair1.refresh_token == "refresh_v2"

        # Second refresh should use new refresh token
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "access_v3",
            "refresh_token": "refresh_v3",
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair2 = await manager.refresh_access_token()

        assert pair2.refresh_token == "refresh_v3"

        # Verify tokens are different (rotation occurred)
        assert pair1.refresh_token != pair2.refresh_token

    def test_token_expiry_calculation(self):
        """Test token expiry timestamp calculation."""
        manager = OAuthManager()

        # 300 seconds (5 minutes)
        expires_at = manager._calculate_expiry(300)

        # Should be approximately 5 minutes from now
        expected = datetime.now(UTC) + timedelta(seconds=300)
        diff = abs((expires_at - expected).total_seconds())

        assert diff < 2  # Allow 2 seconds tolerance
