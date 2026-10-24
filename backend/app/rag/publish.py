"""Active-collection pointer.

A build may mark a new collection ready and then switch this pointer.
Readers use only the named collection. A missing or unreadable pointer is
an error, not a request to open the default collection name.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.rag.errors import StoreError


class IndexPointer:
    def __init__(self, path: Path) -> None:
        self.path = path

    def active(self) -> str:
        """Return the published collection name, or raise ``StoreError``."""
        if not self.path.is_file():
            raise StoreError("Active index pointer is missing.")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise StoreError("Active index pointer is corrupt.") from exc
        if not isinstance(payload, dict):
            raise StoreError("Active index pointer is corrupt.")
        if "active_collection" not in payload:
            raise StoreError("Active index pointer is missing a collection name.")
        name = payload.get("active_collection")
        if not isinstance(name, str) or not name.strip():
            raise StoreError("Active index pointer has an empty collection name.")
        return name.strip()

    def write(self, name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise StoreError("Refusing to publish an empty collection name.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"active_collection": name.strip()}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
