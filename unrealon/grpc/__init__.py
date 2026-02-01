"""
gRPC client for Unrealon SDK.

Provides bidirectional streaming communication with Django server.

Enterprise-grade patterns:
- Circuit breaker for connection resilience
- Exponential backoff with jitter
- Timeout-wrapped stream operations
- Heartbeat failure counting
- Silence detection

Module structure:
- stream_service: Main GRPCStreamService facade
- circuit_breaker: CircuitBreaker, BackoffStrategy
- _config: Configuration models
- _connection: Connection management
- _registration: Register/Deregister RPC
- _messaging: Message generation
- _reconnect: Reconnection logic
- _handlers: Command registry
- _logging: Log buffer
- _types: Type definitions
"""

from ._config import GRPCServiceConfig, LogExtraData
from ._connection import ConnectionManager
from ._handlers import CommandRegistry
from ._logging import LogBuffer
from ._messaging import MessageGenerator
from ._reconnect import ReconnectionManager
from ._registration import RegistrationManager
from ._types import CommandHandler
from .circuit_breaker import (
    BackoffStrategy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitState,
)
from .stream_service import GRPCStreamService

__all__ = [
    # Main service
    "GRPCStreamService",
    "GRPCServiceConfig",
    "LogExtraData",
    "CommandHandler",
    # Components
    "ConnectionManager",
    "RegistrationManager",
    "MessageGenerator",
    "ReconnectionManager",
    "CommandRegistry",
    "LogBuffer",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitState",
    # Backoff
    "BackoffStrategy",
]
