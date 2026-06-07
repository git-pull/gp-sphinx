"""Unit tests for the Sphinx extension component autodoc pipeline.

Covers per-type discovery, fact rows, and the shared
``normalize_component_nodes`` / ``inject_component_badges`` doctree
behavior for sphinx_autodoc_sphinx. Each component type contributes its
own section as it lands.
"""

from __future__ import annotations

import collections.abc as cabc
import typing as t

import pytest
from docutils import nodes
from sphinx import addnodes
from sphinx.builders import Builder

from sphinx_autodoc_sphinx._badges import build_builder_badge_group
from sphinx_autodoc_sphinx._builders_doc import (
    BuilderInfo,
    _builder_fact_rows,
    _builders_from_calls,
    discover_builder,
    discover_builders,
)
from sphinx_autodoc_sphinx._components import (
    component_classes,
    component_markup,
    import_component,
    inject_component_badges,
    normalize_component_nodes,
    replay_setup,
)
from sphinx_autodoc_sphinx._domains_doc import (
    DomainInfo,
    _domain_fact_rows,
    _domains_from_calls,
    discover_domain,
    discover_domains,
)
from sphinx_ux_autodoc_layout import ApiFactRow
from sphinx_ux_autodoc_layout._nodes import api_component

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _DemoBuilder(Builder):
    """Demo builder for metadata tests."""

    name = "demo-test"
    format = "test"
    epilog = "Demo output is in %(outdir)s."
    supported_image_types: list[str] = ["image/png"]  # noqa: RUF012 — matches upstream sphinx.builders.Builder shape

    def get_outdated_docs(self) -> list[str]:
        """Report nothing as outdated."""
        return []

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        """Return the docname unchanged."""
        return docname

    def prepare_writing(self, docnames: cabc.Set[str]) -> None:
        """No writer state is needed."""

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        """Skip per-document output."""


def _make_component_desc(
    objtype: str,
    *,
    name: str = "demo.DemoComponent",
) -> addnodes.desc:
    """Build a minimal sphinxext-domain desc node as Auto* would produce."""
    desc = addnodes.desc(domain="sphinxext", objtype=objtype)
    sig = addnodes.desc_signature(ids=[f"sphinxext-{objtype}-{name.lower()}"])
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


def _demo_fact_rows() -> list[ApiFactRow]:
    """Return a small facts list for normalize tests."""
    paragraph = nodes.paragraph()
    paragraph += nodes.literal("demo", "demo")
    return [ApiFactRow("Python path", paragraph)]


# ---------------------------------------------------------------------------
# Shared pipeline
# ---------------------------------------------------------------------------


def test_component_markup_renders_domain_directive() -> None:
    """component_markup emits a sphinxext-domain object description."""
    markup = component_markup("builder", "pkg.ZipBuilder", "Zip output.")
    assert markup.splitlines()[0] == ".. sphinxext:builder:: pkg.ZipBuilder"
    assert "   Zip output." in markup


def test_normalize_component_inserts_api_facts_after_summary() -> None:
    """normalize_component_nodes inserts gp-sphinx-api-facts after the summary."""
    desc = _make_component_desc("builder")
    content = t.cast("addnodes.desc_content", desc.children[-1])

    normalize_component_nodes(
        [desc],
        objtype="builder",
        fact_rows=_demo_fact_rows(),
    )

    assert isinstance(content.children[0], nodes.paragraph)
    assert _api_facts_child(content) is not None


def test_normalize_component_skips_other_objtypes() -> None:
    """normalize_component_nodes leaves non-matching objtypes untouched."""
    builder_desc = _make_component_desc("builder")
    domain_desc = _make_component_desc("domain")

    normalize_component_nodes(
        [builder_desc, domain_desc],
        objtype="builder",
        fact_rows=_demo_fact_rows(),
    )

    domain_content = t.cast("addnodes.desc_content", domain_desc.children[-1])
    assert _api_facts_child(domain_content) is None


def test_inject_component_badges_marks_signature() -> None:
    """inject_component_badges attaches the badge slot exactly once."""
    desc = _make_component_desc("builder")
    sig = t.cast("addnodes.desc_signature", desc.children[0])

    inject_component_badges(
        [desc],
        objtype="builder",
        badge_group=build_builder_badge_group("zip"),
    )

    assert sig.get("sas_badges_injected") is True


def test_import_component_rejects_non_class() -> None:
    """import_component raises TypeError for non-class attributes."""
    with pytest.raises(TypeError, match="Expected a class"):
        import_component("sphinx.builders.dummy.__doc__")


def test_replay_setup_records_calls_for_extension_modules() -> None:
    """replay_setup captures add_* calls from a real extension."""
    recorder = replay_setup("sphinx.builders.dummy")
    assert recorder is not None
    assert any(name == "add_builder" for name, _, _ in recorder.calls)


def test_replay_setup_none_for_module_without_setup() -> None:
    """replay_setup returns None when the module has no setup()."""
    assert replay_setup("sphinx_autodoc_sphinx._components") is None


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class BuildersFromCallsCase(t.NamedTuple):
    """Test case for _builders_from_calls()."""

    test_id: str
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]]
    expected: list[str]


_BUILDERS_FROM_CALLS_CASES: list[BuildersFromCallsCase] = [
    BuildersFromCallsCase(
        test_id="single_builder",
        calls=[("add_builder", (_DemoBuilder,), {})],
        expected=["_DemoBuilder"],
    ),
    BuildersFromCallsCase(
        test_id="ignores_other_calls",
        calls=[
            ("add_directive", ("noise", object), {}),
            ("add_builder", (_DemoBuilder,), {}),
        ],
        expected=["_DemoBuilder"],
    ),
    BuildersFromCallsCase(
        test_id="ignores_non_builder_classes",
        calls=[("add_builder", (object,), {})],
        expected=[],
    ),
    BuildersFromCallsCase(
        test_id="dedupes_repeat_registrations",
        calls=[
            ("add_builder", (_DemoBuilder,), {}),
            ("add_builder", (_DemoBuilder,), {"override": True}),
        ],
        expected=["_DemoBuilder"],
    ),
]


@pytest.mark.parametrize(
    "case",
    _BUILDERS_FROM_CALLS_CASES,
    ids=lambda c: c.test_id,
)
def test_builders_from_calls(case: BuildersFromCallsCase) -> None:
    """_builders_from_calls extracts builder registrations."""
    infos = _builders_from_calls(case.calls)
    assert [info.cls.__name__ for info in infos] == case.expected
    assert all(info.registered for info in infos)


def test_discover_builders_via_setup_registration() -> None:
    """discover_builders surfaces builders from a module's setup()."""
    infos = discover_builders("sphinx.builders.dummy")
    assert [(info.cls.__name__, info.registered) for info in infos] == [
        ("DummyBuilder", True),
    ]


def test_discover_builders_empty_for_module_without_builders() -> None:
    """discover_builders returns [] for modules without builders."""
    assert discover_builders("sphinx_fonts") == []


def test_discover_builder_single_path() -> None:
    """discover_builder imports one builder from a dotted path."""
    info = discover_builder("sphinx.builders.dummy.DummyBuilder")
    assert info.builder_name == "dummy"


def test_component_classes_scans_builder_modules() -> None:
    """component_classes finds Builder subclasses defined in a module."""
    classes = component_classes("sphinx.builders.dummy", Builder)
    assert [cls.__name__ for cls in classes] == ["DummyBuilder"]


def test_builder_fact_rows_surface_metadata() -> None:
    """Builder fact rows include name, format, image types, and epilog."""
    rows = _builder_fact_rows(BuilderInfo(cls=_DemoBuilder, registered=True))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Builder name"] == "demo-test"
    assert by_label["Output format"] == "test"
    assert by_label["Supported image types"] == "image/png"
    assert by_label["Default translator"] == "—"
    assert by_label["Parallel-safe"] == "False"
    assert by_label["Epilog"] == "Demo output is in %(outdir)s."


def test_builder_fact_rows_dash_for_base_metadata() -> None:
    """Builders inheriting blank base attributes degrade to dashes."""

    class _BareBuilder(Builder):
        """Builder leaving every base attribute untouched."""

        def get_outdated_docs(self) -> list[str]:
            return []

        def get_target_uri(self, docname: str, typ: str | None = None) -> str:
            return docname

        def prepare_writing(self, docnames: cabc.Set[str]) -> None:
            pass

        def write_doc(self, docname: str, doctree: nodes.document) -> None:
            pass

    rows = _builder_fact_rows(BuilderInfo(cls=_BareBuilder))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Builder name"] == "—"
    assert by_label["Output format"] == "—"
    assert by_label["Supported image types"] == "—"


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------


def test_domains_from_calls_filters_domain_classes() -> None:
    """_domains_from_calls keeps only Domain subclasses, deduped."""
    from sphinx_autodoc_argparse.domain import ArgparseDomain

    infos = _domains_from_calls(
        [
            ("add_domain", (ArgparseDomain,), {}),
            ("add_domain", (ArgparseDomain,), {"override": True}),
            ("add_domain", (object,), {}),
            ("add_directive", ("noise", object), {}),
        ],
    )
    assert [(info.cls.__name__, info.registered) for info in infos] == [
        ("ArgparseDomain", True),
    ]


def test_discover_domains_via_setup_registration() -> None:
    """discover_domains surfaces domains a package's setup() registers."""
    infos = discover_domains("sphinx_autodoc_docutils")
    assert [(info.cls.__name__, info.registered) for info in infos] == [
        ("DocutilsDomain", True),
    ]


def test_discover_domains_scan_fallback() -> None:
    """discover_domains scans modules without a registering setup()."""
    infos = discover_domains("sphinx_autodoc_argparse.domain")
    assert [(info.cls.__name__, info.registered) for info in infos] == [
        ("ArgparseDomain", False),
    ]


def test_discover_domains_empty_for_module_without_domains() -> None:
    """discover_domains returns [] for modules without domains."""
    assert discover_domains("sphinx_fonts") == []


def test_discover_domain_single_path() -> None:
    """discover_domain imports one domain from a dotted path."""
    info = discover_domain("sphinx_autodoc_argparse.domain.ArgparseDomain")
    assert info.domain_name == "argparse"


def test_domain_fact_rows_surface_metadata() -> None:
    """Domain fact rows include name, label, surface dicts, and indices."""
    from sphinx_autodoc_argparse.domain import ArgparseDomain

    rows = _domain_fact_rows(DomainInfo(cls=ArgparseDomain))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Domain name"] == "argparse"
    assert by_label["Label"] == "Argparse CLI"
    assert by_label["Object types"] == "option, positional, program, subcommand"
    assert by_label["Roles"] == "option, positional, program, subcommand"
    assert by_label["Directives"] == "—"
    assert by_label["Indices"] == "programsindex, optionsindex"


def test_domain_fact_rows_dash_for_bare_domain() -> None:
    """Domains without surface registrations degrade to dashes."""
    from sphinx.domains import Domain as BaseDomain

    class _BareDomain(BaseDomain):
        """Domain leaving every base attribute untouched."""

        name = "bare"
        label = "Bare"

    rows = _domain_fact_rows(DomainInfo(cls=_BareDomain))
    by_label = {row.label: row.body.astext() for row in rows}
    assert by_label["Object types"] == "—"
    assert by_label["Roles"] == "—"
    assert by_label["Directives"] == "—"
    assert by_label["Indices"] == "—"
