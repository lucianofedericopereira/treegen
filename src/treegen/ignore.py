"""A best-effort ``.gitignore``-style path matcher (standard library only).

This is intentionally a pragmatic subset of full gitignore semantics. It
supports the cases people actually put in these markers:

* bare names match at any depth (``node_modules``, ``*.log``)
* a trailing ``/`` restricts a rule to directories (``build/``)
* a rule containing ``/`` is anchored to the scan root (``src/generated``)
* ``*`` matches within a path segment, ``**`` matches across segments
* a leading ``!`` negates an earlier match

Only the root-level ``.gitignore`` is read; nested ignore files are not merged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Always excluded, regardless of user configuration.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    ".git/",
    ".hg/",
    ".svn/",
    ".DS_Store",
    "node_modules/",
    "__pycache__/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "venv/",
)


def _glob_to_regex(pattern: str) -> str:
    """Translate a glob (already stripped of anchors/flags) into a regex body."""
    out: list[str] = []
    i = 0
    length = len(pattern)
    while i < length:
        char = pattern[i]
        if char == "*":
            if i + 1 < length and pattern[i + 1] == "*":
                # "**/" collapses to "any number of leading segments".
                if i + 2 < length and pattern[i + 2] == "/":
                    out.append("(?:.*/)?")
                    i += 3
                    continue
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    return "".join(out)


@dataclass(frozen=True)
class _Rule:
    regex: re.Pattern[str]
    negate: bool
    dir_only: bool
    anchored: bool


def _compile(pattern: str) -> _Rule | None:
    negate = pattern.startswith("!")
    if negate:
        pattern = pattern[1:]
    dir_only = pattern.endswith("/")
    pattern = pattern.rstrip("/")
    if not pattern:
        return None
    anchored = pattern.startswith("/") or "/" in pattern
    pattern = pattern.lstrip("/")
    regex = re.compile(f"^{_glob_to_regex(pattern)}$")
    return _Rule(regex, negate, dir_only, anchored)


class Matcher:
    """Decide whether a relative path should be excluded from the tree."""

    def __init__(self, patterns: list[str]) -> None:
        self._rules: list[_Rule] = []
        for pattern in patterns:
            stripped = pattern.strip()
            if not stripped or stripped.startswith("#"):
                continue
            rule = _compile(stripped)
            if rule is not None:
                self._rules.append(rule)

    def is_excluded(self, rel_path: str, is_dir: bool) -> bool:
        """Return True if ``rel_path`` (POSIX, root-relative) is ignored."""
        basename = rel_path.rsplit("/", 1)[-1]
        excluded = False
        for rule in self._rules:
            if rule.dir_only and not is_dir:
                continue
            target = rel_path if rule.anchored else basename
            if rule.regex.match(target):
                excluded = not rule.negate
        return excluded

    @classmethod
    def build(
        cls,
        root: Path,
        extra: tuple[str, ...],
        use_gitignore: bool,
    ) -> Matcher:
        """Combine default excludes, user excludes, and root ``.gitignore``."""
        patterns: list[str] = list(DEFAULT_EXCLUDES)
        patterns.extend(extra)
        if use_gitignore:
            gitignore = root / ".gitignore"
            if gitignore.is_file():
                patterns.extend(gitignore.read_text(encoding="utf-8").splitlines())
        return cls(patterns)
