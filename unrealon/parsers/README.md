# Unrealon Parsers

A comprehensive framework for building data parsers with built-in monitoring, streaming upload, and CLI support.

## Installation

```bash
pip install unrealon
```

For browser-based parsing, you'll also need CMDOP:
```bash
pip install cmdop
```

## Quick Start

### API-based Parser

```python
from unrealon.parsers import BaseAPIParser, Monitor

class MyAPIParser(BaseAPIParser):
    SOURCE_CODE = "myparser"
    CURRENCY = "USD"

    async def fetch_listing_page(self, page: int, limit: int = 0) -> tuple[list[dict], int]:
        """Fetch one page of listings."""
        url = f"https://api.example.com/items?page={page}"
        data = await self._get_json(url)
        return data.get("items", []), data.get("total", 0)

    def transform_item(self, item: dict, detail: dict | None = None) -> dict:
        """Transform raw item to upload format."""
        return {
            "id": item["id"],
            "url": f"https://example.com/item/{item['id']}",
            "text": item["description"],
            "photos": item.get("images", []),
        }

if __name__ == "__main__":
    MyAPIParser.main(
        api_key="pk_your_production_key",
        dev_api_key="dk_your_development_key",
    )
```

### Browser-based Parser

```python
from unrealon.parsers import BaseBrowserParser

class MyBrowserParser(BaseBrowserParser):
    SOURCE_CODE = "myparser"
    CURRENCY = "USD"

    def fetch_listing(self, browser, pages: int = 3, limit: int = 0) -> list[dict]:
        """Fetch listing pages using browser."""
        items = []
        for page in range(1, pages + 1):
            browser.navigate(f"https://example.com/items?page={page}")
            # Extract items from page...
            items.extend(extracted_items)
        return items

    def fetch_detail(self, browser, url: str) -> dict:
        """Fetch detail page."""
        browser.navigate(url)
        return {
            "text": browser.get_text("main"),
            "images": browser.get_images("img.gallery"),
        }

if __name__ == "__main__":
    MyBrowserParser.main(api_key="pk_...")
```

## Core Components

### BaseParser (Abstract)

Base class for all parsers. Provides:
- CLI integration with interactive menu
- Streaming upload support
- Local storage backup
- Monitoring integration

**Required attributes:**
- `SOURCE_CODE: str` - Parser identifier (e.g., "encar", "myparser")
- `CURRENCY: str` - Currency code (e.g., "USD", "KRW", "EUR")

**Required methods:**
- `run(pages, limit, skip_details)` - Main parsing logic
- `transform_item(item, detail)` - Convert raw item to upload format

### BaseAPIParser

For parsers using direct HTTP/API calls. Extends BaseParser with:
- Built-in `httpx.AsyncClient`
- Helper methods: `_get_json()`, `_post_json()`
- Async `run_async()` method

**Required methods:**
- `fetch_listing_page(page, limit)` - Fetch one page, return `(items, total_count)`
- `transform_item(item, detail)` - Transform item

**Optional methods:**
- `fetch_detail(item)` - Fetch additional details
- `get_http_headers()` - Custom HTTP headers

**Configuration:**
```python
class MyParser(BaseAPIParser):
    PAGE_SIZE = 50              # Items per page
    REQUEST_TIMEOUT = 30.0      # HTTP timeout in seconds
    DELAY_BETWEEN_PAGES = 0.5   # Delay between page requests
```

### BaseBrowserParser

For parsers using browser automation via CMDOP. Extends BaseParser with:
- CMDOP browser integration
- Automatic session management

**Required methods:**
- `fetch_listing(browser, pages, limit)` - Fetch listings
- `transform_item(item, detail)` - Transform item

**Optional methods:**
- `fetch_detail(browser, url)` - Fetch detail page

## CLI

All parsers get automatic CLI support:

```bash
# Interactive menu (no arguments)
python my_parser.py

# Production mode
python my_parser.py --prod --pages 10

# Development mode
python my_parser.py --dev --limit 5

# Skip detail fetching
python my_parser.py --prod --pages 3 --skip-details

# Continuous mode (wait for commands)
python my_parser.py --prod --continuous
```

**CLI Options:**
| Option | Description |
|--------|-------------|
| `--pages, -p` | Number of pages to parse (default: 3) |
| `--limit, -l` | Max items (0 = no limit) |
| `--skip-details` | Skip fetching detail pages |
| `--dev` | Use development server |
| `--prod` | Use production server |
| `--continuous` | Wait for commands from Unrealon |
| `--headless/--no-headless` | Browser headless mode |

## Monitoring

Built-in integration with Unrealon monitoring service.

```python
from unrealon.parsers import get_monitor, Monitor

with get_monitor("myparser", api_key="pk_...", dev_mode=False) as m:
    m.log.info("Starting parser")

    # Track progress
    m.increment_processed(10)
    m.increment_errors(1)

    # Status control
    m.set_busy()   # Processing
    m.set_idle()   # Waiting

    # Check for interrupts (pause/stop commands)
    m.check_interrupt()

    # Use runner for automatic interrupt handling
    for item in m.runner.iterate(items):
        process(item)
```

## Streaming Upload

Non-blocking upload that runs in a background thread.

```python
from unrealon.parsers import StreamingUploader

def my_upload_func(item: dict) -> tuple[bool, int, int, str | None]:
    """Upload single item. Returns (success, photos_added, photos_failed, error)."""
    # Your upload logic here
    return (True, 5, 0, None)

uploader = StreamingUploader(
    source_code="myparser",
    currency="USD",
    upload_func=my_upload_func,
    logger=monitor.log,
)

# Queue items for upload (non-blocking)
uploader.upload_batch(items, page_num=1)
uploader.upload_batch(more_items, page_num=2)

# Wait for completion and get stats
stats = uploader.finish()
print(f"Uploaded: {stats.success}, Failed: {stats.failed}")
```

## Local Storage

Backup parsed data to local JSON files.

```python
from unrealon.parsers import ResultStorage

storage = ResultStorage("myparser", root_dir="results")

# Save item
storage.save("item-123", {"id": "123", "text": "...", "photos": [...]})

# Load item
data = storage.load("item-123")

# Check existence
if storage.exists("item-123"):
    ...

# List all IDs
ids = storage.list_ids()

# Get statistics
stats = storage.get_stats()  # {"root": "results/myparser", "count": 150, "size_mb": 2.5}
```

## Utilities

### HTML Cleaner

Clean HTML and save in multiple formats for analysis.

```python
from unrealon.parsers.utils import clean_and_save, ALL_FORMATS
from pathlib import Path

clean_and_save(html, "listing", out_dir=Path("cleaned"))

# Saves:
# - listing_raw.html  (original)
# - listing.html      (cleaned DOM)
# - listing.md        (markdown)
# - listing.aom.yaml  (accessibility tree)
# - listing.xtree.txt (tree structure)
```

### OCR Tool

Screenshot pages and extract text via OCR.

```python
from unrealon.parsers.utils import OCRTool, OCRResult

ocr = OCRTool(language_hint="en")

# With existing browser session
result = ocr.extract("https://example.com", browser=browser)
print(result.text)
print(result.cost)

# Standalone (creates its own browser)
result = ocr.extract("https://example.com")

# From existing image
result = ocr.extract_from_file(Path("screenshot.png"))
result = ocr.extract_from_bytes(png_bytes)
```

### Telegram Notifications

Send parser status updates to Telegram.

```python
from unrealon.parsers.utils import ParserNotifier

notifier = ParserNotifier(
    source_code="myparser",
    bot_token="123:ABC...",
    chat_id="-123456",
)

notifier.started(pages=10)
notifier.progress(50, 100, photos=250)
notifier.completed(items=100, success=98, failed=2, duration="00:05:23")
notifier.warning("Rate limited, slowing down")
notifier.failed("Connection timeout", url="https://...")
```

## Custom Uploader

Create your own uploader for specific APIs:

```python
from unrealon.parsers import StreamingUploader, Monitor

def create_my_uploader(monitor: Monitor, mode: str) -> StreamingUploader:
    """Create uploader for my API."""

    def upload_item(item: dict) -> tuple[bool, int, int, str | None]:
        # Call your API here
        response = my_api.upload(item)
        if response.ok:
            return (True, response.photos_added, 0, None)
        else:
            return (False, 0, 0, response.error)

    return StreamingUploader(
        source_code="myparser",
        currency="USD",
        upload_func=upload_item,
        logger=monitor.log,
    )

# Use in parser
if __name__ == "__main__":
    MyParser.main(
        api_key="pk_...",
        create_uploader=create_my_uploader,
    )
```

## Configuration

### Parser Class Attributes

```python
class MyParser(BaseAPIParser):
    # Required
    SOURCE_CODE = "myparser"
    CURRENCY = "USD"

    # Optional (API parser)
    PAGE_SIZE = 20
    REQUEST_TIMEOUT = 30.0
    DELAY_BETWEEN_PAGES = 0.3

    # Optional (base parser)
    UPLOAD_BATCH_SIZE = 20
```

### main() Arguments

```python
MyParser.main(
    description="My Parser",           # CLI description
    api_key="pk_...",                  # Production Unrealon API key
    dev_api_key="dk_...",              # Development Unrealon API key
    service_name_prefix="myproject-",  # Prefix for service registration
    create_uploader=my_uploader_factory,  # Custom uploader factory
)
```

## Error Handling

Parsers support graceful interruption:

```python
from unrealon.exceptions import StopInterrupt, PauseInterrupt

try:
    for item in items:
        monitor.check_interrupt()  # Raises if stop/pause requested
        process(item)
except StopInterrupt:
    print("Parser stopped by command")
except PauseInterrupt:
    print("Parser paused")
```

On Ctrl+C, parsers abort immediately without waiting for pending uploads.

## Dependencies

Core:
- `httpx` - HTTP client
- `rich` - Console output
- `click` - CLI framework

Optional:
- `cmdop` - Browser automation (for BaseBrowserParser)
- `sdkrouter` - OCR and other tools
- `sdkrouter-tools` - HTML cleaner, Telegram sender
