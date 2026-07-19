"""treegen — inject directory trees into Markdown files.

A small, dependency-free toolkit that scans a directory and renders it as an
ASCII tree, a themeable SVG image, or a GitHub-native collapsible ``<details>``
tree, then splices the result into your ``README.md`` between markers.

Public entry points live in :mod:`treegen.cli`.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
