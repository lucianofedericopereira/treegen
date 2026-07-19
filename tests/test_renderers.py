"""Tests for the ASCII, collapsible, and SVG renderers."""

from __future__ import annotations

from pathlib import Path

from treegen.config import STYLE_SVG, TreeOptions
from treegen.descriptions import Descriptions
from treegen.model import Node
from treegen.renderers import RenderContext, render
from treegen.renderers.ascii import render_ascii, render_ascii_html
from treegen.renderers.collapsible import render_collapsible
from treegen.renderers.svg import PALETTE, build_svg, render_svg
from treegen.scanner import build_tree


def _tree(sample_tree: Path, **kwargs: object) -> Node:
    return build_tree(sample_tree, TreeOptions(**kwargs))  # type: ignore[arg-type]


def test_ascii_connectors(sample_tree: Path) -> None:
    out = render_ascii(_tree(sample_tree), TreeOptions())
    lines = out.splitlines()
    assert lines[0].startswith("├── brand-identity/")
    assert any(line.startswith("└── media-center/") for line in lines)
    assert any(line.startswith("│   ") for line in lines)


def test_ascii_descriptions_aligned(sample_tree: Path) -> None:
    root = build_tree(sample_tree, TreeOptions())
    root.description = None
    for child in root.children:
        if child.name == "brand-identity":
            child.description = "Brand"
        if child.name == "media-center":
            child.description = "Media"
    out = render_ascii(root, TreeOptions())
    comment_columns = {line.index("#") for line in out.splitlines() if "#" in line}
    assert len(comment_columns) == 1  # all descriptions aligned to one column


def test_collapsible_structure(sample_tree: Path) -> None:
    out = render_collapsible(_tree(sample_tree), TreeOptions())
    assert "<details open>" in out
    assert "<summary>" in out
    assert "logo.svg" in out
    assert out.count("</details>") == out.count("<details")


def test_collapsible_notes_have_no_dash(sample_tree: Path) -> None:
    root = build_tree(sample_tree, TreeOptions())
    for child in root.children:
        if child.name == "brand-identity":
            child.description = "Brand assets"
    out = render_collapsible(root, TreeOptions())
    assert "&mdash;" not in out and " — " not in out  # dash removed
    assert '<em class="ft-note">Brand assets</em>' in out  # note wrapped for aligning
    assert '<span class="ft-name">' in out


def test_collapsible_closed(sample_tree: Path) -> None:
    out = render_collapsible(_tree(sample_tree), TreeOptions(open=False))
    assert "<details>" in out
    assert "<details open>" not in out


def test_svg_has_viewbox_and_theme(sample_tree: Path) -> None:
    svg = build_svg(_tree(sample_tree), TreeOptions())
    assert "viewBox=" in svg
    assert 'width="' in svg and 'height="' in svg  # intrinsic size -> responsive
    assert "prefers-color-scheme: dark" in svg
    assert 'class="folder"' in svg
    assert svg.strip().endswith("</svg>")


def test_svg_descriptions_render() -> None:
    root = Node("root", "", True, [Node("docs", "docs", True, [], "Documentation")])
    svg = build_svg(root, TreeOptions())
    assert "Documentation" in svg


def test_svg_has_no_slash_and_aligned_comments() -> None:
    import re

    root = Node("root", "", True, [
        Node("a", "a", True, [], "first"),
        Node("bbbbb", "bbbbb", True, [], "second"),
    ])
    svg = build_svg(root, TreeOptions())
    # Directory names carry no trailing slash in the SVG.
    assert "/</tspan>" not in svg
    # Comments are the plain description, with no "# " prefix.
    assert ">first</tspan>" in svg
    assert "# first" not in svg
    # Both comments share the same x column (aligned).
    cols = re.findall(r'class="comment" x="([0-9.]+)"', svg)
    assert len(cols) == 2 and cols[0] == cols[1]


def test_svg_named_color_changes_folder_fill(sample_tree: Path) -> None:
    blue = build_svg(_tree(sample_tree), TreeOptions(color="blue"))
    green = build_svg(_tree(sample_tree), TreeOptions(color="green"))
    assert PALETTE["green"][0] in green  # green folder fill (light)
    assert PALETTE["green"][1] in green  # green name fill (light)
    assert PALETTE["blue"][0] in blue and PALETTE["blue"][0] not in green


def test_svg_unknown_color_falls_back_to_blue(sample_tree: Path) -> None:
    out = build_svg(_tree(sample_tree), TreeOptions(color="chartreuse"))
    assert PALETTE["blue"][0] in out


def test_svg_background_transparent_omits_backdrop(sample_tree: Path) -> None:
    framed = build_svg(_tree(sample_tree), TreeOptions())  # auto
    bare = build_svg(_tree(sample_tree), TreeOptions(background="transparent"))
    assert 'class="bg"' in framed
    assert 'class="bg"' not in bare  # no backdrop rect


def test_svg_custom_background_color(sample_tree: Path) -> None:
    out = build_svg(_tree(sample_tree), TreeOptions(background="#e6f0e6"))
    assert 'fill="#e6f0e6"' in out


def test_default_color_is_github_and_matches_primer(sample_tree: Path) -> None:
    assert TreeOptions().color == "github"  # smart default
    out = build_svg(_tree(sample_tree), TreeOptions())
    assert PALETTE["github"].name_l in out       # Primer accent blue names
    assert PALETTE["github"].comment_l in out    # neutral muted comment (not tinted)


def test_svg_line_and_dot_follow_scheme(sample_tree: Path) -> None:
    out = build_svg(_tree(sample_tree), TreeOptions(color="green"))
    assert PALETTE["green"].line_l in out  # connectors tinted to the scheme
    assert 'class="dot"' in out            # node dots present


def test_palette_covers_declared_colors() -> None:
    from treegen.config import COLORS, DEFAULT_COLOR
    assert set(PALETTE) == set(COLORS) | {DEFAULT_COLOR}


def test_html_ascii_render(sample_tree: Path) -> None:
    out = render_ascii_html(_tree(sample_tree), TreeOptions(output_format="html"))
    assert out.startswith('<pre class="filetree-ascii">')
    assert 'class="ft-branch"' in out
    assert 'class="ft-dir"' in out
    assert 'class="ft-slash"' in out
    assert out.endswith("</pre>")


def test_svg_html_embed_is_img_tag(sample_tree: Path) -> None:
    page = sample_tree / "index.html"
    page.write_text("x", encoding="utf-8")
    opts = TreeOptions(style=STYLE_SVG, output_format="html", svg_output="assets/t.svg")
    result = render_svg(_tree(sample_tree), opts, sample_tree, page)
    assert result.markdown.startswith('<img class="filetree-svg"')
    assert 'src="assets/t.svg"' in result.markdown


def test_render_svg_writes_asset_and_embeds(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    readme.write_text("placeholder", encoding="utf-8")
    options = TreeOptions(style=STYLE_SVG, svg_output="assets/tree.svg")
    result = render_svg(_tree(sample_tree), options, sample_tree, readme)
    assert result.markdown == "![Project structure](assets/tree.svg)"
    (svg_path,) = result.assets
    assert svg_path == (sample_tree / "assets" / "tree.svg").resolve()


def test_render_dispatch_collapse_wraps(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    ctx = RenderContext(base=sample_tree, readme_path=readme)
    result = render(_tree(sample_tree), TreeOptions(collapse=True), ctx)
    assert result.markdown.startswith("<details")
    assert result.markdown.rstrip().endswith("</details>")


def test_descriptions_lookup(tmp_path: Path) -> None:
    (tmp_path / "d.json").write_text('{"a/b/": "note"}', encoding="utf-8")
    desc = Descriptions.load("d.json", tmp_path)
    assert desc.get("a/b") == "note"
    assert desc.get("a/b/") == "note"
    assert desc.get("missing") is None
