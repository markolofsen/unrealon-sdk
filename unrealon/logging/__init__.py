"""
Unrealon Logging - Rich console + File + gRPC Cloud logging.

Provides a standard Python logger with:
- Rich formatted console output
- Rotating file logging
- gRPC cloud logging integration

Example:
    ```python
    # Standalone logger (without cloud)
    from unrealon.logging import get_logger

    log = get_logger(__name__)
    log.info("Hello", user_id=123, action="login")

    # With ServiceClient (including cloud)
    from unrealon import ServiceClient

    with ServiceClient(api_key="...", service_name="parser") as client:
        client.logger.info("Started parsing", url="https://...")
        client.logger.error("Failed", exc_info=True)
    ```
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ._config import DEFAULT_CONFIG, LogConfig, LogLevel
from ._formatters import CloudFormatter, LogFormatter, StructuredFormatter
from ._handlers import CloudHandler, create_file_handler
from ._logger import UnrealonLogger
from ._project import find_project_root, get_log_dir

if TYPE_CHECKING:
    pass

# Track configured loggers to avoid duplicate handlers
_configured_loggers: set[str] = set()


def get_logger(
    name: str | None = None,
    level: LogLevel = "INFO",
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_to_cloud: bool = False,
    use_rich: bool = True,
    app_name: str = "unrealon",
) -> UnrealonLogger:
    """
    Get a configured logger instance.

    Creates an UnrealonLogger with Rich console output, file logging,
    and optional cloud logging handlers.

    Args:
        name: Logger name (defaults to root logger)
        level: Minimum log level
        log_to_console: Enable Rich console output
        log_to_file: Enable file logging
        log_to_cloud: Enable cloud logging (requires gRPC connection)
        use_rich: Use Rich library for console formatting
        app_name: Application name for file naming

    Returns:
        Configured UnrealonLogger instance

    Example:
        ```python
        log = get_logger(__name__)
        log.info("Processing started", items=100)
        log.error("Failed to process", error_code=500)
        ```
    """
    # Ensure UnrealonLogger class is used
    logging.setLoggerClass(UnrealonLogger)

    logger_name = name or "unrealon"
    logger = logging.getLogger(logger_name)

    # Cast to UnrealonLogger (safe because we set the class above)
    if not isinstance(logger, UnrealonLogger):
        # This shouldn't happen, but handle gracefully
        logger.__class__ = UnrealonLogger

    # Avoid adding duplicate handlers
    if logger_name in _configured_loggers:
        return logger  # type: ignore[return-value]

    _configured_loggers.add(logger_name)

    # Set level
    logger.setLevel(getattr(logging, level))

    # Console handler with Rich
    if log_to_console:
        console_handler = _create_console_handler(use_rich)
        console_handler.setLevel(getattr(logging, level))
        logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        file_handler = create_file_handler(app_name=app_name)
        file_handler.setLevel(getattr(logging, level))
        logger.addHandler(file_handler)

    # Cloud handler (disabled by default, enabled via ServiceClient)
    if log_to_cloud:
        cloud_handler = CloudHandler()
        cloud_handler.setLevel(getattr(logging, level))
        logger.addHandler(cloud_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger  # type: ignore[return-value]


def _create_console_handler(use_rich: bool = True) -> logging.Handler:
    """
    Create console handler with optional Rich formatting.

    Args:
        use_rich: Use Rich library for formatting

    Returns:
        Configured console handler
    """
    if use_rich:
        try:
            from rich.logging import RichHandler

            return RichHandler(
                show_time=True,
                show_level=True,
                show_path=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                markup=True,
            )
        except ImportError:
            pass

    # Fallback to standard StreamHandler
    handler = logging.StreamHandler()
    handler.setFormatter(LogFormatter())
    return handler


def setup_logging(config: LogConfig | None = None) -> None:
    """
    Setup root logging configuration.

    Configures the root logger with handlers based on config.
    Call this once at application startup.

    Args:
        config: Logging configuration (uses defaults if None)

    Example:
        ```python
        from unrealon.logging import setup_logging, LogConfig

        setup_logging(LogConfig(
            level="DEBUG",
            log_to_file=True,
            log_to_cloud=True,
        ))
        ```
    """
    if config is None:
        config = DEFAULT_CONFIG

    # Configure root logger
    get_logger(
        name=None,
        level=config.level,
        log_to_console=config.log_to_console,
        log_to_file=config.log_to_file,
        log_to_cloud=config.log_to_cloud,
        use_rich=config.use_rich,
        app_name=config.app_name,
    )


def get_cloud_handler(logger: logging.Logger) -> CloudHandler | None:
    """
    Get CloudHandler from a logger if present.

    Args:
        logger: Logger to search

    Returns:
        CloudHandler instance or None
    """
    for handler in logger.handlers:
        if isinstance(handler, CloudHandler):
            return handler
    return None


def add_cloud_handler(
    logger: logging.Logger,
    level: LogLevel = "INFO",
) -> CloudHandler:
    """
    Add CloudHandler to an existing logger.

    Args:
        logger: Logger to add handler to
        level: Minimum log level for cloud logging

    Returns:
        Created CloudHandler instance
    """
    cloud_handler = CloudHandler()
    cloud_handler.setLevel(getattr(logging, level))
    logger.addHandler(cloud_handler)
    return cloud_handler


__all__ = [
    # Main API
    "get_logger",
    "setup_logging",
    # Configuration
    "LogConfig",
    "LogLevel",
    "DEFAULT_CONFIG",
    # Logger class
    "UnrealonLogger",
    # Handlers
    "CloudHandler",
    "create_file_handler",
    "get_cloud_handler",
    "add_cloud_handler",
    # Formatters
    "LogFormatter",
    "StructuredFormatter",
    "CloudFormatter",
    # Project utilities
    "find_project_root",
    "get_log_dir",
]
