"""Unit tests for secure token storage."""

import pytest

from claude_bedrock_cursor.auth.storage import SecureTokenStorage


@pytest.mark.unit
class TestSecureTokenStorage:
    """Test suite for SecureTokenStorage class."""

    def test_store_and_retrieve_token(self, mock_keyring: dict[str, str]):
        """Test storing and retrieving tokens.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Store token
        storage.store_token("access_token", "test_access_123")

        # Retrieve token
        token = storage.get_token("access_token")
        assert token == "test_access_123"

    def test_store_multiple_tokens(self, mock_keyring: dict[str, str]):
        """Test storing multiple token types.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Store multiple tokens
        storage.store_token("access_token", "access_123")
        storage.store_token("refresh_token", "refresh_456")
        storage.store_token("oauth_token", "oauth_789")

        # Verify all stored correctly
        assert storage.get_token("access_token") == "access_123"
        assert storage.get_token("refresh_token") == "refresh_456"
        assert storage.get_token("oauth_token") == "oauth_789"

    def test_get_nonexistent_token(self, mock_keyring: dict[str, str]):
        """Test retrieving non-existent token returns None.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        token = storage.get_token("nonexistent_token")
        assert token is None

    def test_delete_token(self, mock_keyring: dict[str, str]):
        """Test deleting stored token.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Store token
        storage.store_token("temp_token", "temp_123")
        assert storage.get_token("temp_token") == "temp_123"

        # Delete token
        storage.delete_token("temp_token")
        assert storage.get_token("temp_token") is None

    def test_delete_nonexistent_token(self, mock_keyring: dict[str, str]):
        """Test deleting non-existent token doesn't raise error.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Should not raise error
        storage.delete_token("nonexistent_token")

    def test_clear_all_tokens(self, mock_keyring: dict[str, str]):
        """Test clearing all tokens.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Store multiple tokens
        storage.store_token("access_token", "access_123")
        storage.store_token("refresh_token", "refresh_456")

        # Clear all
        storage.clear_all()

        # Verify all cleared
        assert storage.get_token("access_token") is None
        assert storage.get_token("refresh_token") is None

    def test_has_token(self, mock_keyring: dict[str, str]):
        """Test checking if token exists.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Initially no token
        assert not storage.has_token("access_token")

        # Store token
        storage.store_token("access_token", "test_123")

        # Now token exists
        assert storage.has_token("access_token")

    def test_update_token(self, mock_keyring: dict[str, str]):
        """Test updating existing token.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Store initial token
        storage.store_token("access_token", "old_token")
        assert storage.get_token("access_token") == "old_token"

        # Update token
        storage.store_token("access_token", "new_token")
        assert storage.get_token("access_token") == "new_token"

    def test_token_type_validation(self, mock_keyring: dict[str, str]):
        """Test token type must be non-empty string.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        with pytest.raises(ValueError, match="Token type cannot be empty"):
            storage.store_token("", "test_token")

    def test_token_value_validation(self, mock_keyring: dict[str, str]):
        """Test token value must be non-empty string.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        with pytest.raises(ValueError, match="Token value cannot be empty"):
            storage.store_token("access_token", "")

    def test_service_name_consistency(self, mock_keyring: dict[str, str]):
        """Test all tokens use same service name.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        storage.store_token("token1", "value1")
        storage.store_token("token2", "value2")

        # Both should be under same service
        assert "claude-bedrock-cursor:token1" in mock_keyring
        assert "claude-bedrock-cursor:token2" in mock_keyring

    def test_multiple_token_types(self, mock_keyring: dict[str, str]):
        """Test storing and retrieving multiple token types.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Store different token types
        storage.store_token("access_token", "value1")
        storage.store_token("refresh_token", "value2")
        storage.store_token("oauth_token", "value3")

        # Verify all can be retrieved
        assert storage.has_token("access_token")
        assert storage.has_token("refresh_token")
        assert storage.has_token("oauth_token")
        assert storage.get_token("access_token") == "value1"
        assert storage.get_token("refresh_token") == "value2"
        assert storage.get_token("oauth_token") == "value3"

    def test_token_isolation(self, mock_keyring: dict[str, str]):
        """Test tokens are isolated between instances.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage1 = SecureTokenStorage()
        storage2 = SecureTokenStorage()

        # Store in first instance
        storage1.store_token("shared_token", "value1")

        # Should be accessible from second instance (same service)
        assert storage2.get_token("shared_token") == "value1"

    def test_special_characters_in_token(self, mock_keyring: dict[str, str]):
        """Test storing tokens with special characters.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        special_token = "eyJhbGci0iJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        storage.store_token("jwt_token", special_token)
        assert storage.get_token("jwt_token") == special_token

    def test_empty_storage_clear(self, mock_keyring: dict[str, str]):
        """Test clearing empty storage doesn't error.

        Args:
            mock_keyring: Mocked keyring storage fixture
        """
        storage = SecureTokenStorage()

        # Clear when empty (should not raise error)
        storage.clear_all()

        # Verify storage is still empty
        assert not storage.has_token("access_token")
        assert not storage.has_token("refresh_token")
        assert not storage.has_token("oauth_token")
