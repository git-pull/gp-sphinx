"""Unit tests for _normalize_directive_nodes and _normalize_role_nodes tree output."""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx import addnodes

from sphinx_autodoc_docutils._directives import (
    _normalize_directive_nodes,
    _normalize_role_nodes,
)
from sphinx_autodoc_layout._nodes import api_component


class _DemoDirective(Directive):
    """Demo directive with one required argument, one option, and content."""

    required_arguments = 1
    optional_arguments = 2
    final_argument_whitespace = True
    has_content = True
    option_spec: t.ClassVar[dict[str, t.Any]] = {"class": directives.class_option}

    def run(self) -> list[nodes.Node]:
        return []


def _demo_role(
    name: object,
    rawtext: object,
    text: object,
    lineno: object,
    inliner: object,
    options: object = None,
    content: object = None,
) -> tuple[list[nodes.Node], list[nodes.Node]]:
    """Demo role with options and content support."""
    return [], []


_demo_role.options = {"class": directives.class_option}  # type: ignore[attr-defined]
_demo_role.content = True  # type: ignore[attr-defined]


def _make_directive_desc(
    directive_name: str = "demo",
    *,
    with_option: bool = True,
) -> addnodes.desc:
    """Build a minimal rst:directive desc node as AutoDirective.run() would produce."""
    desc = addnodes.desc(domain="rst", objtype="directive")
    sig = addnodes.desc_signature(ids=[f"directive-{directive_name}"])
    sig += addnodes.desc_name("", f".. {directive_name}::")
    desc += sig
    content = addnodes.desc_content()
    content += nodes.paragraph("", "A demo directive for testing.")
    if with_option:
        opt_desc = addnodes.desc(domain="rst", objtype="directive:option")
        opt_sig = addnodes.desc_signature(
            ids=[f"directive-option-{directive_name}-class"]
        )
        opt_sig += addnodes.desc_name("", ":class:")
        opt_desc += opt_sig
        opt_content = addnodes.desc_content()
        opt_content += nodes.paragraph("", "Validator: class_option.")
        opt_desc += opt_content
        content += opt_desc
    desc += content
    return desc


def _make_role_desc(role_name: str = "demo-badge") -> addnodes.desc:
    """Build a minimal rst:role desc node as AutoRole.run() would produce."""
    desc = addnodes.desc(domain="rst", objtype="role")
    sig = addnodes.desc_signature(ids=[f"role-{role_name}"])
    sig += addnodes.desc_name("", f":{role_name}:")
    desc += sig
    content = addnodes.desc_content()
    content += nodes.paragraph("", "A demo role for testing.")
    desc += content
    return desc


def _api_facts_child(content: addnodes.desc_content) -> api_component | None:
    """Return the api-facts component in desc_content, or None."""
    for child in content.children:
        if isinstance(child, api_component) and child.get("name") == "api-facts":
            return child
    return None


def _api_options_child(content: addnodes.desc_content) -> api_component | None:
    """Return the api-options component in desc_content, or None."""
    for child in content.children:
        if isinstance(child, api_component) and child.get("name") == "api-options":
            return child
    return None


def _fact_labels(facts_section: api_component) -> list[str]:
    """Return the field-name labels from an api-facts section."""
    return [
        field.children[0].astext()
        for field in facts_section.findall(nodes.field)
        if field.children
    ]


def test_normalize_directive_inserts_api_facts_after_summary() -> None:
    """_normalize_directive_nodes inserts api-facts after the summary paragraph."""
    desc = _make_directive_desc(with_option=False)
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_directive_nodes(
        [desc],
        path="demo.DemoDirective",
        directive_cls=_DemoDirective,
    )

    assert len(content.children) >= 2
    assert isinstance(content.children[0], nodes.paragraph)
    facts = _api_facts_child(content)
    assert facts is not None, "api-facts section should be inserted"
    labels = _fact_labels(facts)
    assert "Python path" in labels
    assert "Required arguments" in labels
    assert "Optional arguments" in labels
    assert "Final argument whitespace" in labels
    assert "Has content" in labels


def test_normalize_directive_fact_values_match_directive_class() -> None:
    """Fact row values reflect the actual directive class attributes."""
    desc = _make_directive_desc(with_option=False)
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_directive_nodes(
        [desc],
        path="my_mod.DemoDirective",
        directive_cls=_DemoDirective,
    )

    facts = _api_facts_child(content)
    assert facts is not None
    by_label: dict[str, str] = {}
    for field in facts.findall(nodes.field):
        if field.children:
            label = field.children[0].astext()
            body = field.children[1].astext() if len(field.children) > 1 else ""
            by_label[label] = body

    assert by_label["Python path"] == "my_mod.DemoDirective"
    assert by_label["Required arguments"] == str(_DemoDirective.required_arguments)
    assert by_label["Optional arguments"] == str(_DemoDirective.optional_arguments)
    assert by_label["Has content"] == str(_DemoDirective.has_content)


def test_normalize_directive_extracts_options_into_api_options() -> None:
    """Option sub-entries are removed from desc_content and placed in api-options."""
    desc = _make_directive_desc(with_option=True)
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_directive_nodes(
        [desc],
        path="demo.DemoDirective",
        directive_cls=_DemoDirective,
    )

    options = _api_options_child(content)
    assert options is not None, (
        "api-options section should be created for option entries"
    )
    assert any(
        isinstance(child, addnodes.desc) and child.get("objtype") == "directive:option"
        for child in options.children
    )


def test_normalize_directive_removes_option_descs_from_main_content() -> None:
    """directive:option desc nodes are no longer direct children of desc_content."""
    desc = _make_directive_desc(with_option=True)
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_directive_nodes(
        [desc],
        path="demo.DemoDirective",
        directive_cls=_DemoDirective,
    )

    direct_option_descs = [
        child
        for child in content.children
        if isinstance(child, addnodes.desc)
        and child.get("objtype") == "directive:option"
    ]
    assert direct_option_descs == [], (
        "directive:option entries should be moved into api-options, not left in content"
    )


def test_normalize_directive_skips_non_directive_descs() -> None:
    """Desc nodes with non-directive objtypes are left untouched."""
    role_desc = _make_role_desc()
    directive_desc = _make_directive_desc(with_option=False)
    node_list: list[nodes.Node] = [role_desc, directive_desc]

    _normalize_directive_nodes(
        node_list,
        path="demo.DemoDirective",
        directive_cls=_DemoDirective,
    )

    role_content = t.cast(addnodes.desc_content, role_desc.children[-1])
    assert _api_facts_child(role_content) is None, (
        "_normalize_directive_nodes should not touch rst:role entries"
    )


def test_normalize_role_inserts_api_facts_with_python_path() -> None:
    """_normalize_role_nodes inserts an api-facts section with Python path."""
    desc = _make_role_desc()
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_role_nodes([desc], path="demo.demo_badge_role", role_fn=_demo_role)

    facts = _api_facts_child(content)
    assert facts is not None, "api-facts section should be inserted for roles"
    labels = _fact_labels(facts)
    assert "Python path" in labels
    assert "Accepts role content" in labels


def test_normalize_role_content_value_reflects_role_fn() -> None:
    """The Accepts role content fact matches the role callable's .content attribute."""
    desc = _make_role_desc()
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_role_nodes([desc], path="demo.demo_badge_role", role_fn=_demo_role)

    facts = _api_facts_child(content)
    assert facts is not None
    by_label: dict[str, str] = {}
    for field in facts.findall(nodes.field):
        if field.children:
            by_label[field.children[0].astext()] = (
                field.children[1].astext() if len(field.children) > 1 else ""
            )
    assert by_label["Accepts role content"] == str(getattr(_demo_role, "content"))


def test_normalize_role_without_content_attr_omits_accepts_content_row() -> None:
    """Roles without a .content attribute do not produce an Accepts role content row."""

    def _bare_role(
        name: object,
        rawtext: object,
        text: object,
        lineno: object,
        inliner: object,
        options: object = None,
        content: object = None,
    ) -> tuple[list[nodes.Node], list[nodes.Node]]:
        return [], []

    desc = _make_role_desc()
    content = t.cast(addnodes.desc_content, desc.children[-1])

    _normalize_role_nodes([desc], path="demo._bare_role", role_fn=_bare_role)

    facts = _api_facts_child(content)
    assert facts is not None
    labels = _fact_labels(facts)
    assert "Python path" in labels
    assert "Accepts role content" not in labels


def test_normalize_role_skips_non_role_descs() -> None:
    """Desc nodes with non-role objtypes are left untouched."""
    directive_desc = _make_directive_desc(with_option=False)
    role_desc = _make_role_desc()
    node_list: list[nodes.Node] = [directive_desc, role_desc]

    _normalize_role_nodes(node_list, path="demo.demo_badge_role", role_fn=_demo_role)

    dir_content = t.cast(addnodes.desc_content, directive_desc.children[-1])
    assert _api_facts_child(dir_content) is None, (
        "_normalize_role_nodes should not touch rst:directive entries"
    )
