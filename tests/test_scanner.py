"""Tests for the directory scanner."""

from __future__ import annotations

from pathlib import Path

from treegen.config import TreeOptions
from treegen.scanner import build_tree


def _names(root_path: Path, options: TreeOptions) -> list[str]:
    root = build_tree(root_path, options)
    return [child.name for child in root.sorted_children()]


def test_directories_sorted_before_files(sample_tree: Path) -> None:
    root = build_tree(sample_tree, TreeOptions())
    top = root.sorted_children()
    assert [n.name for n in top] == [
        "brand-identity",
        "design-resources",
        "media-center",
    ]


def test_dirs_only(sample_tree: Path) -> None:
    root = build_tree(sample_tree, TreeOptions(dirs_only=True))
    logos = next(
        c
        for c in next(c for c in root.children if c.name == "brand-identity").children
        if c.name == "logos"
    )
    assert logos.children == []  # files dropped


def test_max_depth(sample_tree: Path) -> None:
    root = build_tree(sample_tree, TreeOptions(max_depth=1))
    brand = next(c for c in root.children if c.name == "brand-identity")
    assert brand.children == []  # depth limited to the top level


def test_exclude_pattern(sample_tree: Path) -> None:
    names = _names(sample_tree, TreeOptions(exclude=("design-resources",)))
    assert "design-resources" not in names


def test_gitignore_respected(sample_tree: Path) -> None:
    (sample_tree / ".gitignore").write_text("media-center/\n", encoding="utf-8")
    names = _names(sample_tree, TreeOptions())
    assert "media-center" not in names


def test_subdirectory_scan(sample_tree: Path) -> None:
    root = build_tree(sample_tree, TreeOptions(directory="brand-identity"))
    assert root.name == "brand-identity"
    assert {c.name for c in root.children} == {"banners", "logos"}
