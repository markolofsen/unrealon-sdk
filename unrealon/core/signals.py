"""Signal handlers for graceful shutdown."""

from __future__ import annotations

import logging
import signal
import sys
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Type for signal handler callback
ShutdownCallback = Callable[[], Any]


class SignalHandlerConfig(BaseModel):
    """Configuration for signal handler."""

    model_config = ConfigDict(frozen=True)

    handle_sigint: bool = Field(default=True, description="Handle SIGINT (Ctrl+C)")
    handle_sigterm: bool = Field(default=True, description="Handle SIGTERM (kill)")
    exit_on_signal: bool = Field(default=True, description="Exit after handling signal")
    exit_code: Annotated[int, Field(ge=0, le=255)] = Field(
        default=0,
        description="Exit code on graceful shutdown",
    )


class SignalHandler:
    """
    Manages Unix signal handlers for graceful shutdown.

    Handles SIGINT (Ctrl+C) and SIGTERM (kill) signals.

    Example:
        ```python
        def cleanup():
            print("Cleaning up...")

        handler = SignalHandler()
        handler.register(cleanup)
        handler.setup()

        # ... run application ...

        handler.restore()  # Restore original handlers
        ```
    """

    def __init__(self, config: SignalHandlerConfig | None = None):
        self._config = config or SignalHandlerConfig()
        self._callbacks: list[ShutdownCallback] = []
        self._original_sigint: Any = None
        self._original_sigterm: Any = None
        self._is_setup = False

    @property
    def config(self) -> SignalHandlerConfig:
        """Get handler configuration."""
        return self._config

    def register(self, callback: ShutdownCallback) -> None:
        """
        Register shutdown callback.

        Args:
            callback: Function to call on shutdown signal
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.debug("Registered shutdown callback: %s", callback.__name__)

    def unregister(self, callback: ShutdownCallback) -> None:
        """
        Unregister shutdown callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug("Unregistered shutdown callback: %s", callback.__name__)

    def setup(self) -> bool:
        """
        Setup signal handlers.

        Returns:
            True if handlers were set up, False if not possible
        """
        if self._is_setup:
            return True

        def handler(signum: int, _frame: Any) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s signal, initiating shutdown...", sig_name)
            self._run_callbacks()
            if self._config.exit_on_signal:
                sys.exit(self._config.exit_code)

        try:
            if self._config.handle_sigint:
                self._original_sigint = signal.signal(signal.SIGINT, handler)
            if self._config.handle_sigterm:
                self._original_sigterm = signal.signal(signal.SIGTERM, handler)
            self._is_setup = True
            logger.debug("Signal handlers installed")
            return True
        except ValueError:
            # Cannot set signal handlers (not in main thread)
            logger.warning("Cannot set signal handlers (not in main thread)")
            return False

    def restore(self) -> None:
        """Restore original signal handlers."""
        if not self._is_setup:
            return

        try:
            if self._original_sigint is not None:
                signal.signal(signal.SIGINT, self._original_sigint)
            if self._original_sigterm is not None:
                signal.signal(signal.SIGTERM, self._original_sigterm)
            self._is_setup = False
            logger.debug("Signal handlers restored")
        except ValueError:
            pass

    def _run_callbacks(self) -> None:
        """Run all registered shutdown callbacks."""
        for callback in reversed(self._callbacks):
            try:
                logger.debug("Running shutdown callback: %s", callback.__name__)
                callback()
            except Exception as e:
                logger.error("Error in shutdown callback %s: %s", callback.__name__, e)

    @property
    def is_setup(self) -> bool:
        """Check if signal handlers are set up."""
        return self._is_setup

    @property
    def callbacks_count(self) -> int:
        """Number of registered callbacks."""
        return len(self._callbacks)


# Global signal handler instance
_global_handler: SignalHandler | None = None


def setup_signal_handlers(
    callback: ShutdownCallback | None = None,
    config: SignalHandlerConfig | None = None,
) -> SignalHandler:
    """
    Setup global signal handlers.

    Args:
        callback: Optional shutdown callback to register
        config: Optional handler configuration

    Returns:
        SignalHandler instance
    """
    global _global_handler

    if _global_handler is None:
        _global_handler = SignalHandler(config)
        _global_handler.setup()

    if callback:
        _global_handler.register(callback)

    return _global_handler


def get_signal_handler() -> SignalHandler | None:
    """Get global signal handler if set up."""
    return _global_handler


__all__ = [
    "SignalHandler",
    "SignalHandlerConfig",
    "ShutdownCallback",
    "setup_signal_handlers",
    "get_signal_handler",
]
