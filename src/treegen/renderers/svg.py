"""Render a directory tree to a themeable, responsive SVG image.

The generated SVG:

* carries a ``viewBox`` plus intrinsic ``width``/``height`` so GitHub scales it
  down to the container width without distortion (responsive);
* ships light and dark palettes lifted from GitHub's Primer design tokens,
  switched with ``@media (prefers-color-scheme: dark)`` so it matches whichever
  theme the reader is using;
* draws real folder/file glyphs and ``tree``-style connector lines.

Because GitHub strips inline ``<svg>`` from Markdown, the image is written to a
file and embedded with a normal Markdown image reference (which GitHub renders
and, thanks to its stylesheet, makes responsive for free).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from xml.sax.saxutils import escape

from ..config import TreeOptions
from ..model import Node, iter_rows

if TYPE_CHECKING:
    from . import RenderResult

# --- Layout constants (all in SVG user units == px at 100% scale). ----------
FONT_SIZE = 13
LINE_HEIGHT = 22
CHAR_WIDTH = 7.8  # Monospace advance width at FONT_SIZE.
PAD_X = 16
PAD_Y = 14
INDENT = 22
ICON_W = 16
ICON_GAP = 8


@dataclass(frozen=True)
class _PlacedRow:
    node: Node
    depth: int
    is_last: bool
    ancestors_last: tuple[bool, ...]


def _place_rows(root: Node, options: TreeOptions) -> list[_PlacedRow]:
    rows: list[_PlacedRow] = []
    if options.show_root:
        rows.append(_PlacedRow(root, -1, True, ()))
    for row in iter_rows(root):
        rows.append(
            _PlacedRow(row.node, row.depth, row.is_last, row.ancestors_last)
        )
    return rows


def _cx(depth: int) -> float:
    """X centre of the connector column for a node at ``depth``."""
    return PAD_X + depth * INDENT + INDENT * 0.5


def _icon_x(depth: int) -> float:
    """Left edge of the icon for a node at ``depth``."""
    return PAD_X + (depth + 1) * INDENT


COMMENT_GAP = 22  # Space between the longest name and the aligned comment column.


def _folder_glyph(x: float, y: float) -> str:
    # A folder silhouette with a tab on the upper-left. All commands are
    # relative so the glyph can be dropped at any (x, y) offset.
    d = (
        f"M{x + 1} {y + 4}"
        "h4.5l1.4 1.6h8.1v7.8h-14z"
    )
    return f'<path class="folder" d="{d}"/>'


def _file_glyph(x: float, y: float) -> str:
    body = f"M{x + 3.5} {y + 2}h5l3 3v9h-8z"
    fold = f"M{x + 8.5} {y + 2}v3h3"
    return (
        f'<path class="file" d="{body}"/>'
        f'<path class="file-fold" d="{fold}"/>'
    )


def build_svg(root: Node, options: TreeOptions) -> str:
    """Build the SVG document as a string."""
    rows = _place_rows(root, options)

    # Geometry pre-pass. Names carry no trailing slash in the SVG; instead the
    # comments are aligned into a single column (like the ASCII renderer), which
    # is why they need no leading "#".
    def text_x_of(depth: int) -> float:
        return _icon_x(depth) + ICON_W + ICON_GAP

    name_end = [text_x_of(r.depth) + len(r.node.name) * CHAR_WIDTH for r in rows]
    desc_indexes = [i for i, r in enumerate(rows) if r.node.description]
    comment_col = (
        max(name_end[i] for i in desc_indexes) + COMMENT_GAP if desc_indexes else 0.0
    )

    right_edges = [
        comment_col + len(row.node.description or "") * CHAR_WIDTH
        if row.node.description
        else name_end[i]
        for i, row in enumerate(rows)
    ]
    width = int(max(right_edges, default=0.0) + PAD_X)
    height = int(PAD_Y * 2 + max(len(rows), 1) * LINE_HEIGHT)

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
        f'role="img" aria-label="{escape(options.title)}">'
    )
    parts.append(_style(options.color))
    background = options.background.strip().lower()
    if background in {"transparent", "none"}:
        pass  # No backdrop — the tree blends into whatever contains it.
    elif background in {"", "auto", "github"}:
        # Theme-aware framed panel (GitHub-matched light/dark).
        parts.append(
            f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
            f'rx="6" class="bg"/>'
        )
    else:  # Custom solid colour.
        parts.append(
            f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" '
            f'rx="6" fill="{escape(options.background)}"/>'
        )

    connectors: list[str] = []
    icons: list[str] = []
    labels: list[str] = []

    for index, row in enumerate(rows):
        row_top = PAD_Y + index * LINE_HEIGHT
        row_mid = row_top + LINE_HEIGHT / 2
        depth = row.depth

        if depth >= 0:
            # Continuation guides from ancestors that still have siblings below.
            for level, ancestor_last in enumerate(row.ancestors_last):
                if not ancestor_last:
                    x = _cx(level)
                    connectors.append(
                        f'<line class="guide" x1="{x:.1f}" y1="{row_top}" '
                        f'x2="{x:.1f}" y2="{row_top + LINE_HEIGHT}"/>'
                    )
            cx = _cx(depth)
            icon_x = _icon_x(depth)
            if row.is_last:
                # Last child: a rounded corner from the spine to the icon.
                r = 6.0
                connectors.append(
                    f'<path class="guide" fill="none" d="M{cx:.1f} {row_top} '
                    f'V{row_mid - r:.1f} Q{cx:.1f} {row_mid:.1f} '
                    f'{cx + r:.1f} {row_mid:.1f} H{icon_x:.1f}"/>'
                )
            else:
                # Middle children stay plain: straight spine + straight tick.
                connectors.append(
                    f'<line class="guide" x1="{cx:.1f}" y1="{row_top}" '
                    f'x2="{cx:.1f}" y2="{row_top + LINE_HEIGHT}"/>'
                )
                connectors.append(
                    f'<line class="guide" x1="{cx:.1f}" y1="{row_mid:.1f}" '
                    f'x2="{icon_x:.1f}" y2="{row_mid:.1f}"/>'
                )

        icon_x = _icon_x(depth)
        icon_y = row_mid - ICON_W / 2
        icons.append(
            _folder_glyph(icon_x, icon_y) if row.node.is_dir
            else _file_glyph(icon_x, icon_y)
        )

        text_x = icon_x + ICON_W + ICON_GAP
        name_class = "name-dir" if row.node.is_dir else "name-file"
        label = (
            f'<text y="{row_mid:.1f}" '
            f'dominant-baseline="central" font-size="{FONT_SIZE}">'
            f'<tspan class="{name_class}" x="{text_x:.1f}">{escape(row.node.name)}</tspan>'
        )
        if row.node.description:
            # Absolute x aligns every comment into one column, no "#" needed.
            label += (
                f'<tspan class="comment" x="{comment_col:.1f}">'
                f'{escape(row.node.description)}</tspan>'
            )
        label += "</text>"
        labels.append(label)

    # A single node dot at the very top of the root spine.
    root_index = next((i for i, row in enumerate(rows) if row.depth == 0), None)
    if root_index is not None:
        cy = PAD_Y + root_index * LINE_HEIGHT
        connectors.append(f'<circle class="dot" cx="{_cx(0):.1f}" cy="{cy}" r="2"/>')

    parts.extend(connectors)
    parts.extend(icons)
    parts.extend(labels)
    parts.append("</svg>")
    return "\n".join(parts)


def render_svg(
    root: Node,
    options: TreeOptions,
    base: Path,
    readme_path: Path,
) -> RenderResult:
    """Build the SVG, schedule it for writing, and return the embed Markdown."""
    from . import RenderResult  # Local import to avoid a cycle.

    svg = build_svg(root, options)
    svg_abs = (base / options.svg_output).resolve()
    rel = os.path.relpath(svg_abs, start=readme_path.resolve().parent)
    rel_posix = Path(rel).as_posix()
    alt = escape(options.title)
    if options.output_format.lower() in {"html", "htm"}:
        embed = f'<img class="filetree-svg" src="{rel_posix}" alt="{alt}" />'
    else:
        embed = f"![{alt}]({rel_posix})"
    return RenderResult(markdown=embed, assets={svg_abs: svg})


class _Palette(NamedTuple):
    """Light + dark colours for one named scheme."""

    folder_l: str
    name_l: str
    comment_l: str
    line_l: str  # connectors + node dots
    folder_d: str
    name_d: str
    comment_d: str
    line_d: str


# Named folder colours (macOS-label-ish), each theme-aware. Folder, name,
# comment AND the connector lines/dots all lean into the scheme — except
# "github" (the default), which matches GitHub's own palette exactly with a
# neutral muted comment and neutral connectors.
PALETTE: dict[str, _Palette] = {
    # fields: light(folder, name, comment, line) then dark(folder, name, comment, line)
    "github": _Palette("#54aeff", "#0969da", "#59636e", "#8c959f", "#388bfd", "#2f81f7", "#8b949e", "#6e7681"),  # noqa: E501
    "blue":   _Palette("#54aeff", "#0969da", "#5b6b7d", "#94b8e0", "#388bfd", "#2f81f7", "#8b98a8", "#4d6480"),  # noqa: E501
    "green":  _Palette("#4ac26b", "#1a7f37", "#5c6f5c", "#93c4a0", "#3fb950", "#57d472", "#8fa891", "#4f6b57"),  # noqa: E501
    "red":    _Palette("#ff8182", "#cf222e", "#86635f", "#e0a3a3", "#f85149", "#ff7b72", "#b39894", "#7d5453"),  # noqa: E501
    "orange": _Palette("#fd9843", "#bc4c00", "#806a52", "#e6b98c", "#ec8e2c", "#e0975a", "#b39d84", "#7d6144"),  # noqa: E501
    "yellow": _Palette("#eac54f", "#9a6700", "#756a4c", "#d8c88a", "#d4a72c", "#e3b341", "#ab9f80", "#6e6440"),  # noqa: E501
    "purple": _Palette("#c297ff", "#8250df", "#6d6280", "#c3aee0", "#a371f7", "#b083f0", "#9c93ad", "#63577a"),  # noqa: E501
    "pink":   _Palette("#ff9bce", "#bf3989", "#856072", "#e8b3cf", "#f778ba", "#ff9bce", "#b394a6", "#7d5468"),  # noqa: E501
    "gray":   _Palette("#afb8c1", "#59636e", "#59636e", "#afb8c1", "#6e7681", "#8b949e", "#8b949e", "#6e7681"),  # noqa: E501
}
# "auto" is a synonym for the default, "github".
_FALLBACK = "github"
_ALIASES = {"auto": "github"}


def _style(color: str) -> str:
    """GitHub-Primer-based ``<style>`` with a chosen scheme colour."""
    key = _ALIASES.get(color.lower(), color.lower())
    p = PALETTE.get(key, PALETTE[_FALLBACK])
    return f"""<style>
  .bg {{ fill: #ffffff; stroke: #d1d9e0; }}
  .name-dir {{ fill: {p.name_l}; font-weight: 600; }}
  .name-file {{ fill: #1f2328; }}
  .comment {{ fill: {p.comment_l}; }}
  .folder {{ fill: {p.folder_l}; }}
  .file {{ fill: #eaeef2; stroke: #afb8c1; stroke-width: 1; }}
  .file-fold {{ fill: none; stroke: #afb8c1; stroke-width: 1; }}
  .guide {{ stroke: {p.line_l}; stroke-width: 1; }}
  .dot {{ fill: {p.line_l}; }}
  @media (prefers-color-scheme: dark) {{
    .bg {{ fill: #0d1117; stroke: #30363d; }}
    .name-dir {{ fill: {p.name_d}; }}
    .name-file {{ fill: #e6edf3; }}
    .comment {{ fill: {p.comment_d}; }}
    .folder {{ fill: {p.folder_d}; }}
    .file {{ fill: #21262d; stroke: #484f58; }}
    .file-fold {{ stroke: #484f58; }}
    .guide {{ stroke: {p.line_d}; }}
    .dot {{ fill: {p.line_d}; }}
  }}
</style>"""
