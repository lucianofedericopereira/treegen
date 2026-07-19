"""Core data model shared across the scanner and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Node:
    """A single entry in a directory tree.

    Attributes:
        name: The bare file or directory name (no path separators).
        path: POSIX-style path relative to the scan root (``""`` for the root).
        is_dir: Whether this node is a directory.
        children: Child nodes, already sorted (directories first, then files).
        description: Optional human-written note shown next to the entry.
    """

    name: str
    path: str
    is_dir: bool
    children: list[Node] = field(default_factory=list)
    description: str | None = None

    def sorted_children(self) -> list[Node]:
        """Return children with directories first, then alphabetical by name."""
        return sorted(self.children, key=lambda n: (not n.is_dir, n.name.lower()))


@dataclass(frozen=True)
class Row:
    """A flattened tree row used by the ASCII and SVG renderers.

    Attributes:
        node: The node this row represents.
        depth: Indentation depth (0 for top-level entries under the root).
        is_last: Whether this node is the last among its siblings.
        ancestors_last: For each ancestor level, whether that ancestor was the
            last of its siblings. Drives the ``│`` vs. blank guide columns.
    """

    node: Node
    depth: int
    is_last: bool
    ancestors_last: tuple[bool, ...]


def iter_rows(root: Node) -> list[Row]:
    """Flatten ``root``'s descendants (not the root itself) into display rows."""
    rows: list[Row] = []

    def walk(node: Node, ancestors: tuple[bool, ...]) -> None:
        children = node.sorted_children()
        for index, child in enumerate(children):
            is_last = index == len(children) - 1
            rows.append(Row(child, len(ancestors), is_last, ancestors))
            walk(child, (*ancestors, is_last))

    walk(root, ())
    return rows
