"""Banned-strings denylist guard for shipped per-package subpages.

Ensures no per-package documentation file in ``packages/<name>/docs/``
or ``docs/packages/<name>/`` contains placeholder filler such as
``TBD``, ``Coming soon``, ``Lorem ipsum``, or ``FIXME``. The migration
script in ``scripts/docs_split.py`` (and any human author) MUST
produce subpages that ship — never empty stubs.

This test runs across the entire workspace docs tree so any regression
trips CI before reaching readers.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


_BANNED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:TBD|XXX|FIXME|placeholder)\b", re.IGNORECASE),
    re.compile(r"\bComing soon\b", re.IGNORECASE),
    re.compile(r"\bintentionally blank\b", re.IGNORECASE),
    re.compile(r"\bLorem ipsum\b", re.IGNORECASE),
    # Parens are non-word characters so a leading/trailing \b would
    # never match here; the literal parens are sufficient delimiters.
    re.compile(r"\(write me\)", re.IGNORECASE),
)


def _find_banned(text: str) -> re.Match[str] | None:
    """Return the first banned-pattern match in ``text``, or ``None``."""
    for pattern in _BANNED_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return match
    return None


def _shipped_subpage_files() -> list[pathlib.Path]:
    """Return every docs markdown file that ships to readers.

    Walks both the co-located package source tree
    (``packages/*/docs/*.md``) and the legacy in-docs tree
    (``docs/packages/<name>/*.md`` and the migration-window flat
    pages ``docs/packages/*.md``). Excludes ``packages/*/README.md``
    because READMEs target PyPI, not the docs site.
    """
    files: list[pathlib.Path] = []
    files.extend((REPO_ROOT / "packages").glob("*/docs/*.md"))
    files.extend((REPO_ROOT / "docs" / "packages").rglob("*.md"))
    return files


def test_shipped_subpages_contain_no_banned_filler() -> None:
    """No shipped subpage carries a placeholder string from the denylist."""
    offenders: list[str] = []
    for md_path in _shipped_subpage_files():
        text = md_path.read_text(encoding="utf-8")
        match = _find_banned(text)
        if match is not None:
            offenders.append(
                f"{md_path.relative_to(REPO_ROOT)}: {match.group()!r} "
                f"at offset {match.start()}",
            )
    assert not offenders, "banned filler in shipped subpages:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    ("token", "should_match"),
    [
        ("TBD", True),
        ("Coming soon", True),
        ("intentionally blank", True),
        ("Lorem ipsum dolor", True),
        ("(write me)", True),
        ("XXX", True),
        ("FIXME", True),
        ("placeholder", True),
        ("Tutorial: document your first FastMCP tool", False),
        ("Reference", False),
        ("see :doc:`how-to`", False),
    ],
    ids=lambda v: str(v),
)
def test_banned_patterns_match_only_filler_words(
    token: str,
    should_match: bool,
) -> None:
    """Banned-pattern set matches each filler token but skips real prose."""
    assert (_find_banned(token) is not None) is should_match
