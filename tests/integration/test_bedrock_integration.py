"""Integration tests for Bedrock client with mocked AWS."""

import asyncio
import json
from unittest.mock import MagicMock

import pytest
from moto import mock_aws

from claude_bedrock_cursor.bedrock.client import BedrockClient, BedrockClientWithMetrics
from claude_bedrock_cursor.config import Config
from claude_bedrock_cursor.utils.errors import (
    BedrockThrottlingError,
    BedrockValidationError,
)


@pytest.mark.integration
class TestBedrockIntegration:
    """Integration tests for Bedrock client."""

    @pytest.mark.asyncio
    @mock_aws
    async def test_full_streaming_workflow(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test complete streaming workflow with AWS.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        client = BedrockClient(config=sample_config)

        # Collect all chunks
        chunks = []
        async for chunk in client.invoke_streaming("Write a haiku about coding"):
            chunks.append(chunk)

        # Verify received response
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.asyncio
    @mock_aws
    async def test_prompt_caching_enabled(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test prompt caching is applied when enabled.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        sample_config.enable_prompt_caching = True
        client = BedrockClient(config=sample_config)

        system_context = (
            "You are a helpful AI assistant specialized in Python programming."
        )

        # Make request with system context
        chunks = []
        async for chunk in client.invoke_streaming(
            "Explain decorators", system_context=system_context
        ):
            chunks.append(chunk)

        # Verify cache_control was sent
        call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args.kwargs["body"])

        assert "system" in body
        assert body["system"][0]["cache_control"] == {"type": "ephemeral"}

    @pytest.mark.asyncio
    @mock_aws
    async def test_concurrent_requests(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test handling multiple concurrent requests.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        client = BedrockClient(config=sample_config)

        # Create multiple concurrent requests
        async def make_request(prompt: str):
            chunks = []
            async for chunk in client.invoke_streaming(prompt):
                chunks.append(chunk)
            return "".join(chunks)

        prompts = [
            "Write a function",
            "Explain async/await",
            "What is a decorator",
        ]

        # Run concurrently
        results = await asyncio.gather(*[make_request(p) for p in prompts])

        # Verify all completed successfully
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    @mock_aws
    async def test_retry_on_throttling(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test automatic retry on throttling errors.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        from botocore.exceptions import ClientError

        # First call throttles, second succeeds
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ClientError(
                    error_response={"Error": {"Code": "ThrottlingException"}},
                    operation_name="InvokeModel",
                )
            return mock_boto3_client.invoke_model_with_response_stream.return_value

        mock_boto3_client.invoke_model_with_response_stream.side_effect = side_effect

        client = BedrockClient(config=sample_config)

        chunks = []
        async for chunk in client.invoke_streaming("test prompt"):
            chunks.append(chunk)

        # Should succeed after retry
        assert len(chunks) > 0
        assert call_count == 2  # First failed, second succeeded

    @pytest.mark.asyncio
    @mock_aws
    async def test_metrics_tracking_integration(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test metrics tracking in real workflow.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        client = BedrockClientWithMetrics(config=sample_config)

        # Make multiple requests
        for i in range(3):
            async for _ in client.invoke_streaming(f"Request {i}"):
                pass

        # Verify metrics
        metrics = client.get_metrics()
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 3
        assert metrics["failed_requests"] == 0

    @pytest.mark.asyncio
    @mock_aws
    async def test_large_system_context_caching(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test caching with large system context (>1024 tokens).

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        sample_config.enable_prompt_caching = True
        client = BedrockClient(config=sample_config)

        # Create large system context (simulating project documentation)
        large_context = (
            """
        You are an AI assistant with deep knowledge of Python.

        Project Architecture:
        - FastAPI backend with PostgreSQL database
        - JWT authentication with refresh tokens
        - Redis caching layer
        - Celery for async tasks
        - Docker deployment

        Code Standards:
        - Type hints required
        - 88 character line limit
        - Comprehensive docstrings
        - 80%+ test coverage

        """
            * 20
        )  # Repeat to ensure >1024 tokens

        chunks = []
        async for chunk in client.invoke_streaming(
            "Explain authentication flow", system_context=large_context
        ):
            chunks.append(chunk)

        # Verify cache_control applied
        call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args.kwargs["body"])

        assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert len(body["system"][0]["text"]) > 1024

    @pytest.mark.asyncio
    @mock_aws
    async def test_max_tokens_configuration(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test MAX_OUTPUT_TOKENS configuration is respected.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        # Test with 4096 (minimum)
        sample_config.max_output_tokens = 4096
        client = BedrockClient(config=sample_config)

        async for _ in client.invoke_streaming("test"):
            pass

        call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args.kwargs["body"])
        assert body["max_tokens"] == 4096

        # Test with higher value
        sample_config.max_output_tokens = 8192
        client = BedrockClient(config=sample_config)

        async for _ in client.invoke_streaming("test"):
            pass

        call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
        body = json.loads(call_args.kwargs["body"])
        assert body["max_tokens"] == 8192


@pytest.mark.integration
class TestBedrockErrorHandling:
    """Integration tests for error handling scenarios."""

    @pytest.mark.asyncio
    @mock_aws
    async def test_validation_error_handling(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test handling of validation errors from Bedrock.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        from botocore.exceptions import ClientError

        mock_boto3_client.invoke_model_with_response_stream.side_effect = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Invalid input"}
            },
            operation_name="InvokeModel",
        )

        client = BedrockClient(config=sample_config)

        with pytest.raises(BedrockValidationError, match="Invalid input"):
            async for _ in client.invoke_streaming("test"):
                pass

    @pytest.mark.asyncio
    @mock_aws
    async def test_throttling_max_retries(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test max retries limit for throttling.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        from botocore.exceptions import ClientError

        # Always throttle
        mock_boto3_client.invoke_model_with_response_stream.side_effect = ClientError(
            error_response={"Error": {"Code": "ThrottlingException"}},
            operation_name="InvokeModel",
        )

        client = BedrockClient(config=sample_config)

        with pytest.raises(BedrockThrottlingError, match="Max retries exceeded"):
            async for _ in client.invoke_streaming("test", max_retries=2):
                pass

    @pytest.mark.asyncio
    @mock_aws
    async def test_empty_response_handling(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test handling of empty response from Bedrock.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        # Mock empty stream
        mock_boto3_client.invoke_model_with_response_stream.return_value = {
            "body": iter([])
        }

        client = BedrockClient(config=sample_config)

        chunks = []
        async for chunk in client.invoke_streaming("test"):
            chunks.append(chunk)

        # Should handle gracefully
        assert chunks == []


@pytest.mark.integration
class TestBedrockClientConfiguration:
    """Integration tests for client configuration."""

    @pytest.mark.asyncio
    @mock_aws
    async def test_different_regions(self, mock_boto3_client: MagicMock):
        """Test client works with different AWS regions.

        Args:
            mock_boto3_client: Mocked boto3 client fixture
        """
        regions = ["us-east-1", "us-west-2", "eu-west-1"]

        for region in regions:
            config = Config(aws_region=region)
            client = BedrockClient(config=config)

            chunks = []
            async for chunk in client.invoke_streaming("test"):
                chunks.append(chunk)

            assert len(chunks) > 0

    @pytest.mark.asyncio
    @mock_aws
    async def test_different_models(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test client works with different Claude models.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        models = [
            "anthropic.claude-sonnet-4-20250514-v1:0",
            "anthropic.claude-3-opus-20240229",
            "anthropic.claude-3-sonnet-20240229",
        ]

        for model_id in models:
            sample_config.bedrock_model_id = model_id
            client = BedrockClient(config=sample_config)

            async for _ in client.invoke_streaming("test"):
                pass

            # Verify correct model was called
            call_args = mock_boto3_client.invoke_model_with_response_stream.call_args
            assert call_args.kwargs["modelId"] == model_id

    @pytest.mark.asyncio
    @mock_aws
    async def test_streaming_disabled(
        self, sample_config: Config, mock_boto3_client: MagicMock
    ):
        """Test behavior when streaming is disabled.

        Args:
            sample_config: Sample config fixture
            mock_boto3_client: Mocked boto3 client fixture
        """
        sample_config.enable_streaming = False
        client = BedrockClient(config=sample_config)

        # Should still work (fallback to streaming internally)
        chunks = []
        async for chunk in client.invoke_streaming("test"):
            chunks.append(chunk)

        assert len(chunks) > 0
