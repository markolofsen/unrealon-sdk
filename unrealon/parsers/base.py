"""
Abstract base parser class with common functionality.

Provides shared logic for all parsers:
- Streaming upload to server
- Local storage backup
- CLI integration

Subclasses:
    BaseBrowserParser - for browser-based parsing (requires cmdop)
    BaseAPIParser - for direct HTTP/API parsing
"""
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from .cli import CLIConfig, create_parser_cli, print_config, run_continuous, show_interactive_menu
from .monitor import Monitor, get_monitor
from .storage import ResultStorage
from .upload import StreamingStats, StreamingUploader

if TYPE_CHECKING:
    pass


class BaseParser(ABC):
    """
    Abstract base parser with upload and storage integration.

    Subclasses must define:
        SOURCE_CODE: str - parser identifier (e.g., "myparser")
        CURRENCY: str - currency code (e.g., "KRW", "JPY", "USD")

    Subclasses must implement:
        run() - main parsing logic
        transform_item() - convert raw item to upload format

    Optional:
        create_uploader() - create custom uploader instance
    """

    # -- Must be defined in subclass --
    SOURCE_CODE: str = ""
    CURRENCY: str = ""

    # -- Upload config --
    UPLOAD_BATCH_SIZE: int = 20

    def __init__(
        self,
        monitor: Monitor,
        *,
        uploader: StreamingUploader | None = None,
        enable_storage: bool = True,
    ):
        """
        Initialize parser.

        Args:
            monitor: Monitor instance from get_monitor()
            uploader: Custom uploader instance (optional)
            enable_storage: If False, skip local storage
        """
        if not self.SOURCE_CODE:
            raise ValueError("SOURCE_CODE must be defined in subclass")
        if not self.CURRENCY:
            raise ValueError("CURRENCY must be defined in subclass")

        self.m = monitor
        self.log = monitor.log

        # Local storage (backup)
        self.storage: ResultStorage | None = None
        if enable_storage:
            self.storage = ResultStorage(self.SOURCE_CODE)

        # Streaming uploader
        self.uploader = uploader

        # Upload buffer for batching
        self._upload_buffer: list[dict] = []

    # -- Transform (must implement) --

    @abstractmethod
    def transform_item(self, item: dict, detail: dict | None = None) -> dict:
        """
        Transform raw item to upload format.

        Args:
            item: Raw listing item
            detail: Detail page data (if fetched)

        Returns:
            Dict ready for upload: {id, url, text, photos}
        """
        ...

    # -- Upload helpers --

    def _upload_item(self, transformed: dict) -> None:
        """Add item to upload buffer, flush if batch size reached."""
        if not self.uploader:
            return

        self._upload_buffer.append(transformed)

        if self.UPLOAD_BATCH_SIZE > 0 and len(self._upload_buffer) >= self.UPLOAD_BATCH_SIZE:
            self._flush_upload_buffer()

    def _flush_upload_buffer(self, page_num: int = 0) -> None:
        """Upload buffered items."""
        if not self.uploader or not self._upload_buffer:
            return

        self.uploader.upload_batch(self._upload_buffer, page_num=page_num)
        self._upload_buffer = []

    def _finish_upload(self, duration: str = "", force: bool = False) -> StreamingStats | None:
        """Flush remaining items and finish upload session."""
        self._flush_upload_buffer()

        if self.uploader:
            stats = self.uploader.finish(duration=duration, force=force)
            self.log.info(
                "Upload complete: %d success, %d failed, %d photos",
                stats.success, stats.failed, stats.photos_added,
            )
            return stats
        return None

    # -- Abstract run method --

    @abstractmethod
    def run(
        self,
        pages: int = 3,
        limit: int = 0,
        skip_details: bool = False,
    ) -> None:
        """
        Main run method - fetches data and uploads.

        Args:
            pages: Number of listing pages
            limit: Max items (0 = no limit)
            skip_details: Skip detail page fetching
        """
        ...

    # -- CLI entry point --

    @classmethod
    def main(
        cls,
        description: str | None = None,
        *,
        api_key: str | None = None,
        dev_api_key: str | None = None,
        service_name_prefix: str = "",
        create_uploader: Callable[[Monitor, str], StreamingUploader | None] | None = None,
    ) -> None:
        """
        CLI entry point with interactive menu.

        Shows interactive menu if no CLI args provided.
        Otherwise uses CLI arguments.

        Args:
            description: Parser description for CLI help
            api_key: Production API key for Unrealon
            dev_api_key: Development API key for Unrealon
            service_name_prefix: Prefix for service name (default: parser SOURCE_CODE)
            create_uploader: Factory function to create uploader instance

        Usage in parser file:
            if __name__ == "__main__":
                MyParser.main(api_key="pk_...")
        """
        desc = description or f"{cls.SOURCE_CODE.upper()} Parser"

        # Check if any CLI args provided
        has_args = len(sys.argv) > 1

        if has_args:
            # CLI mode - use argparse
            config = create_parser_cli(desc)
            # Show config for CLI mode
            if sys.stdin.isatty():
                print_config(config, desc)
        elif sys.stdin.isatty():
            # Interactive mode - show menu (includes config display)
            config = show_interactive_menu(desc)
        else:
            # Non-interactive, no args - defaults
            config = CLIConfig()

        # Select API key
        selected_api_key = dev_api_key if config.dev else api_key
        if not selected_api_key:
            print(f"Error: {'dev_api_key' if config.dev else 'api_key'} is required", file=sys.stderr)
            sys.exit(1)

        service_name = f"{service_name_prefix}{cls.SOURCE_CODE}" if service_name_prefix else cls.SOURCE_CODE

        try:
            with get_monitor(service_name, api_key=selected_api_key, dev_mode=config.dev) as m:
                upload_mode = "dev" if config.dev else "prod"

                def create_and_run(params: dict) -> None:
                    """Create fresh uploader/parser and run."""
                    uploader = create_uploader(m, upload_mode) if create_uploader else None
                    parser = cls(m, uploader=uploader, enable_storage=True)
                    parser.run(
                        pages=params.get("pages", config.pages),
                        limit=params.get("limit", config.limit),
                        skip_details=params.get("skip_details", config.skip_details),
                    )

                if config.continuous:
                    run_continuous(m, create_and_run, config)
                else:
                    create_and_run({})
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting immediately.")
            os._exit(0)  # Fast exit without waiting for threads
