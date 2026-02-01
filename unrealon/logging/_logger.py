"""
UnrealonLogger - Extended Python logger with extra data support.

Provides a standard logging.Logger with support for structured
extra data in log calls.
"""

from __future__ import annotations

import logging
from typing import Any


class UnrealonLogger(logging.Logger):
    """Logger with structured extra data support.

    Extends standard Logger to allow passing extra keyword arguments
    that are stored in the LogRecord for handlers to access.

    Example:
        ```python
        log = UnrealonLogger("myapp")
        log.info("User logged in", user_id=123, action="login")
        # Handlers can access record.extra = {"user_id": 123, "action": "login"}
        ```

    Note:
        Reserved keywords that cannot be used in extra:
        level, msg, args, exc_info, stack_info, stacklevel
    """

    # Reserved keywords that conflict with internal parameters
    _RESERVED_KEYWORDS = frozenset({"level", "msg", "args", "exc_info", "stack_info", "stacklevel"})

    def _filter_extra(self, extra: dict[str, Any], stacklevel: int = 3) -> dict[str, Any]:
        """Filter reserved keywords from extra dict."""
        if not extra:
            return extra
        reserved_found = self._RESERVED_KEYWORDS & extra.keys()
        if reserved_found:
            import warnings
            warnings.warn(
                f"Reserved keywords in log extra will be ignored: {reserved_found}",
                UserWarning,
                stacklevel=stacklevel,
            )
            return {k: v for k, v in extra.items() if k not in self._RESERVED_KEYWORDS}
        return extra

    def _log_with_extra(
        self,
        level: int,
        msg: object,
        args: tuple[Any, ...] = (),
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 2,
        **extra: Any,
    ) -> None:
        """
        Log with structured extra data.

        Extra kwargs are stored in record.extra for handlers.

        Args:
            level: Logging level
            msg: Log message
            args: Message formatting args
            exc_info: Exception info
            stack_info: Include stack info
            stacklevel: Stack level for caller info
            **extra: Extra structured data
        """
        if not self.isEnabledFor(level):
            return

        # Find the caller frame, adjusting for our wrapper
        try:
            fn, lno, func, sinfo = self.findCaller(stack_info, stacklevel + 1)
        except ValueError:
            fn, lno, func, sinfo = "(unknown file)", 0, "(unknown function)", None

        # Create log record
        record = self.makeRecord(
            self.name,
            level,
            fn,
            lno,
            msg,
            args,
            exc_info,
            func,
            extra=None,
            sinfo=sinfo,
        )

        # Store extra data on the record
        if extra:
            record.extra = extra  # type: ignore[attr-defined]

        self.handle(record)

    def debug(self, msg: object, *args: Any, **extra: Any) -> None:  # type: ignore[override]
        """
        Log debug message with optional extra data.

        Args:
            msg: Log message
            *args: Message formatting args
            **extra: Extra structured data (user_id=123, action="login")
        """
        extra = self._filter_extra(extra)
        if args:
            self._log_with_extra(logging.DEBUG, msg, args, **extra)
        else:
            self._log_with_extra(logging.DEBUG, msg, (), **extra)

    def info(self, msg: object, *args: Any, **extra: Any) -> None:  # type: ignore[override]
        """
        Log info message with optional extra data.

        Args:
            msg: Log message
            *args: Message formatting args
            **extra: Extra structured data
        """
        extra = self._filter_extra(extra)
        if args:
            self._log_with_extra(logging.INFO, msg, args, **extra)
        else:
            self._log_with_extra(logging.INFO, msg, (), **extra)

    def warning(self, msg: object, *args: Any, **extra: Any) -> None:  # type: ignore[override]
        """
        Log warning message with optional extra data.

        Args:
            msg: Log message
            *args: Message formatting args
            **extra: Extra structured data
        """
        extra = self._filter_extra(extra)
        if args:
            self._log_with_extra(logging.WARNING, msg, args, **extra)
        else:
            self._log_with_extra(logging.WARNING, msg, (), **extra)

    def error(self, msg: object, *args: Any, **extra: Any) -> None:  # type: ignore[override]
        """
        Log error message with optional extra data.

        Args:
            msg: Log message
            *args: Message formatting args
            **extra: Extra structured data
        """
        extra = self._filter_extra(extra)
        if args:
            self._log_with_extra(logging.ERROR, msg, args, **extra)
        else:
            self._log_with_extra(logging.ERROR, msg, (), **extra)

    def critical(self, msg: object, *args: Any, **extra: Any) -> None:  # type: ignore[override]
        """
        Log critical message with optional extra data.

        Args:
            msg: Log message
            *args: Message formatting args
            **extra: Extra structured data
        """
        extra = self._filter_extra(extra)
        if args:
            self._log_with_extra(logging.CRITICAL, msg, args, **extra)
        else:
            self._log_with_extra(logging.CRITICAL, msg, (), **extra)

    def exception(self, msg: object, *args: Any, **extra: Any) -> None:  # type: ignore[override]
        """
        Log exception with traceback and optional extra data.

        Args:
            msg: Log message
            *args: Message formatting args
            **extra: Extra structured data
        """
        import sys

        extra = self._filter_extra(extra)
        exc_info = sys.exc_info()
        if args:
            self._log_with_extra(logging.ERROR, msg, args, exc_info=exc_info, **extra)
        else:
            self._log_with_extra(logging.ERROR, msg, (), exc_info=exc_info, **extra)


# Register our logger class
logging.setLoggerClass(UnrealonLogger)


__all__ = ["UnrealonLogger"]
