"""Claude Bedrock Cursor Integration.

Production-ready integration of Claude Code with Cursor IDE through AWS Bedrock.

Features:
    - OAuth2 authentication with Claude MAX subscription
    - AWS Bedrock streaming responses
    - Prompt caching for cost optimization
    - Secure credential storage
    - Comprehensive testing and CI/CD

Example:
    >>> from claude_bedrock_cursor import BedrockClient
    >>> client = BedrockClient()
    >>> async for chunk in client.invoke_streaming("Hello!"):
    ...     print(chunk, end="", flush=True)
"""

__version__ = "1.0.0"
__author__ = "Claude Code Team"
__license__ = "MIT"

from claude_bedrock_cursor.auth.oauth import OAuthManager
from claude_bedrock_cursor.bedrock.client import BedrockClient
from claude_bedrock_cursor.config import Config

__all__ = [
    "BedrockClient",
    "Config",
    "OAuthManager",
    "__version__",
]
