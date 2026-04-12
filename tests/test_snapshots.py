"""Tests for snapshot normalization helpers."""

from __future__ import annotations

import pathlib

from docutils import nodes
from docutils.utils import new_document

from tests._snapshots import (
    normalize_doctree_text,
    normalize_html_fragment,
    normalize_warning_text,
)

_SNAPSHOT_ROOT = pathlib.Path("/virtual/test-root")


def test_normalize_warning_text_strips_ansi_and_roots() -> None:
    """Warning normalization removes ANSI escapes and concrete roots."""
    source_path = _SNAPSHOT_ROOT / "src" / "index.rst"
    warning_text = f"\x1b[91mWARNING: issue in {source_path}\x1b[39;49;00m\n"

    normalized = normalize_warning_text(warning_text, roots=(_SNAPSHOT_ROOT,))

    assert "\x1b[" not in normalized
    assert str(_SNAPSHOT_ROOT) not in normalized
    assert "<root-1>" in normalized


def test_normalize_html_fragment_replaces_roots() -> None:
    """HTML fragment normalization replaces concrete filesystem paths."""
    fragment = f'  <a href="{_SNAPSHOT_ROOT / "out" / "index.html"}">demo</a>\n'

    normalized = normalize_html_fragment(fragment, roots=(_SNAPSHOT_ROOT,))

    assert normalized == '<a href="<root-1>/out/index.html">demo</a>'


def test_normalize_doctree_text_relativizes_sources() -> None:
    """Doctree normalization strips unstable document metadata."""
    doctree = new_document(str(_SNAPSHOT_ROOT / "index.rst"))
    doctree["translation_progress"] = {"total": 0, "translated": 0}

    paragraph = nodes.paragraph("", "hello")
    paragraph["source"] = str(_SNAPSHOT_ROOT / "subdir" / "index.rst")
    paragraph["translated"] = True
    doctree += paragraph

    normalized = normalize_doctree_text(doctree, roots=(_SNAPSHOT_ROOT,))

    assert "translation_progress" not in normalized
    assert "translated" not in normalized
    assert 'source="subdir/index.rst"' in normalized
