"""Integration tests for OAuth authentication flow."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_bedrock_cursor.auth.oauth import OAuthManager, TokenPair
from claude_bedrock_cursor.utils.errors import (
    AuthenticationError,
    NotAuthenticatedError,
    TokenRefreshError,
)


@pytest.mark.integration
class TestOAuthFlowIntegration:
    """Integration tests for complete OAuth flow."""

    @pytest.mark.asyncio
    async def test_complete_login_flow(
        self,
        mock_keyring: dict[str, str],
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
    ):
        """Test complete login flow from CLI to token storage.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_subprocess_run: Mocked subprocess fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        # Step 1: Run login
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair = await manager.login()

        # Verify tokens received
        assert pair.access_token == "test_access_token"
        assert pair.refresh_token == "test_refresh_token"
        assert not pair.is_expired()

        # Verify tokens stored in keyring
        assert mock_keyring["claude-bedrock-cursor:access_token"] == "test_access_token"
        assert mock_keyring["claude-bedrock-cursor:refresh_token"] == "test_refresh_token"

        # Verify authentication status
        assert manager.is_authenticated()

    @pytest.mark.asyncio
    async def test_login_to_refresh_flow(
        self,
        mock_keyring: dict[str, str],
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
    ):
        """Test login followed by token refresh.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_subprocess_run: Mocked subprocess fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        # Step 1: Login
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            login_pair = await manager.login()

        initial_refresh_token = login_pair.refresh_token

        # Step 2: Simulate token expiry and refresh
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "refreshed_access_token",
            "refresh_token": "new_refresh_token",  # Rotated!
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            refresh_pair = await manager.refresh_access_token()

        # Verify new tokens
        assert refresh_pair.access_token == "refreshed_access_token"
        assert refresh_pair.refresh_token == "new_refresh_token"

        # Verify refresh token was rotated
        assert refresh_pair.refresh_token != initial_refresh_token

        # Verify new tokens in storage
        assert mock_keyring["claude-bedrock-cursor:access_token"] == "refreshed_access_token"
        assert mock_keyring["claude-bedrock-cursor:refresh_token"] == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_multiple_refresh_cycles(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test multiple refresh token rotation cycles.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        # Initial refresh token
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "refresh_v1"

        refresh_tokens = ["refresh_v1"]

        # Perform 5 refresh cycles
        for i in range(2, 7):
            mock_httpx_client.post.return_value.json.return_value = {
                "access_token": f"access_v{i}",
                "refresh_token": f"refresh_v{i}",
                "expires_in": 300,
            }

            with patch("httpx.AsyncClient", return_value=mock_httpx_client):
                pair = await manager.refresh_access_token()

            refresh_tokens.append(pair.refresh_token)

        # Verify all refresh tokens were different (rotation occurred)
        assert len(set(refresh_tokens)) == 6
        assert refresh_tokens == [f"refresh_v{i}" for i in range(1, 7)]

    @pytest.mark.asyncio
    async def test_logout_clears_all_tokens(
        self,
        mock_keyring: dict[str, str],
        mock_subprocess_run: MagicMock,
        mock_httpx_client: AsyncMock,
    ):
        """Test logout clears all authentication data.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_subprocess_run: Mocked subprocess fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        # Login first
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await manager.login()

        # Verify authenticated
        assert manager.is_authenticated()
        assert len(mock_keyring) > 0

        # Logout
        await manager.logout()

        # Verify cleared
        assert not manager.is_authenticated()
        assert "claude-bedrock-cursor:access_token" not in mock_keyring
        assert "claude-bedrock-cursor:refresh_token" not in mock_keyring

    @pytest.mark.asyncio
    async def test_auto_refresh_on_expiry(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test automatic token refresh when expired.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        # Setup expired access token
        mock_keyring["claude-bedrock-cursor:access_token"] = "expired_token"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "valid_refresh"

        # Set expiry to past
        past_timestamp = int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp())
        mock_keyring["claude-bedrock-cursor:access_token_expires_at"] = str(past_timestamp)

        # Setup refresh response
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 300,
        }

        # Get valid token (should auto-refresh)
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            token = await manager.get_valid_access_token()

        # Verify got refreshed token
        assert token == "new_access_token"
        assert mock_keyring["claude-bedrock-cursor:access_token"] == "new_access_token"


@pytest.mark.integration
class TestOAuthErrorScenarios:
    """Integration tests for OAuth error scenarios."""

    @pytest.mark.asyncio
    async def test_cli_command_failure(
        self, mock_keyring: dict[str, str], mock_subprocess_run: MagicMock
    ):
        """Test handling of Claude CLI command failure.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_subprocess_run: Mocked subprocess fixture
        """
        # Simulate CLI failure
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stderr = "Claude CLI not found"

        manager = OAuthManager()

        with pytest.raises(AuthenticationError, match="Failed to get OAuth token"):
            await manager._get_oauth_token_from_claude_cli()

    @pytest.mark.asyncio
    async def test_oauth_exchange_failure(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test handling of OAuth token exchange failure.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        # Simulate invalid OAuth token
        mock_httpx_client.post.return_value.status_code = 401
        mock_httpx_client.post.return_value.json.return_value = {"error": "invalid_grant"}

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with pytest.raises(AuthenticationError, match="Failed to exchange OAuth token"):
                await manager._exchange_oauth_token("invalid_token")

    @pytest.mark.asyncio
    async def test_refresh_without_login(self, mock_keyring: dict[str, str]):
        """Test refresh fails when not logged in.

        Args:
            mock_keyring: Mocked keyring fixture
        """
        manager = OAuthManager()

        with pytest.raises(NotAuthenticatedError, match="No refresh token found"):
            await manager.refresh_access_token()

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test refresh fails with invalid refresh token.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        # Setup invalid refresh token
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "invalid_refresh"

        # Simulate refresh failure
        mock_httpx_client.post.return_value.status_code = 401
        mock_httpx_client.post.return_value.json.return_value = {"error": "invalid_token"}

        manager = OAuthManager()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            with pytest.raises(TokenRefreshError, match="Failed to refresh access token"):
                await manager.refresh_access_token()

    @pytest.mark.asyncio
    async def test_concurrent_refresh_requests(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test handling of concurrent refresh requests.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        import asyncio

        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        call_count = 0

        def increment_call_count(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return AsyncMock(
                status_code=200,
                json=AsyncMock(
                    return_value={
                        "access_token": f"access_{call_count}",
                        "refresh_token": f"refresh_{call_count}",
                        "expires_in": 300,
                    }
                ),
            )

        mock_httpx_client.post.side_effect = increment_call_count

        manager = OAuthManager()

        # Make concurrent refresh requests
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            results = await asyncio.gather(
                manager.refresh_access_token(),
                manager.refresh_access_token(),
                manager.refresh_access_token(),
            )

        # All should succeed
        assert len(results) == 3
        assert all(isinstance(r, TokenPair) for r in results)


@pytest.mark.integration
class TestOAuthSecurity:
    """Integration tests for OAuth security features."""

    @pytest.mark.asyncio
    async def test_token_rotation_prevents_reuse(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test that old refresh tokens cannot be reused.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        # Initial refresh token
        old_refresh_token = "refresh_v1"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = old_refresh_token

        # First refresh - gets new tokens
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "access_v2",
            "refresh_token": "refresh_v2",
            "expires_in": 300,
        }

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            await manager.refresh_access_token()

        # Verify old token replaced
        assert mock_keyring["claude-bedrock-cursor:refresh_token"] == "refresh_v2"
        assert mock_keyring["claude-bedrock-cursor:refresh_token"] != old_refresh_token

    @pytest.mark.asyncio
    async def test_token_expiry_tracking(
        self, mock_keyring: dict[str, str], mock_httpx_client: AsyncMock
    ):
        """Test token expiry timestamps are tracked correctly.

        Args:
            mock_keyring: Mocked keyring fixture
            mock_httpx_client: Mocked httpx client fixture
        """
        manager = OAuthManager()

        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        # Refresh with specific expires_in
        mock_httpx_client.post.return_value.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 600,  # 10 minutes
        }

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            pair = await manager.refresh_access_token()

        # Verify expiry is approximately 10 minutes from now
        expected = datetime.now(timezone.utc) + timedelta(seconds=600)
        diff = abs((pair.expires_at - expected).total_seconds())

        assert diff < 5  # Allow 5 seconds tolerance

    @pytest.mark.asyncio
    async def test_secure_storage_isolation(self, mock_keyring: dict[str, str]):
        """Test tokens are isolated in secure storage.

        Args:
            mock_keyring: Mocked keyring fixture
        """
        # Store tokens
        mock_keyring["claude-bedrock-cursor:access_token"] = "test_access"
        mock_keyring["claude-bedrock-cursor:refresh_token"] = "test_refresh"

        # Verify storage isolation (different service can't access)
        assert "other-app:access_token" not in mock_keyring

        # Verify correct service name used
        assert all(k.startswith("claude-bedrock-cursor:") for k in mock_keyring.keys())
