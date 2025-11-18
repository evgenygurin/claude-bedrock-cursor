"""OAuth2 authentication manager with refresh token rotation."""

import subprocess  # nosec B404 - Used safely to call claude CLI command
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from functools import wraps
from typing import Any

import httpx

from claude_bedrock_cursor.auth.storage import SecureTokenStorage
from claude_bedrock_cursor.utils.errors import (
    AuthenticationError,
    NotAuthenticatedError,
    TokenRefreshError,
)


@dataclass
class TokenPair:
    """Access and refresh token pair.

    Attributes:
        access_token: Short-lived access token (5 minutes)
        refresh_token: Long-lived refresh token (7 days)
        expires_at: Unix timestamp when access token expires
    """

    access_token: str
    refresh_token: str
    expires_at: int


class OAuthManager:
    """OAuth2 manager with automatic token rotation.

    Implements secure OAuth flow:
    1. Login via Claude Code MAX subscription
    2. Exchange OAuth token for access + refresh tokens
    3. Rotate refresh token on every use
    4. Store tokens securely in system keyring

    Example:
        >>> manager = OAuthManager()
        >>> await manager.login()
        >>> token = await manager.get_valid_access_token()
        >>> print(f"Access token: {token[:10]}...")
    """

    # Token lifetimes (in seconds)
    ACCESS_TOKEN_LIFETIME = 300  # 5 minutes
    REFRESH_TOKEN_LIFETIME = 604800  # 7 days

    # API endpoints (placeholder - update with actual endpoints)
    TOKEN_ENDPOINT = "https://api.anthropic.com/v1/oauth/token"  # nosec B105 - Not a password, API endpoint URL
    REVOKE_ENDPOINT = "https://api.anthropic.com/v1/oauth/revoke"

    def __init__(self) -> None:
        """Initialize OAuth manager."""
        self.storage = SecureTokenStorage()
        self.client = httpx.AsyncClient(timeout=10.0)

    async def login(self) -> TokenPair:
        """Perform OAuth login via Claude Code.

        Returns:
            TokenPair: Access and refresh tokens

        Raises:
            AuthenticationError: If login fails

        Example:
            >>> manager = OAuthManager()
            >>> tokens = await manager.login()
            >>> print("Login successful!")
        """
        # Step 1: Get OAuth token from Claude Code CLI
        oauth_token = await self._get_claude_oauth_token()

        # Step 2: Exchange OAuth token for token pair
        tokens = await self._exchange_oauth_token(oauth_token)

        # Step 3: Store tokens securely
        self.storage.store_token("access_token", tokens.access_token)
        self.storage.store_token("refresh_token", tokens.refresh_token)
        self.storage.store_token("oauth_token", oauth_token)

        return tokens

    async def refresh_access_token(self) -> TokenPair:
        """Refresh access token with rotation.

        Implements refresh token rotation:
        1. Use current refresh token
        2. Get new access token
        3. Get NEW refresh token
        4. Invalidate old refresh token
        5. Store new tokens

        Returns:
            TokenPair: New access and refresh tokens

        Raises:
            TokenRefreshError: If refresh fails
            NotAuthenticatedError: If no refresh token found

        Example:
            >>> manager = OAuthManager()
            >>> tokens = await manager.refresh_access_token()
            >>> print("Token refreshed!")
        """
        current_refresh = self.storage.get_token("refresh_token")
        if not current_refresh:
            raise NotAuthenticatedError(
                "No refresh token found. Please run: claude-bedrock auth login"
            )

        try:
            # Exchange refresh token for new token pair
            response = await self.client.post(
                self.TOKEN_ENDPOINT,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": current_refresh,
                },
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Refresh token expired or invalid
                self.storage.clear_all()
                raise NotAuthenticatedError(
                    "Refresh token expired. Please run: claude-bedrock auth login"
                ) from e
            raise TokenRefreshError(f"Token refresh failed: {e.response.text}") from e

        except httpx.HTTPError as e:
            raise TokenRefreshError(f"Token refresh failed: {e}") from e

        data = response.json()

        new_tokens = TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],  # NEW refresh token!
            expires_at=int(time.time()) + self.ACCESS_TOKEN_LIFETIME,
        )

        # Store new tokens (old refresh token is now invalid)
        self.storage.store_token("access_token", new_tokens.access_token)
        self.storage.store_token("refresh_token", new_tokens.refresh_token)

        return new_tokens

    async def get_valid_access_token(self) -> str:
        """Get valid access token, refreshing if needed.

        Returns:
            str: Valid access token

        Raises:
            NotAuthenticatedError: If not authenticated

        Example:
            >>> manager = OAuthManager()
            >>> token = await manager.get_valid_access_token()
            >>> # Use token for API calls
        """
        access_token = self.storage.get_token("access_token")

        if not access_token:
            raise NotAuthenticatedError(
                "Not authenticated. Please run: claude-bedrock auth login"
            )

        # For production: store expires_at and check if token is expired
        # For now: return token and refresh on 401 errors

        return access_token

    async def logout(self) -> None:
        """Logout and clear all tokens.

        Revokes tokens on server and clears local storage.

        Example:
            >>> manager = OAuthManager()
            >>> await manager.logout()
            >>> print("Logged out successfully!")
        """
        refresh_token = self.storage.get_token("refresh_token")

        # Revoke token on server
        if refresh_token:
            with suppress(httpx.HTTPError):
                await self.client.post(
                    self.REVOKE_ENDPOINT,
                    json={"token": refresh_token},
                    timeout=5.0,
                )
            # Server revocation failed, still clear local storage

        # Clear local token storage
        self.storage.clear_all()

    async def is_authenticated(self) -> bool:
        """Check if user is authenticated.

        Returns:
            bool: True if authenticated, False otherwise

        Example:
            >>> manager = OAuthManager()
            >>> if await manager.is_authenticated():
            ...     print("Already logged in!")
        """
        return self.storage.has_token("access_token")

    async def _get_claude_oauth_token(self) -> str:
        """Get OAuth token from Claude Code CLI.

        Returns:
            str: OAuth token

        Raises:
            AuthenticationError: If token generation fails

        Note:
            Runs `claude setup-token` command and extracts token from output.
        """
        try:
            # Run claude setup-token command
            result = subprocess.run(  # nosec B603 B607 - Safe: calling trusted claude CLI with fixed args
                ["claude", "setup-token"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise AuthenticationError(
                    f"Failed to generate OAuth token: {result.stderr}"
                )

            # Extract token from output
            # Format: "Your OAuth token: <token>"
            output = result.stdout.strip()
            if "OAuth token:" in output:
                token = output.split("OAuth token:")[-1].strip()
                return token

            raise AuthenticationError(
                f"Could not parse OAuth token from output: {output}"
            )

        except subprocess.TimeoutExpired as e:
            raise AuthenticationError("OAuth token generation timed out") from e

        except FileNotFoundError as e:
            raise AuthenticationError(
                "Claude Code CLI not found. Please install: npm install -g @anthropic-ai/claude-code"
            ) from e

    async def _exchange_oauth_token(self, oauth_token: str) -> TokenPair:
        """Exchange OAuth token for access + refresh tokens.

        Args:
            oauth_token: OAuth token from Claude Code

        Returns:
            TokenPair: Access and refresh tokens

        Raises:
            AuthenticationError: If exchange fails
        """
        try:
            response = await self.client.post(
                self.TOKEN_ENDPOINT,
                json={
                    "grant_type": "authorization_code",
                    "code": oauth_token,
                },
            )
            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            raise AuthenticationError(
                f"OAuth token exchange failed: {e.response.text}"
            ) from e

        except httpx.HTTPError as e:
            raise AuthenticationError(f"OAuth token exchange failed: {e}") from e

        data = response.json()

        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=int(time.time()) + self.ACCESS_TOKEN_LIFETIME,
        )

    async def __aenter__(self) -> "OAuthManager":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.client.aclose()


def requires_auth(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to ensure valid access token.

    Automatically refreshes expired tokens on 401 errors.

    Example:
        >>> @requires_auth
        ... async def call_api(access_token: str):
        ...     # Use access_token for API call
        ...     pass
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        oauth_manager = OAuthManager()

        try:
            # Try with current token
            access_token = await oauth_manager.get_valid_access_token()
            return await func(*args, access_token=access_token, **kwargs)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token expired - refresh and retry
                tokens = await oauth_manager.refresh_access_token()
                return await func(*args, access_token=tokens.access_token, **kwargs)
            raise

        finally:
            await oauth_manager.client.aclose()

    return wrapper
