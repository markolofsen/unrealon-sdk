"""
Message generation and handling for gRPC stream.

Handles heartbeat creation, log batching, and outgoing queue management.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import datetime
from threading import Lock
from typing import Any

from ._config import GRPCServiceConfig
from ._constants import OUTGOING_QUEUE_MAX_SIZE
from .generated import unrealon_pb2

logger = logging.getLogger(__name__)


class MessageGenerator:
    """Generates and manages outgoing gRPC messages.

    Handles:
    - Heartbeat message creation with system metrics
    - Log batching and buffering
    - Outgoing message queue with bounded size
    - Command acknowledgment queue
    """

    __slots__ = (
        "_config",
        "_service_id_getter",
        "_status_getter",
        "_metrics_getter",
        "_outgoing_queue",
        "_log_buffer",
        "_log_lock",
        "_sequence",
    )

    def __init__(
        self,
        config: GRPCServiceConfig,
        service_id_getter: callable,
        status_getter: callable,
        metrics_getter: callable,
    ) -> None:
        """
        Initialize message generator.

        Args:
            config: Service configuration
            service_id_getter: Callable that returns current service_id
            status_getter: Callable that returns current status
            metrics_getter: Callable that returns (items_processed, errors_count)
        """
        self._config = config
        self._service_id_getter = service_id_getter
        self._status_getter = status_getter
        self._metrics_getter = metrics_getter

        self._outgoing_queue: asyncio.Queue[unrealon_pb2.ClientMessage] = asyncio.Queue(
            maxsize=OUTGOING_QUEUE_MAX_SIZE
        )
        self._log_buffer: list[unrealon_pb2.LogEntry] = []
        self._log_lock = Lock()
        self._sequence: int = 0

    @property
    def sequence(self) -> int:
        """Get current sequence number."""
        return self._sequence

    @property
    def outgoing_queue(self) -> asyncio.Queue:
        """Get outgoing message queue."""
        return self._outgoing_queue

    def next_sequence(self) -> int:
        """Increment and return next sequence number."""
        self._sequence += 1
        return self._sequence

    def create_heartbeat(self) -> unrealon_pb2.ClientMessage:
        """Create heartbeat message with current metrics."""
        seq = self.next_sequence()
        items_processed, errors_count = self._metrics_getter()

        metrics = unrealon_pb2.SystemMetrics(
            items_processed=items_processed,
            errors_count=errors_count,
        )

        # Try to get system metrics
        try:
            import psutil

            process = psutil.Process(os.getpid())
            metrics.memory_mb = process.memory_info().rss / 1024 / 1024
            metrics.cpu_percent = process.cpu_percent()
            metrics.uptime_seconds = (
                datetime.now() - datetime.fromtimestamp(process.create_time())
            ).total_seconds()
        except Exception:
            pass

        return unrealon_pb2.ClientMessage(
            service_id=self._service_id_getter(),
            sequence=seq,
            heartbeat=unrealon_pb2.Heartbeat(
                status=self._status_getter(),
                metrics=metrics,
            ),
        )

    def add_log(self, level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        """Add log entry to buffer."""
        with self._log_lock:
            self._log_buffer.append(
                unrealon_pb2.LogEntry(
                    level=level,
                    message=message,
                    timestamp=datetime.now().isoformat(),
                    extra=json.dumps(extra) if extra else "",
                )
            )

    def get_log_batch(self) -> unrealon_pb2.ClientMessage | None:
        """Get log batch if buffer has enough entries."""
        with self._log_lock:
            batch_size = self._config.log_batch_size
            if len(self._log_buffer) >= batch_size:
                batch = self._log_buffer[:batch_size]
                self._log_buffer = self._log_buffer[batch_size:]

                seq = self.next_sequence()
                return unrealon_pb2.ClientMessage(
                    service_id=self._service_id_getter(),
                    sequence=seq,
                    logs=unrealon_pb2.LogBatch(entries=batch),
                )
        return None

    def flush_logs(self) -> unrealon_pb2.ClientMessage | None:
        """Flush all buffered logs."""
        with self._log_lock:
            if self._log_buffer:
                batch = self._log_buffer
                self._log_buffer = []

                seq = self.next_sequence()
                return unrealon_pb2.ClientMessage(
                    service_id=self._service_id_getter(),
                    sequence=seq,
                    logs=unrealon_pb2.LogBatch(entries=batch),
                )
        return None

    def create_command_ack(
        self,
        command_id: str,
        status: int,
        result: str | None = None,
        error: str | None = None,
    ) -> unrealon_pb2.ClientMessage:
        """Create command acknowledgment message."""
        seq = self.next_sequence()
        return unrealon_pb2.ClientMessage(
            service_id=self._service_id_getter(),
            sequence=seq,
            command_ack=unrealon_pb2.CommandAck(
                command_id=command_id,
                status=status,
                result=result or "",
                error=error or "",
            ),
        )

    def create_status_update(
        self,
        status: str,
        error_message: str | None = None,
    ) -> unrealon_pb2.ClientMessage:
        """Create status update message."""
        seq = self.next_sequence()
        return unrealon_pb2.ClientMessage(
            service_id=self._service_id_getter(),
            sequence=seq,
            status_update=unrealon_pb2.StatusUpdate(
                status=status,
                error_message=error_message or "",
            ),
        )

    def create_schedule_ack(
        self,
        schedule_id: str,
        run_id: str,
        status: int,
        result: str | None = None,
        error: str | None = None,
        items_processed: int = 0,
        duration_ms: int = 0,
    ) -> unrealon_pb2.ClientMessage:
        """Create schedule acknowledgment message."""
        seq = self.next_sequence()
        return unrealon_pb2.ClientMessage(
            service_id=self._service_id_getter(),
            sequence=seq,
            schedule_ack=unrealon_pb2.ScheduleAck(
                schedule_id=schedule_id,
                run_id=run_id,
                status=status,
                result=result or "",
                error=error or "",
                items_processed=items_processed,
                duration_ms=duration_ms,
            ),
        )

    async def generate_messages(
        self,
        running_getter: callable,
    ) -> AsyncIterator[unrealon_pb2.ClientMessage]:
        """Generate outgoing messages (heartbeat, logs, acks).

        Args:
            running_getter: Callable that returns whether service is running
        """
        # Send initial heartbeat immediately
        yield self.create_heartbeat()

        last_heartbeat = asyncio.get_event_loop().time()
        last_log_flush = asyncio.get_event_loop().time()

        while running_getter():
            now = asyncio.get_event_loop().time()

            # Periodic heartbeat
            if now - last_heartbeat >= self._config.heartbeat_interval:
                yield self.create_heartbeat()
                last_heartbeat = now

            # Periodic log flush - send ALL buffered logs
            if now - last_log_flush >= self._config.log_flush_interval:
                log_batch = self.flush_logs()
                if log_batch:
                    yield log_batch
                last_log_flush = now

            # Immediate batch send if buffer is full (size-based flush)
            while True:
                batch = self.get_log_batch()
                if batch:
                    yield batch
                else:
                    break

            # Check outgoing queue (command acks, status updates) - non-blocking
            try:
                msg = self._outgoing_queue.get_nowait()
                payload_type = msg.WhichOneof("payload")
                logger.info(f"Sending message from queue: type={payload_type}, seq={msg.sequence}")
                yield msg
            except asyncio.QueueEmpty:
                pass

            await asyncio.sleep(0.01)


__all__ = ["MessageGenerator"]
