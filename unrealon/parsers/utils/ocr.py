"""
Screenshot + OCR tool for parsers.

Universal utility: navigate to URL, take a screenshot, extract text via SDKRouter OCR.

Usage:
    from unrealon.parsers.utils import OCRTool, OCRResult

    ocr = OCRTool()

    # With browser session (reuse existing)
    with ocr.cmdop.browser.create_session(headless=True) as b:
        result = ocr.extract(url, browser=b)
        print(result.text)
        print(result.cost)

    # Standalone (creates its own browser session)
    result = ocr.extract(url)
    print(result.text)

    # From existing screenshot bytes
    result = ocr.extract_from_bytes(png_bytes)

    # From existing screenshot file
    result = ocr.extract_from_file(Path("/tmp/screenshot.png"))
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cmdop import CMDOPClient
from cmdop.services.browser.models import WaitUntil
from sdkrouter import SDKRouter
from sdkrouter.tools import OCRRequestRequestMode

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

DEFAULT_TEMP_DIR = Path("/tmp/parser_ocr")


@dataclass
class OCRResult:
    """Result of OCR extraction."""

    text: str
    cost: float
    screenshot_path: Path | None = None


class OCRTool:
    """
    Screenshot + OCR extraction tool.

    Takes a screenshot of a page and extracts text via SDKRouter vision.ocr.
    """

    def __init__(
        self,
        *,
        sdk: SDKRouter | None = None,
        cmdop: CMDOPClient | None = None,
        mode: OCRRequestRequestMode = OCRRequestRequestMode.MAXIMUM,
        language_hint: str = "en",
        headless: bool = True,
        wait_seconds: float = 3.0,
        save_screenshots: bool = True,
        temp_dir: Path = DEFAULT_TEMP_DIR,
        sdk_api_key: str = "test-api-key",
        sdk_timeout: float = 180.0,
    ):
        """
        Initialize OCR tool.

        Args:
            sdk: SDKRouter instance (created if not provided)
            cmdop: CMDOPClient instance (created if not provided)
            mode: OCR mode (FAST, BALANCED, MAXIMUM)
            language_hint: Language hint for OCR (e.g., "en", "ja", "ko")
            headless: Run browser in headless mode
            wait_seconds: Seconds to wait after page load before screenshot
            save_screenshots: Whether to save screenshots to disk
            temp_dir: Directory for temporary screenshot files
            sdk_api_key: API key for SDKRouter (if sdk not provided)
            sdk_timeout: Timeout for SDKRouter requests
        """
        self.sdk = sdk or SDKRouter(api_key=sdk_api_key, timeout=sdk_timeout)
        self.cmdop = cmdop or CMDOPClient.local()
        self.mode = mode
        self.language_hint = language_hint
        self.headless = headless
        self.wait_seconds = wait_seconds
        self.save_screenshots = save_screenshots
        self.temp_dir = temp_dir

    def _save_screenshot(self, png_bytes: bytes, name: str = "page") -> Path:
        """Save PNG bytes to temp file."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.temp_dir / f"{name}_{ts}.png"
        path.write_bytes(png_bytes)
        log.info("Screenshot saved: %s (%d bytes)", path.name, len(png_bytes))
        return path

    def _ocr(self, image_path: Path) -> OCRResult:
        """Run OCR on image file."""
        log.info("OCR extract: %s", image_path.name)
        result = self.sdk.vision.ocr(
            image_path=image_path,
            mode=self.mode,
            language_hint=self.language_hint,
        )
        return OCRResult(
            text=result.text or "",
            cost=result.cost_usd or 0.0,
            screenshot_path=image_path,
        )

    def _screenshot(self, url: str, browser: Any, *, name: str = "page") -> Path:
        """Navigate to URL and take screenshot."""
        log.info("Navigating to %s", url[:100])
        browser.navigate(url, timeout_ms=60000, wait_until=WaitUntil.DOMCONTENTLOADED)
        if self.wait_seconds > 0:
            time.sleep(self.wait_seconds)
        png = browser.screenshot()
        return self._save_screenshot(png, name=name)

    def extract(
        self,
        url: str,
        *,
        browser: Any = None,
        name: str = "page",
    ) -> OCRResult:
        """
        Navigate to URL, screenshot, and extract text via OCR.

        Args:
            url: Page URL to screenshot
            browser: Existing browser session. If None, creates a new one.
            name: Filename prefix for the screenshot

        Returns:
            OCRResult with extracted text, cost, and screenshot path
        """
        if browser is not None:
            img = self._screenshot(url, browser, name=name)
            return self._ocr(img)

        # Create own browser session
        with self.cmdop.browser.create_session(headless=self.headless) as b:
            img = self._screenshot(url, b, name=name)
            return self._ocr(img)

    def extract_from_bytes(self, png_bytes: bytes, *, name: str = "page") -> OCRResult:
        """
        Run OCR on raw PNG bytes.

        Args:
            png_bytes: PNG image bytes
            name: Filename prefix for the saved screenshot

        Returns:
            OCRResult with extracted text and cost
        """
        img = self._save_screenshot(png_bytes, name=name)
        return self._ocr(img)

    def extract_from_file(self, image_path: Path) -> OCRResult:
        """
        Run OCR on an existing image file.

        Args:
            image_path: Path to existing PNG/image file

        Returns:
            OCRResult with extracted text and cost
        """
        return self._ocr(image_path)
