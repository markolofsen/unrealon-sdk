"""
Local storage for parser results.

Saves parsed data to JSON files for backup/debugging.

Usage:
    from unrealon.parsers import ResultStorage

    storage = ResultStorage("myparser")
    storage.save("item-123", {"id": "123", "text": "...", "photos": [...]})

    # Files saved to: results/myparser/item-123.json
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ResultStorage:
    """Local storage for parser results."""

    def __init__(
        self,
        source_code: str,
        root_dir: str | Path = "results",
    ):
        """
        Initialize storage.

        Args:
            source_code: Parser identifier (e.g., "encar")
            root_dir: Root directory for results (default: "results")
        """
        self.source_code = source_code
        self.root = Path(root_dir) / source_code
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, item_id: str, data: dict[str, Any]) -> Path:
        """
        Save item data to JSON file.

        Args:
            item_id: Unique item identifier
            data: Data to save

        Returns:
            Path to saved file
        """
        # Add metadata
        data["_saved_at"] = datetime.now().isoformat()

        path = self.root / f"{item_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def load(self, item_id: str) -> dict[str, Any] | None:
        """
        Load item data from JSON file.

        Args:
            item_id: Unique item identifier

        Returns:
            Loaded data or None if not found
        """
        path = self.root / f"{item_id}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def exists(self, item_id: str) -> bool:
        """Check if item exists in storage."""
        return (self.root / f"{item_id}.json").exists()

    def list_ids(self) -> list[str]:
        """List all saved item IDs."""
        return [p.stem for p in self.root.glob("*.json")]

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        files = list(self.root.glob("*.json"))
        return {
            "root": str(self.root),
            "count": len(files),
            "size_mb": sum(f.stat().st_size for f in files) / (1024 * 1024),
        }

    def clear(self) -> int:
        """
        Clear all saved items.

        Returns:
            Number of files deleted
        """
        count = 0
        for f in self.root.glob("*.json"):
            f.unlink()
            count += 1
        return count
