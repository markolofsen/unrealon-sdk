"""
Type definitions for gRPC stream service.

Provides type aliases and protocols for command handling.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Command handler type: receives params dict, returns result dict or None
CommandHandler = Callable[[dict[str, Any]], dict[str, Any] | None]
"""Type alias for command handler functions.

Command handlers receive a dictionary of parameters and optionally return
a dictionary result. Both sync and async handlers are supported.

Example:
    def my_handler(params: dict[str, Any]) -> dict[str, Any] | None:
        return {"status": "ok", "value": params.get("key")}

    async def my_async_handler(params: dict[str, Any]) -> dict[str, Any] | None:
        await some_async_operation()
        return {"result": "done"}
"""


__all__ = ["CommandHandler"]
