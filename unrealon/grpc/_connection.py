"""
gRPC connection management.

Handles channel creation, lifecycle, and state monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import grpc
from grpc import aio

from ._config import GRPCServiceConfig
from ._constants import (
    CONNECTION_STATE_CHECK_INTERVAL,
    KEEPALIVE_TIME_MS,
    KEEPALIVE_TIMEOUT_MS,
)
from .circuit_breaker import BackoffStrategy, CircuitBreaker
from .generated import unrealon_pb2_grpc

if TYPE_CHECKING:
    from grpc.aio import Channel

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages gRPC channel lifecycle and state monitoring.

    Provides:
    - Channel creation with optimized keepalive settings
    - TLS/insecure channel selection
    - Connection state watching (TRANSIENT_FAILURE, SHUTDOWN detection)
    - Automatic backoff strategy switching based on connection state
    """

    __slots__ = (
        "_config",
        "_channel",
        "_stub",
        "_connected",
        "_circuit_breaker",
        "_backoff",
        "_use_aggressive_backoff",
        "_state_watcher_task",
        "_running",
    )

    def __init__(
        self,
        config: GRPCServiceConfig,
        circuit_breaker: CircuitBreaker,
        use_aggressive_backoff: bool = False,
    ) -> None:
        """
        Initialize connection manager.

        Args:
            config: Service configuration
            circuit_breaker: Circuit breaker for failure tracking
            use_aggressive_backoff: Use aggressive backoff permanently
        """
        self._config = config
        self._circuit_breaker = circuit_breaker
        self._use_aggressive_backoff = use_aggressive_backoff

        self._channel: Channel | None = None
        self._stub: unrealon_pb2_grpc.UnrealonServiceStub | None = None
        self._connected: bool = False
        self._running: bool = False
        self._state_watcher_task: asyncio.Task[None] | None = None

        # Initialize backoff strategy
        if use_aggressive_backoff:
            self._backoff = BackoffStrategy.aggressive()
        else:
            self._backoff = BackoffStrategy.standard()

    @property
    def channel(self) -> Channel | None:
        """Get current gRPC channel."""
        return self._channel

    @property
    def stub(self) -> unrealon_pb2_grpc.UnrealonServiceStub | None:
        """Get gRPC stub."""
        return self._stub

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @is_connected.setter
    def is_connected(self, value: bool) -> None:
        """Set connection status."""
        self._connected = value

    @property
    def backoff(self) -> BackoffStrategy:
        """Get backoff strategy."""
        return self._backoff

    async def connect(self) -> None:
        """Establish gRPC channel with optimized keepalive settings."""
        options: list[tuple[str, int | bool]] = [
            # Faster keepalive (10s vs 30s) - matches CMDOP Go
            ("grpc.keepalive_time_ms", KEEPALIVE_TIME_MS),
            ("grpc.keepalive_timeout_ms", KEEPALIVE_TIMEOUT_MS),
            ("grpc.keepalive_permit_without_calls", True),
            ("grpc.enable_retries", 1),
            ("grpc.max_send_message_length", 32 * 1024 * 1024),
            ("grpc.max_receive_message_length", 32 * 1024 * 1024),
        ]

        if self._config.secure:
            credentials = grpc.ssl_channel_credentials()
            self._channel = aio.secure_channel(
                self._config.grpc_server,
                credentials,
                options=options,
            )
        else:
            self._channel = aio.insecure_channel(
                self._config.grpc_server,
                options=options,
            )

        self._stub = unrealon_pb2_grpc.UnrealonServiceStub(self._channel)
        logger.info("gRPC channel created to %s", self._config.grpc_server)

    async def disconnect(self) -> None:
        """Close gRPC channel."""
        self._running = False

        if self._state_watcher_task:
            self._state_watcher_task.cancel()
            try:
                await self._state_watcher_task
            except asyncio.CancelledError:
                pass

        if self._channel:
            await self._channel.close()
            self._channel = None

        self._connected = False
        logger.info("gRPC channel closed")

    def start_state_watcher(self) -> None:
        """Start connection state watcher task."""
        self._running = True
        self._state_watcher_task = asyncio.create_task(self._watch_connection_state())

    def stop_state_watcher(self) -> None:
        """Stop connection state watcher task."""
        self._running = False
        if self._state_watcher_task:
            self._state_watcher_task.cancel()

    async def _watch_connection_state(self) -> None:
        """
        Monitor gRPC channel connectivity state changes.

        Detects TRANSIENT_FAILURE and SHUTDOWN states to trigger faster reconnection.
        Based on CMDOP Go's watchConnectionState() pattern.
        """
        if not self._channel:
            return

        last_state: grpc.ChannelConnectivity | None = None

        while self._running:
            try:
                # Get current state without trying to connect
                current_state = self._channel.get_state(try_to_connect=False)

                if current_state != last_state:
                    logger.debug(
                        "Connection state changed: %s -> %s",
                        last_state.name if last_state else "None",
                        current_state.name,
                    )
                    last_state = current_state

                # Handle critical states
                if current_state == grpc.ChannelConnectivity.SHUTDOWN:
                    logger.error("Channel shutdown detected")
                    self._connected = False
                    self._circuit_breaker.record_failure()
                    break

                if current_state == grpc.ChannelConnectivity.TRANSIENT_FAILURE:
                    logger.warning("Transient failure detected, switching to aggressive backoff")
                    self._connected = False
                    # Switch to aggressive backoff for faster recovery
                    if not self._use_aggressive_backoff:
                        self._backoff = BackoffStrategy.aggressive()
                    self._circuit_breaker.record_failure()
                    # Close channel to trigger reconnection
                    if self._channel:
                        await self._channel.close()
                    break

                if current_state == grpc.ChannelConnectivity.READY:
                    # Restore standard backoff on successful connection
                    if not self._use_aggressive_backoff:
                        self._backoff = BackoffStrategy.standard()

                # Wait before next check
                await asyncio.sleep(CONNECTION_STATE_CHECK_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Connection state watcher error: %s", e)
                await asyncio.sleep(CONNECTION_STATE_CHECK_INTERVAL)

    def on_connection_success(self) -> None:
        """Handle successful connection."""
        self._connected = True
        self._circuit_breaker.record_success()
        self._backoff.reset()

    def on_connection_failure(self) -> None:
        """Handle connection failure."""
        self._connected = False
        self._circuit_breaker.record_failure()


__all__ = ["ConnectionManager"]
