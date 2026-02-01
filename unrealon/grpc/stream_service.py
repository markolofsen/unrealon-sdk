"""
gRPC Stream Service for Unrealon SDK.

Provides bidirectional streaming replacing HTTP polling.

Implements enterprise-grade patterns:
- Circuit breaker for connection resilience
- Exponential backoff with jitter
- Timeout-wrapped stream operations
- Heartbeat failure counting
- Silence detection
"""

from __future__ import annotations

import asyncio
import logging
from threading import Thread
from typing import TYPE_CHECKING, Any

from grpc import aio

from ..scheduling import ScheduleManager, ScheduleResult, ScheduleRunStatus
from ._config import RECEIVE_TIMEOUT, SEND_TIMEOUT, SILENCE_TIMEOUT, GRPCServiceConfig
from ._connection import ConnectionManager
from ._handlers import CommandRegistry
from ._messaging import MessageGenerator
from ._reconnect import ReconnectionManager
from ._registration import RegistrationManager
from ._types import CommandHandler
from .circuit_breaker import BackoffStrategy, CircuitBreaker, CircuitBreakerConfig
from .generated import unrealon_pb2

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GRPCStreamService:
    """
    Single gRPC bidirectional stream for SDK <-> Server communication.

    Replaces:
    - HeartbeatService (30s polling)
    - CommandService (10s polling)
    - LoggerService (batch HTTP POST)
    - RegistrarService (HTTP POST register/deregister)

    With single persistent connection providing:
    - Service registration via unary RPC
    - Immediate command delivery
    - Real-time log streaming
    - Low-latency heartbeat

    Enterprise patterns:
    - Circuit breaker for fail-fast behavior
    - Exponential backoff with jitter
    - Heartbeat failure counting
    - Silence detection timeout
    - Timeout-wrapped operations
    """

    __slots__ = (
        "_config",
        "_connection",
        "_registration",
        "_messaging",
        "_reconnection",
        "_command_registry",
        "_schedule_manager",
        "_running",
        "_status",
        "_items_processed",
        "_errors_count",
        "_loop",
        "_thread",
        "_circuit_breaker",
    )

    def __init__(
        self,
        api_key: str,
        service_name: str,
        grpc_server: str = "localhost:50051",
        secure: bool = False,
        heartbeat_interval: float = 30.0,
        log_batch_size: int = 50,
        log_flush_interval: float = 5.0,
        description: str = "",
        source_code: str = "",
        # Phase 1 parameters
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 60.0,
        send_timeout: float = SEND_TIMEOUT,
        receive_timeout: float = RECEIVE_TIMEOUT,
        silence_timeout: float = SILENCE_TIMEOUT,
        backoff_jitter: float = 0.1,
        # Phase 2 parameters
        use_aggressive_backoff: bool = False,
    ) -> None:
        """
        Initialize gRPC stream service.

        Args:
            api_key: API key for authentication
            service_name: Service name for registration
            grpc_server: gRPC server address (host:port)
            secure: Use TLS for gRPC connection
            heartbeat_interval: Heartbeat interval in seconds
            log_batch_size: Number of logs to batch before sending
            log_flush_interval: Max seconds to wait before flushing logs
            description: Service description
            source_code: Source code identifier
            circuit_failure_threshold: Failures before circuit opens
            circuit_recovery_timeout: Seconds before circuit tests recovery
            send_timeout: Timeout for send operations
            receive_timeout: Timeout for receive operations
            silence_timeout: Max seconds without messages before reconnect
            backoff_jitter: Jitter factor for backoff (0.1 = ±10%)
            use_aggressive_backoff: Use aggressive backoff for faster recovery
        """
        self._config = GRPCServiceConfig(
            api_key=api_key,
            service_name=service_name,
            grpc_server=grpc_server,
            secure=secure,
            heartbeat_interval=heartbeat_interval,
            log_batch_size=log_batch_size,
            log_flush_interval=log_flush_interval,
            description=description,
            source_code=source_code,
            circuit_failure_threshold=circuit_failure_threshold,
            circuit_recovery_timeout=circuit_recovery_timeout,
            send_timeout=send_timeout,
            receive_timeout=receive_timeout,
            silence_timeout=silence_timeout,
            backoff_jitter=backoff_jitter,
            use_aggressive_backoff=use_aggressive_backoff,
        )

        # Status tracking
        self._running: bool = False
        self._status: str = "initializing"
        self._items_processed: int = 0
        self._errors_count: int = 0

        # Background thread for sync usage
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: Thread | None = None

        # Circuit breaker
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=circuit_failure_threshold,
                recovery_timeout=circuit_recovery_timeout,
            )
        )

        # Initialize components
        self._connection = ConnectionManager(
            config=self._config,
            circuit_breaker=self._circuit_breaker,
            use_aggressive_backoff=use_aggressive_backoff,
        )

        self._registration = RegistrationManager(config=self._config)

        self._messaging = MessageGenerator(
            config=self._config,
            service_id_getter=lambda: self._registration.service_id,
            status_getter=lambda: self._status,
            metrics_getter=lambda: (self._items_processed, self._errors_count),
        )

        self._reconnection = ReconnectionManager(
            config=self._config,
            circuit_breaker=self._circuit_breaker,
            backoff_getter=lambda: self._connection.backoff,
        )

        self._command_registry = CommandRegistry()
        self._schedule_manager = ScheduleManager()
        self._schedule_manager.set_ack_callback(self._send_schedule_ack)

    # ═══════════════════════════════════════════════════════════
    # PROPERTIES
    # ═══════════════════════════════════════════════════════════

    @property
    def service_id(self) -> str | None:
        """Get registered service ID."""
        return self._registration.service_id

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._config.service_name

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker instance for monitoring."""
        return self._circuit_breaker

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connection.is_connected

    @property
    def status(self) -> str:
        """Get current status."""
        return self._status

    # ═══════════════════════════════════════════════════════════
    # REGISTRATION
    # ═══════════════════════════════════════════════════════════

    async def register_async(
        self,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Register service via unary RPC (async)."""
        if not self._connection.channel:
            await self._connection.connect()

        service_id, initial_config = await self._registration.register_async(
            stub=self._connection.stub,
            description=description,
            metadata=metadata,
        )

        self._circuit_breaker.record_success()

        if initial_config:
            self._apply_config(initial_config)

        return service_id

    def register(
        self,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Register service via unary RPC (sync)."""
        # Ensure we have an event loop for sync operations
        if not self._loop:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        async def _do_register():
            # Ensure connection is established
            if not self._connection.channel:
                await self._connection.connect()

            service_id, initial_config = await self._registration.register_async(
                stub=self._connection.stub,
                description=description,
                metadata=metadata,
            )

            self._circuit_breaker.record_success()

            if initial_config:
                self._apply_config(initial_config)

            return service_id

        return self._loop.run_until_complete(_do_register())

    async def deregister_async(self, reason: str | None = None) -> bool:
        """Deregister service via unary RPC (async)."""
        if not self._connection.channel or not self._connection.stub:
            # Silent return if already disconnected (normal shutdown)
            logger.debug("Skipping deregister: not connected")
            return False

        return await self._registration.deregister_async(
            stub=self._connection.stub,
            reason=reason,
        )

    def deregister(self, reason: str | None = None) -> bool:
        """Deregister service via unary RPC (sync)."""
        if not self._loop:
            # Silent return if no loop (normal shutdown)
            logger.debug("Skipping deregister: no event loop")
            return False

        if self._loop.is_running():
            # Schedule in running loop
            future = asyncio.run_coroutine_threadsafe(
                self.deregister_async(reason),
                self._loop,
            )
            return future.result(timeout=10.0)
        else:
            # Run directly
            return self._loop.run_until_complete(self.deregister_async(reason))

    # ═══════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    async def connect(self) -> None:
        """Establish gRPC channel."""
        await self._connection.connect()

    async def start(self) -> None:
        """Start bidirectional streaming with circuit breaker protection."""
        if not self._connection.channel:
            await self._connection.connect()

        # Check circuit breaker before attempting connection
        if not self._circuit_breaker.allow_request():
            logger.warning(
                "Circuit breaker open, waiting %.1fs before retry",
                self._circuit_breaker.recovery_timeout,
            )
            await asyncio.sleep(self._circuit_breaker.recovery_timeout)

        self._running = True
        self._status = "running"

        # Start monitoring tasks
        self._reconnection.start_silence_detector(self._on_silence_timeout)
        self._connection.start_state_watcher()

        # Auth metadata
        metadata = [("x-api-key", self._config.api_key)]

        try:
            # Start bidirectional stream
            response_stream = self._connection.stub.Connect(
                self._messaging.generate_messages(lambda: self._running),
                metadata=metadata,
            )

            self._connection.on_connection_success()
            self._reconnection.consecutive_heartbeat_failures = 0
            logger.info("gRPC stream connected for service %s", self._registration.service_id)

            # Process incoming messages
            async for message in response_stream:
                self._reconnection.update_last_message_time()
                await self._handle_server_message(message)

        except aio.AioRpcError as e:
            logger.error("gRPC error: %s - %s", e.code(), e.details())
            self._connection.on_connection_failure()
            if self._running:
                await self._reconnect()
        except asyncio.CancelledError:
            logger.info("Stream cancelled")
            self._connection.is_connected = False
        except Exception as e:
            logger.error("Stream error: %s", e, exc_info=True)
            self._connection.on_connection_failure()
        finally:
            self._connection.is_connected = False
            self._reconnection.stop_silence_detector()
            self._connection.stop_state_watcher()

    async def stop(self) -> None:
        """Stop streaming and close channel."""
        self._status = "stopping"

        # Stop monitoring
        self._reconnection.stop_silence_detector()
        self._connection.stop_state_watcher()

        # Flush remaining logs and wait for queue to drain (while stream is still running)
        await self._flush_logs_now()
        await self._wait_for_queue_drain(timeout=3.0)

        # Now stop the stream
        self._running = False

        # Close connection
        await self._connection.disconnect()
        logger.info("gRPC stream stopped")

    # ═══════════════════════════════════════════════════════════
    # SYNC API
    # ═══════════════════════════════════════════════════════════

    def start_sync(self) -> None:
        """Start gRPC stream in background thread (sync API)."""
        # Ensure we have an event loop
        if not self._loop:
            self._loop = asyncio.new_event_loop()

        def run_loop() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self.start())

        self._thread = Thread(target=run_loop, daemon=True)
        self._thread.start()

    def stop_sync(self) -> None:
        """Stop gRPC stream (sync API)."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.stop(), self._loop)
            if self._thread:
                self._thread.join(timeout=5.0)

    # ═══════════════════════════════════════════════════════════
    # MESSAGE HANDLING
    # ═══════════════════════════════════════════════════════════

    async def _handle_server_message(self, message: unrealon_pb2.ServerMessage) -> None:
        """Handle incoming server messages."""
        payload_type = message.WhichOneof("payload")

        if payload_type == "command":
            await self._execute_command(message.command)
        elif payload_type == "heartbeat_ack":
            self._reconnection.reset_heartbeat_failures()
            logger.debug("Heartbeat ack: %s", message.heartbeat_ack.server_time)
        elif payload_type == "config_update":
            self._apply_config(message.config_update)
        elif payload_type == "server_status":
            logger.info("Server status: %s", message.server_status.message)

    async def _execute_command(self, command: unrealon_pb2.Command) -> None:
        """Execute command and send acknowledgment."""
        # Check if this is a schedule command
        if command.type.startswith("schedule:"):
            await self._execute_schedule_command(command)
            return

        # Send acknowledgment
        try:
            ack_msg = self._messaging.create_command_ack(
                command_id=command.id,
                status=unrealon_pb2.ACKNOWLEDGED,
            )
            await asyncio.wait_for(
                self._messaging.outgoing_queue.put(ack_msg),
                timeout=self._config.send_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Timeout sending command ack for %s", command.id)
            return

        # Execute via registry
        status, result, error = await self._command_registry.execute(command)

        # Send result
        try:
            result_msg = self._messaging.create_command_ack(
                command_id=command.id,
                status=status,
                result=result,
                error=error,
            )
            await asyncio.wait_for(
                self._messaging.outgoing_queue.put(result_msg),
                timeout=self._config.send_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Timeout sending command result for %s", command.id)

    async def _execute_schedule_command(self, command: unrealon_pb2.Command) -> None:
        """Execute schedule command and send ScheduleAck."""
        import json

        # Parse command params
        try:
            params = json.loads(command.params) if command.params else {}
        except json.JSONDecodeError:
            params = {}

        # Extract schedule info
        schedule_id = params.get("schedule_id", "")
        run_id = params.get("run_id", command.id)
        action_type = command.type.replace("schedule:", "")

        # Send STARTED ack
        self._send_schedule_ack(ScheduleResult(
            schedule_id=schedule_id,
            run_id=run_id,
            status=ScheduleRunStatus.STARTED,
        ))

        # Execute via schedule manager (result ack is sent via callback)
        await self._schedule_manager.execute(
            schedule_id=schedule_id,
            run_id=run_id,
            action_type=action_type,
            params=params,
        )

    def _apply_config(self, config: unrealon_pb2.ConfigUpdate) -> None:
        """Apply config update from server."""
        logger.info(
            "Config update received: heartbeat=%ss, log_batch=%s",
            config.heartbeat_interval_seconds,
            config.log_batch_size,
        )

        # Update schedule config if present
        if config.HasField("schedule_config"):
            self._schedule_manager.update_schedules(config.schedule_config)

    def _send_schedule_ack(self, result: ScheduleResult) -> None:
        """Send schedule acknowledgment to server."""
        import json

        # Map ScheduleRunStatus to proto enum
        status_map = {
            ScheduleRunStatus.UNSPECIFIED: unrealon_pb2.SCHEDULE_RUN_STATUS_UNSPECIFIED,
            ScheduleRunStatus.STARTED: unrealon_pb2.SCHEDULE_STARTED,
            ScheduleRunStatus.COMPLETED: unrealon_pb2.SCHEDULE_COMPLETED,
            ScheduleRunStatus.FAILED: unrealon_pb2.SCHEDULE_FAILED,
            ScheduleRunStatus.SKIPPED: unrealon_pb2.SCHEDULE_SKIPPED,
            ScheduleRunStatus.TIMEOUT: unrealon_pb2.SCHEDULE_TIMEOUT,
        }

        msg = self._messaging.create_schedule_ack(
            schedule_id=result.schedule_id,
            run_id=result.run_id,
            status=status_map.get(result.status, unrealon_pb2.SCHEDULE_RUN_STATUS_UNSPECIFIED),
            result=json.dumps(result.result) if result.result else "",
            error=result.error,
            items_processed=result.items_processed,
            duration_ms=result.duration_ms,
        )

        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._messaging.outgoing_queue.put(msg),
                self._loop,
            )

    # ═══════════════════════════════════════════════════════════
    # RECONNECTION
    # ═══════════════════════════════════════════════════════════

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff and circuit breaker."""
        await self._reconnection.reconnect_loop(
            running_getter=lambda: self._running,
            connect_fn=self._connection.connect,
            start_fn=self.start,
        )

    async def _on_silence_timeout(self) -> None:
        """Handle silence timeout."""
        if self._connection.channel:
            await self._connection.channel.close()

    # ═══════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════

    def on_command(self, command_type: str, handler: CommandHandler) -> None:
        """Register command handler for specific command type."""
        self._command_registry.register(command_type, handler)

    def on_any_command(self, handler: CommandHandler) -> None:
        """Register default command handler for unhandled command types."""
        self._command_registry.register_default(handler)

    def on_schedule(self, action_type: str, handler: Any) -> None:
        """Register handler for specific schedule action type.

        Args:
            action_type: Schedule action type (e.g., "process", "pause")
            handler: Function(schedule: Schedule, params: dict) -> dict | None
        """
        self._schedule_manager.register(action_type, handler)

    def on_any_schedule(self, handler: Any) -> None:
        """Register default handler for unhandled schedule action types.

        Args:
            handler: Function(schedule: Schedule, params: dict) -> dict | None
        """
        self._schedule_manager.register_default(handler)

    def log(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        """Add log entry to buffer."""
        self._messaging.add_log(level, message, extra)

    def debug(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log debug message."""
        self.log("debug", message, extra)

    def info(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log info message."""
        self.log("info", message, extra)

    def warning(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log warning message."""
        self.log("warning", message, extra)

    def error(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log error message."""
        self.log("error", message, extra)

    def critical(self, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log critical message."""
        self.log("critical", message, extra)

    def increment_processed(self, count: int = 1) -> None:
        """Increment items processed counter."""
        self._items_processed += count

    def increment_errors(self, count: int = 1) -> None:
        """Increment errors counter."""
        self._errors_count += count

    def update_status(self, status: str, error_message: str | None = None) -> None:
        """Update service status."""
        self._status = status

        if self._loop:
            msg = self._messaging.create_status_update(status, error_message)
            asyncio.run_coroutine_threadsafe(
                self._messaging.outgoing_queue.put(msg),
                self._loop,
            )

    # ═══════════════════════════════════════════════════════════
    # LOG BATCHING
    # ═══════════════════════════════════════════════════════════

    async def _flush_logs_now(self) -> None:
        """Flush all buffered logs immediately."""
        msg = self._messaging.flush_logs()
        if msg:
            try:
                await asyncio.wait_for(
                    self._messaging.outgoing_queue.put(msg),
                    timeout=self._config.send_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout flushing logs on shutdown")

    async def _wait_for_queue_drain(self, timeout: float = 3.0) -> None:
        """Wait for outgoing queue to drain (logs to be sent)."""
        start = asyncio.get_event_loop().time()
        while not self._messaging.outgoing_queue.empty():
            if asyncio.get_event_loop().time() - start > timeout:
                logger.warning(
                    "Timeout waiting for queue drain, %d messages remaining",
                    self._messaging.outgoing_queue.qsize(),
                )
                break
            await asyncio.sleep(0.1)


__all__ = [
    "GRPCStreamService",
    "GRPCServiceConfig",
    "CommandHandler",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "BackoffStrategy",
]
