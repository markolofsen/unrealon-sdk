"""
Streaming uploader — upload items as they are parsed, not in batch.

Instead of: parse all → save all → upload all
Does: parse page → queue for upload → next page (non-blocking)

Benefits:
- Data goes to server immediately
- Progress visible in real-time
- If crash — part already uploaded
- Less memory usage
- Non-blocking: parsing continues while upload runs in background

Usage:
    from unrealon.parsers import StreamingUploader

    uploader = StreamingUploader(
        source_code="myparser",
        currency="USD",
        upload_func=my_upload_function,
    )

    for page_items in parser.fetch_pages():
        uploader.upload_batch(page_items, page_num=page)

    stats = uploader.finish()
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Protocol

# -- Config --------------------------------------------------------------------

# Parallel upload settings
PARALLEL_WORKERS = 3     # Number of parallel upload workers
MAX_RETRIES = 3          # Retry on server errors
RETRY_DELAY = 2.0        # Seconds between retries

# Fallback logger (used if no logger provided)
_default_log = logging.getLogger(__name__)


@dataclass
class StreamingStats:
    """Accumulated stats for streaming upload."""
    pages: int = 0
    items: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    photos_added: int = 0
    photos_failed: int = 0


class UploadResult(Protocol):
    """Protocol for upload function result."""
    success: bool
    photos_added: int
    photos_failed: int
    error: str | None


class StreamingUploader:
    """
    Streaming uploader that uploads items as they come.

    Usage:
        def my_upload(item: dict) -> UploadResult:
            # Upload item to your API
            ...

        uploader = StreamingUploader(
            source_code="myparser",
            currency="USD",
            upload_func=my_upload,
        )

        for page_items in parser.fetch_pages():
            uploader.upload_batch(page_items)

        uploader.finish()  # waits for completion, prints summary
    """

    def __init__(
        self,
        source_code: str,
        currency: str,
        upload_func: Callable[[dict], tuple[bool, int, int, str | None]],
        *,
        logger: Any = None,
        parallel_workers: int = PARALLEL_WORKERS,
        on_progress: Callable[[StreamingStats], None] | None = None,
    ):
        """
        Initialize uploader.

        Args:
            source_code: Parser identifier
            currency: Currency code (e.g., "USD", "KRW")
            upload_func: Function to upload single item.
                         Returns (success, photos_added, photos_failed, error_msg)
            logger: Logger instance (optional)
            parallel_workers: Number of parallel upload workers
            on_progress: Callback for progress updates (optional)
        """
        self.source_code = source_code
        self.currency = currency
        self.upload_func = upload_func
        self.parallel_workers = parallel_workers
        self.on_progress = on_progress
        self.stats = StreamingStats()

        # Use provided logger or fallback
        self.log = logger if logger is not None else _default_log

        self._existing_ids: set[str] = set()
        self._session_started = False

        # Background upload queue and thread
        self._upload_queue: queue.Queue[tuple[list[dict], int] | None] = queue.Queue()
        self._upload_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.log.info("=== Upload session initialized: %s ===", source_code.upper())

    def add_existing_ids(self, ids: set[str]) -> None:
        """Add IDs to skip (already uploaded)."""
        self._existing_ids.update(ids)
        self.log.info("Added %d existing IDs to skip", len(ids))

    def _should_skip(self, item_id: str) -> bool:
        """Check if item already exists."""
        return item_id in self._existing_ids

    def _upload_one(self, item: dict) -> tuple[str, bool, int, int, str | None]:
        """
        Upload single item with retry.
        Returns (item_id, success, photos_added, photos_failed, error).
        Thread-safe for parallel execution.
        """
        item_id = str(item.get("id", ""))

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                success, photos_added, photos_failed, error = self.upload_func(item)
                if success:
                    return (item_id, True, photos_added, photos_failed, None)
                else:
                    return (item_id, False, 0, 0, error or "upload failed")

            except Exception as e:
                last_error = str(e)[:100]
                # Retry on server errors (502, 503, etc)
                if "502" in last_error or "503" in last_error or "504" in last_error:
                    if attempt < MAX_RETRIES - 1:
                        self.log.debug("[%s] Retry %d/%d after server error", item_id, attempt + 1, MAX_RETRIES)
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                # Don't retry on client errors (4xx)
                break

        self.log.warning("[%s] Upload error: %s", item_id, last_error)
        return (item_id, False, 0, 0, last_error)

    def _start_upload_thread(self) -> None:
        """Start background upload thread if not already running."""
        if self._upload_thread is not None and self._upload_thread.is_alive():
            return

        self._stop_event.clear()
        self._upload_thread = threading.Thread(
            target=self._upload_worker,
            name="upload-worker",
            daemon=True,
        )
        self._upload_thread.start()
        self.log.debug("Upload worker thread started")

    def _upload_worker(self) -> None:
        """Background worker that processes upload queue."""
        while not self._stop_event.is_set():
            try:
                # Wait for items with timeout to allow checking stop_event
                task = self._upload_queue.get(timeout=0.5)
                if task is None:
                    # Poison pill - stop worker
                    break
                items, page_num = task
                self._upload_batch_sync(items, page_num)
                self._upload_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.log.error("Upload worker error: %s", e)

    def upload_batch(self, items: list[dict], page_num: int = 0) -> None:
        """
        Queue a batch of items for background upload (non-blocking).
        Items are uploaded in a separate thread.
        """
        if not items:
            return

        # Start upload thread on first batch
        if not self._session_started:
            self._session_started = True
            self.log.info("=== Starting upload: %s ===", self.source_code.upper())
            self._start_upload_thread()

        # Queue items for background upload
        self._upload_queue.put((items.copy(), page_num))

    def _upload_batch_sync(self, items: list[dict], page_num: int = 0) -> int:
        """
        Upload a batch of items in parallel (blocking, runs in worker thread).
        Returns number of successful uploads.
        """
        self.stats.pages += 1
        batch_success = 0
        batch_skipped = 0

        # Filter items to upload (skip already existing)
        to_upload = []
        for item in items:
            item_id = str(item.get("id", ""))
            if self._should_skip(item_id):
                self.stats.skipped += 1
                batch_skipped += 1
            else:
                to_upload.append(item)

        if not to_upload:
            if page_num > 0:
                self.log.info("[upload] Page %d: 0 uploaded, %d skipped (all duplicates)",
                         page_num, batch_skipped)
            return 0

        self.stats.items += len(to_upload)

        if page_num > 0:
            self.log.info("[upload] Page %d: uploading %d items...", page_num, len(to_upload))

        # Parallel upload
        with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
            futures = {executor.submit(self._upload_one, item): item for item in to_upload}

            for future in as_completed(futures):
                item_id, success, photos_added, photos_failed, error = future.result()

                if success:
                    self.stats.success += 1
                    batch_success += 1
                    self.stats.photos_added += photos_added
                    self.stats.photos_failed += photos_failed
                    self._existing_ids.add(item_id)
                else:
                    self.stats.failed += 1

        # Log page progress
        if page_num > 0:
            self.log.info("[upload] Page %d: done — %d uploaded, %d skipped",
                     page_num, batch_success, batch_skipped)

        # Progress callback
        if self.on_progress:
            self.on_progress(self.stats)

        return batch_success

    def abort(self) -> None:
        """Abort upload immediately without waiting for pending items."""
        self._stop_event.set()
        # Clear the queue
        while not self._upload_queue.empty():
            try:
                self._upload_queue.get_nowait()
                self._upload_queue.task_done()
            except queue.Empty:
                break
        # Stop thread
        if self._upload_thread is not None and self._upload_thread.is_alive():
            self._upload_queue.put(None)  # Poison pill
            self._upload_thread.join(timeout=1)

    def finish(self, duration: str = "", force: bool = False) -> StreamingStats:
        """Finish upload session, wait for pending uploads, log summary."""
        # Wait for all queued uploads to complete (unless forced)
        if self._upload_thread is not None and self._upload_thread.is_alive():
            if force:
                self.log.info("Force finishing, aborting pending uploads...")
                self.abort()
            else:
                self.log.info("Waiting for pending uploads to complete...")
                self._upload_queue.join()  # Wait for queue to empty
                self._upload_queue.put(None)  # Poison pill to stop worker
                self._upload_thread.join(timeout=10)  # Wait for thread to finish
                self.log.debug("Upload worker thread stopped")

        self.log.info("=== Upload complete: %d items, %d success, %d failed, %d skipped ===",
                 self.stats.items, self.stats.success, self.stats.failed, self.stats.skipped)
        self.log.info("Photos: %d added, %d failed", self.stats.photos_added, self.stats.photos_failed)

        return self.stats
