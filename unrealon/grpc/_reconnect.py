"""
Reconnection and health monitoring for gRPC stream.

Handles exponential backoff, silence detection, and heartbeat health.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from ._constants import MAX_HEARTBEAT_FAILURES

if TYPE_CHECKING:
    from ._config import GRPCServiceConfig
    from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class ReconnectionManager:
    """Manages reconnection logic and health monitoring.

    Provides:
    - Exponential backoff with circuit breaker integration
    - Silence detection (no messages for extended period)
    - Heartbeat failure counting
    """

    __slots__ = (
        "_config",
        "_circuit_breaker",
        "_backoff_getter",
        "_consecutive_heartbeat_failures",
        "_last_message_time",
        "_silence_task",
        "_running",
    )

    def __init__(
        self,
        config: GRPCServiceConfig,
        circuit_breaker: CircuitBreaker,
        backoff_getter: callable,
    ) -> None:
        """
        Initialize reconnection manager.

        Args:
            config: Service configuration
            circuit_breaker: Circuit breaker for failure tracking
            backoff_getter: Callable that returns current BackoffStrategy
        """
        self._config = config
        self._circuit_breaker = circuit_breaker
        self._backoff_getter = backoff_getter

        self._consecutive_heartbeat_failures: int = 0
        self._last_message_time: float = 0.0
        self._silence_task: asyncio.Task[None] | None = None
        self._running: bool = False

    @property
    def consecutive_heartbeat_failures(self) -> int:
        """Get consecutive heartbeat failures count."""
        return self._consecutive_heartbeat_failures

    @consecutive_heartbeat_failures.setter
    def consecutive_heartbeat_failures(self, value: int) -> None:
        """Set consecutive heartbeat failures count."""
        self._consecutive_heartbeat_failures = value

    @property
    def last_message_time(self) -> float:
        """Get last message timestamp."""
        return self._last_message_time

    @last_message_time.setter
    def last_message_time(self, value: float) -> None:
        """Set last message timestamp."""
        self._last_message_time = value

    def reset_heartbeat_failures(self) -> None:
        """Reset heartbeat failure counter on successful ack."""
        self._consecutive_heartbeat_failures = 0

    def check_heartbeat_health(self) -> bool:
        """
        Check heartbeat health.

        Returns:
            True if healthy, False if reconnect needed
        """
        if self._consecutive_heartbeat_failures >= MAX_HEARTBEAT_FAILURES:
            logger.error(
                "Heartbeat failed %d consecutive times, triggering reconnect",
                self._consecutive_heartbeat_failures,
            )
            return False
        return True

    def update_last_message_time(self) -> None:
        """Update last message timestamp to current time."""
        self._last_message_time = asyncio.get_event_loop().time()

    def start_silence_detector(self, on_silence_timeout: callable) -> None:
        """Start silence detection task.

        Args:
            on_silence_timeout: Callback when silence timeout occurs
        """
        self._running = True
        self._last_message_time = asyncio.get_event_loop().time()
        self._silence_task = asyncio.create_task(
            self._silence_detector(on_silence_timeout)
        )

    def stop_silence_detector(self) -> None:
        """Stop silence detection task."""
        self._running = False
        if self._silence_task:
            self._silence_task.cancel()

    async def _silence_detector(self, on_silence_timeout: callable) -> None:
        """Detect silence (no messages for extended period).

        Args:
            on_silence_timeout: Callback when silence timeout occurs
        """
        while self._running:
            await asyncio.sleep(10)  # Check every 10 seconds

            elapsed = asyncio.get_event_loop().time() - self._last_message_time
            if elapsed > self._config.silence_timeout:
                logger.error(
                    "Silence timeout: no messages for %.0fs, triggering reconnect",
                    elapsed,
                )
                self._circuit_breaker.record_failure()
                await on_silence_timeout()
                break

    async def reconnect_loop(
        self,
        running_getter: callable,
        connect_fn: callable,
        start_fn: callable,
    ) -> None:
        """Reconnect with exponential backoff and circuit breaker.

        Args:
            running_getter: Callable that returns whether service is running
            connect_fn: Async function to establish connection
            start_fn: Async function to start streaming
        """
        while running_getter():
            # Check circuit breaker
            if not self._circuit_breaker.allow_request():
                logger.warning(
                    "Circuit breaker open, waiting %.1fs",
                    self._circuit_breaker.recovery_timeout,
                )
                await asyncio.sleep(self._circuit_breaker.recovery_timeout)
                continue

            # Get backoff delay with jitter
            backoff = self._backoff_getter()
            delay = backoff.next()
            logger.info("Reconnecting in %.2fs (attempt %d)...", delay, backoff.attempt)
            await asyncio.sleep(delay)

            try:
                await connect_fn()
                await start_fn()
                return
            except Exception as e:
                logger.error("Reconnect failed: %s", e)
                self._circuit_breaker.record_failure()


__all__ = ["ReconnectionManager"]
