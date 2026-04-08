"""Snapshot helpers for normalized doctree, HTML fragment, and warning output."""

from __future__ import annotations

import pathlib
import re
import typing as t

import pytest
from docutils import nodes

if t.TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _replace_roots(text: str, roots: tuple[pathlib.Path, ...]) -> str:
    """Replace concrete filesystem roots with stable placeholders."""
    normalized = text
    for index, root in enumerate(roots, start=1):
        placeholder = f"<root-{index}>"
        normalized = normalized.replace(str(root), placeholder)
    return normalized


def normalize_html_fragment(
    fragment: str,
    *,
    roots: tuple[pathlib.Path, ...] = (),
) -> str:
    """Return a stable HTML fragment string for snapshot assertions."""
    normalized = fragment.strip().replace("\r\n", "\n")
    return _replace_roots(normalized, roots)


def normalize_warning_text(
    warnings: str,
    *,
    roots: tuple[pathlib.Path, ...] = (),
) -> str:
    """Return normalized warning text for snapshot assertions."""
    normalized = _ANSI_ESCAPE_RE.sub("", warnings).replace("\r\n", "\n")
    lines = [
        line
        for line in normalized.splitlines()
        if "already registered" not in line and "alabaster" not in line
    ]
    normalized = "\n".join(lines).strip()
    normalized = _replace_roots(normalized, roots)
    return normalized


def normalize_doctree_text(
    doctree: nodes.Node,
    *,
    roots: tuple[pathlib.Path, ...] = (),
) -> str:
    """Return normalized doctree text for snapshot assertions."""
    normalized_tree = doctree.deepcopy()
    if isinstance(normalized_tree, nodes.document):
        normalized_tree.attributes.pop("translation_progress", None)
    for node in normalized_tree.findall(nodes.Element):
        node.attributes.pop("translated", None)
        source = node.get("source")
        if not isinstance(source, str):
            continue
        source_path = pathlib.Path(source)
        replacement = source
        for root in roots:
            try:
                replacement = source_path.relative_to(root).as_posix()
                break
            except ValueError:
                continue
        else:
            replacement = source_path.name
        node["source"] = replacement
    normalized = normalized_tree.pformat().replace("\r\n", "\n").strip()
    return _replace_roots(normalized, roots)


@pytest.fixture
def snapshot_doctree(snapshot: SnapshotAssertion) -> t.Callable[..., None]:
    """Assert a normalized doctree snapshot."""
    base_snapshot = snapshot.with_defaults()

    def _assert(
        doctree: nodes.Node,
        *,
        name: str | None = None,
        roots: tuple[pathlib.Path, ...] = (),
    ) -> None:
        expected = base_snapshot(name=name) if name is not None else base_snapshot
        assert normalize_doctree_text(doctree, roots=roots) == expected

    return _assert


@pytest.fixture
def snapshot_html_fragment(snapshot: SnapshotAssertion) -> t.Callable[..., None]:
    """Assert a normalized HTML fragment snapshot."""
    base_snapshot = snapshot.with_defaults()

    def _assert(
        fragment: str,
        *,
        name: str | None = None,
        roots: tuple[pathlib.Path, ...] = (),
    ) -> None:
        expected = base_snapshot(name=name) if name is not None else base_snapshot
        assert normalize_html_fragment(fragment, roots=roots) == expected

    return _assert


@pytest.fixture
def snapshot_warnings(snapshot: SnapshotAssertion) -> t.Callable[..., None]:
    """Assert normalized warning output snapshots."""
    base_snapshot = snapshot.with_defaults()

    def _assert(
        warnings: str,
        *,
        name: str | None = None,
        roots: tuple[pathlib.Path, ...] = (),
    ) -> None:
        expected = base_snapshot(name=name) if name is not None else base_snapshot
        assert normalize_warning_text(warnings, roots=roots) == expected

    return _assert
