"""Optional per-path descriptions loaded from a JSON file.

The file maps a POSIX path (relative to the scan root) to a short note, e.g.::

    {
      "brand-identity": "Core visual brand elements",
      "brand-identity/logos": "Official logos and icons (SVG, PNG)"
    }

Trailing slashes on keys are ignored, so ``"logos/"`` and ``"logos"`` match.
"""

from __future__ import annotations

import json
from pathlib import Path


class Descriptions:
    """A lookup of path -> description, tolerant of trailing slashes."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = {key.strip("/"): value for key, value in mapping.items()}

    def get(self, path: str) -> str | None:
        """Return the description for ``path`` (POSIX, root-relative), if any."""
        return self._mapping.get(path.strip("/")) or None

    def __bool__(self) -> bool:
        return bool(self._mapping)

    @classmethod
    def empty(cls) -> Descriptions:
        return cls({})

    @classmethod
    def load(cls, path: str | None, base: Path) -> Descriptions:
        """Load descriptions from ``path`` (relative to ``base``), if it exists."""
        if not path:
            return cls.empty()
        file_path = base / path
        if not file_path.is_file():
            return cls.empty()
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{file_path}: expected a JSON object of path -> text")
        mapping: dict[str, str] = {}
        for key, value in raw.items():
            mapping[str(key)] = str(value)
        return cls(mapping)
