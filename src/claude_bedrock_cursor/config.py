"""Configuration management with Pydantic validation."""

from pathlib import Path
from typing import Literal

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for Python 3.10

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration with environment variable support.

    Attributes:
        aws_region: AWS region for Bedrock
        aws_profile: AWS CLI profile name
        bedrock_model_id: Primary Bedrock model ID
        bedrock_fast_model_id: Fast/cheap model for simple tasks
        max_output_tokens: Maximum output tokens (min 4096 for Bedrock)
        max_thinking_tokens: Maximum thinking tokens
        enable_prompt_caching: Enable prompt caching (90% cost reduction)
        enable_streaming: Enable streaming responses
        cursor_integration_mode: Cursor integration mode
        cursor_path: Path to Cursor application
        enable_cloudwatch: Enable CloudWatch logging
        log_level: Logging level
        cost_alerts_enabled: Enable cost alerts
        monthly_budget_usd: Monthly budget limit in USD

    Example:
        >>> config = Config()
        >>> print(config.aws_region)
        'us-east-1'

        >>> # Load from file
        >>> config = Config.from_toml(Path("config.toml"))

        >>> # Override with environment variables
        >>> os.environ["AWS_REGION"] = "us-west-2"
        >>> config = Config()
        >>> print(config.aws_region)
        'us-west-2'
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # AWS Bedrock Configuration
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock",
    )
    aws_profile: str | None = Field(
        default=None,
        description="AWS CLI profile name",
    )
    bedrock_model_id: str = Field(
        default="anthropic.claude-sonnet-4-20250514-v1:0",
        description="Primary Bedrock model ID",
    )
    bedrock_fast_model_id: str = Field(
        default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        description="Fast/cheap model for simple tasks",
    )
    max_output_tokens: int = Field(
        default=4096,
        ge=4096,  # Bedrock minimum for burndown throttling
        description="Maximum output tokens",
    )
    max_thinking_tokens: int = Field(
        default=1024,
        ge=0,
        description="Maximum thinking tokens",
    )

    # Feature Flags
    claude_code_use_bedrock: bool = Field(
        default=True,
        description="Enable Bedrock integration",
    )
    enable_prompt_caching: bool = Field(
        default=True,
        description="Enable prompt caching (90% cost reduction)",
    )
    enable_streaming: bool = Field(
        default=True,
        description="Enable streaming responses",
    )

    # Cursor Integration
    cursor_integration_mode: Literal["cli", "extension", "both"] = Field(
        default="both",
        description="Cursor integration mode",
    )
    cursor_path: Path | None = Field(
        default=None,
        description="Path to Cursor application",
    )

    # Monitoring
    enable_cloudwatch: bool = Field(
        default=True,
        description="Enable CloudWatch logging",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Cost Management
    cost_alerts_enabled: bool = Field(
        default=True,
        description="Enable cost alerts",
    )
    monthly_budget_usd: float = Field(
        default=100.0,
        gt=0,
        description="Monthly budget limit in USD",
    )

    @field_validator("cursor_path")
    @classmethod
    def validate_cursor_path(cls, v: Path | None) -> Path | None:
        """Validate Cursor path exists if provided.

        Args:
            v: Cursor path to validate

        Returns:
            Path: Validated path

        Raises:
            ValueError: If path doesn't exist
        """
        if v is not None and not v.exists():
            raise ValueError(f"Cursor path does not exist: {v}")
        return v

    @field_validator("aws_region")
    @classmethod
    def validate_aws_region(cls, v: str) -> str:
        """Validate AWS region format.

        Args:
            v: AWS region to validate

        Returns:
            str: Validated region

        Raises:
            ValueError: If region format is invalid
        """
        valid_prefixes = ["us-", "eu-", "ap-", "sa-", "ca-", "me-", "af-"]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Invalid AWS region: {v}")
        return v

    @classmethod
    def from_toml(cls, path: Path) -> "Config":
        """Load configuration from TOML file.

        Args:
            path: Path to TOML file

        Returns:
            Config: Loaded configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If TOML is invalid

        Example:
            >>> config = Config.from_toml(Path("config.toml"))
            >>> print(config.aws_region)
            'us-east-1'
        """
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return cls(**data)

    def to_dict(self) -> dict:
        """Convert config to dictionary.

        Returns:
            dict: Configuration as dictionary

        Example:
            >>> config = Config()
            >>> config_dict = config.to_dict()
            >>> print(config_dict["aws_region"])
            'us-east-1'
        """
        return self.model_dump()

    def to_env_vars(self) -> dict[str, str]:
        """Convert config to environment variables.

        Returns:
            dict: Configuration as environment variables

        Example:
            >>> config = Config()
            >>> env_vars = config.to_env_vars()
            >>> print(env_vars["AWS_REGION"])
            'us-east-1'
        """
        return {
            key.upper(): str(value)
            for key, value in self.to_dict().items()
            if value is not None
        }


# Global configuration instance
_config: Config | None = None


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Config: Global configuration

    Example:
        >>> config = get_config()
        >>> print(config.aws_region)
        'us-east-1'
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance.

    Args:
        config: Configuration to set

    Example:
        >>> custom_config = Config(aws_region="us-west-2")
        >>> set_config(custom_config)
        >>> print(get_config().aws_region)
        'us-west-2'
    """
    global _config
    _config = config
