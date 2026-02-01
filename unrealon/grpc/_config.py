"""
Configuration models for gRPC stream service.

Provides Pydantic models for service configuration with validation.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Default timeout values
SEND_TIMEOUT = 10.0
RECEIVE_TIMEOUT = 45.0
SILENCE_TIMEOUT = 120.0


class LogExtraData(BaseModel):
    """Extra data for log entries."""

    model_config = ConfigDict(extra="allow")


class GRPCServiceConfig(BaseModel):
    """Configuration for gRPC stream service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Core settings
    api_key: Annotated[str, Field(min_length=1, description="API key for authentication")]
    service_name: Annotated[str, Field(min_length=1, max_length=255, description="Service name")]
    grpc_server: str = Field(default="localhost:50051", description="gRPC server address")
    secure: bool = Field(default=False, description="Use TLS for gRPC connection")

    # Heartbeat and logging
    heartbeat_interval: Annotated[float, Field(gt=0, le=300)] = 30.0
    log_batch_size: Annotated[int, Field(gt=0, le=1000)] = 10
    log_flush_interval: Annotated[float, Field(gt=0, le=60)] = 3.0

    # Service metadata
    description: str = Field(default="", max_length=1000)
    source_code: str = Field(default="", max_length=500)

    # Circuit breaker settings
    circuit_failure_threshold: Annotated[int, Field(ge=1, le=20)] = 5
    circuit_recovery_timeout: Annotated[float, Field(gt=0, le=300)] = 60.0

    # Timeout settings
    send_timeout: Annotated[float, Field(gt=0, le=60)] = SEND_TIMEOUT
    receive_timeout: Annotated[float, Field(gt=0, le=120)] = RECEIVE_TIMEOUT
    silence_timeout: Annotated[float, Field(gt=0, le=300)] = SILENCE_TIMEOUT

    # Backoff settings
    backoff_jitter: Annotated[float, Field(ge=0, le=0.5)] = 0.1
    use_aggressive_backoff: bool = Field(
        default=False,
        description="Use aggressive backoff for faster recovery from transient failures",
    )


__all__ = [
    "GRPCServiceConfig",
    "LogExtraData",
    "SEND_TIMEOUT",
    "RECEIVE_TIMEOUT",
    "SILENCE_TIMEOUT",
]
