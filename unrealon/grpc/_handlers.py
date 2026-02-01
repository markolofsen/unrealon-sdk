"""
Command handler registry for gRPC stream service.

Manages command handlers and provides execution with proper response handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from ._types import CommandHandler
from .generated import unrealon_pb2

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Registry for command handlers.

    Manages both type-specific handlers and a default fallback handler.
    """

    __slots__ = ("_handlers", "_default_handler")

    def __init__(self) -> None:
        """Initialize command registry."""
        self._handlers: dict[str, CommandHandler] = {}
        self._default_handler: CommandHandler | None = None

    def register(self, command_type: str, handler: CommandHandler) -> None:
        """Register handler for specific command type.

        Args:
            command_type: Command type to handle
            handler: Handler function (sync or async)
        """
        self._handlers[command_type] = handler
        logger.debug("Registered handler for command: %s", command_type)

    def register_default(self, handler: CommandHandler) -> None:
        """Register default handler for unhandled command types.

        Args:
            handler: Default handler function
        """
        self._default_handler = handler
        logger.debug("Registered default command handler")

    def get_handler(self, command_type: str) -> CommandHandler | None:
        """Get handler for command type.

        Args:
            command_type: Command type to look up

        Returns:
            Handler function or None if not found
        """
        handler = self._handlers.get(command_type)
        if not handler and self._default_handler:
            return self._default_handler
        return handler

    async def execute(
        self,
        command: unrealon_pb2.Command,
    ) -> tuple[unrealon_pb2.CommandStatus, str | None, str | None]:
        """Execute command and return result.

        Args:
            command: Command to execute

        Returns:
            Tuple of (status, result_json, error_message)
        """
        handler = self.get_handler(command.type)
        logger.info("Executing command: type=%s, id=%s", command.type, command.id)

        if not handler:
            logger.warning("No handler for command type: %s", command.type)
            return unrealon_pb2.FAILED, None, f"No handler for command type: {command.type}"

        try:
            params: dict[str, Any] = json.loads(command.params) if command.params else {}
            logger.info("Command params: %s", params)

            # Support both sync and async handlers
            # IMPORTANT: Sync handlers run in thread pool to not block asyncio loop
            if asyncio.iscoroutinefunction(handler):
                result = await handler(params)
            else:
                # Run sync handler in thread pool so stream can still receive messages
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, handler, params)

            result_json = json.dumps(result) if result else None
            logger.info("Command %s completed: result=%s", command.type, result)
            return unrealon_pb2.COMPLETED, result_json, None

        except Exception as e:
            logger.error("Command %s failed: %s", command.type, e)
            return unrealon_pb2.FAILED, None, str(e)


__all__ = ["CommandRegistry"]
