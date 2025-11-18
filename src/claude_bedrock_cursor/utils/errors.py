"""Custom exception classes for claude-bedrock-cursor."""


class ClaudeBedrockError(Exception):
    """Base exception for all claude-bedrock-cursor errors."""

    pass


class ConfigError(ClaudeBedrockError):
    """Configuration-related errors."""

    pass


class AuthenticationError(ClaudeBedrockError):
    """Authentication-related errors."""

    pass


class NotAuthenticatedError(AuthenticationError):
    """User is not authenticated."""

    pass


class TokenRefreshError(AuthenticationError):
    """Failed to refresh access token."""

    pass


class BedrockError(ClaudeBedrockError):
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


class CursorIntegrationError(ClaudeBedrockError):
    """Cursor IDE integration errors."""

    pass


class IAMPolicyError(ClaudeBedrockError):
    """IAM policy-related errors."""

    pass
