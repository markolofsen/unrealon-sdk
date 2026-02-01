"""System metrics collection utilities."""

import os
import time

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_memory_mb() -> float | None:
    """Get current process memory usage in MB."""
    if not HAS_PSUTIL:
        return None

    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return round(memory_info.rss / 1024 / 1024, 2)
    except Exception:
        return None


def get_cpu_percent() -> float | None:
    """Get current process CPU usage percentage."""
    if not HAS_PSUTIL:
        return None

    try:
        process = psutil.Process(os.getpid())
        return process.cpu_percent(interval=0.1)
    except Exception:
        return None


def get_uptime_seconds() -> float | None:
    """Get process uptime in seconds."""
    if not HAS_PSUTIL:
        return None

    try:
        process = psutil.Process(os.getpid())
        return time.time() - process.create_time()
    except Exception:
        return None


def get_thread_count() -> int | None:
    """Get number of threads in current process."""
    if not HAS_PSUTIL:
        return None

    try:
        process = psutil.Process(os.getpid())
        return process.num_threads()
    except Exception:
        return None


__all__ = [
    "get_memory_mb",
    "get_cpu_percent",
    "get_uptime_seconds",
    "get_thread_count",
]
