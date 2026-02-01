"""
Custom logging handlers.

Provides CloudHandler for gRPC logging and file handler factory.
"""

from __future__ import annotations

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ._formatters import CloudFormatter, LogFormatter
from ._project import get_log_dir

if TYPE_CHECKING:
    from ..grpc.stream_service import GRPCStreamService


class CloudHandler(logging.Handler):
    """Handler that sends logs to gRPC cloud.

    Buffers logs until gRPC service is connected, then flushes
    and sends subsequent logs directly.

    Attributes:
        _grpc: gRPC stream service for sending logs
        _buffer: Buffer for logs before connection
        _max_buffer_size: Maximum buffer size (oldest logs dropped if exceeded)
    """

    def __init__(
        self,
        grpc_service: GRPCStreamService | None = None,
        max_buffer_size: int = 1000,
    ) -> None:
        """
        Initialize cloud handler.

        Args:
            grpc_service: gRPC stream service (can be set later)
            max_buffer_size: Maximum logs to buffer before connection
        """
        super().__init__()
        self._grpc: GRPCStreamService | None = grpc_service
        self._buffer: list[logging.LogRecord] = []
        self._max_buffer_size = max_buffer_size
        self.setFormatter(CloudFormatter())

    @property
    def grpc(self) -> GRPCStreamService | None:
        """Get gRPC service."""
        return self._grpc

    @property
    def is_connected(self) -> bool:
        """Check if gRPC is connected."""
        return self._grpc is not None and self._grpc.is_connected

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record.

        If connected, sends to cloud. Otherwise, buffers for later.

        Args:
            record: Log record to emit
        """
        try:
            if self.is_connected and self._grpc is not None:
                self._send_record(record)
            else:
                self._buffer_record(record)
        except Exception:
            self.handleError(record)

    def _send_record(self, record: logging.LogRecord) -> None:
        """Send record to gRPC cloud.

        Args:
            record: Log record to send
        """
        if self._grpc is None:
            return

        # Extract extra data from record
        extra = getattr(record, "extra", None)

        # Add standard log metadata to extra
        extra_data: dict[str, Any] = extra.copy() if extra else {}
        extra_data.update(
            {
                "logger_name": record.name,
                "lineno": record.lineno,
                "funcName": record.funcName,
            }
        )

        # Add exception info if present
        if record.exc_info:
            if self.formatter:
                extra_data["exception"] = self.formatter.formatException(record.exc_info)
            else:
                extra_data["exception"] = str(record.exc_info)

        self._grpc._messaging.add_log(
            level=record.levelname.lower(),
            message=self.format(record),
            extra=extra_data if extra_data else None,
        )

    def _buffer_record(self, record: logging.LogRecord) -> None:
        """Buffer record for later sending.

        Args:
            record: Log record to buffer
        """
        self._buffer.append(record)

        # Drop oldest logs if buffer exceeds max size
        if len(self._buffer) > self._max_buffer_size:
            self._buffer = self._buffer[-self._max_buffer_size :]

    def set_grpc_service(self, grpc: GRPCStreamService) -> None:
        """
        Set gRPC service and flush buffered logs.

        Call this after gRPC connection is established.

        Args:
            grpc: Connected gRPC stream service
        """
        self._grpc = grpc
        self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Flush all buffered logs to gRPC."""
        if not self._buffer or not self.is_connected:
            return

        for record in self._buffer:
            self._send_record(record)

        self._buffer.clear()

    def close(self) -> None:
        """Close the handler."""
        self._buffer.clear()
        super().close()


def create_file_handler(
    app_name: str = "unrealon",
    log_dir: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> RotatingFileHandler:
    """
    Create rotating file handler.

    Creates daily log files with rotation on size limit.

    Args:
        app_name: Application name for log file naming
        log_dir: Log directory (auto-detected if None)
        max_bytes: Max file size before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured RotatingFileHandler
    """
    if log_dir is None:
        log_dir = get_log_dir(app_name)

    # Create filename with date
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{app_name}_{date_str}.log"

    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(LogFormatter())

    return handler


__all__ = ["CloudHandler", "create_file_handler"]
