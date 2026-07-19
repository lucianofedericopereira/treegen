"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


def make_sample_tree(root: Path) -> None:
    """Create a small, deterministic directory tree under ``root``."""
    (root / "brand-identity" / "logos").mkdir(parents=True)
    (root / "brand-identity" / "banners").mkdir(parents=True)
    (root / "design-resources").mkdir(parents=True)
    (root / "media-center" / "press-kit").mkdir(parents=True)
    (root / "brand-identity" / "logos" / "logo.svg").write_text("x", encoding="utf-8")
    (root / "brand-identity" / "logos" / "icon.png").write_text("x", encoding="utf-8")
    (root / "design-resources" / "ui-kit.fig").write_text("x", encoding="utf-8")


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    make_sample_tree(tmp_path)
    return tmp_path
