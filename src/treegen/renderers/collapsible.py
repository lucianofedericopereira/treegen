"""GitHub-native collapsible tree using nested ``<details>`` elements.

Each directory becomes a ``<details>`` you can expand/collapse directly on
GitHub; files are grouped into ``<ul>`` lists. Everything is plain HTML so it
renders identically whether or not the surrounding Markdown parser is lenient.
"""

from __future__ import annotations

from html import escape

from ..config import TreeOptions
from ..model import Node

FOLDER_ICON = "\U0001f4c1"  # 📁
FILE_ICON = "\U0001f4c4"  # 📄
INDENT = "  "


def _row(icon: str, name_html: str, node: Node) -> str:
    """Build ``<span class="ft-name">icon name</span> <em class="ft-note">…</em>``.

    No dash separator; the ``ft-name`` / ``ft-note`` split lets a host page
    align the notes into a column (see the landing page CSS). On GitHub, which
    strips CSS, it simply renders inline.
    """
    name = f'<span class="ft-name">{icon} {name_html}</span>'
    if not node.description:
        return name
    return f'{name} <em class="ft-note">{escape(node.description)}</em>'


def _render_dir(node: Node, options: TreeOptions, indent: str) -> list[str]:
    lines: list[str] = []
    open_attr = " open" if options.open else ""
    summary = _row(FOLDER_ICON, f"<strong>{escape(node.name)}</strong>", node)
    lines.append(f"{indent}<details{open_attr}>")
    lines.append(f"{indent}<summary>{summary}</summary>")
    lines.extend(_render_children(node, options, indent + INDENT))
    lines.append(f"{indent}</details>")
    return lines


def _render_children(node: Node, options: TreeOptions, indent: str) -> list[str]:
    children = node.sorted_children()
    lines: list[str] = []
    pending_files: list[Node] = []

    def flush_files() -> None:
        if not pending_files:
            return
        lines.append(f"{indent}<ul>")
        for file_node in pending_files:
            item = _row(FILE_ICON, escape(file_node.name), file_node)
            lines.append(f"{indent}{INDENT}<li>{item}</li>")
        lines.append(f"{indent}</ul>")
        pending_files.clear()

    for child in children:
        if child.is_dir:
            flush_files()
            lines.extend(_render_dir(child, options, indent))
        else:
            pending_files.append(child)
    flush_files()
    return lines


def render_collapsible(root: Node, options: TreeOptions) -> str:
    """Render ``root`` as nested collapsible ``<details>`` blocks."""
    if options.show_root:
        return "\n".join(_render_dir(root, options, ""))
    lines = _render_children(root, options, "")
    return "\n".join(lines) if lines else "<em>(empty)</em>"
