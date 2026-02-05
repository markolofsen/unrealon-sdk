"""
Unrealon SDK - Service management SDK for Django backend via gRPC.

Example:
    ```python
    from unrealon import ServiceClient

    # Using context manager (recommended)
    with ServiceClient(api_key="...", service_name="my-service") as client:
        client.info("Processing started")
        for item in items:
            process(item)
            client.increment_processed()
        client.info("Processing complete")

    # Manual control
    client = ServiceClient(api_key="...", service_name="my-service")
    client.start()
    # ... do work ...
    client.stop()

    # Async client
    async with AsyncServiceClient(api_key="...", service_name="my-service") as client:
        client.info("Async processing")
    ```
"""

from ._client import AsyncServiceClient, ServiceClient
from ._config import UnrealonConfig, configure, get_config, reset_config
from ._version import __version__
from .core import (
    LifecycleConfig,
    LifecycleEvent,
    LifecycleManager,
    ServiceState,
    SignalHandler,
    SignalHandlerConfig,
    StateMachine,
    StateTransitionError,
)
from .exceptions import (
    APIError,
    AuthenticationError,
    HeartbeatError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    RegistrationError,
    TimeoutError,
    UnrealonError,
    ValidationError,
)
from .grpc import GRPCStreamService
from .logging import get_logger
from .models import ServiceStatus
from .runner import TaskRunner
from .scheduling import Schedule, ScheduleResult, ScheduleRunStatus

__all__ = [
    # Version
    "__version__",
    # Config
    "UnrealonConfig",
    "configure",
    "get_config",
    "reset_config",
    # Main clients
    "ServiceClient",
    "AsyncServiceClient",
    # Logging
    "get_logger",
    # gRPC
    "GRPCStreamService",
    # Exceptions
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
    # Core
    "LifecycleManager",
    "LifecycleConfig",
    "LifecycleEvent",
    "SignalHandler",
    "SignalHandlerConfig",
    "ServiceState",
    "StateMachine",
    "StateTransitionError",
    # Enums
    "ServiceStatus",
    # Scheduling
    "Schedule",
    "ScheduleResult",
    "ScheduleRunStatus",
    # Runner
    "TaskRunner",
    # Parsers submodule (import as: from unrealon.parsers import ...)
    # Note: parsers module requires optional dependencies: pip install unrealon[parsers]
]
