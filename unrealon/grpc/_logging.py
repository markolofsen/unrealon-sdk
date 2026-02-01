"""
Log buffer management for gRPC stream service.

Provides thread-safe log buffering with batched sending.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, Any

from .generated import unrealon_pb2

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LogBuffer:
    """Thread-safe log buffer with batched sending.

    Collects log entries and provides batch retrieval for efficient
    gRPC streaming.
    """

    __slots__ = ("_buffer", "_lock", "_batch_size")

    def __init__(self, batch_size: int = 50) -> None:
        """
        Initialize log buffer.

        Args:
            batch_size: Number of logs to batch before sending
        """
        self._buffer: list[unrealon_pb2.LogEntry] = []
        self._lock = Lock()
        self._batch_size = batch_size

    def add(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        """Add log entry to buffer.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            extra: Additional structured data
        """
        entry = unrealon_pb2.LogEntry(
            level=level,
            message=message,
            timestamp=datetime.now().isoformat(),
            extra=json.dumps(extra) if extra else "",
        )
        with self._lock:
            self._buffer.append(entry)

    def get_batch(self) -> list[unrealon_pb2.LogEntry] | None:
        """Get log batch if buffer has enough entries.

        Returns:
            List of log entries if buffer >= batch_size, None otherwise
        """
        with self._lock:
            if len(self._buffer) >= self._batch_size:
                batch = self._buffer[: self._batch_size]
                self._buffer = self._buffer[self._batch_size :]
                return batch
        return None

    def flush(self) -> list[unrealon_pb2.LogEntry]:
        """Flush all buffered logs.

        Returns:
            All remaining log entries
        """
        with self._lock:
            batch = self._buffer
            self._buffer = []
            return batch

    def __len__(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)

    @property
    def batch_size(self) -> int:
        """Get configured batch size."""
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value: int) -> None:
        """Set batch size."""
        self._batch_size = value


__all__ = ["LogBuffer"]
