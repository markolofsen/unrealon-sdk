"""Unrealon SDK exceptions."""

from .handlers import (
    api_error_handler,
    async_api_error_handler,
    handle_api_errors,
)
from .types import (
    APIError,
    AuthenticationError,
    HeartbeatError,
    InterruptError,
    NetworkError,
    NotFoundError,
    PauseInterrupt,
    RateLimitError,
    RegistrationError,
    StopInterrupt,
    TimeoutError,
    UnrealonError,
    ValidationError,
)

__all__ = [
    # Exception types
    "UnrealonError",
    "APIError",
    "AuthenticationError",
    "RegistrationError",
    "HeartbeatError",
    "ValidationError",
    "TimeoutError",
    "NetworkError",
    "NotFoundError",
    "RateLimitError",
    "InterruptError",
    "PauseInterrupt",
    "StopInterrupt",
    # Handlers
    "api_error_handler",
    "async_api_error_handler",
    "handle_api_errors",
]
