"""Renderers turn a :class:`~treegen.model.Node` tree into Markdown.

Each renderer returns a :class:`RenderResult`: the Markdown to splice into the
README plus any side files to write (only the SVG renderer uses the latter).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..config import STYLE_ASCII, STYLE_COLLAPSIBLE, STYLE_SVG, TreeOptions
from ..model import Node
from .ascii import render_ascii, render_ascii_html
from .collapsible import render_collapsible
from .svg import render_svg


def is_html_format(options: TreeOptions) -> bool:
    """Whether output should be HTML (styled) rather than Markdown."""
    return options.output_format.lower() in {"html", "htm"}


@dataclass(frozen=True)
class RenderContext:
    """Filesystem context a renderer needs to resolve and place assets."""

    base: Path  # Directory the README lives in (assets resolve against it).
    readme_path: Path  # Absolute path of the README being edited.


@dataclass
class RenderResult:
    """Rendered Markdown plus any asset files to write to disk."""

    markdown: str
    assets: dict[Path, str] = field(default_factory=dict)


def _wrap_details(inner: str, title: str, is_open: bool) -> str:
    open_attr = " open" if is_open else ""
    return (
        f"<details{open_attr}>\n"
        f"<summary>{title}</summary>\n\n"
        f"{inner}\n\n"
        f"</details>"
    )


def render(root: Node, options: TreeOptions, ctx: RenderContext) -> RenderResult:
    """Render ``root`` according to ``options.style`` and output format."""
    if options.style == STYLE_ASCII:
        if is_html_format(options):
            result = RenderResult(markdown=render_ascii_html(root, options))
        else:
            result = RenderResult(markdown=f"```\n{render_ascii(root, options)}\n```")
    elif options.style == STYLE_COLLAPSIBLE:
        result = RenderResult(markdown=render_collapsible(root, options))
    elif options.style == STYLE_SVG:
        result = render_svg(root, options, ctx.base, ctx.readme_path)
    else:  # pragma: no cover - guarded by input validation.
        raise ValueError(f"unknown style: {options.style!r}")

    if options.collapse:
        result.markdown = _wrap_details(result.markdown, options.title, options.open)
    return result
