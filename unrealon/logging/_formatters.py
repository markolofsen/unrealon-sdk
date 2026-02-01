"""
Log formatters for different output targets.

Provides standard and structured formatters for file and cloud logging.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any


class LogFormatter(logging.Formatter):
    """Standard formatter for file output.

    Produces human-readable log lines with timestamp, level, logger name,
    and line number.
    """

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT, datefmt=self.DATE_FORMAT)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for cloud logging.

    Produces JSON objects with extra data preserved for structured logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string representation
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "lineno": record.lineno,
            "funcName": record.funcName,
        }

        # Add extra data if present
        extra = getattr(record, "extra", None)
        if extra:
            log_data["extra"] = extra

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class CloudFormatter(logging.Formatter):
    """Formatter for cloud handler.

    Returns just the message for cloud logging,
    as metadata is handled separately.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for cloud.

        Args:
            record: Log record to format

        Returns:
            Formatted message string
        """
        return record.getMessage()


__all__ = ["LogFormatter", "StructuredFormatter", "CloudFormatter"]
