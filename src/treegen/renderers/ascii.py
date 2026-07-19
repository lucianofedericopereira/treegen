"""Classic ``tree``-style ASCII renderer with optional aligned descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from ..config import TreeOptions
from ..model import Node, iter_rows


@dataclass(frozen=True)
class _AsciiRow:
    branch: str  # The leading connectors, e.g. "│   ├── ".
    name: str
    is_dir: bool
    description: str | None

    @property
    def width(self) -> int:
        return len(self.branch) + len(self.name) + (1 if self.is_dir else 0)


def _ascii_rows(root: Node, options: TreeOptions) -> list[_AsciiRow]:
    rows: list[_AsciiRow] = []
    if options.show_root:
        rows.append(_AsciiRow("", root.name, root.is_dir, root.description))
    for row in iter_rows(root):
        prefix = "".join("    " if last else "│   " for last in row.ancestors_last)
        connector = "└── " if row.is_last else "├── "
        rows.append(
            _AsciiRow(prefix + connector, row.node.name, row.node.is_dir,
                      row.node.description)
        )
    return rows


def render_ascii(root: Node, options: TreeOptions) -> str:
    """Render ``root``'s tree using ├──/└──/│ connectors.

    Returns the raw text (no code fence); the caller wraps it.
    """
    rows = _ascii_rows(root, options)
    # Align every description to a single column, based only on the rows that
    # actually carry one (so a long path without a note can't push them out).
    width = max((r.width for r in rows if r.description), default=0)

    lines: list[str] = []
    for r in rows:
        text = r.branch + r.name + ("/" if r.is_dir else "")
        if r.description:
            lines.append(f"{text.ljust(width)}  # {r.description}")
        else:
            lines.append(text)
    return "\n".join(lines) if lines else "(empty)"


def render_ascii_html(root: Node, options: TreeOptions) -> str:
    """Render the ASCII tree as a coloured ``<pre>`` for embedding in HTML.

    Same layout as :func:`render_ascii`, but each part is wrapped in a span so a
    host page can colour connectors, names, slashes and comments independently
    (classes ``ft-branch``, ``ft-dir`` / ``ft-file``, ``ft-slash``, ``ft-comment``).
    """
    rows = _ascii_rows(root, options)
    width = max((r.width for r in rows if r.description), default=0)

    lines: list[str] = []
    for r in rows:
        name_class = "ft-dir" if r.is_dir else "ft-file"
        parts = [
            f'<span class="ft-branch">{escape(r.branch)}</span>',
            f'<span class="{name_class}">{escape(r.name)}</span>',
        ]
        if r.is_dir:
            parts.append('<span class="ft-slash">/</span>')
        if r.description:
            pad = " " * (width - r.width + 2)
            parts.append(f'{pad}<span class="ft-comment"># {escape(r.description)}</span>')
        lines.append("".join(parts))

    inner = "\n".join(lines) if lines else "(empty)"
    return f'<pre class="filetree-ascii">{inner}</pre>'
