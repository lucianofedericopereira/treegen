"""Tests for marker discovery and README splicing."""

from __future__ import annotations

from pathlib import Path

from treegen.config import TreeOptions
from treegen.readme import (
    ProcessResult,
    has_markers,
    parse_attributes,
    process_file,
)


def _run(sample_tree: Path, body: str) -> ProcessResult:
    readme = sample_tree / "README.md"
    readme.write_text(body, encoding="utf-8")
    return process_file(readme, TreeOptions(), sample_tree)


def test_parse_attributes_forms() -> None:
    attrs = parse_attributes(' dir="src" style=svg collapse title=\'My Tree\' ')
    assert attrs == {
        "dir": "src",
        "style": "svg",
        "collapse": "true",
        "title": "My Tree",
    }


def test_placeholder_expands_to_marker_block(sample_tree: Path) -> None:
    result = _run(sample_tree, "# Title\n\n[[files]]\n")
    assert "<!-- filetree:start -->" in result.text
    assert "<!-- filetree:end -->" in result.text
    assert "brand-identity/" in result.text
    assert result.changed
    assert result.blocks == 1


def test_placeholder_preserves_attributes(sample_tree: Path) -> None:
    result = _run(sample_tree, '[[files dir="brand-identity" style="ascii"]]\n')
    assert '<!-- filetree:start dir="brand-identity" style="ascii" -->' in result.text


def test_regeneration_is_idempotent(sample_tree: Path) -> None:
    first = _run(sample_tree, "[[files]]\n")
    (sample_tree / "README.md").write_text(first.text, encoding="utf-8")
    second = process_file(sample_tree / "README.md", TreeOptions(), sample_tree)
    assert not second.changed
    assert second.text == first.text


def test_marker_block_updates_when_tree_changes(sample_tree: Path) -> None:
    first = _run(sample_tree, "[[files]]\n")
    (sample_tree / "README.md").write_text(first.text, encoding="utf-8")
    (sample_tree / "new-folder").mkdir()
    second = process_file(sample_tree / "README.md", TreeOptions(), sample_tree)
    assert second.changed
    assert "new-folder/" in second.text


def test_has_markers() -> None:
    assert has_markers("intro [[files]] outro")
    assert has_markers("<!-- filetree:start --><!-- filetree:end -->")
    assert not has_markers("nothing here")


def test_placeholder_in_fenced_code_is_ignored(sample_tree: Path) -> None:
    body = "Docs:\n\n```md\n[[files]]\n```\n\nReal:\n\n[[files]]\n"
    result = _run(sample_tree, body)
    # The fenced example is preserved verbatim...
    assert "```md\n[[files]]\n```" in result.text
    # ...while the real one outside the fence is expanded exactly once.
    assert result.blocks == 1
    assert "<!-- filetree:start -->" in result.text


def test_placeholder_in_inline_code_is_ignored(sample_tree: Path) -> None:
    result = _run(sample_tree, "Use `[[files]]` to insert a tree.\n")
    assert result.text == "Use `[[files]]` to insert a tree.\n"
    assert not result.changed


def test_marker_block_in_fence_not_regenerated(sample_tree: Path) -> None:
    body = "```\n<!-- filetree:start -->\n<!-- filetree:end -->\n```\n"
    result = _run(sample_tree, body)
    assert result.text == body
    assert result.blocks == 0


def test_marker_in_inline_code_is_not_expanded(sample_tree: Path) -> None:
    # A marker written inside `inline code` in prose must be left alone, and
    # must NOT swallow content up to the next real end marker.
    body = (
        "The `<!-- filetree:start -->` marker starts a block.\n"
        "\n"
        "Keep me.\n"
        "\n"
        "[[files]]\n"
    )
    result = _run(sample_tree, body)
    assert "Keep me." in result.text
    assert "The `<!-- filetree:start -->` marker starts a block." in result.text
    assert result.blocks == 1


def test_nested_fence_protects_inner_markers(sample_tree: Path) -> None:
    # A 4-backtick fence documenting a block that itself contains a 3-backtick
    # fence must be preserved verbatim (inner ``` must not close the outer).
    body = (
        "````markdown\n"
        "<!-- filetree:start -->\n"
        "```\n"
        "tree here\n"
        "```\n"
        "<!-- filetree:end -->\n"
        "````\n"
        "\n"
        "[[files]]\n"
    )
    result = _run(sample_tree, body)
    assert "tree here" in result.text  # documented block untouched
    assert result.blocks == 1  # only the real placeholder expanded


def test_no_placeholder_fills_markers_only(sample_tree: Path) -> None:
    page = sample_tree / "page.html"
    page.write_text(
        '<!-- filetree:start dirs-only="true" format="html" -->\n'
        "<!-- filetree:end -->\n"
        "Docs mention [[files]] literally.\n",
        encoding="utf-8",
    )
    result = process_file(
        page, TreeOptions(), sample_tree, enable_placeholder=False
    )
    assert '<pre class="filetree-ascii">' in result.text  # marker filled as HTML
    assert "[[files]]" in result.text  # literal token untouched


def test_custom_placeholder(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    readme.write_text("[[tree]]\n", encoding="utf-8")
    result = process_file(readme, TreeOptions(), sample_tree, placeholder="tree")
    assert "<!-- filetree:start -->" in result.text
