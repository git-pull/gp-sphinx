"""Tests for the ``{subpage-exists}`` conditional cross-reference role.

The role guards "Where to next" links in tutorials and how-tos so the
prose never breaks when a sibling subpage has not been authored yet.
When the target docname resolves, the role emits a Sphinx ``:doc:``
cross-reference; otherwise it degrades to plain text.
"""

from __future__ import annotations

import pathlib
import sys
import typing as t
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


class _FakeEnv:
    """Minimal Sphinx env stand-in carrying ``found_docs`` + ``docname``."""

    def __init__(self, *, found_docs: set[str], docname: str) -> None:
        self.found_docs = found_docs
        self.docname = docname


def _make_inliner(env: _FakeEnv) -> SimpleNamespace:
    """Return a docutils-inliner stand-in that exposes ``settings.env``."""
    document = SimpleNamespace(settings=SimpleNamespace(env=env))
    return SimpleNamespace(document=document)


class _SubpageExistsCase(t.NamedTuple):
    """Fixture row for ``subpage_exists_role`` outcomes."""

    test_id: str
    found_docs: frozenset[str]
    current_docname: str
    target: str
    expected_xref: bool


_SUBPAGE_EXISTS_CASES: list[_SubpageExistsCase] = [
    _SubpageExistsCase(
        test_id="sibling_present_renders_xref",
        found_docs=frozenset({"packages/foo/index", "packages/foo/how-to"}),
        current_docname="packages/foo/tutorial",
        target="how-to",
        expected_xref=True,
    ),
    _SubpageExistsCase(
        test_id="sibling_absent_degrades_to_plain_text",
        found_docs=frozenset({"packages/foo/index"}),
        current_docname="packages/foo/tutorial",
        target="errors",
        expected_xref=False,
    ),
    _SubpageExistsCase(
        test_id="absolute_docname_present_renders_xref",
        found_docs=frozenset({"packages/foo/index"}),
        current_docname="quickstart",
        target="packages/foo/index",
        expected_xref=True,
    ),
    _SubpageExistsCase(
        test_id="absolute_docname_absent_degrades_to_plain_text",
        found_docs=frozenset({"packages/bar/index"}),
        current_docname="quickstart",
        target="packages/foo/index",
        expected_xref=False,
    ),
]


@pytest.mark.parametrize(
    list(_SubpageExistsCase._fields),
    _SUBPAGE_EXISTS_CASES,
    ids=[case.test_id for case in _SUBPAGE_EXISTS_CASES],
)
def test_subpage_exists_role(
    test_id: str,
    found_docs: frozenset[str],
    current_docname: str,
    target: str,
    expected_xref: bool,
) -> None:
    """Subpage role emits xref when target resolves, plain text otherwise."""
    from sphinx import addnodes

    env = _FakeEnv(found_docs=set(found_docs), docname=current_docname)
    inliner = _make_inliner(env)
    inline_nodes, messages = package_reference.subpage_exists_role(
        "subpage-exists",
        f"{{subpage-exists}}`{target}`",
        target,
        lineno=1,
        inliner=inliner,
    )

    assert messages == []
    assert len(inline_nodes) == 1
    if expected_xref:
        assert isinstance(inline_nodes[0], addnodes.pending_xref)
        assert inline_nodes[0]["reftarget"] == target
    else:
        assert not isinstance(inline_nodes[0], addnodes.pending_xref)
        assert inline_nodes[0].astext() == target


def test_subpage_target_exists_helper_handles_top_level_docname() -> None:
    """The helper does not crash when current docname has no slash."""
    env = _FakeEnv(found_docs={"index"}, docname="index")
    assert package_reference._subpage_target_exists(env, "index") is True
    assert package_reference._subpage_target_exists(env, "missing") is False


def test_subpage_target_exists_helper_strips_no_path_components() -> None:
    """Sibling resolution prefers exact matches before sibling resolution."""
    env = _FakeEnv(
        found_docs={"how-to", "packages/foo/how-to"},
        docname="packages/foo/tutorial",
    )
    # exact-match beats sibling-resolution; both succeed but "how-to" alone
    # is enough to satisfy the role.
    assert package_reference._subpage_target_exists(env, "how-to") is True
