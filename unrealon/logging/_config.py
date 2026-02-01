"""
Logging configuration.

Defines LogConfig dataclass for logging settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass(frozen=True)
class LogConfig:
    """Configuration for logging behavior.

    Attributes:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Enable console output with Rich formatting
        log_to_file: Enable file output
        log_to_cloud: Enable gRPC cloud logging
        use_rich: Use Rich library for console formatting
        app_name: Application name for log file naming
        log_dir: Custom log directory (auto-detected if None)
        file_rotation: Enable daily log rotation
        max_file_size_mb: Max log file size before rotation
        backup_count: Number of rotated files to keep
    """

    level: LogLevel = "INFO"
    log_to_console: bool = True
    log_to_file: bool = True
    log_to_cloud: bool = True
    use_rich: bool = True
    app_name: str = "unrealon"
    log_dir: Path | None = None
    file_rotation: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5


# Default configuration instance
DEFAULT_CONFIG = LogConfig()


__all__ = ["LogConfig", "LogLevel", "DEFAULT_CONFIG"]
