"""Options for a single tree block and helpers for merging marker attributes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

# Styles understood by :func:`treegen.renderers.render`.
STYLE_ASCII = "ascii"
STYLE_SVG = "svg"
STYLE_COLLAPSIBLE = "collapsible"
STYLES = (STYLE_ASCII, STYLE_SVG, STYLE_COLLAPSIBLE)

# Named folder colours for the SVG style (macOS-label-ish). The actual hex
# values (light + dark) live in :data:`treegen.renderers.svg.PALETTE`.
COLORS = ("blue", "green", "red", "orange", "yellow", "purple", "pink", "gray")

# The default, "github", is a smart default that matches GitHub's own folder
# colour (Primer blue, theme-aware). It resolves to the "blue" palette entry.
DEFAULT_COLOR = "github"
COLOR_CHOICES = (DEFAULT_COLOR, *COLORS)


@dataclass(frozen=True)
class TreeOptions:
    """Everything needed to render one tree block.

    Values come from three layers (lowest priority first): built-in defaults,
    action/CLI inputs, and per-marker attributes. Later layers win.
    """

    directory: str = "."
    style: str = STYLE_ASCII
    max_depth: int = 0  # 0 means "no limit".
    dirs_only: bool = False
    exclude: tuple[str, ...] = ()
    use_gitignore: bool = True
    show_root: bool = False
    descriptions_file: str | None = None
    # Output flavour: "markdown" (code fence / image / details) or "html"
    # (styled <pre>/<img>/<details>) for embedding in an HTML page.
    output_format: str = "markdown"
    svg_output: str = "assets/filetree.svg"
    # Folder colour for the SVG style: "github" (default, matches GitHub) or a
    # name from COLORS; ignored for other styles.
    color: str = DEFAULT_COLOR
    # SVG backdrop: "auto" (theme-aware framed panel), "transparent", or a CSS
    # colour to blend the tree into a themed page.
    background: str = "auto"
    # Wrap the rendered block in a single top-level <details> element.
    collapse: bool = False
    # Whether that top-level <details> (and collapsible folders) start open.
    open: bool = True
    # Optional label for the <details> summary / SVG alt text.
    title: str = "Project structure"


# Marker attribute name -> canonical TreeOptions field name.
_ALIASES: dict[str, str] = {
    "dir": "directory",
    "directory": "directory",
    "path": "directory",
    "style": "style",
    "depth": "max_depth",
    "max-depth": "max_depth",
    "max_depth": "max_depth",
    "dirs-only": "dirs_only",
    "dirs_only": "dirs_only",
    "dirsonly": "dirs_only",
    "exclude": "exclude",
    "ignore": "exclude",
    "gitignore": "use_gitignore",
    "use-gitignore": "use_gitignore",
    "use_gitignore": "use_gitignore",
    "root": "show_root",
    "show-root": "show_root",
    "show_root": "show_root",
    "desc": "descriptions_file",
    "descriptions": "descriptions_file",
    "descriptions-file": "descriptions_file",
    "descriptions_file": "descriptions_file",
    "svg": "svg_output",
    "svg-output": "svg_output",
    "svg_output": "svg_output",
    "output": "svg_output",
    "format": "output_format",
    "output-format": "output_format",
    "output_format": "output_format",
    "color": "color",
    "colour": "color",
    "svg-color": "color",
    "background": "background",
    "bg": "background",
    "svg-bg": "background",
    "collapse": "collapse",
    "open": "open",
    "title": "title",
}

_BOOL_FIELDS = {"dirs_only", "use_gitignore", "show_root", "collapse", "open"}
_INT_FIELDS = {"max_depth"}
_TUPLE_FIELDS = {"exclude"}


def parse_bool(value: str) -> bool:
    """Parse a human-friendly truthy/falsey string."""
    return value.strip().lower() in {"1", "true", "yes", "on", "y", ""}


def _split_list(value: str) -> tuple[str, ...]:
    """Split a comma/newline separated list, dropping blanks."""
    parts = (piece.strip() for chunk in value.splitlines() for piece in chunk.split(","))
    return tuple(part for part in parts if part)


def apply_attrs(base: TreeOptions, attrs: dict[str, str]) -> TreeOptions:
    """Return a copy of ``base`` with marker ``attrs`` applied on top."""
    updates: dict[str, Any] = {}
    for raw_key, raw_value in attrs.items():
        field_name = _ALIASES.get(raw_key.strip().lower().replace("_", "-"))
        if field_name is None:
            field_name = _ALIASES.get(raw_key.strip().lower())
        if field_name is None:
            continue
        if field_name in _BOOL_FIELDS:
            updates[field_name] = parse_bool(raw_value)
        elif field_name in _INT_FIELDS:
            try:
                updates[field_name] = int(raw_value)
            except ValueError:
                continue
        elif field_name in _TUPLE_FIELDS:
            merged = base.exclude + _split_list(raw_value)
            updates[field_name] = merged
        else:
            updates[field_name] = raw_value
    return replace(base, **updates)
