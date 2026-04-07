"""Tests for sphinx_autodoc_layout._transforms."""

from __future__ import annotations

from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_layout._nodes import gal_fold, gal_region
from sphinx_autodoc_layout._transforms import (
    _classify_child,
    _fold_large_field_regions,
    _wrap_content_runs,
)

# -- helpers -----------------------------------------------------------------


def _make_desc(
    *content_children: nodes.Node,
    domain: str = "py",
    objtype: str = "function",
) -> addnodes.desc:
    desc = addnodes.desc(domain=domain, objtype=objtype)
    desc += addnodes.desc_signature()
    content = addnodes.desc_content()
    for child in content_children:
        content += child
    desc += content
    return desc


def _make_field_list(num_fields: int = 5) -> nodes.field_list:
    fl = nodes.field_list()
    for i in range(num_fields):
        f = nodes.field()
        f += nodes.field_name("", f"param{i}")
        f += nodes.field_body("", nodes.paragraph("", f"desc {i}"))
        fl += f
    return fl


# -- _classify_child --------------------------------------------------------


def test_classify_paragraph_as_narrative() -> None:
    assert _classify_child(nodes.paragraph()) == "narrative"


def test_classify_field_list_as_fields() -> None:
    assert _classify_child(nodes.field_list()) == "fields"


def test_classify_desc_as_members() -> None:
    assert _classify_child(addnodes.desc()) == "members"


def test_classify_note_as_narrative() -> None:
    assert _classify_child(nodes.note()) == "narrative"


# -- _wrap_content_runs ------------------------------------------------------


def test_wrap_groups_narrative() -> None:
    desc = _make_desc(
        nodes.paragraph("", "hello"),
        nodes.paragraph("", "world"),
    )
    _wrap_content_runs(desc)

    content = desc.children[-1]
    assert len(content.children) == 1
    r = content.children[0]
    assert isinstance(r, gal_region)
    assert r.get("kind") == "narrative"
    assert len(r.children) == 2


def test_wrap_groups_contiguous_types() -> None:
    desc = _make_desc(
        nodes.paragraph("", "text"),
        _make_field_list(3),
        addnodes.desc(domain="py", objtype="method"),
    )
    _wrap_content_runs(desc)

    content = desc.children[-1]
    assert len(content.children) == 3
    r0, r1, r2 = content.children
    assert isinstance(r0, gal_region) and r0.get("kind") == "narrative"
    assert isinstance(r1, gal_region) and r1.get("kind") == "fields"
    assert isinstance(r2, gal_region) and r2.get("kind") == "members"


def test_wrap_preserves_order() -> None:
    """Interleaved types stay in authored order."""
    desc = _make_desc(
        nodes.paragraph("", "intro"),
        _make_field_list(2),
        nodes.paragraph("", "examples"),
        addnodes.desc(domain="py", objtype="method"),
    )
    _wrap_content_runs(desc)

    content = desc.children[-1]
    for c in content.children:
        assert isinstance(c, gal_region)
    kinds = [c.get("kind") for c in content.children if isinstance(c, gal_region)]
    assert kinds == ["narrative", "fields", "narrative", "members"]


def test_wrap_empty_content_noop() -> None:
    desc = _make_desc()
    _wrap_content_runs(desc)
    content = desc.children[-1]
    assert len(content.children) == 0


def test_wrap_non_python_noop() -> None:
    """Non-Python desc nodes are still wrapped (wrapping is domain-agnostic)."""
    desc = _make_desc(
        nodes.paragraph("", "text"),
        domain="cpp",
        objtype="function",
    )
    _wrap_content_runs(desc)
    content = desc.children[-1]
    assert len(content.children) == 1
    assert isinstance(content.children[0], gal_region)


# -- _fold_large_field_regions -----------------------------------------------


def test_fold_wraps_large_field_list() -> None:
    content = addnodes.desc_content()
    region = gal_region(kind="fields")
    region += _make_field_list(12)
    content += region

    _fold_large_field_regions(content, threshold=10)

    fold = region.children[0]
    assert isinstance(fold, gal_fold)
    assert fold.get("summary") == "Parameters (12)"
    assert isinstance(fold.children[0], nodes.field_list)


def test_fold_skips_small_field_list() -> None:
    content = addnodes.desc_content()
    region = gal_region(kind="fields")
    fl = _make_field_list(5)
    region += fl
    content += region

    _fold_large_field_regions(content, threshold=10)

    assert isinstance(region.children[0], nodes.field_list)
    assert not isinstance(region.children[0], gal_fold)


def test_fold_skips_narrative_regions() -> None:
    content = addnodes.desc_content()
    region = gal_region(kind="narrative")
    region += nodes.paragraph("", "text")
    content += region

    _fold_large_field_regions(content, threshold=1)

    assert isinstance(region.children[0], nodes.paragraph)
