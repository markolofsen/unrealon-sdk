"""
Unrealon Parsers - base classes for building data parsers.

Usage:
    from unrealon.parsers import BaseAPIParser, BaseBrowserParser

    class MyParser(BaseAPIParser):
        SOURCE_CODE = "myparser"
        CURRENCY = "USD"

        async def fetch_listing_page(self, page: int, limit: int = 0):
            ...

        def transform_item(self, item: dict, detail: dict | None = None):
            ...

    if __name__ == "__main__":
        MyParser.main()
"""
from .api_parser import BaseAPIParser
from .base import BaseParser
from .browser_parser import BaseBrowserParser
from .cli import CLIConfig, cli_options, create_parser_cli
from .monitor import Monitor, get_monitor
from .storage import ResultStorage
from .upload import StreamingStats, StreamingUploader
from .utils import ALL_FORMATS, OCRResult, OCRTool, ParserNotifier, clean_and_save

__all__ = [
    # Base classes
    "BaseParser",
    "BaseAPIParser",
    "BaseBrowserParser",
    # CLI
    "CLIConfig",
    "cli_options",
    "create_parser_cli",
    # Upload & Storage
    "StreamingUploader",
    "StreamingStats",
    "ResultStorage",
    # Monitoring
    "Monitor",
    "get_monitor",
    # Utils
    "clean_and_save",
    "ALL_FORMATS",
    "ParserNotifier",
    "OCRTool",
    "OCRResult",
]
