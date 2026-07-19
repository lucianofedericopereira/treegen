"""Find tree markers/placeholders in a Markdown file and splice in the render.

Two authoring styles are supported:

* **Placeholder** (easy insert): a one-off token, ``[[files]]`` by default,
  optionally carrying attributes: ``[[files dir="src" style="svg"]]``. On the
  first run it is expanded into a managed marker block.
* **Marker block** (idempotent): a ``<!-- filetree:start ... -->`` /
  ``<!-- filetree:end -->`` pair. Everything between the markers is regenerated
  on every run; the start line's attributes are preserved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import TreeOptions, apply_attrs
from .renderers import RenderContext, render
from .scanner import build_tree

_START_RE = re.compile(r"<!--\s*filetree:start(?P<attrs>.*?)-->", re.IGNORECASE)
_END_RE = re.compile(r"<!--\s*filetree:end\s*-->", re.IGNORECASE)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")

_ATTR_RE = re.compile(
    r"""(?P<key>[\w-]+)
        (?:\s*=\s*
            (?: "(?P<dq>[^"]*)"
              | '(?P<sq>[^']*)'
              | (?P<bare>[^\s"'\]]+)
            )
        )?""",
    re.VERBOSE,
)


@dataclass
class ProcessResult:
    """Outcome of processing a single Markdown file."""

    text: str
    assets: dict[Path, str] = field(default_factory=dict)
    changed: bool = False
    blocks: int = 0


def parse_attributes(text: str) -> dict[str, str]:
    """Parse an attribute string like ``dir="src" style=svg collapse`` to a dict."""
    attrs: dict[str, str] = {}
    for match in _ATTR_RE.finditer(text):
        key = match.group("key")
        value = match.group("dq")
        if value is None:
            value = match.group("sq")
        if value is None:
            value = match.group("bare")
        attrs[key] = "true" if value is None else value
    return attrs


def _placeholder_re(name: str) -> re.Pattern[str]:
    escaped = re.escape(name)
    return re.compile(rf"\[\[\s*{escaped}(?P<attrs>[^\]]*)\]\]", re.IGNORECASE)


def _render_block(
    attrs_text: str,
    base_options: TreeOptions,
    ctx: RenderContext,
    assets: dict[Path, str],
) -> str:
    options = apply_attrs(base_options, parse_attributes(attrs_text))
    root = build_tree(ctx.base, options)
    result = render(root, options, ctx)
    assets.update(result.assets)
    return result.markdown


def _start_marker(attrs_text: str) -> str:
    stripped = attrs_text.strip()
    if stripped:
        return f"<!-- filetree:start {stripped} -->"
    return "<!-- filetree:start -->"


_FENCE_OPEN_RE = re.compile(r"^(?P<seq>`{3,}|~{3,})(?P<info>.*)$")


def _fence_open(stripped_line: str) -> tuple[str, int] | None:
    """If the line opens a code fence, return its ``(char, length)``.

    Follows CommonMark closely enough for nesting: a backtick fence's info
    string may not itself contain a backtick.
    """
    match = _FENCE_OPEN_RE.match(stripped_line)
    if match is None:
        return None
    seq = match.group("seq")
    char = seq[0]
    if char == "`" and "`" in match.group("info"):
        return None
    return char, len(seq)


def _fence_closes(stripped_line: str, char: str, length: int) -> bool:
    """Whether the line closes a fence opened with ``length`` ``char`` chars."""
    return bool(re.match(rf"^{re.escape(char)}{{{length},}}\s*$", stripped_line))


def _mask_inline_code(line: str) -> str:
    """Blank out inline code spans (keeping length) so markers inside `code`
    are not mistaken for real ones."""
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group()), line)


def process_text(
    text: str,
    base_options: TreeOptions,
    ctx: RenderContext,
    placeholder: str = "files",
    enable_placeholder: bool = True,
) -> ProcessResult:
    """Return ``text`` with every marker/placeholder block regenerated.

    Processing is *fence-aware*: marker blocks and ``[[…]]`` placeholders inside
    fenced code blocks or inline code spans are left untouched, so you can safely
    document the syntax in the very same file it operates on.

    When ``enable_placeholder`` is false, only explicit ``filetree`` marker blocks
    are (re)generated and ``[[…]]`` tokens are left alone — useful for HTML pages
    that contain the token literally as documentation.
    """
    assets: dict[Path, str] = {}
    count = 0
    ph_re = _placeholder_re(placeholder)

    def render(attrs_text: str) -> str:
        nonlocal count
        count += 1
        content = _render_block(attrs_text, base_options, ctx, assets)
        return f"{_start_marker(attrs_text)}\n{content}\n<!-- filetree:end -->"

    def expand_placeholders(line: str) -> str:
        # Only expand tokens that are not inside an inline code span.
        segments = _INLINE_CODE_RE.split(line)
        codes = _INLINE_CODE_RE.findall(line)
        rebuilt: list[str] = []
        for index, segment in enumerate(segments):
            rebuilt.append(
                ph_re.sub(lambda m: render(m.group("attrs")), segment)
            )
            if index < len(codes):
                rebuilt.append(codes[index])
        return "".join(rebuilt)

    lines = text.splitlines()
    out: list[str] = []
    index = 0
    fence: tuple[str, int] | None = None

    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip()

        if fence is not None:
            out.append(line)
            if _fence_closes(stripped, *fence):
                fence = None
            index += 1
            continue

        # Marker detection ignores markers written inside `inline code`.
        start = _START_RE.search(_mask_inline_code(line))
        if start:
            attrs_text = start.group("attrs")
            if _END_RE.search(_mask_inline_code(line), start.end()):
                # Start and end on the same line: regenerate in place.
                out.append(render(attrs_text))
                index += 1
                continue
            end = index + 1
            while end < len(lines) and not _END_RE.search(_mask_inline_code(lines[end])):
                end += 1
            out.append(render(attrs_text))
            # Skip the old body + end marker; if no end existed, only skip start.
            index = end + 1 if end < len(lines) else index + 1
            continue

        opened = _fence_open(stripped)
        if opened is not None:
            fence = opened
            out.append(line)
            index += 1
            continue

        out.append(expand_placeholders(line) if enable_placeholder else line)
        index += 1

    new_text = "\n".join(out)
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"

    return ProcessResult(
        text=new_text,
        assets=assets,
        changed=new_text != text,
        blocks=count,
    )


def has_markers(text: str, placeholder: str = "files") -> bool:
    """Whether ``text`` contains any marker block or placeholder token."""
    return bool(_START_RE.search(text) or _placeholder_re(placeholder).search(text))


def process_file(
    path: Path,
    base_options: TreeOptions,
    base: Path,
    placeholder: str = "files",
    enable_placeholder: bool = True,
) -> ProcessResult:
    """Process a single README file on disk (does not write it back)."""
    text = path.read_text(encoding="utf-8")
    ctx = RenderContext(base=base, readme_path=path.resolve())
    return process_text(text, base_options, ctx, placeholder, enable_placeholder)
