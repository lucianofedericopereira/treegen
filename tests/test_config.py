"""Tests for option merging from marker attributes."""

from __future__ import annotations

from treegen.config import TreeOptions, apply_attrs, parse_bool


def test_apply_attrs_types() -> None:
    base = TreeOptions()
    merged = apply_attrs(
        base,
        {
            "dir": "src",
            "style": "svg",
            "depth": "3",
            "dirs-only": "true",
            "collapse": "yes",
            "open": "false",
        },
    )
    assert merged.directory == "src"
    assert merged.style == "svg"
    assert merged.max_depth == 3
    assert merged.dirs_only is True
    assert merged.collapse is True
    assert merged.open is False


def test_apply_attrs_aliases() -> None:
    merged = apply_attrs(TreeOptions(), {"path": "docs", "max-depth": "2"})
    assert merged.directory == "docs"
    assert merged.max_depth == 2


def test_exclude_accumulates() -> None:
    base = TreeOptions(exclude=("a",))
    merged = apply_attrs(base, {"exclude": "b, c"})
    assert merged.exclude == ("a", "b", "c")


def test_unknown_attrs_ignored() -> None:
    merged = apply_attrs(TreeOptions(), {"bogus": "1"})
    assert merged == TreeOptions()


def test_invalid_int_ignored() -> None:
    merged = apply_attrs(TreeOptions(max_depth=5), {"depth": "notanumber"})
    assert merged.max_depth == 5


def test_parse_bool() -> None:
    assert parse_bool("true")
    assert parse_bool("YES")
    assert parse_bool("")  # bare attribute -> present == true
    assert not parse_bool("false")
    assert not parse_bool("0")
