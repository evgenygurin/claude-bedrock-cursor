"""Secure token storage using system keyring."""

from typing import Optional

import keyring
import keyring.errors

from claude_bedrock_cursor.utils.errors import AuthenticationError


class SecureTokenStorage:
    """System keyring integration for encrypted token storage.

    Uses OS-level encryption:
    - macOS: Keychain
    - Windows: Credential Manager
    - Linux: Secret Service API / kwallet / gnome-keyring

    Example:
        >>> storage = SecureTokenStorage()
        >>> storage.store_token("access_token", "secret_value")
        >>> token = storage.get_token("access_token")
        >>> print(token)
        'secret_value'
        >>> storage.delete_token("access_token")
    """

    SERVICE_NAME = "claude-bedrock-cursor"

    def store_token(self, token_type: str, token: str) -> None:
        """Store token in system keyring (encrypted).

        Args:
            token_type: Type of token (access_token, refresh_token, oauth_token)
            token: Token value to store

        Raises:
            AuthenticationError: If storage fails

        Example:
            >>> storage = SecureTokenStorage()
            >>> storage.store_token("access_token", "my_secret_token")
        """
        try:
            keyring.set_password(self.SERVICE_NAME, token_type, token)
        except keyring.errors.KeyringError as e:
            raise AuthenticationError(
                f"Failed to store token in keyring: {e}"
            ) from e

    def get_token(self, token_type: str) -> Optional[str]:
        """Retrieve token from keyring.

        Args:
            token_type: Type of token to retrieve

        Returns:
            str: Token value if found, None otherwise

        Raises:
            AuthenticationError: If retrieval fails

        Example:
            >>> storage = SecureTokenStorage()
            >>> token = storage.get_token("access_token")
            >>> if token:
            ...     print("Token found!")
        """
        try:
            return keyring.get_password(self.SERVICE_NAME, token_type)
        except keyring.errors.KeyringError as e:
            raise AuthenticationError(
                f"Failed to retrieve token from keyring: {e}"
            ) from e

    def delete_token(self, token_type: str) -> None:
        """Remove token from keyring.

        Args:
            token_type: Type of token to remove

        Example:
            >>> storage = SecureTokenStorage()
            >>> storage.delete_token("access_token")
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, token_type)
        except keyring.errors.PasswordDeleteError:
            # Token doesn't exist, nothing to delete
            pass
        except keyring.errors.KeyringError as e:
            raise AuthenticationError(
                f"Failed to delete token from keyring: {e}"
            ) from e

    def clear_all(self) -> None:
        """Clear all stored tokens.

        Example:
            >>> storage = SecureTokenStorage()
            >>> storage.clear_all()
        """
        self.delete_token("access_token")
        self.delete_token("refresh_token")
        self.delete_token("oauth_token")

    def has_token(self, token_type: str) -> bool:
        """Check if token exists in keyring.

        Args:
            token_type: Type of token to check

        Returns:
            bool: True if token exists, False otherwise

        Example:
            >>> storage = SecureTokenStorage()
            >>> if storage.has_token("access_token"):
            ...     print("Already authenticated!")
        """
        return self.get_token(token_type) is not None
