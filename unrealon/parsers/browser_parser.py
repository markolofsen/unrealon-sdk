"""
Browser-based parser class with CMDOP integration.

For parsers that use browser automation via CMDOP.

Requires: cmdop package

Usage:
    from unrealon.parsers import BaseBrowserParser

    class MyBrowserParser(BaseBrowserParser):
        SOURCE_CODE = "myparser"
        CURRENCY = "USD"

        def fetch_listing(self, browser, pages: int, limit: int) -> list[dict]:
            # Return raw items with: id, url, text, photos (optional)
            ...

        def fetch_detail(self, browser, url: str) -> dict:
            # Return: text, images
            ...

    # Run:
    MyBrowserParser.main(api_key="pk_...")
"""
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base import BaseParser
from .monitor import Monitor

if TYPE_CHECKING:
    pass


class BaseBrowserParser(BaseParser):
    """
    Browser-based parser with CMDOP + Monitor + StreamingUploader integration.

    Subclasses must define:
        SOURCE_CODE: str - parser identifier (e.g., "myparser")
        CURRENCY: str - currency code (e.g., "KRW", "JPY", "USD")

    Subclasses must implement:
        fetch_listing() - fetch listing pages via browser
        fetch_detail() - fetch single detail page (optional if skip_details)

    Transform methods (optional override):
        transform_item() - convert raw item to upload format

    Note: Requires cmdop package to be installed.
    """

    def __init__(
        self,
        monitor: Monitor,
        *,
        headless: bool = True,
        uploader: StreamingUploader | None = None,
        enable_storage: bool = True,
    ):
        """
        Initialize browser parser.

        Args:
            monitor: Monitor instance from get_monitor()
            headless: Browser headless mode
            uploader: Streaming uploader instance
            enable_storage: If False, skip local storage
        """
        super().__init__(
            monitor,
            uploader=uploader,
            enable_storage=enable_storage,
        )
        self.headless = headless

        # CMDOP browser client (lazy import to avoid hard dependency)
        self._cmdop_client: Any = None

    def _get_cmdop_client(self) -> Any:
        """Get or create CMDOP client."""
        if self._cmdop_client is None:
            try:
                from cmdop import CMDOPClient
                self._cmdop_client = CMDOPClient.local()
            except ImportError:
                raise ImportError(
                    "cmdop package is required for browser-based parsing. "
                    "Install it with: pip install cmdop"
                )
        return self._cmdop_client

    # -- Abstract methods (must implement) --

    @abstractmethod
    def fetch_listing(
        self,
        browser: Any,
        pages: int = 3,
        limit: int = 0,
    ) -> list[dict]:
        """
        Fetch listing pages.

        Args:
            browser: CMDOP browser session
            pages: Number of pages to fetch
            limit: Max items (0 = no limit)

        Returns:
            List of items with at least: {"id": str, "url": str, "text": str}
            Optional: "detail_url", "photos", any other fields
        """
        ...

    def fetch_detail(self, browser: Any, url: str) -> dict:
        """
        Fetch detail page. Override if detail fetching is needed.

        Args:
            browser: CMDOP browser session
            url: Detail page URL

        Returns:
            Dict with: {"text": str, "images": list[str]}
        """
        return {"text": "", "images": []}

    # -- Transform (override if needed) --

    def transform_item(self, item: dict, detail: dict | None = None) -> dict:
        """
        Transform raw item to upload format.

        Override to customize. Default combines listing + detail text.

        Args:
            item: Raw listing item
            detail: Detail page data (if fetched)

        Returns:
            Dict ready for upload: {id, url, text, photos}
        """
        text_parts = []

        # Listing text
        listing_text = item.get("text", "")
        if listing_text:
            text_parts.append(listing_text)

        # Detail text
        if detail:
            detail_text = detail.get("text", "")
            if detail_text:
                text_parts.append(detail_text)

        combined_text = "\n\n".join(text_parts)

        # Photos from detail or listing
        photos = []
        if detail and detail.get("images"):
            photos = detail["images"]
        elif item.get("photos"):
            photos = item["photos"]

        return {
            "id": str(item.get("id", item.get("car_id", ""))),
            "url": item.get("url", item.get("detail_url", "")),
            "text": combined_text,
            "photos": photos,
        }

    # -- Main run method --

    def run(self, pages: int = 3, limit: int = 0, skip_details: bool = False) -> None:
        """
        Main run method - fetches listing, details, uploads.

        Args:
            pages: Number of listing pages
            limit: Max items (0 = no limit)
            skip_details: Skip detail page fetching
        """
        start_time = datetime.now()
        fetched_at = start_time.isoformat()

        self.log.info(
            "=== Starting %s Parser ===",
            self.SOURCE_CODE.upper(),
            pages=pages,
            limit=limit,
            skip_details=skip_details,
        )

        client = self._get_cmdop_client()

        with client.browser.create_session(
            headless=self.headless,
            block_images=True,
            block_media=True,
        ) as browser:
            # Step 1: Fetch listing
            self.log.info("=== Step 1: Listing ===")
            items = self.fetch_listing(browser, pages=pages, limit=limit)

            if not items:
                self.log.warning("No items found")
                return

            # Preview first items
            for item in items[:3]:
                item_id = item.get("id", item.get("car_id", "?"))
                text = item.get("text", "")[:80]
                self.log.info("[%s] %s", item_id, text)

            # Step 2: Process items (with or without details)
            if skip_details:
                self._process_listing_only(items, fetched_at)
            else:
                self._process_with_details(browser, items, fetched_at)

        # Finish upload
        duration = str(datetime.now() - start_time).split(".")[0]
        self._finish_upload(duration=duration)

        # Final stats
        if self.storage:
            stats = self.storage.get_stats()
            self.log.info(
                "=== Done. %d items | %s (%d saved) ===",
                len(items), stats["root"], stats["count"],
            )

    def _process_listing_only(self, items: list[dict], fetched_at: str) -> None:
        """Process items without detail fetching."""
        self.log.info("=== Processing listing only (%d items) ===", len(items))

        for item in self.m.runner.iterate(items):
            item_id = str(item.get("id", item.get("car_id", "")))

            # Save locally
            if self.storage:
                self.storage.save(item_id, {
                    "id": item_id,
                    "meta": {"url": item.get("url", ""), "fetched_at": fetched_at},
                    "dom_data": {"text": item.get("text", "")},
                    "photos": item.get("photos", []),
                })

            # Transform and upload
            transformed = self.transform_item(item)
            self._upload_item(transformed)

            self.m.increment_processed()

        self.log.info("Processed %d listing-only items", len(items))

    def _process_with_details(
        self,
        browser: Any,
        items: list[dict],
        fetched_at: str,
    ) -> None:
        """Process items with detail fetching."""
        self.log.info("=== Step 2: Details (%d items) ===", len(items))

        for i, item in enumerate(self.m.runner.iterate(items)):
            item_id = str(item.get("id", item.get("car_id", "")))
            detail_url = item.get("detail_url", item.get("url", ""))

            self.log.info("--- [%d/%d] %s ---", i + 1, len(items), detail_url[:80])

            try:
                # Fetch detail
                detail = self.fetch_detail(browser, detail_url)
                self.log.info(
                    "Text: %d chars | Images: %d",
                    len(detail.get("text", "")),
                    len(detail.get("images", [])),
                )

                # Save locally
                if self.storage:
                    self.storage.save(item_id, {
                        "id": item_id,
                        "meta": {"url": item.get("url", ""), "fetched_at": fetched_at},
                        "dom_data": {
                            "listing_text": item.get("text", ""),
                            "detail_text": detail.get("text", ""),
                        },
                        "photos": detail.get("images", []),
                    })

                # Transform and upload
                transformed = self.transform_item(item, detail)
                self._upload_item(transformed)

                self.m.increment_processed()

            except Exception as e:
                self.log.error("Failed to fetch detail for %s: %s", item_id, e)
                self.m.increment_errors()

        # Flush remaining items at end
        self._flush_upload_buffer()


# Import for type hints
from .upload import StreamingUploader  # noqa: E402
