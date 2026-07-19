"""Tests for the .gitignore-style path matcher."""

from __future__ import annotations

from pathlib import Path

from treegen.ignore import Matcher


def test_bare_name_matches_any_depth() -> None:
    matcher = Matcher(["node_modules"])
    assert matcher.is_excluded("node_modules", True)
    assert matcher.is_excluded("src/node_modules", True)


def test_extension_glob() -> None:
    matcher = Matcher(["*.log"])
    assert matcher.is_excluded("debug.log", False)
    assert matcher.is_excluded("logs/debug.log", False)
    assert not matcher.is_excluded("debug.txt", False)


def test_dir_only_rule() -> None:
    matcher = Matcher(["build/"])
    assert matcher.is_excluded("build", True)
    assert not matcher.is_excluded("build", False)


def test_anchored_rule() -> None:
    matcher = Matcher(["src/generated"])
    assert matcher.is_excluded("src/generated", True)
    assert not matcher.is_excluded("lib/src/generated", True)


def test_negation_reincludes() -> None:
    matcher = Matcher(["*.log", "!keep.log"])
    assert matcher.is_excluded("a.log", False)
    assert not matcher.is_excluded("keep.log", False)


def test_double_star_across_segments() -> None:
    matcher = Matcher(["**/cache"])
    assert matcher.is_excluded("cache", True)
    assert matcher.is_excluded("a/b/cache", True)


def test_comments_and_blanks_ignored() -> None:
    matcher = Matcher(["# a comment", "   ", "*.tmp"])
    assert matcher.is_excluded("x.tmp", False)


def test_build_reads_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
    matcher = Matcher.build(tmp_path, extra=(), use_gitignore=True)
    assert matcher.is_excluded("secret.txt", False)
    assert matcher.is_excluded(".git", True)  # default exclude


def test_build_can_skip_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
    matcher = Matcher.build(tmp_path, extra=(), use_gitignore=False)
    assert not matcher.is_excluded("secret.txt", False)
