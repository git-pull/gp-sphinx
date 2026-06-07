"""Unit tests for the docutils component autodoc pipeline.

Covers per-type discovery, fact rows, and the shared
``normalize_component_nodes`` / ``inject_component_badges`` doctree
behavior. One file per package; each component type contributes its own
section as it lands.
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import nodes
from docutils.transforms import Transform
from sphinx import addnodes

from sphinx_autodoc_docutils._badges import build_transform_badge_group
from sphinx_autodoc_docutils._components import (
    component_classes,
    component_markup,
    import_component,
    inject_component_badges,
    normalize_component_nodes,
)
from sphinx_autodoc_docutils._transforms_doc import (
    TransformInfo,
    _transform_fact_rows,
    _transforms_from_calls,
    discover_transform,
    discover_transforms,
)
from sphinx_ux_autodoc_layout import ApiFactRow
from sphinx_ux_autodoc_layout._nodes import api_component

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _DemoTransform(Transform):
    """Demo transform that reorders nothing."""

    default_priority = 321

    def apply(self) -> None:
        """Do nothing; exists for metadata tests."""


class _BareTransform(Transform):
    """Demo transform without an explicit priority."""

    def apply(self) -> None:
        """Do nothing; exists for metadata tests."""


def _make_component_desc(
    objtype: str,
    *,
    name: str = "demo.DemoComponent",
) -> addnodes.desc:
    """Build a minimal docutils-domain desc node as Auto* would produce."""
    desc = addnodes.desc(domain="docutils", objtype=objtype)
    sig = addnodes.desc_signature(ids=[f"docutils-{objtype}-{name.lower()}"])
    sig += addnodes.desc_name("", name)
    desc += sig
    content = addnodes.desc_content()
    content += nodes.paragraph("", "A demo component for testing.")
    desc += content
    return desc


def _api_facts_child(content: addnodes.desc_content) -> api_component | None:
    """Return the gp-sphinx-api-facts component in desc_content, or None."""
    for child in content.children:
        if (
            isinstance(child, api_component)
            and child.get("name") == "gp-sphinx-api-facts"
        ):
            return child
    return None


def _facts_by_label(facts_section: api_component) -> dict[str, str]:
    """Return label -> body text for an gp-sphinx-api-facts section."""
    by_label: dict[str, str] = {}
    for field in facts_section.findall(nodes.field):
        if field.children:
            label = field.children[0].astext()
            body = field.children[1].astext() if len(field.children) > 1 else ""
            by_label[label] = body
    return by_label


def _demo_fact_rows() -> list[ApiFactRow]:
    """Return a small facts list for normalize tests."""
    paragraph = nodes.paragraph()
    paragraph += nodes.literal("demo", "demo")
    return [ApiFactRow("Python path", paragraph)]


# ---------------------------------------------------------------------------
# Shared pipeline
# ---------------------------------------------------------------------------


def test_component_markup_renders_domain_directive() -> None:
    """component_markup emits a docutils-domain object description."""
    markup = component_markup("transform", "pkg.Sanitize", "Strip stuff.")
    assert markup.splitlines()[0] == ".. docutils:transform:: pkg.Sanitize"
    assert "   Strip stuff." in markup


def test_component_markup_default_summary() -> None:
    """component_markup falls back to a generic summary."""
    markup = component_markup("writer", "pkg.W", "")
    assert "Autodocumented docutils writer." in markup


def test_normalize_component_inserts_api_facts_after_summary() -> None:
    """normalize_component_nodes inserts gp-sphinx-api-facts after the summary."""
    desc = _make_component_desc("transform")
    content = t.cast("addnodes.desc_content", desc.children[-1])

    normalize_component_nodes(
        [desc],
        objtype="transform",
        fact_rows=_demo_fact_rows(),
    )

    assert isinstance(content.children[0], nodes.paragraph)
    facts = _api_facts_child(content)
    assert facts is not None, "gp-sphinx-api-facts section should be inserted"
    assert "Python path" in _facts_by_label(facts)


def test_normalize_component_skips_other_objtypes() -> None:
    """normalize_component_nodes leaves non-matching objtypes untouched."""
    transform_desc = _make_component_desc("transform")
    writer_desc = _make_component_desc("writer")

    normalize_component_nodes(
        [transform_desc, writer_desc],
        objtype="transform",
        fact_rows=_demo_fact_rows(),
    )

    writer_content = t.cast("addnodes.desc_content", writer_desc.children[-1])
    assert _api_facts_child(writer_content) is None


def test_inject_component_badges_marks_signature() -> None:
    """inject_component_badges attaches the badge slot exactly once."""
    desc = _make_component_desc("transform")
    sig = t.cast("addnodes.desc_signature", desc.children[0])

    inject_component_badges(
        [desc],
        objtype="transform",
        badge_group=build_transform_badge_group(760),
    )

    assert sig.get("sadoc_badges_injected") is True


def test_inject_component_badges_skips_other_objtypes() -> None:
    """inject_component_badges leaves non-matching objtypes untouched."""
    desc = _make_component_desc("writer")
    sig = t.cast("addnodes.desc_signature", desc.children[0])

    inject_component_badges(
        [desc],
        objtype="transform",
        badge_group=build_transform_badge_group(None),
    )

    assert sig.get("sadoc_badges_injected") is None


def test_import_component_rejects_non_class() -> None:
    """import_component raises TypeError for non-class attributes."""
    with pytest.raises(TypeError, match="Expected a class"):
        import_component("docutils.transforms.misc.__doc__")


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------


class TransformsFromCallsCase(t.NamedTuple):
    """Test case for _transforms_from_calls()."""

    test_id: str
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]]
    expected: list[tuple[str, str]]


_TRANSFORMS_FROM_CALLS_CASES: list[TransformsFromCallsCase] = [
    TransformsFromCallsCase(
        test_id="read_phase",
        calls=[("add_transform", (_DemoTransform,), {})],
        expected=[("_DemoTransform", "add_transform")],
    ),
    TransformsFromCallsCase(
        test_id="post_phase",
        calls=[("add_post_transform", (_DemoTransform,), {})],
        expected=[("_DemoTransform", "add_post_transform")],
    ),
    TransformsFromCallsCase(
        test_id="ignores_other_calls",
        calls=[
            ("add_directive", ("noise", object), {}),
            ("add_transform", (_DemoTransform,), {}),
        ],
        expected=[("_DemoTransform", "add_transform")],
    ),
    TransformsFromCallsCase(
        test_id="ignores_non_transform_classes",
        calls=[("add_transform", (object,), {})],
        expected=[],
    ),
    TransformsFromCallsCase(
        test_id="dedupes_same_phase",
        calls=[
            ("add_transform", (_DemoTransform,), {}),
            ("add_transform", (_DemoTransform,), {}),
        ],
        expected=[("_DemoTransform", "add_transform")],
    ),
    TransformsFromCallsCase(
        test_id="keeps_both_phases",
        calls=[
            ("add_transform", (_DemoTransform,), {}),
            ("add_post_transform", (_DemoTransform,), {}),
        ],
        expected=[
            ("_DemoTransform", "add_transform"),
            ("_DemoTransform", "add_post_transform"),
        ],
    ),
]


@pytest.mark.parametrize(
    "case",
    _TRANSFORMS_FROM_CALLS_CASES,
    ids=lambda c: c.test_id,
)
def test_transforms_from_calls(case: TransformsFromCallsCase) -> None:
    """_transforms_from_calls extracts transform registrations."""
    infos = _transforms_from_calls(case.calls)
    assert [(info.cls.__name__, info.registered_via) for info in infos] == case.expected


def test_discover_transforms_scan_fallback() -> None:
    """discover_transforms scans modules without a registering setup()."""
    infos = discover_transforms("docutils.transforms.misc")
    names = sorted(info.cls.__name__ for info in infos)
    assert names == ["CallBack", "ClassAttribute", "Transitions"]
    assert {info.registered_via for info in infos} == {""}


def test_discover_transforms_empty_for_module_without_transforms() -> None:
    """discover_transforms returns [] for modules without transforms."""
    assert discover_transforms("sphinx_fonts") == []


def test_discover_transform_single_path() -> None:
    """discover_transform imports one transform from a dotted path."""
    info = discover_transform("docutils.transforms.misc.Transitions")
    assert info.cls.__name__ == "Transitions"
    assert info.qualified_name == "docutils.transforms.misc.Transitions"


def test_component_classes_excludes_base() -> None:
    """component_classes never surfaces the base class itself."""
    classes = component_classes("docutils.transforms", Transform)
    assert Transform not in classes


def test_transform_fact_rows_with_priority_and_phase() -> None:
    """Fact rows surface priority and registration phase."""
    rows = _transform_fact_rows(
        TransformInfo(cls=_DemoTransform, registered_via="add_post_transform"),
    )
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Python path"].endswith("_DemoTransform")
    assert by_label["Default priority"] == "321"
    assert by_label["Registered via"] == "app.add_post_transform()"


def test_transform_fact_rows_without_priority() -> None:
    """A None default_priority renders as an em dash."""
    rows = _transform_fact_rows(TransformInfo(cls=_BareTransform))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Default priority"] == "—"
    assert "Registered via" not in by_label
