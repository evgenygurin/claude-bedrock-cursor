"""AWS Bedrock integration modules."""

from claude_bedrock_cursor.bedrock.client import (
    BedrockClient,
    BedrockClientWithMetrics,
)

__all__ = [
    "BedrockClient",
    "BedrockClientWithMetrics",
]
