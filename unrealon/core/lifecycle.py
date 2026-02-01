"""Lifecycle manager for coordinating service startup and shutdown."""

from __future__ import annotations

import atexit
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .signals import SignalHandler, SignalHandlerConfig
from .state import ServiceState, StateMachine, StateTransitionError

logger = logging.getLogger(__name__)

# Callback types
StartupCallback = Callable[[], Any]
ShutdownCallback = Callable[[], Any]
StateChangeCallback = Callable[[ServiceState, ServiceState], Any]


class LifecycleConfig(BaseModel):
    """Configuration for lifecycle manager."""

    model_config = ConfigDict(frozen=True)

    auto_setup_signals: bool = Field(
        default=True,
        description="Automatically setup signal handlers",
    )
    auto_register_atexit: bool = Field(
        default=True,
        description="Automatically register atexit handler",
    )
    signal_config: SignalHandlerConfig = Field(
        default_factory=SignalHandlerConfig,
        description="Signal handler configuration",
    )


class LifecycleEvent(BaseModel):
    """Lifecycle event data."""

    model_config = ConfigDict(frozen=True)

    from_state: ServiceState
    to_state: ServiceState
    success: bool = True
    error: str | None = None


class LifecycleManager:
    """
    Manages service lifecycle with callbacks and state tracking.

    Coordinates:
    - State machine transitions
    - Signal handlers for graceful shutdown
    - Startup and shutdown callbacks
    - atexit handlers

    Example:
        ```python
        lifecycle = LifecycleManager()

        # Register callbacks
        lifecycle.on_startup(init_database)
        lifecycle.on_shutdown(close_connections)
        lifecycle.on_state_change(log_state_change)

        # Start lifecycle
        lifecycle.start()

        # ... service runs ...

        # Shutdown (or signal triggers this)
        lifecycle.shutdown()
        ```
    """

    def __init__(self, config: LifecycleConfig | None = None):
        self._config = config or LifecycleConfig()
        self._state_machine = StateMachine()
        self._signal_handler: SignalHandler | None = None

        # Callbacks
        self._startup_callbacks: list[StartupCallback] = []
        self._shutdown_callbacks: list[ShutdownCallback] = []
        self._state_change_callbacks: list[StateChangeCallback] = []

        # Setup
        if self._config.auto_setup_signals:
            self._setup_signal_handler()
        if self._config.auto_register_atexit:
            atexit.register(self._atexit_handler)

    @property
    def state(self) -> ServiceState:
        """Current service state."""
        return self._state_machine.state

    @property
    def state_machine(self) -> StateMachine:
        """Get state machine."""
        return self._state_machine

    @property
    def config(self) -> LifecycleConfig:
        """Get lifecycle configuration."""
        return self._config

    def on_startup(self, callback: StartupCallback) -> None:
        """
        Register startup callback.

        Args:
            callback: Function to call during startup
        """
        self._startup_callbacks.append(callback)
        logger.debug("Registered startup callback: %s", callback.__name__)

    def on_shutdown(self, callback: ShutdownCallback) -> None:
        """
        Register shutdown callback.

        Args:
            callback: Function to call during shutdown
        """
        self._shutdown_callbacks.append(callback)
        logger.debug("Registered shutdown callback: %s", callback.__name__)

        # Also register with signal handler
        if self._signal_handler:
            self._signal_handler.register(callback)

    def on_state_change(self, callback: StateChangeCallback) -> None:
        """
        Register state change callback.

        Args:
            callback: Function to call on state change (receives from_state, to_state)
        """
        self._state_change_callbacks.append(callback)
        logger.debug("Registered state change callback: %s", callback.__name__)

    def transition_to(self, target: ServiceState) -> LifecycleEvent:
        """
        Transition to new state.

        Args:
            target: Target state

        Returns:
            LifecycleEvent with transition result
        """
        from_state = self._state_machine.state

        try:
            self._state_machine.transition_to(target)
            self._notify_state_change(from_state, target)
            return LifecycleEvent(from_state=from_state, to_state=target)
        except StateTransitionError as e:
            logger.error("State transition failed: %s", e)
            return LifecycleEvent(
                from_state=from_state,
                to_state=target,
                success=False,
                error=str(e),
            )

    def start(self) -> LifecycleEvent:
        """
        Start service lifecycle.

        Transitions: INITIALIZED -> REGISTERING -> RUNNING
        Runs all startup callbacks.

        Returns:
            LifecycleEvent with startup result
        """
        logger.info("Starting lifecycle...")

        # Transition to registering
        event = self.transition_to(ServiceState.REGISTERING)
        if not event.success:
            return event

        # Run startup callbacks
        for callback in self._startup_callbacks:
            try:
                logger.debug("Running startup callback: %s", callback.__name__)
                callback()
            except Exception as e:
                logger.error("Startup callback failed: %s", e)
                self.transition_to(ServiceState.ERROR)
                return LifecycleEvent(
                    from_state=ServiceState.REGISTERING,
                    to_state=ServiceState.ERROR,
                    success=False,
                    error=str(e),
                )

        # Transition to running
        event = self.transition_to(ServiceState.RUNNING)
        if event.success:
            logger.info("Lifecycle started successfully")

        return event

    def shutdown(self) -> LifecycleEvent:
        """
        Shutdown service lifecycle.

        Transitions: * -> STOPPING -> STOPPED
        Runs all shutdown callbacks.

        Returns:
            LifecycleEvent with shutdown result
        """
        if self._state_machine.is_terminal():
            logger.debug("Already in terminal state")
            return LifecycleEvent(
                from_state=self.state,
                to_state=self.state,
            )

        logger.info("Shutting down lifecycle...")

        # Transition to stopping
        event = self.transition_to(ServiceState.STOPPING)
        if not event.success:
            # Force to error state if transition fails
            self._state_machine.state = ServiceState.ERROR

        # Run shutdown callbacks in reverse order
        for callback in reversed(self._shutdown_callbacks):
            try:
                logger.debug("Running shutdown callback: %s", callback.__name__)
                callback()
            except Exception as e:
                logger.error("Shutdown callback failed: %s", e)

        # Transition to stopped
        try:
            from_state = self._state_machine.state
            self._state_machine.transition_to(ServiceState.STOPPED)
            self._notify_state_change(from_state, ServiceState.STOPPED)
        except StateTransitionError:
            pass  # Already handled

        logger.info("Lifecycle shutdown complete")

        return LifecycleEvent(
            from_state=ServiceState.STOPPING,
            to_state=ServiceState.STOPPED,
        )

    def pause(self) -> LifecycleEvent:
        """Pause service."""
        return self.transition_to(ServiceState.PAUSED)

    def resume(self) -> LifecycleEvent:
        """Resume service from paused state."""
        return self.transition_to(ServiceState.RUNNING)

    def error(self, message: str | None = None) -> LifecycleEvent:
        """Transition to error state."""
        event = self.transition_to(ServiceState.ERROR)
        if message:
            logger.error("Lifecycle error: %s", message)
        return event

    def _setup_signal_handler(self) -> None:
        """Setup signal handler for graceful shutdown."""
        self._signal_handler = SignalHandler(self._config.signal_config)

        if self._signal_handler is not None:
            # Register shutdown as signal callback
            self._signal_handler.register(self.shutdown)

            # Setup handlers
            self._signal_handler.setup()

    def _notify_state_change(
        self,
        from_state: ServiceState,
        to_state: ServiceState,
    ) -> None:
        """Notify all state change callbacks."""
        for callback in self._state_change_callbacks:
            try:
                callback(from_state, to_state)
            except Exception as e:
                logger.error(
                    "State change callback %s failed: %s",
                    callback.__name__,
                    e,
                )

    def _atexit_handler(self) -> None:
        """Handle process exit."""
        if not self._state_machine.is_terminal():
            logger.debug("atexit handler triggered, running shutdown")
            self.shutdown()


__all__ = [
    "LifecycleManager",
    "LifecycleConfig",
    "LifecycleEvent",
    "StartupCallback",
    "ShutdownCallback",
    "StateChangeCallback",
]
