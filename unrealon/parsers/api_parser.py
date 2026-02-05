"""
Base API parser class with integrated monitoring and upload.

For parsers that use direct HTTP/API calls instead of browser automation.

Usage:
    from unrealon.parsers import BaseAPIParser

    class MyAPIParser(BaseAPIParser):
        SOURCE_CODE = "myparser"
        CURRENCY = "USD"

        async def fetch_listing_page(self, page: int) -> tuple[list[dict], int]:
            # Return (items, total_count)
            ...

        def transform_item(self, item: dict) -> dict:
            # Return {id, url, text, photos}
            ...

    # Run:
    MyAPIParser.main(api_key="pk_...")
"""
from __future__ import annotations

import asyncio
from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

import httpx

from ..exceptions import StopInterrupt
from .base import BaseParser
from .monitor import Monitor

if TYPE_CHECKING:
    pass


class BaseAPIParser(BaseParser):
    """
    Base parser for API-based data fetching with streaming upload.

    Subclasses must define:
        SOURCE_CODE: str - parser identifier (e.g., "myparser")
        CURRENCY: str - currency code (e.g., "KRW", "JPY", "USD")

    Subclasses must implement:
        fetch_listing_page() - fetch one page of listings via API
        transform_item() - convert raw item to upload format

    Optional override:
        fetch_detail() - fetch additional details for item
        get_http_headers() - custom HTTP headers
    """

    # -- Config --
    PAGE_SIZE: int = 20
    REQUEST_TIMEOUT: float = 30.0
    DELAY_BETWEEN_PAGES: float = 0.3

    def __init__(
        self,
        monitor: Monitor,
        *,
        uploader: StreamingUploader | None = None,
        enable_storage: bool = False,  # API parsers typically don't need local storage
    ):
        super().__init__(
            monitor,
            uploader=uploader,
            enable_storage=enable_storage,
        )

        # HTTP client (created in run_async)
        self._client: httpx.AsyncClient | None = None

    # -- HTTP helpers --

    def get_http_headers(self) -> dict[str, str]:
        """Override to customize HTTP headers."""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }

    async def _get_json(self, url: str) -> dict | list | None:
        """Fetch JSON from URL with error handling."""
        try:
            resp = await self._client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.log.debug("HTTP error for %s: %s", url[:80], e)
            return None

    async def _post_json(self, url: str, data: dict) -> dict | list | None:
        """POST JSON to URL with error handling."""
        try:
            resp = await self._client.post(url, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.log.debug("HTTP POST error for %s: %s", url[:80], e)
            return None

    # -- Abstract methods --

    @abstractmethod
    async def fetch_listing_page(
        self,
        page: int,
        limit: int = 0,
    ) -> tuple[list[dict], int]:
        """
        Fetch one page of listings via API.

        Args:
            page: Page number (1-based)
            limit: Max items total (0 = no limit)

        Returns:
            Tuple of (items, total_available_count)
            Items should have at least 'id' field.
        """
        ...

    @abstractmethod
    def transform_item(self, item: dict, detail: dict | None = None) -> dict:
        """
        Transform raw API item to upload format.

        Args:
            item: Raw item from API (may include _details if fetch_detail was called)
            detail: Not used in API parser (details stored in item["_details"])

        Returns:
            Dict with: {id, url, text, photos}
        """
        ...

    # -- Optional override --

    async def fetch_detail(self, item: dict) -> dict | None:
        """
        Fetch additional details for item. Override if needed.

        Args:
            item: Raw item from listing

        Returns:
            Additional data to merge into item, or None
        """
        return None

    # -- Main run logic --

    async def run_async(
        self,
        pages: int = 3,
        limit: int = 0,
        skip_details: bool = False,
    ) -> None:
        """Main async run method."""
        start_time = datetime.now()
        total_fetched = 0
        aborted = False

        self.log.info(
            "=== Starting %s API Parser ===",
            self.SOURCE_CODE.upper(),
            pages=pages,
            limit=limit,
            skip_details=skip_details,
        )

        try:
            seen_ids: set[str] = set()
            items_limit_reached = False

            async with httpx.AsyncClient(
                headers=self.get_http_headers(),
                timeout=self.REQUEST_TIMEOUT,
                follow_redirects=True,
                proxy=None,  # Disable proxy to avoid 407 errors
            ) as client:
                self._client = client

                for page in range(1, pages + 1):
                    # Check for pause/stop
                    self.m.check_interrupt()

                    self.log.info("Page %d/%d...", page, pages)

                    items, total = await self.fetch_listing_page(page, limit)
                    if not items:
                        self.log.info("No more items at page %d", page)
                        break

                    self.log.info("Page %d: %d items (total available: %d)", page, len(items), total)

                    # Process items
                    page_items = []
                    for idx, item in enumerate(items, 1):
                        item_id = str(item.get("id", item.get("Id", "")))
                        if not item_id or item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)

                        # Fetch details if enabled
                        if not skip_details:
                            details = await self.fetch_detail(item)
                            if details:
                                item["_details"] = details

                        # Transform and collect
                        transformed = self.transform_item(item)
                        page_items.append(transformed)

                        # Log item progress
                        photos_count = len(transformed.get("photos", []))
                        self.log.info(
                            "  [%d/%d] id=%s photos=%d",
                            idx, len(items), item_id, photos_count
                        )

                        # Check limit
                        if limit > 0 and len(seen_ids) >= limit:
                            items_limit_reached = True
                            break

                    total_fetched += len(page_items)

                    # Upload this page
                    if self.uploader and page_items:
                        self.uploader.upload_batch(page_items, page_num=page)

                    self.m.increment_processed(len(page_items))

                    if items_limit_reached:
                        break

                    # Delay between pages
                    if self.DELAY_BETWEEN_PAGES > 0:
                        await asyncio.sleep(self.DELAY_BETWEEN_PAGES)

                self._client = None

        except (StopInterrupt, KeyboardInterrupt):
            self.log.info("=== Interrupted, aborting... ===")
            aborted = True
            self._client = None
            raise

        finally:
            # Finish upload (force abort if interrupted)
            duration = str(datetime.now() - start_time).split(".")[0]
            if self.uploader:
                stats = self.uploader.finish(duration=duration, force=aborted)
                self.log.info(
                    "=== Done: %d fetched, %d uploaded, %d failed ===",
                    total_fetched, stats.success, stats.failed,
                )
            else:
                self.log.info("=== Done: %d fetched ===", total_fetched)

    def run(
        self,
        pages: int = 3,
        limit: int = 0,
        skip_details: bool = False,
    ) -> None:
        """Sync wrapper for run_async."""
        asyncio.run(self.run_async(pages=pages, limit=limit, skip_details=skip_details))


# Import for type hints
from .upload import StreamingUploader  # noqa: E402
