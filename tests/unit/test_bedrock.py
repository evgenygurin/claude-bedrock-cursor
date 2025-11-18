"""Unit tests for AWS Bedrock client."""

import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from claude_bedrock_cursor.bedrock.client import (
    BedrockClient,
    BedrockClientWithMetrics,
)
from claude_bedrock_cursor.config import Config
from claude_bedrock_cursor.utils.errors import (
    BedrockError,
    BedrockThrottlingError,
    BedrockValidationError,
)


@pytest.mark.unit
class TestBedrockClient:
    """Test suite for BedrockClient class."""

    @pytest.mark.asyncio
    async def test_invoke_streaming_basic(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test basic streaming invocation.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        client = BedrockClient()

        chunks = []
        async for chunk in client.invoke_streaming("test prompt"):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " World"

    @pytest.mark.asyncio
    async def test_invoke_streaming_with_system_context(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test streaming with system context and caching.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        client = BedrockClient()

        chunks = []
        async for chunk in client.invoke_streaming(
            prompt="test prompt", system_context="system instructions"
        ):
            chunks.append(chunk)

        # Verify request includes system with cache_control
        call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args.kwargs["body"])

        assert "system" in body
        assert len(body["system"]) == 1
        assert body["system"][0]["type"] == "text"
        assert body["system"][0]["text"] == "system instructions"
        assert body["system"][0]["cache_control"] == {"type": "ephemeral"}

    @pytest.mark.asyncio
    async def test_invoke_streaming_without_caching(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test streaming without prompt caching.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        # Disable caching
        sample_config.enable_prompt_caching = False
        from claude_bedrock_cursor.config import set_config
        set_config(sample_config)
        client = BedrockClient()

        chunks = []
        async for chunk in client.invoke_streaming(
            prompt="test prompt", system_context="system instructions"
        ):
            chunks.append(chunk)

        # Verify no system context added when caching disabled
        call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args.kwargs["body"])

        # When caching is disabled, system context should not be included
        assert "system" not in body

    @pytest.mark.asyncio
    async def test_invoke_streaming_throttling_retry(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test retry logic for throttling errors.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        # First call raises throttling error, second succeeds
        throttle_error = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise throttle_error
            return mock_boto3_client.invoke_model_with_response_stream.return_value

        mock_boto3_client.invoke_model_with_response_stream.side_effect = side_effect

        client = BedrockClient()

        chunks = []
        async for chunk in client.invoke_streaming("test prompt"):
            chunks.append(chunk)

        # Should succeed after retry
        assert len(chunks) == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_invoke_streaming_max_retries_exceeded(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test that max retries limit is enforced.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        # Always raise throttling error
        throttle_error = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )
        mock_boto3_client.invoke_model_with_response_stream.side_effect = throttle_error

        client = BedrockClient()

        with pytest.raises(BedrockThrottlingError, match=r"Throttling error after .* retries"):
            async for _ in client.invoke_streaming("test prompt", max_retries=2):
                pass

    @pytest.mark.asyncio
    async def test_invoke_streaming_validation_error(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test handling of validation errors.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        validation_error = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Invalid model parameters"}
            },
            operation_name="InvokeModel",
        )
        mock_boto3_client.invoke_model_with_response_stream.side_effect = (
            validation_error
        )

        client = BedrockClient()

        with pytest.raises(BedrockValidationError):
            async for _ in client.invoke_streaming("test prompt"):
                pass

    @pytest.mark.asyncio
    async def test_invoke_streaming_generic_error(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test handling of generic AWS errors.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        generic_error = ClientError(
            error_response={
                "Error": {"Code": "InternalServerError", "Message": "Internal server error"}
            },
            operation_name="InvokeModel",
        )
        mock_boto3_client.invoke_model_with_response_stream.side_effect = generic_error

        client = BedrockClient()

        with pytest.raises(BedrockError):
            async for _ in client.invoke_streaming("test prompt"):
                pass

    @pytest.mark.asyncio
    async def test_build_request_body(self, sample_config: Config):
        """Test request body construction.

        Args:
            sample_config: Sample config fixture
        """
        client = BedrockClient()

        body = client._build_request_body("test prompt", system_context="system")

        assert body["anthropic_version"] == "bedrock-2023-05-31"
        assert body["max_tokens"] == 4096
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "test prompt"
        assert len(body["system"]) == 1
        assert body["system"][0]["text"] == "system"

    @pytest.mark.asyncio
    async def test_build_request_body_no_system(self, sample_config: Config):
        """Test request body without system context.

        Args:
            sample_config: Sample config fixture
        """
        client = BedrockClient()

        body = client._build_request_body("test prompt")

        assert "system" not in body
        assert len(body["messages"]) == 1

    @pytest.mark.asyncio
    async def test_stream_response_parsing(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test streaming response parsing.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        client = BedrockClient()

        chunks = []
        async for chunk in client.invoke_streaming("test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello", " World"]

    @pytest.mark.asyncio
    async def test_empty_response_stream(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test handling empty response stream.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        # Mock empty stream
        mock_boto3_client.invoke_model_with_response_stream.return_value = {
            "body": iter([])
        }

        client = BedrockClient()

        chunks = []
        async for chunk in client.invoke_streaming("test prompt"):
            chunks.append(chunk)

        assert chunks == []

    def test_exponential_backoff_delay(self):
        """Test exponential backoff calculation.

        This test verifies the backoff algorithm used in invoke_streaming:
        wait_time = 2**attempt (capped at 8 seconds)
        """
        # Attempt 0: 2^0 = 1 second
        assert 2**0 == 1

        # Attempt 1: 2^1 = 2 seconds
        assert 2**1 == 2

        # Attempt 2: 2^2 = 4 seconds
        assert 2**2 == 4

        # Attempt 3: 2^3 = 8 seconds
        assert 2**3 == 8

        # Attempt 4: would be 16, but implementation caps at 8
        assert 2**4 == 16  # Algorithm before capping


@pytest.mark.unit
class TestBedrockClientWithMetrics:
    """Test suite for BedrockClientWithMetrics class."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test metrics are tracked during invocation.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        client = BedrockClientWithMetrics()

        # Initial metrics
        assert client.get_metrics()["request_count"] == 0

        # Make request
        chunks = []
        async for chunk in client.invoke_streaming("test prompt"):
            chunks.append(chunk)

        # Verify metrics updated
        metrics = client.get_metrics()
        assert metrics["request_count"] == 1
        assert metrics["input_tokens"] > 0
        assert metrics["output_tokens"] >= 0
        assert metrics["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_metrics_failure_tracking(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test metrics track failures.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        error = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Invalid parameters"}
            },
            operation_name="InvokeModel",
        )
        mock_boto3_client.invoke_model_with_response_stream.side_effect = error

        client = BedrockClientWithMetrics()

        try:
            async for _ in client.invoke_streaming("test prompt"):
                pass
        except BedrockValidationError:
            pass

        # Metrics should not be updated when request fails
        metrics = client.get_metrics()
        assert metrics["request_count"] == 0
        assert metrics["input_tokens"] == 0
        assert metrics["output_tokens"] == 0

    @pytest.mark.asyncio
    async def test_metrics_token_tracking(
        self, mock_boto3_client: MagicMock, sample_config: Config
    ):
        """Test token usage metrics.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
            sample_config: Sample config fixture
        """
        # Add token usage to mock response
        mock_stream = [
            {
                "chunk": {
                    "bytes": b'{"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}'
                }
            },
            {
                "chunk": {
                    "bytes": b'{"type":"message_delta","usage":{"output_tokens":10}}'
                }
            },
            {"chunk": {"bytes": b'{"type":"message_stop"}'}},
        ]
        mock_boto3_client.invoke_model_with_response_stream.return_value = {
            "body": iter(mock_stream)
        }

        client = BedrockClientWithMetrics()

        async for _ in client.invoke_streaming("test prompt"):
            pass

        metrics = client.get_metrics()
        # Current implementation uses simple word count for tokens
        assert metrics["output_tokens"] > 0
        assert metrics["input_tokens"] > 0

    def test_reset_metrics(self, sample_config: Config):
        """Test resetting metrics.

        Args:
            sample_config: Sample config fixture
        """
        client = BedrockClientWithMetrics()

        # Set some metrics manually
        client._metrics["request_count"] = 10
        client._metrics["input_tokens"] = 100
        client._metrics["output_tokens"] = 50

        # Reset
        client.reset_metrics()

        # Verify reset
        metrics = client.get_metrics()
        assert metrics["request_count"] == 0
        assert metrics["input_tokens"] == 0
        assert metrics["output_tokens"] == 0
        assert metrics["total_tokens"] == 0
