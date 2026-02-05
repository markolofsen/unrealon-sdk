"""
Parser monitoring with ServiceClient integration.

Usage:
    from unrealon.parsers import get_monitor, Monitor

    with get_monitor("myparser") as m:
        parser = MyParser(m)
        parser.run()

Monitor provides:
    m.log           - UnrealonLogger (console + file + cloud)
    m.increment_processed() / m.increment_errors() - metrics
    m.set_busy() / m.set_idle() - status control
    m.is_paused / m.should_stop / m.is_busy - state checks
"""
from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from .. import ServiceClient, TaskRunner
from ..exceptions import RegistrationError
from ..logging import UnrealonLogger

if TYPE_CHECKING:
    pass


class Monitor:
    """Monitor with ServiceClient, logger, and lifecycle control.

    Lifecycle commands (pause/resume/stop) are handled by SDK built-in handlers.
    This class provides a thin wrapper with property accessors for parser code.

    Key feature: `m.runner` - TaskRunner for automatic interrupt handling.

    Example:
        ```python
        with get_monitor("myparser") as m:
            # Use runner.iterate() instead of plain for loops
            for page in m.runner.iterate(range(1, 10)):
                data = fetch_page(page)
                m.runner.checkpoint()  # Check after long operation

            for item in m.runner.iterate(items):
                process_item(item)  # Auto-stops on pause/stop
        ```
    """

    def __init__(self, client: ServiceClient):
        self.client = client
        self.log: UnrealonLogger = client.logger
        self.runner: TaskRunner = TaskRunner(client)

    # -- Metrics --

    def increment_processed(self, count: int = 1) -> None:
        self.client.increment_processed(count)

    def increment_errors(self, count: int = 1) -> None:
        self.client.increment_errors(count)

    # -- Status control (delegated to SDK) --

    def set_busy(self) -> None:
        """Mark service as busy (actively processing)."""
        self.client.set_busy()

    def set_idle(self) -> None:
        """Mark service as idle (waiting for commands)."""
        self.client.set_idle()

    # -- State checks (delegated to SDK) --

    @property
    def is_paused(self) -> bool:
        """Check if service is paused (set by SDK command handler)."""
        return self.client.is_paused

    @property
    def is_busy(self) -> bool:
        """Check if service is busy (actively processing)."""
        return self.client.is_busy

    @property
    def should_stop(self) -> bool:
        """Check if stop was requested (set by SDK command handler or signal)."""
        return self.client.shutdown_requested

    @property
    def service_id(self) -> str | None:
        return self.client.service_id

    def check_interrupt(self) -> None:
        """Check for pause/stop and raise exception if requested.

        Call this frequently in long-running operations to allow
        graceful interruption by commands from Unrealon dashboard.

        Raises:
            StopInterrupt: If stop was requested
            PauseInterrupt: If pause was requested
        """
        self.client.check_interrupt()


@contextmanager
def get_monitor(
    service_name: str,
    *,
    api_key: str | None = None,
    dev_mode: bool = False,
) -> Generator[Monitor, None, None]:
    """
    Get Unrealon monitor for parser.

    Args:
        service_name: Service name for registration (e.g., "myparser")
        api_key: Unrealon API key (required unless dev_mode=True with default dev key)
        dev_mode: If True, connect to local gRPC server (localhost:50051)
        log_level: Log level for cloud logging (default: DEBUG)

    Yields:
        Monitor with client, logger, and lifecycle control
    """
    if api_key is None and not dev_mode:
        raise ValueError("api_key is required unless dev_mode=True")

    client = ServiceClient(
        api_key=api_key or "",
        service_name=service_name,
        dev_mode=dev_mode,
    )
    try:
        client.start()
        yield Monitor(client)
    except RegistrationError as e:
        # Print clean error without traceback
        print(f"\n✗ {e.message}", file=sys.stderr)
        if e.suggestion:
            print(f"  → {e.suggestion}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.stop()
