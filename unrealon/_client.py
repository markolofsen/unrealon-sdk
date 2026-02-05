"""Main SDK client with unified interface using gRPC."""

from __future__ import annotations

import atexit
import logging
import signal
import threading
from types import FrameType
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from ._config import UnrealonConfig, configure
from .exceptions import RegistrationError, StopInterrupt
from .grpc.stream_service import GRPCStreamService
from .logging import CloudHandler, UnrealonLogger, get_logger
from .models import ServiceStatus

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class ServiceMetadata(BaseModel):
    """Metadata for service registration."""

    model_config = ConfigDict(extra="forbid")

    tags: list[str] = Field(default_factory=list)
    environment: str | None = None
    version: str | None = None
    custom: dict[str, str] = Field(default_factory=dict)


CommandHandler = Annotated[
    "Callable[[dict[str, Any]], dict[str, Any] | None]",
    "Command handler function",
]


class ServiceClient:
    """
    Main SDK client for service management via gRPC.

    Provides unified interface for:
    - Registration and deregistration (unary RPC)
    - Heartbeat (via bidirectional stream)
    - Logging (via bidirectional stream)
    - Command handling (via bidirectional stream)

    Example:
        ```python
        client = ServiceClient(
            api_key="pk_live_xxx",
            service_name="my-service",
        )

        with client:
            client.info("Service started")
            for item in items:
                process(item)
                client.increment_processed()
            client.info("Processing complete")
        ```
    """

    __slots__ = (
        "_config",
        "_service_id",
        "_is_started",
        "_is_paused",
        "_is_busy",
        "_shutdown_requested",
        "_grpc",
        "_original_sigint",
        "_original_sigterm",
        "_logger",
        "_cloud_handler",
        "_resume_event",
        "_log_level",
    )

    def __init__(
        self,
        api_key: str | None = None,
        service_name: str | None = None,
        *,
        grpc_server: str | None = None,
        grpc_secure: bool | None = None,
        dev_mode: bool = False,
        source_code: str | None = None,
        description: str | None = None,
        heartbeat_interval: int | None = None,
        log_batch_size: int | None = None,
        log_flush_interval: float | None = None,
        log_level: str = "INFO",
    ) -> None:
        """
        Initialize service client.

        Args:
            api_key: API key (or UNREALON_API_KEY env var)
            service_name: Service name (or UNREALON_SERVICE_NAME env var)
            grpc_server: gRPC server address (or UNREALON_GRPC_SERVER env var)
            grpc_secure: Use TLS for gRPC (or UNREALON_GRPC_SECURE env var)
            dev_mode: If True, use local gRPC server (localhost:50051)
            source_code: Source code identifier
            description: Service description
            heartbeat_interval: Heartbeat interval in seconds
            log_batch_size: Number of logs to batch before sending
            log_flush_interval: Max seconds to wait before flushing logs
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        config_kwargs: dict[str, object] = {}
        if api_key:
            config_kwargs["api_key"] = api_key
        if service_name:
            config_kwargs["service_name"] = service_name
        if dev_mode:
            config_kwargs["dev_mode"] = dev_mode
        if grpc_server:
            config_kwargs["grpc_server"] = grpc_server
        if grpc_secure is not None:
            config_kwargs["grpc_secure"] = grpc_secure
        if source_code:
            config_kwargs["source_code"] = source_code
        if description:
            config_kwargs["description"] = description
        if heartbeat_interval:
            config_kwargs["heartbeat_interval"] = heartbeat_interval
        if log_batch_size:
            config_kwargs["log_batch_size"] = log_batch_size
        if log_flush_interval:
            config_kwargs["log_flush_interval"] = log_flush_interval

        if config_kwargs:
            self._config = configure(**config_kwargs)
        else:
            from ._config import get_config

            self._config = get_config()

        self._service_id: str | None = None
        self._is_started: bool = False
        self._is_paused: bool = False
        self._is_busy: bool = False
        self._shutdown_requested: bool = False
        self._grpc: GRPCStreamService | None = None
        self._original_sigint: signal.Handlers | None = None
        self._original_sigterm: signal.Handlers | None = None
        self._resume_event: threading.Event = threading.Event()
        self._resume_event.set()  # Start as "not paused" (event is set)

        # Initialize logger with Rich console + file, cloud handler added on start
        self._log_level = log_level.upper()
        self._logger: UnrealonLogger = get_logger(
            name=self._config.service_name,
            level=self._log_level,  # type: ignore[arg-type]
            log_to_cloud=False,  # Will be connected after gRPC start
        )
        self._cloud_handler: CloudHandler = CloudHandler()
        self._cloud_handler.setLevel(getattr(logging, self._log_level))

    @property
    def grpc(self) -> GRPCStreamService:
        """Get gRPC stream service."""
        if self._grpc is None:
            self._grpc = GRPCStreamService(
                api_key=self._config.api_key,
                service_name=self._config.service_name,
                grpc_server=self._config.grpc_server or "localhost:50051",
                secure=self._config.grpc_secure or False,
                heartbeat_interval=float(self._config.heartbeat_interval),
                log_batch_size=self._config.log_batch_size,
                log_flush_interval=self._config.log_flush_interval,
                description=self._config.description or "",
                source_code=self._config.source_code or "",
            )
        return self._grpc

    @property
    def service_id(self) -> str | None:
        """Get registered service ID."""
        return self._service_id

    @property
    def is_started(self) -> bool:
        """Check if client is started."""
        return self._is_started

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown was requested."""
        return self._shutdown_requested

    @property
    def is_paused(self) -> bool:
        """Check if service is paused."""
        return self._is_paused

    @property
    def is_busy(self) -> bool:
        """Check if service is busy (actively processing)."""
        return self._is_busy

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._grpc.is_connected if self._grpc else False

    @property
    def status(self) -> str:
        """Get current service status."""
        return self._grpc.status if self._grpc else "initializing"

    @property
    def config(self) -> UnrealonConfig:
        """Get configuration."""
        return self._config

    @property
    def logger(self) -> UnrealonLogger:
        """Get the service logger.

        Returns a configured logger with Rich console output, file logging,
        and gRPC cloud logging (when connected).

        Example:
            ```python
            with ServiceClient(api_key="...", service_name="parser") as client:
                client.logger.info("Processing started", url="https://...")
                client.logger.error("Failed to parse", error_code=500)
            ```
        """
        return self._logger

    def start(
        self,
        *,
        description: str | None = None,
        metadata: ServiceMetadata | None = None,
    ) -> str:
        """
        Start service: register and start gRPC streaming.

        Args:
            description: Service description
            metadata: Additional metadata

        Returns:
            Service ID

        Raises:
            RegistrationError: If registration fails
        """
        if self._is_started:
            logger.warning("Client already started")
            if self._service_id is None:
                raise RegistrationError(message="Client started but no service_id")
            return self._service_id

        logger.info("Starting service client: name=%s", self._config.service_name)

        try:
            self._service_id = self.grpc.register(
                description=description or self._config.description,
                metadata=metadata.model_dump() if metadata else None,
            )
        except Exception as e:
            # Use clean error message without traceback chain
            raise RegistrationError(
                message=str(e),
                suggestion="Check that gRPC server is running and accessible",
            ) from None

        self.grpc.start_sync()
        self._is_started = True
        self._setup_signal_handlers()
        atexit.register(self._atexit_handler)

        # Register built-in command handlers for pause/resume/stop
        self.on_command("pause", self._handle_pause)
        self.on_command("resume", self._handle_resume)
        self.on_command("stop", self._handle_stop)

        # Connect cloud handler to gRPC service
        self._logger.addHandler(self._cloud_handler)
        self._cloud_handler.set_grpc_service(self.grpc)

        logger.info("Service client started: service_id=%s", self._service_id)
        return self._service_id

    def stop(self, reason: str | None = None) -> None:
        """
        Stop service: stop streaming and deregister.

        Args:
            reason: Reason for stopping (default: "normal_shutdown")
        """
        if not self._is_started:
            return

        logger.info("Stopping service client...")

        if self._grpc:
            self._grpc.update_status("stopping")
            self._grpc.stop_sync()

        if self._grpc and self._service_id:
            try:
                self._grpc.deregister(reason=reason)
                logger.info("Service deregistered")
            except Exception as e:
                logger.error("Failed to deregister: %s", e)

        self._is_started = False
        self._service_id = None
        logger.info("Service client stopped")

    def update_status(
        self, status: str | ServiceStatus, error_message: str | None = None
    ) -> None:
        """Update service status.

        Args:
            status: New status (ServiceStatus enum or valid status string)
            error_message: Optional error message (for ERROR status)

        Raises:
            ValueError: If status is not valid

        Valid statuses: initializing, running, paused, stopping, stopped, error, offline, stale
        """
        status_str = self._validate_status(status)
        if self._grpc:
            self._grpc.update_status(status_str, error_message)

    @staticmethod
    def _validate_status(status: str | ServiceStatus) -> str:
        """Validate and normalize status value."""
        if isinstance(status, ServiceStatus):
            return status.value
        valid_statuses = {s.value for s in ServiceStatus}
        status_lower = status.lower()
        if status_lower not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Valid statuses: {', '.join(sorted(valid_statuses))}"
            )
        return status_lower

    def increment_processed(self, count: int = 1) -> None:
        """Increment processed items counter."""
        if self._grpc:
            self._grpc.increment_processed(count)

    def increment_errors(self, count: int = 1) -> None:
        """Increment error counter."""
        if self._grpc:
            self._grpc.increment_errors(count)

    def debug(self, message: str, **extra: str | int | float | bool) -> None:
        """Log debug message.

        Logs to Rich console, file, and gRPC cloud (when connected).

        Args:
            message: Log message
            **extra: Extra structured data (user_id=123, action="login")
        """
        self._logger.debug(message, **extra)

    def info(self, message: str, **extra: str | int | float | bool) -> None:
        """Log info message.

        Logs to Rich console, file, and gRPC cloud (when connected).

        Args:
            message: Log message
            **extra: Extra structured data
        """
        self._logger.info(message, **extra)

    def warning(self, message: str, **extra: str | int | float | bool) -> None:
        """Log warning message.

        Logs to Rich console, file, and gRPC cloud (when connected).

        Args:
            message: Log message
            **extra: Extra structured data
        """
        self._logger.warning(message, **extra)

    def error(self, message: str, **extra: str | int | float | bool) -> None:
        """Log error message.

        Logs to Rich console, file, and gRPC cloud (when connected).

        Args:
            message: Log message
            **extra: Extra structured data
        """
        self._logger.error(message, **extra)

    def critical(self, message: str, **extra: str | int | float | bool) -> None:
        """Log critical message.

        Logs to Rich console, file, and gRPC cloud (when connected).

        Args:
            message: Log message
            **extra: Extra structured data
        """
        self._logger.critical(message, **extra)

    def on_command(
        self,
        command_type: str,
        handler: Callable[[dict[str, Any]], dict[str, Any] | None],
    ) -> None:
        """Register command handler for specific command type.

        This handler will be called for:
        - Manual commands from dashboard (Run, Pause, Resume, Stop)
        - Scheduled triggers with matching action_type (fallback)

        For example, `on_command("run", handler)` handles both manual Run
        button clicks AND scheduled runs with action_type="run".

        Args:
            command_type: Command type (e.g., "run", "pause", "resume", "stop")
            handler: Function(params: dict) -> dict | None
        """
        self.grpc.on_command(command_type, handler)

    def on_any_command(
        self, handler: Callable[[dict[str, Any]], dict[str, Any] | None]
    ) -> None:
        """Register default command handler for unhandled command types."""
        self.grpc.on_any_command(handler)

    def on_schedule(
        self,
        action_type: str,
        handler: Callable[..., dict[str, Any] | None],
    ) -> None:
        """Register handler for specific schedule action type.

        Use this only if you need schedule-specific behavior different from
        the command handler. This handler takes priority over command fallback.

        Note: If no schedule handler is registered for an action_type, the SDK
        automatically falls back to the command handler with the same name.
        For most cases, just use `on_command("run", handler)` for both manual
        and scheduled runs.

        Args:
            action_type: Schedule action type (e.g., "process", "custom")
            handler: Function(schedule: Schedule, params: dict) -> dict | None

        Example:
            ```python
            # Only needed if you want different behavior for scheduled vs manual
            @client.on_schedule("process")
            def handle_scheduled_process(schedule, params):
                # Has access to schedule.name, schedule.id, etc.
                items = do_work(schedule.action_params)
                return {"items_processed": len(items)}
            ```
        """
        self.grpc.on_schedule(action_type, handler)

    def on_any_schedule(
        self, handler: Callable[..., dict[str, Any] | None]
    ) -> None:
        """Register default handler for unhandled schedule action types.

        Args:
            handler: Function(schedule: Schedule, params: dict) -> dict | None

        Example:
            ```python
            @client.on_any_schedule
            def handle_any_schedule(schedule, params):
                logger.info(f"Schedule {schedule.name} triggered")
                return {}
            ```
        """
        self.grpc.on_any_schedule(handler)

    def _handle_pause(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle pause command from server."""
        self._logger.info("Command received: PAUSE", params=params)
        # Don't reset _is_busy - we need to remember if we were processing
        self._is_paused = True
        self._resume_event.clear()  # Block check_interrupt() wait
        self.update_status("paused")
        self._logger.info("Service paused", is_paused=self._is_paused, is_busy=self._is_busy)
        return {"status": "paused"}

    def _handle_resume(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resume command from server."""
        self._logger.info("Command received: RESUME", params=params)
        self._is_paused = False
        self._resume_event.set()  # Unblock check_interrupt() wait
        # Restore status based on whether we were processing before pause
        new_status = "busy" if self._is_busy else "idle"
        self.update_status(new_status)
        self._logger.info("Service resumed", is_paused=self._is_paused, is_busy=self._is_busy)
        return {"status": new_status}

    def _handle_stop(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle stop command from server."""
        self._logger.info("Command received: STOP", params=params)
        self._shutdown_requested = True
        self._is_busy = False
        self._resume_event.set()  # Unblock check_interrupt() wait (so it can raise StopInterrupt)
        self.update_status("stopping")
        self._logger.info("Service stopping", shutdown_requested=self._shutdown_requested)
        return {"status": "stopping"}

    def set_busy(self) -> None:
        """Mark service as busy (actively processing).

        Call this at the start of processing work.
        Status will be set to 'busy'.
        """
        if self._is_paused:
            logger.warning("Cannot set busy while paused")
            return
        if self._shutdown_requested:
            logger.warning("Cannot set busy while shutdown requested")
            return
        self._is_busy = True
        self.update_status("busy")

    def set_idle(self) -> None:
        """Mark service as idle (waiting for commands).

        Call this when processing is complete and waiting for next task.
        Status will be set to 'idle'.
        """
        if self._is_paused:
            return  # Stay paused
        if self._shutdown_requested:
            return  # Stay stopping
        self._is_busy = False
        self.update_status("idle")

    def request_shutdown(self) -> None:
        """Request graceful shutdown (sets flag for main loop to check)."""
        self._shutdown_requested = True
        logger.info("Shutdown requested")

    def check_interrupt(self) -> None:
        """Check for pause/stop and handle accordingly.

        Call this frequently in long-running operations to allow
        graceful interruption by commands from Unrealon dashboard.

        Behavior:
            - If stop requested: raises StopInterrupt
            - If paused: waits (blocks) until resumed or stopped

        Raises:
            StopInterrupt: If stop was requested

        Example:
            for item in items:
                m.client.check_interrupt()  # Will wait if paused, raise if stop
                process(item)
        """
        if self._shutdown_requested:
            # Use module-level logger to avoid Rich/cloud which may trigger time.sleep
            logger.info("check_interrupt: raising StopInterrupt")
            raise StopInterrupt()

        if self._is_paused:
            # Use module-level logger to avoid Rich/cloud which may trigger time.sleep
            logger.info("Paused, waiting for resume...")
            # Wait on event - unblocked by _handle_resume() or _handle_stop()
            # Uses threading.Event which is not affected by time.sleep patches
            self._resume_event.wait()
            # After wait unblocks, check if it was due to stop
            if self._shutdown_requested:
                logger.info("Stop requested while paused, raising StopInterrupt")
                raise StopInterrupt()
            logger.info("Resumed, continuing...")

    def __enter__(self) -> ServiceClient:
        """Start client on context enter."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Stop client on context exit."""
        if exc_type is not None:
            logger.error("Service exiting with error: %s", exc_val)
            self.update_status("error")
        self.stop()

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""
        import os

        def signal_handler(signum: int, _frame: FrameType | None) -> None:
            if self._shutdown_requested:
                # Second signal - force exit immediately
                logger.info("Received signal %d again, forcing exit...", signum)
                os._exit(1)
            logger.info("Received signal %d, requesting shutdown...", signum)
            self._shutdown_requested = True
            # Unblock any waiting threads
            self._resume_event.set()

        try:
            self._original_sigint = signal.signal(signal.SIGINT, signal_handler)
            self._original_sigterm = signal.signal(signal.SIGTERM, signal_handler)
        except ValueError:
            pass

    def _atexit_handler(self) -> None:
        """Handle process exit."""
        if self._is_started:
            self.stop()


class AsyncServiceClient:
    """Async version of ServiceClient using gRPC."""

    __slots__ = (
        "_config",
        "_service_id",
        "_is_started",
        "_shutdown_requested",
        "_grpc",
        "_logger",
        "_cloud_handler",
        "_log_level",
    )

    def __init__(
        self,
        api_key: str | None = None,
        service_name: str | None = None,
        *,
        grpc_server: str | None = None,
        grpc_secure: bool | None = None,
        dev_mode: bool = False,
        source_code: str | None = None,
        description: str | None = None,
        log_level: str = "INFO",
    ) -> None:
        """Initialize async service client."""
        config_kwargs: dict[str, object] = {}
        if api_key:
            config_kwargs["api_key"] = api_key
        if service_name:
            config_kwargs["service_name"] = service_name
        if dev_mode:
            config_kwargs["dev_mode"] = dev_mode
        if grpc_server:
            config_kwargs["grpc_server"] = grpc_server
        if grpc_secure is not None:
            config_kwargs["grpc_secure"] = grpc_secure
        if source_code:
            config_kwargs["source_code"] = source_code
        if description:
            config_kwargs["description"] = description

        if config_kwargs:
            self._config = configure(**config_kwargs)
        else:
            from ._config import get_config

            self._config = get_config()

        self._service_id: str | None = None
        self._is_started: bool = False
        self._shutdown_requested: bool = False
        self._grpc: GRPCStreamService | None = None

        # Initialize logger with Rich console + file, cloud handler added on start
        self._log_level = log_level.upper()
        self._logger: UnrealonLogger = get_logger(
            name=self._config.service_name,
            level=self._log_level,  # type: ignore[arg-type]
            log_to_cloud=False,
        )
        self._cloud_handler: CloudHandler = CloudHandler()
        self._cloud_handler.setLevel(getattr(logging, self._log_level))

    @property
    def grpc(self) -> GRPCStreamService:
        """Get gRPC stream service."""
        if self._grpc is None:
            self._grpc = GRPCStreamService(
                api_key=self._config.api_key,
                service_name=self._config.service_name,
                grpc_server=self._config.grpc_server or "localhost:50051",
                secure=self._config.grpc_secure or False,
                heartbeat_interval=float(self._config.heartbeat_interval),
                log_batch_size=self._config.log_batch_size,
                log_flush_interval=self._config.log_flush_interval,
                description=self._config.description or "",
                source_code=self._config.source_code or "",
            )
        return self._grpc

    @property
    def service_id(self) -> str | None:
        """Get registered service ID."""
        return self._service_id

    @property
    def is_started(self) -> bool:
        """Check if client is started."""
        return self._is_started

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown was requested."""
        return self._shutdown_requested

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._grpc.is_connected if self._grpc else False

    @property
    def status(self) -> str:
        """Get current service status."""
        return self._grpc.status if self._grpc else "initializing"

    @property
    def logger(self) -> UnrealonLogger:
        """Get the service logger."""
        return self._logger

    async def start(
        self,
        *,
        description: str | None = None,
        metadata: ServiceMetadata | None = None,
    ) -> str:
        """Start service (async)."""
        if self._is_started:
            if self._service_id is None:
                raise RegistrationError(message="Client started but no service_id")
            return self._service_id

        logger.info("Starting async service client: name=%s", self._config.service_name)

        try:
            self._service_id = await self.grpc.register_async(
                description=description or self._config.description,
                metadata=metadata.model_dump() if metadata else None,
            )
        except Exception as e:
            raise RegistrationError(
                message=f"Failed to register service: {e}",
                original_error=e,
            ) from e

        import asyncio

        asyncio.create_task(self.grpc.start())

        self._is_started = True

        # Connect cloud handler to gRPC service
        self._logger.addHandler(self._cloud_handler)
        self._cloud_handler.set_grpc_service(self.grpc)

        logger.info("Async service client started: service_id=%s", self._service_id)
        return self._service_id

    async def stop(self, reason: str | None = None) -> None:
        """Stop service (async)."""
        if not self._is_started:
            return

        logger.info("Stopping async service client...")

        if self._grpc:
            await self._grpc.stop()

        if self._grpc and self._service_id:
            try:
                await self._grpc.deregister_async(reason=reason)
            except Exception as e:
                logger.error("Failed to deregister: %s", e)

        self._is_started = False
        self._service_id = None
        logger.info("Async service client stopped")

    def debug(self, message: str, **extra: str | int | float | bool) -> None:
        """Log debug message."""
        self._logger.debug(message, **extra)

    def info(self, message: str, **extra: str | int | float | bool) -> None:
        """Log info message."""
        self._logger.info(message, **extra)

    def warning(self, message: str, **extra: str | int | float | bool) -> None:
        """Log warning message."""
        self._logger.warning(message, **extra)

    def error(self, message: str, **extra: str | int | float | bool) -> None:
        """Log error message."""
        self._logger.error(message, **extra)

    def critical(self, message: str, **extra: str | int | float | bool) -> None:
        """Log critical message."""
        self._logger.critical(message, **extra)

    def on_command(
        self,
        command_type: str,
        handler: Callable[[dict[str, Any]], dict[str, Any] | None],
    ) -> None:
        """Register command handler (also handles scheduled triggers with same action_type)."""
        self.grpc.on_command(command_type, handler)

    def on_any_command(self, handler: Callable[[dict[str, Any]], dict[str, Any] | None]) -> None:
        """Register default command handler."""
        self.grpc.on_any_command(handler)

    def on_schedule(
        self,
        action_type: str,
        handler: Callable[..., dict[str, Any] | None],
    ) -> None:
        """Register schedule-specific handler (takes priority over command fallback)."""
        self.grpc.on_schedule(action_type, handler)

    def on_any_schedule(
        self, handler: Callable[..., dict[str, Any] | None]
    ) -> None:
        """Register default handler for unhandled schedule action types."""
        self.grpc.on_any_schedule(handler)

    def update_status(
        self, status: str | ServiceStatus, error_message: str | None = None
    ) -> None:
        """Update service status.

        Args:
            status: New status (ServiceStatus enum or valid status string)
            error_message: Optional error message (for ERROR status)

        Raises:
            ValueError: If status is not valid

        Valid statuses: initializing, running, paused, stopping, stopped, error, offline, stale
        """
        status_str = self._validate_status(status)
        if self._grpc:
            self._grpc.update_status(status_str, error_message)

    @staticmethod
    def _validate_status(status: str | ServiceStatus) -> str:
        """Validate and normalize status value."""
        if isinstance(status, ServiceStatus):
            return status.value
        valid_statuses = {s.value for s in ServiceStatus}
        status_lower = status.lower()
        if status_lower not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Valid statuses: {', '.join(sorted(valid_statuses))}"
            )
        return status_lower

    def increment_processed(self, count: int = 1) -> None:
        """Increment processed items counter."""
        if self._grpc:
            self._grpc.increment_processed(count)

    def increment_errors(self, count: int = 1) -> None:
        """Increment error counter."""
        if self._grpc:
            self._grpc.increment_errors(count)

    def request_shutdown(self) -> None:
        """Request graceful shutdown (sets flag for main loop to check)."""
        self._shutdown_requested = True
        logger.info("Shutdown requested")

    async def __aenter__(self) -> AsyncServiceClient:
        """Start client on async context enter."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Stop client on async context exit."""
        await self.stop()


__all__ = ["ServiceClient", "AsyncServiceClient", "ServiceMetadata"]
