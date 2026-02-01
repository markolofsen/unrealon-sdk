"""SDK configuration with Pydantic v2 type safety."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ._constants import (
    DEFAULT_GRPC_SERVER,
    DEFAULT_GRPC_SERVER_LOCAL,
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_LOG_BATCH_SIZE,
    DEFAULT_LOG_FLUSH_INTERVAL,
    DEV_HEARTBEAT_INTERVAL,
    DEV_LOG_FLUSH_INTERVAL,
)


class UnrealonConfig(BaseSettings):
    """
    SDK configuration with environment variable support and Pydantic v2 validation.

    All settings can be configured via environment variables with UNREALON_ prefix.

    Example:
        UNREALON_API_KEY=pk_live_xxx
        UNREALON_SERVICE_NAME=my-service
        UNREALON_DEV_MODE=true
        UNREALON_GRPC_SERVER=grpc.unrealon.com:443
    """

    model_config = SettingsConfigDict(
        env_prefix="UNREALON_",
        env_file=".env",
        extra="ignore",
        validate_assignment=True,
    )

    # Required credentials
    api_key: Annotated[str, Field(min_length=1, description="API key for authentication")]
    service_name: Annotated[str, Field(min_length=1, max_length=255, description="Service name")]

    # Development mode - auto-switches gRPC server
    dev_mode: bool = Field(default=False, description="Use local gRPC server")

    # gRPC settings
    grpc_server: str | None = Field(default=None, description="gRPC server address")
    grpc_secure: bool | None = Field(default=None, description="Use TLS for gRPC")

    # Heartbeat settings
    heartbeat_interval: Annotated[int, Field(gt=0, le=300)] = DEFAULT_HEARTBEAT_INTERVAL

    # Logging settings
    log_batch_size: Annotated[int, Field(gt=0, le=1000)] = DEFAULT_LOG_BATCH_SIZE
    log_flush_interval: Annotated[float, Field(gt=0, le=60)] = DEFAULT_LOG_FLUSH_INTERVAL

    # Optional metadata
    service_version: str | None = Field(default=None, max_length=50)
    source_code: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def set_grpc_defaults(self) -> UnrealonConfig:
        """Set gRPC server and secure based on dev_mode if not explicitly provided."""
        if self.grpc_server is None:
            object.__setattr__(
                self,
                "grpc_server",
                DEFAULT_GRPC_SERVER_LOCAL if self.dev_mode else DEFAULT_GRPC_SERVER,
            )
        if self.grpc_secure is None:
            object.__setattr__(self, "grpc_secure", not self.dev_mode)

        # In dev_mode, use faster intervals for testing (if not explicitly set)
        if self.dev_mode:
            # Check if heartbeat_interval is still at default value
            if self.heartbeat_interval == DEFAULT_HEARTBEAT_INTERVAL:
                object.__setattr__(self, "heartbeat_interval", DEV_HEARTBEAT_INTERVAL)
            # Check if log_flush_interval is still at default value
            if self.log_flush_interval == DEFAULT_LOG_FLUSH_INTERVAL:
                object.__setattr__(self, "log_flush_interval", DEV_LOG_FLUSH_INTERVAL)

        return self


# Global config singleton
_config: UnrealonConfig | None = None


def configure(**kwargs: object) -> UnrealonConfig:
    """
    Configure SDK with provided settings.

    Args:
        **kwargs: Configuration options (api_key, service_name, etc.)

    Returns:
        UnrealonConfig instance
    """
    global _config
    _config = UnrealonConfig.model_validate(kwargs)
    return _config


def get_config() -> UnrealonConfig:
    """
    Get current configuration.

    Returns:
        Current UnrealonConfig instance

    Raises:
        RuntimeError: If configure() was not called first
    """
    global _config
    if _config is None:
        _config = UnrealonConfig()
    return _config


def reset_config() -> None:
    """Reset configuration to None (for testing)."""
    global _config
    _config = None


__all__ = ["UnrealonConfig", "configure", "get_config", "reset_config"]
