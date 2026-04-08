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


def test_normalize_warning_text_strips_ansi_and_roots(tmp_path: pathlib.Path) -> None:
    """Warning normalization removes ANSI escapes and concrete roots."""
    warning_text = (
        f"\x1b[91mWARNING: issue in {tmp_path / 'src' / 'index.rst'}\x1b[39;49;00m\n"
    )

    normalized = normalize_warning_text(warning_text, roots=(tmp_path,))

    assert "\x1b[" not in normalized
    assert str(tmp_path) not in normalized
    assert "<root-1>" in normalized


def test_normalize_html_fragment_replaces_roots(tmp_path: pathlib.Path) -> None:
    """HTML fragment normalization replaces concrete filesystem paths."""
    fragment = f'  <a href="{tmp_path / "out" / "index.html"}">demo</a>\n'

    normalized = normalize_html_fragment(fragment, roots=(tmp_path,))

    assert normalized == '<a href="<root-1>/out/index.html">demo</a>'


def test_normalize_doctree_text_relativizes_sources(tmp_path: pathlib.Path) -> None:
    """Doctree normalization strips unstable document metadata."""
    doctree = new_document(str(tmp_path / "index.rst"))
    doctree["translation_progress"] = {"total": 0, "translated": 0}

    paragraph = nodes.paragraph("", "hello")
    paragraph["source"] = str(tmp_path / "subdir" / "index.rst")
    paragraph["translated"] = True
    doctree += paragraph

    normalized = normalize_doctree_text(doctree, roots=(tmp_path,))

    assert "translation_progress" not in normalized
    assert "translated" not in normalized
    assert 'source="subdir/index.rst"' in normalized
