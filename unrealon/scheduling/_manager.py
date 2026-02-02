"""
Schedule Manager for SDK.

Manages schedule handlers and execution on the client side.
Server sends schedule triggers via commands, SDK executes handlers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from ._models import Schedule, ScheduleResult, ScheduleRunStatus

logger = logging.getLogger(__name__)

# Handler types
ScheduleHandler = Callable[[Schedule, dict[str, Any]], dict[str, Any] | None]
AsyncScheduleHandler = Callable[[Schedule, dict[str, Any]], Awaitable[dict[str, Any] | None]]


class ScheduleManager:
    """
    Manages schedule execution on SDK client.

    Server pushes schedule configuration via ConfigUpdate.
    Server triggers schedules via Command (type="schedule:*").
    SDK executes registered handlers and sends ScheduleAck.

    Fallback behavior: If no schedule-specific handler is registered for an
    action_type (e.g., "run"), the manager will look for a command handler
    with the same name. This allows `on_command("run", handler)` to handle
    both manual runs and scheduled runs with action_type="run".

    Example:
        ```python
        client = ServiceClient(...)

        # This handler will be used for both:
        # - Manual "run" commands from dashboard
        # - Scheduled runs with action_type="run"
        @client.on_command("run")
        def handle_run(params: dict) -> dict:
            process_items()
            return {"status": "ok"}

        # Or register schedule-specific handler (takes priority)
        @client.on_schedule("process")
        def handle_process(schedule: Schedule, params: dict) -> dict:
            return {"items": 100}
        ```
    """

    __slots__ = (
        "_schedules",
        "_config_version",
        "_handlers",
        "_default_handler",
        "_ack_callback",
        "_command_handler_getter",
    )

    def __init__(self) -> None:
        """Initialize schedule manager."""
        self._schedules: dict[str, Schedule] = {}
        self._config_version: int = 0
        self._handlers: dict[str, ScheduleHandler | AsyncScheduleHandler] = {}
        self._default_handler: ScheduleHandler | AsyncScheduleHandler | None = None
        self._ack_callback: Callable[[ScheduleResult], None] | None = None
        self._command_handler_getter: Callable[[str], Any] | None = None

    @property
    def schedules(self) -> dict[str, Schedule]:
        """Get current schedules by ID."""
        return self._schedules.copy()

    @property
    def config_version(self) -> int:
        """Get current config version."""
        return self._config_version

    def set_ack_callback(self, callback: Callable[[ScheduleResult], None]) -> None:
        """Set callback for sending schedule acknowledgments."""
        self._ack_callback = callback

    def set_command_handler_getter(
        self, getter: Callable[[str], Any] | None
    ) -> None:
        """
        Set function to get command handlers for fallback.

        This allows schedule manager to fall back to command handlers
        when no schedule-specific handler is registered.

        Args:
            getter: Function(command_type: str) -> handler or None
        """
        self._command_handler_getter = getter

    def update_schedules(self, schedule_config) -> None:
        """
        Update schedules from server ConfigUpdate.

        Args:
            schedule_config: ScheduleConfig protobuf message
        """
        if not schedule_config:
            return

        new_version = schedule_config.config_version
        if new_version <= self._config_version:
            logger.debug(
                "Ignoring schedule config (version %d <= %d)",
                new_version,
                self._config_version,
            )
            return

        self._schedules.clear()

        for proto_schedule in schedule_config.schedules:
            schedule = Schedule.from_proto(proto_schedule)
            self._schedules[schedule.id] = schedule
            logger.debug("Schedule loaded: %s (%s)", schedule.name, schedule.id)

        self._config_version = new_version
        logger.info(
            "Schedule config updated: %d schedules, version %d",
            len(self._schedules),
            new_version,
        )

    def register(
        self,
        action_type: str,
        handler: ScheduleHandler | AsyncScheduleHandler,
    ) -> None:
        """
        Register handler for specific action type.

        Args:
            action_type: Schedule action type (e.g., "process", "pause")
            handler: Handler function
        """
        self._handlers[action_type] = handler
        logger.debug("Schedule handler registered: %s", action_type)

    def register_default(
        self,
        handler: ScheduleHandler | AsyncScheduleHandler,
    ) -> None:
        """
        Register default handler for unhandled action types.

        Args:
            handler: Default handler function
        """
        self._default_handler = handler
        logger.debug("Default schedule handler registered")

    async def execute(
        self,
        schedule_id: str,
        run_id: str,
        action_type: str,
        params: dict[str, Any],
    ) -> ScheduleResult:
        """
        Execute schedule with registered handler.

        Called when server sends schedule:* command.

        Args:
            schedule_id: Schedule ID
            run_id: Unique run ID for this execution
            action_type: Action type from schedule
            params: Action parameters

        Returns:
            ScheduleResult with execution outcome
        """
        start_time = time.perf_counter()

        # Get schedule info
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            # Create minimal schedule for handler
            schedule = Schedule(
                id=schedule_id,
                name=params.get("schedule_name", "unknown"),
                enabled=True,
                action_type=action_type,
                action_params=params,
            )

        # Find handler with fallback to command handlers
        handler = self._handlers.get(action_type)
        use_command_handler = False

        if not handler:
            # Try fallback to command handler
            if self._command_handler_getter:
                command_handler = self._command_handler_getter(action_type)
                if command_handler:
                    handler = command_handler
                    use_command_handler = True
                    logger.debug(
                        "Using command handler as fallback for schedule action: %s",
                        action_type,
                    )

        if not handler:
            handler = self._default_handler

        if not handler:
            logger.warning("No handler for schedule action type: %s", action_type)
            return ScheduleResult(
                schedule_id=schedule_id,
                run_id=run_id,
                status=ScheduleRunStatus.SKIPPED,
                error=f"No handler for action type: {action_type}",
            )

        # Execute handler
        try:
            if use_command_handler:
                # Command handlers take only params
                if asyncio.iscoroutinefunction(handler):
                    result_data = await handler(params)
                else:
                    result_data = handler(params)
            else:
                # Schedule handlers take (schedule, params)
                if asyncio.iscoroutinefunction(handler):
                    result_data = await handler(schedule, params)
                else:
                    result_data = handler(schedule, params)

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            items_processed = 0
            if isinstance(result_data, dict):
                items_processed = result_data.get("items_processed", 0)

            result = ScheduleResult(
                schedule_id=schedule_id,
                run_id=run_id,
                status=ScheduleRunStatus.COMPLETED,
                result=result_data,
                items_processed=items_processed,
                duration_ms=duration_ms,
            )

            logger.info(
                "Schedule executed: %s (run=%s, duration=%dms, items=%d)",
                schedule.name,
                run_id,
                duration_ms,
                items_processed,
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            result = ScheduleResult(
                schedule_id=schedule_id,
                run_id=run_id,
                status=ScheduleRunStatus.TIMEOUT,
                error="Handler timed out",
                duration_ms=duration_ms,
            )
            logger.error("Schedule timeout: %s (run=%s)", schedule.name, run_id)

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            result = ScheduleResult(
                schedule_id=schedule_id,
                run_id=run_id,
                status=ScheduleRunStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms,
            )
            logger.error(
                "Schedule failed: %s (run=%s, error=%s)",
                schedule.name,
                run_id,
                e,
                exc_info=True,
            )

        # Send ack via callback
        if self._ack_callback:
            try:
                self._ack_callback(result)
            except Exception as e:
                logger.error("Failed to send schedule ack: %s", e)

        return result


__all__ = ["ScheduleManager", "ScheduleHandler", "AsyncScheduleHandler"]
