"""Core components for service lifecycle management."""

from __future__ import annotations

from .lifecycle import (
    LifecycleConfig,
    LifecycleEvent,
    LifecycleManager,
    ShutdownCallback,
    StartupCallback,
    StateChangeCallback,
)
from .signals import (
    SignalHandler,
    SignalHandlerConfig,
    get_signal_handler,
    setup_signal_handlers,
)
from .state import (
    ServiceState,
    StateMachine,
    StateSnapshot,
    StateTransitionError,
    can_transition,
    validate_transition,
)

__all__ = [
    # Lifecycle
    "LifecycleManager",
    "LifecycleConfig",
    "LifecycleEvent",
    "StartupCallback",
    "ShutdownCallback",
    "StateChangeCallback",
    # Signals
    "SignalHandler",
    "SignalHandlerConfig",
    "setup_signal_handlers",
    "get_signal_handler",
    # State
    "ServiceState",
    "StateMachine",
    "StateSnapshot",
    "StateTransitionError",
    "can_transition",
    "validate_transition",
]
