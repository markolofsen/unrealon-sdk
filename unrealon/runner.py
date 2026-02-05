"""
Task runner with automatic interrupt handling.

Provides simple primitives for running interruptible tasks.
The runner automatically checks for pause/stop commands between iterations.

Example:
    ```python
    from unrealon import ServiceClient, TaskRunner

    with ServiceClient(...) as client:
        runner = TaskRunner(client)

        # Simple iteration - auto-checks interrupt between items
        for car in runner.iterate(cars):
            process_car(car)

        # With checkpoint for long operations
        for page in runner.iterate(range(1, 10)):
            data = fetch_page(page)  # Long operation
            runner.checkpoint()       # Check after fetch
            parse_data(data)          # Another operation
            runner.checkpoint()       # Check after parse
    ```
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from ._client import ServiceClient

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TaskRunner:
    """
    Runner for interruptible tasks.

    Wraps iteration and long operations with automatic pause/stop handling.
    No need to manually call check_interrupt() - the runner does it for you.

    Features:
    - `iterate(items)` - Yields items, checking interrupt between each
    - `checkpoint()` - Explicit check point for long operations
    - `run(func, *args)` - Run function with interrupt check before/after

    Example:
        ```python
        runner = TaskRunner(client)

        # Automatically stops/pauses between items
        for item in runner.iterate(items):
            process(item)

        # Manual checkpoints for fine-grained control
        for batch in runner.iterate(batches):
            result = slow_operation(batch)
            runner.checkpoint()  # Check after slow op
            save_result(result)
        ```
    """

    __slots__ = ("_client", "_current_item", "_items_processed")

    def __init__(self, client: ServiceClient) -> None:
        """
        Initialize task runner.

        Args:
            client: ServiceClient instance (must be started)
        """
        self._client = client
        self._current_item: Any = None
        self._items_processed: int = 0

    @property
    def items_processed(self) -> int:
        """Number of items processed in current run."""
        return self._items_processed

    @property
    def is_paused(self) -> bool:
        """Check if currently paused."""
        return self._client.is_paused

    @property
    def is_stopping(self) -> bool:
        """Check if stop was requested."""
        return self._client.shutdown_requested

    def iterate(self, items: Iterable[T]) -> Iterator[T]:
        """
        Iterate over items with automatic interrupt handling.

        Checks for pause/stop before yielding each item.
        If paused, waits until resumed or stopped.
        If stopped, raises StopInterrupt.

        Args:
            items: Iterable to iterate over (list, range, generator, etc.)

        Yields:
            Items from the iterable

        Raises:
            StopInterrupt: If stop was requested

        Example:
            ```python
            # Simple - just iterate
            for car in runner.iterate(cars):
                process_car(car)

            # With progress tracking
            for i, page in enumerate(runner.iterate(range(1, 100))):
                client.info(f"Processing page {i+1}")
                fetch_page(page)
            ```
        """
        for item in items:
            # Check before processing each item
            self._client.check_interrupt()
            self._current_item = item
            yield item
            self._items_processed += 1

    def checkpoint(self) -> None:
        """
        Explicit interrupt check point.

        Call this during long operations to allow interruption.
        If paused, blocks until resumed.
        If stopped, raises StopInterrupt.

        Example:
            ```python
            for url in runner.iterate(urls):
                data = fetch(url)      # Might take 30s
                runner.checkpoint()    # Allow interrupt here
                parsed = parse(data)   # Might take 10s
                runner.checkpoint()    # And here
                save(parsed)
            ```
        """
        self._client.check_interrupt()

    def run(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Run function with interrupt checks before and after.

        Args:
            func: Function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            StopInterrupt: If stop was requested

        Example:
            ```python
            # Instead of:
            #   check_interrupt()
            #   result = slow_function(arg)
            #   check_interrupt()

            # Just:
            result = runner.run(slow_function, arg)
            ```
        """
        self._client.check_interrupt()
        result = func(*args, **kwargs)
        self._client.check_interrupt()
        return result

    def reset(self) -> None:
        """Reset counters for new run."""
        self._items_processed = 0
        self._current_item = None


__all__ = ["TaskRunner"]
