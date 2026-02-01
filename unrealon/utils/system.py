"""System information utilities."""

import os
import socket
import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def get_hostname() -> str:
    """Get machine hostname."""
    return socket.gethostname()


@lru_cache(maxsize=1)
def get_ip_address() -> str:
    """Get machine IP address."""
    try:
        # Connect to external address to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_pid() -> int:
    """Get current process ID."""
    return os.getpid()


def get_executable_path() -> str:
    """Get Python executable path."""
    return sys.executable


def get_working_directory() -> str:
    """Get current working directory."""
    return os.getcwd()


def get_python_version() -> str:
    """Get Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


__all__ = [
    "get_hostname",
    "get_ip_address",
    "get_pid",
    "get_executable_path",
    "get_working_directory",
    "get_python_version",
]
