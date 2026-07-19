"""Command-line interface: ``python -m treegen``.

Scans directories and updates one or more Markdown files in place. Designed to
be driven either by a human locally or by the bundled GitHub Action.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from dataclasses import replace
from pathlib import Path

from . import __version__
from .config import COLOR_CHOICES, DEFAULT_COLOR, STYLES, TreeOptions
from .readme import ProcessResult, process_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="treegen",
        description="Inject directory trees into Markdown files.",
    )
    parser.add_argument("--version", action="version", version=f"treegen {__version__}")
    parser.add_argument(
        "--readme",
        action="append",
        default=None,
        metavar="GLOB",
        help="Markdown file(s) to update. Repeatable; globs allowed. "
        "Default: README.md",
    )
    parser.add_argument(
        "--base",
        default=".",
        help="Repository root used to resolve scan directories (default: .).",
    )
    parser.add_argument("--directory", "--dir", dest="directory", default=".",
                        help="Default directory to scan (default: .).")
    parser.add_argument(
        "--style", default="ascii", choices=list(STYLES),
        help="Default render style (default: ascii).",
    )
    parser.add_argument("--max-depth", type=int, default=0,
                        help="Maximum depth, 0 for unlimited (default: 0).")
    parser.add_argument("--dirs-only", action="store_true",
                        help="Only include directories.")
    parser.add_argument("--exclude", action="append", default=None, metavar="PATTERN",
                        help="Extra ignore pattern (repeatable, comma-separated ok).")
    parser.add_argument("--no-gitignore", action="store_true",
                        help="Do not read the repository .gitignore.")
    parser.add_argument("--show-root", action="store_true",
                        help="Include the root directory itself in the tree.")
    parser.add_argument("--descriptions", default=None, metavar="FILE",
                        help="JSON file mapping paths to descriptions.")
    parser.add_argument("--svg-output", default="assets/filetree.svg",
                        help="Where SVG assets are written (default: assets/filetree.svg).")
    parser.add_argument("--color", default=DEFAULT_COLOR, choices=list(COLOR_CHOICES),
                        help="Folder colour for the svg style. 'github' (default) "
                        "matches GitHub's own folder colour.")
    parser.add_argument("--background", default="auto",
                        help="SVG backdrop: auto (framed, default), transparent, "
                        "or a CSS colour.")
    parser.add_argument("--title", default="Project structure",
                        help="Label for <details> summaries and SVG alt text.")
    parser.add_argument("--collapse", action="store_true",
                        help="Wrap each block in a top-level <details>.")
    parser.add_argument("--closed", action="store_true",
                        help="Render collapsibles closed instead of open.")
    parser.add_argument("--placeholder", default="files",
                        help='Placeholder token name (default: "files" -> [[files]]).')
    parser.add_argument("--format", dest="fmt", default="auto",
                        choices=["auto", "markdown", "html"],
                        help="Output flavour. 'auto' picks html for .html/.htm "
                        "files, markdown otherwise (default: auto).")
    parser.add_argument("--no-placeholder", action="store_true",
                        help="Only (re)generate explicit markers; ignore [[…]] "
                        "tokens (handy for HTML pages that document the syntax).")
    parser.add_argument("--check", action="store_true",
                        help="Do not write; exit 1 if any file would change.")
    return parser


def _format_for(path: Path, chosen: str) -> str:
    if chosen != "auto":
        return chosen
    return "html" if path.suffix.lower() in {".html", ".htm"} else "markdown"


def _resolve_readmes(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        chunks = [c for line in pattern.splitlines() for c in line.split(",")]
        for chunk in chunks:
            piece = chunk.strip()
            if not piece:
                continue
            matches = [Path(m) for m in glob.glob(piece, recursive=True)]
            for match in matches or [Path(piece)]:
                resolved = match.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    paths.append(match)
    return paths


def _options_from_args(args: argparse.Namespace) -> TreeOptions:
    exclude: tuple[str, ...] = ()
    if args.exclude:
        parts = [p.strip() for value in args.exclude for p in str(value).split(",")]
        exclude = tuple(p for p in parts if p)
    return TreeOptions(
        directory=str(args.directory),
        style=str(args.style),
        max_depth=int(args.max_depth),
        dirs_only=bool(args.dirs_only),
        exclude=exclude,
        use_gitignore=not bool(args.no_gitignore),
        show_root=bool(args.show_root),
        descriptions_file=None if args.descriptions is None else str(args.descriptions),
        svg_output=str(args.svg_output),
        color=str(args.color),
        background=str(args.background),
        collapse=bool(args.collapse),
        open=not bool(args.closed),
        title=str(args.title),
    )


def _write_assets(assets: dict[Path, str], check: bool) -> bool:
    """Write asset files. Returns True if any asset changed."""
    changed = False
    for path, content in assets.items():
        existing = path.read_text(encoding="utf-8") if path.is_file() else None
        if existing == content:
            continue
        changed = True
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return changed


def _set_github_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    base = Path(str(args.base)).resolve()
    options = _options_from_args(args)
    placeholder = str(args.placeholder)
    chosen_format = str(args.fmt)
    enable_placeholder = not bool(args.no_placeholder)
    check = bool(args.check)

    patterns: list[str] = list(args.readme) if args.readme else ["README.md"]
    readmes = _resolve_readmes(patterns)
    if not readmes:
        print("treegen: no README files matched", file=sys.stderr)
        return 1

    any_changed = False
    total_blocks = 0
    processed = 0
    for readme in readmes:
        if not readme.is_file():
            print(f"treegen: skipping missing file {readme}", file=sys.stderr)
            continue
        processed += 1
        file_options = replace(options, output_format=_format_for(readme, chosen_format))
        result: ProcessResult = process_file(
            readme, file_options, base, placeholder, enable_placeholder
        )
        total_blocks += result.blocks
        assets_changed = _write_assets(result.assets, check)
        file_changed = result.changed

        if result.changed and not check:
            readme.write_text(result.text, encoding="utf-8")

        status = "changed" if (file_changed or assets_changed) else "unchanged"
        print(f"treegen: {readme} — {result.blocks} block(s), {status}")
        any_changed = any_changed or file_changed or assets_changed

    if processed == 0:
        print("treegen: no existing README files to process", file=sys.stderr)
        return 1

    _set_github_output("changed", "true" if any_changed else "false")
    _set_github_output("blocks", str(total_blocks))

    if check and any_changed:
        print("treegen: files are out of date (run without --check to update)",
              file=sys.stderr)
        return 1
    return 0
