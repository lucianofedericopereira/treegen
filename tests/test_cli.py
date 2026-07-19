"""End-to-end tests for the command-line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from treegen.cli import main


def test_cli_updates_readme(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    readme.write_text("# Project\n\n[[files]]\n", encoding="utf-8")
    code = main(["--base", str(sample_tree), "--readme", str(readme)])
    assert code == 0
    assert "brand-identity/" in readme.read_text(encoding="utf-8")


def test_cli_check_mode_detects_drift(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    readme.write_text("[[files]]\n", encoding="utf-8")
    before = readme.read_text(encoding="utf-8")
    code = main(["--base", str(sample_tree), "--readme", str(readme), "--check"])
    assert code == 1  # would change
    assert readme.read_text(encoding="utf-8") == before  # but did not write


def test_cli_check_mode_passes_when_current(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    readme.write_text("[[files]]\n", encoding="utf-8")
    main(["--base", str(sample_tree), "--readme", str(readme)])  # bring up to date
    code = main(["--base", str(sample_tree), "--readme", str(readme), "--check"])
    assert code == 0


def test_cli_writes_svg_asset(sample_tree: Path) -> None:
    readme = sample_tree / "README.md"
    readme.write_text('[[files style="svg" svg-output="assets/t.svg"]]\n', encoding="utf-8")
    code = main(["--base", str(sample_tree), "--readme", str(readme)])
    assert code == 0
    svg = (sample_tree / "assets" / "t.svg").read_text(encoding="utf-8")
    assert "<svg" in svg


def test_cli_html_format_auto_by_extension(sample_tree: Path) -> None:
    page = sample_tree / "index.html"
    page.write_text(
        '<!-- filetree:start dirs-only="true" -->\n<!-- filetree:end -->\n'
        "Docs: [[files]]\n",
        encoding="utf-8",
    )
    code = main(["--base", str(sample_tree), "--readme", str(page), "--no-placeholder"])
    assert code == 0
    text = page.read_text(encoding="utf-8")
    assert '<pre class="filetree-ascii">' in text  # html chosen from .html suffix
    assert "[[files]]" in text  # token preserved


def test_cli_missing_readme_errors(tmp_path: Path) -> None:
    code = main(["--base", str(tmp_path), "--readme", str(tmp_path / "nope.md")])
    assert code == 1


def test_cli_writes_github_output(
    sample_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme = sample_tree / "README.md"
    readme.write_text("[[files]]\n", encoding="utf-8")
    output_file = sample_tree / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    main(["--base", str(sample_tree), "--readme", str(readme)])
    contents = output_file.read_text(encoding="utf-8")
    assert "changed=true" in contents
