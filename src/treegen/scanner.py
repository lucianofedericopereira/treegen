"""Walk a directory into a :class:`~treegen.model.Node` tree."""

from __future__ import annotations

import os
from pathlib import Path

from .config import TreeOptions
from .descriptions import Descriptions
from .ignore import Matcher
from .model import Node


def build_tree(base: Path, options: TreeOptions) -> Node:
    """Scan ``options.directory`` (resolved against ``base``) into a tree.

    Args:
        base: The directory the README lives in / the repository root.
        options: Rendering options controlling depth, excludes, and so on.

    Returns:
        The root :class:`Node`. Its ``path`` is ``""`` and its ``name`` is the
        resolved directory's display name.
    """
    root_dir = (base / options.directory).resolve()
    if not root_dir.is_dir():
        raise NotADirectoryError(f"not a directory: {root_dir}")

    matcher = Matcher.build(root_dir, options.exclude, options.use_gitignore)
    descriptions = Descriptions.load(options.descriptions_file, base)

    root_name = "." if options.directory in {"", "."} else root_dir.name
    root = Node(name=root_name, path="", is_dir=True, description=descriptions.get(""))
    _scan_into(root, root_dir, "", 1, options, matcher, descriptions)
    return root


def _scan_into(
    parent: Node,
    directory: Path,
    rel_prefix: str,
    depth: int,
    options: TreeOptions,
    matcher: Matcher,
    descriptions: Descriptions,
) -> None:
    if options.max_depth and depth > options.max_depth:
        return

    try:
        entries = list(os.scandir(directory))
    except PermissionError:
        return

    for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower())):
        is_dir = entry.is_dir()
        if options.dirs_only and not is_dir:
            continue
        rel_path = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name
        if matcher.is_excluded(rel_path, is_dir):
            continue

        node = Node(
            name=entry.name,
            path=rel_path,
            is_dir=is_dir,
            description=descriptions.get(rel_path),
        )
        parent.children.append(node)
        if is_dir:
            _scan_into(
                node,
                Path(entry.path),
                rel_path,
                depth + 1,
                options,
                matcher,
                descriptions,
            )
