"""
Project root detection for log file placement.

Finds project root by looking for common project markers.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_MARKERS = ["pyproject.toml", "setup.py", ".git", "requirements.txt"]


def find_project_root(start_path: Path | None = None) -> Path | None:
    """
    Find project root by searching for marker files.

    Traverses up from start_path until a project marker is found.

    Args:
        start_path: Starting directory (defaults to cwd)

    Returns:
        Path to project root, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        for marker in PROJECT_MARKERS:
            if (current / marker).exists():
                return current
        current = current.parent

    # Check root as well
    for marker in PROJECT_MARKERS:
        if (current / marker).exists():
            return current

    return None


def get_log_dir(app_name: str = "unrealon") -> Path:
    """
    Get or create log directory.

    Creates logs/ directory in project root if found,
    otherwise uses ~/.{app_name}/logs/

    Args:
        app_name: Application name for fallback directory

    Returns:
        Path to log directory (created if needed)
    """
    project_root = find_project_root()

    if project_root:
        log_dir = project_root / "logs"
    else:
        # Fallback to user home
        log_dir = Path.home() / f".{app_name}" / "logs"

    # Create directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir


__all__ = ["find_project_root", "get_log_dir", "PROJECT_MARKERS"]
