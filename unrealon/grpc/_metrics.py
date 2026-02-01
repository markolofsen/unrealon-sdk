"""
Metrics collection for gRPC stream service.

Provides system and service metrics for heartbeat messages.
"""

from __future__ import annotations

import os
from datetime import datetime


def get_sdk_version() -> str:
    """Get SDK version.

    Returns:
        SDK version string or "unknown" if not available
    """
    try:
        from .._version import __version__

        return __version__
    except ImportError:
        return "unknown"


def get_system_metrics() -> dict[str, float]:
    """Get current system metrics.

    Returns:
        Dictionary with memory_mb, cpu_percent, uptime_seconds
    """
    metrics: dict[str, float] = {}

    try:
        import psutil

        process = psutil.Process(os.getpid())
        metrics["memory_mb"] = process.memory_info().rss / 1024 / 1024
        metrics["cpu_percent"] = process.cpu_percent()
        metrics["uptime_seconds"] = (
            datetime.now() - datetime.fromtimestamp(process.create_time())
        ).total_seconds()
    except Exception:
        pass

    return metrics


__all__ = ["get_sdk_version", "get_system_metrics"]
