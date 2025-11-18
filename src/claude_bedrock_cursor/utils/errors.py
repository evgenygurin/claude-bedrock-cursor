"""Custom exception classes for claude-bedrock-cursor."""


class ClaudeBedrock Error(Exception):
    """Base exception for all claude-bedrock-cursor errors."""

    pass


class ConfigError(ClaudeBedrock Error):
    """Configuration-related errors."""

    pass


class AuthenticationError(ClaudeBedrock Error):
    """Authentication-related errors."""

    pass


class NotAuthenticatedError(AuthenticationError):
    """User is not authenticated."""

    pass


class TokenRefreshError(AuthenticationError):
    """Failed to refresh access token."""

    pass


class BedrockError(ClaudeBedrock Error):
    """AWS Bedrock-related errors."""

    pass


class BedrockConnectionError(BedrockError):
    """Failed to connect to AWS Bedrock."""

    pass


class BedrockThrottlingError(BedrockError):
    """AWS Bedrock throttling error."""

    pass


class BedrockValidationError(BedrockError):
    """Invalid request to AWS Bedrock."""

    pass


class CursorIntegrationError(ClaudeBedrock Error):
    """Cursor IDE integration errors."""

    pass


class IAMPolicyError(ClaudeBedrock Error):
    """IAM policy-related errors."""

    pass
