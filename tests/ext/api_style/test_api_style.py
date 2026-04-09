"""Tests for sphinx_autodoc_api_style Sphinx extension."""

from __future__ import annotations

import types
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_badges import BadgeNode
from sphinx_autodoc_layout._nodes import api_slot

import sphinx_autodoc_api_style
from sphinx_autodoc_api_style._badges import (
    _MOD_ORDER,
    _MOD_TOOLTIPS,
    _TYPE_LABELS,
    _TYPE_TOOLTIPS,
    build_badge_group,
)
from sphinx_autodoc_api_style._css import _CSS
from sphinx_autodoc_api_style._transforms import (
    _HANDLED_OBJTYPES,
    _KEYWORD_TO_MOD,
    _SKIP_OBJTYPES,
    _detect_deprecated,
    _detect_modifiers,
    _inject_badges,
    _prune_empty_desc_content,
    on_doctree_resolved,
)

# ---------------------------------------------------------------------------
# _CSS constants
# ---------------------------------------------------------------------------


def test_css_prefix() -> None:
    """CSS prefix is now 'sab' (unified palette)."""
    assert _CSS.PREFIX == "sab"


def test_css_badge_group_class() -> None:
    """Badge group class uses the shared sab- prefix."""
    assert _CSS.BADGE_GROUP == "sab-badge-group"


def test_css_obj_type_class() -> None:
    """obj_type() returns sab-type-* class (unified palette)."""
    assert _CSS.obj_type("function") == "sab-type-function"
    assert _CSS.obj_type("class") == "sab-type-class"
    assert _CSS.obj_type("method") == "sab-type-method"


# ---------------------------------------------------------------------------
# build_badge_group
# ---------------------------------------------------------------------------


def test_badge_group_returns_inline() -> None:
    """build_badge_group returns a nodes.inline with badge-group class."""
    group = build_badge_group("function", modifiers=frozenset())
    assert isinstance(group, nodes.inline)
    assert _CSS.BADGE_GROUP in group["classes"]


def test_badge_group_type_badge_present() -> None:
    """Type badge is present when show_type_badge is True (default)."""
    group = build_badge_group("class", modifiers=frozenset())
    badges = list(group.findall(BadgeNode))
    assert len(badges) == 1
    assert badges[0].astext() == "class"
    assert _CSS.BADGE_TYPE in badges[0]["classes"]
    assert _CSS.obj_type("class") in badges[0]["classes"]


def test_badge_group_type_badge_suppressed() -> None:
    """Type badge is absent when show_type_badge is False."""
    group = build_badge_group("function", modifiers=frozenset(), show_type_badge=False)
    badges = list(group.findall(BadgeNode))
    assert len(badges) == 0


def test_badge_group_with_modifiers() -> None:
    """Modifier badges appear before the type badge."""
    group = build_badge_group(
        "method",
        modifiers=frozenset({"async", "abstract"}),
    )
    badges = list(group.findall(BadgeNode))
    labels = [b.astext() for b in badges]
    assert "abstract" in labels
    assert "async" in labels
    assert "method" in labels
    # Type badge is last
    assert labels[-1] == "method"


def test_badge_group_modifier_order() -> None:
    """Modifiers appear in the canonical order defined by _MOD_ORDER."""
    all_mods = frozenset(_MOD_ORDER)
    group = build_badge_group("function", modifiers=all_mods)
    badges = list(group.findall(BadgeNode))
    mod_labels = [b.astext() for b in badges if _CSS.BADGE_MOD in b["classes"]]
    expected = list(_MOD_ORDER)
    assert mod_labels == expected


def test_badge_group_tabindex() -> None:
    """All badges have tabindex='0' for keyboard accessibility."""
    group = build_badge_group(
        "function",
        modifiers=frozenset({"async"}),
    )
    for badge in group.findall(BadgeNode):
        assert badge.get("tabindex") == "0"


def test_badge_group_tooltips() -> None:
    """Badges have explanation attributes for hover tooltips."""
    group = build_badge_group(
        "function",
        modifiers=frozenset({"async"}),
    )
    badges = list(group.findall(BadgeNode))
    async_badge = [b for b in badges if b.astext() == "async"][0]
    assert async_badge["badge_tooltip"] == _MOD_TOOLTIPS["async"]

    func_badge = [b for b in badges if b.astext() == "function"][0]
    assert func_badge["badge_tooltip"] == _TYPE_TOOLTIPS["function"]


def test_badge_group_text_separators() -> None:
    """Text separators between badges for non-HTML builders."""
    group = build_badge_group(
        "method",
        modifiers=frozenset({"async"}),
    )
    text_nodes = [c for c in group.children if isinstance(c, nodes.Text)]
    assert len(text_nodes) == 1
    assert text_nodes[0].astext() == " "


def test_badge_group_single_badge_no_separator() -> None:
    """No text separator when only one badge."""
    group = build_badge_group("function", modifiers=frozenset())
    text_nodes = [c for c in group.children if isinstance(c, nodes.Text)]
    assert len(text_nodes) == 0


def test_badge_group_deprecated() -> None:
    """Deprecated modifier badge uses DEPRECATED CSS class."""
    group = build_badge_group("class", modifiers=frozenset({"deprecated"}))
    badges = list(group.findall(BadgeNode))
    dep_badge = [b for b in badges if b.astext() == "deprecated"][0]
    assert _CSS.DEPRECATED in dep_badge["classes"]
    assert _CSS.BADGE_MOD in dep_badge["classes"]


def test_badge_group_all_type_labels() -> None:
    """All handled objtypes produce a valid type badge label."""
    for objtype in _HANDLED_OBJTYPES:
        group = build_badge_group(objtype, modifiers=frozenset())
        badges = list(group.findall(BadgeNode))
        assert len(badges) >= 1
        label = badges[-1].astext()
        assert label == _TYPE_LABELS.get(objtype, objtype)


# ---------------------------------------------------------------------------
# _detect_modifiers
# ---------------------------------------------------------------------------


def test_detect_modifiers_empty() -> None:
    """Empty signature has no modifiers."""
    sig = addnodes.desc_signature()
    assert _detect_modifiers(sig) == frozenset()


def test_detect_modifiers_async() -> None:
    """Detects async keyword in desc_annotation."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "async")
    sig += ann
    assert "async" in _detect_modifiers(sig)


def test_detect_modifiers_classmethod() -> None:
    """Detects classmethod keyword."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "classmethod")
    sig += ann
    assert "classmethod" in _detect_modifiers(sig)


def test_detect_modifiers_static() -> None:
    """Detects 'static' keyword and maps to 'staticmethod'."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "static")
    sig += ann
    assert "staticmethod" in _detect_modifiers(sig)


def test_detect_modifiers_abstract() -> None:
    """Detects abstract keyword."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "abstract")
    sig += ann
    assert "abstract" in _detect_modifiers(sig)


def test_detect_modifiers_abstractmethod() -> None:
    """Detects abstractmethod keyword (used by py:property)."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "abstractmethod")
    sig += ann
    assert "abstract" in _detect_modifiers(sig)


def test_detect_modifiers_multiple() -> None:
    """Detects multiple keywords in one annotation."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "abstract")
    ann += addnodes.desc_sig_space()
    ann += addnodes.desc_sig_keyword("", "async")
    sig += ann
    mods = _detect_modifiers(sig)
    assert "abstract" in mods
    assert "async" in mods


def test_detect_modifiers_ignores_type_keywords() -> None:
    """Keywords like 'class' and 'property' are not modifiers."""
    sig = addnodes.desc_signature()
    ann = addnodes.desc_annotation()
    ann += addnodes.desc_sig_keyword("", "class")
    sig += ann
    assert _detect_modifiers(sig) == frozenset()


def test_keyword_to_mod_mapping() -> None:
    """_KEYWORD_TO_MOD maps Sphinx keywords to modifier names."""
    assert _KEYWORD_TO_MOD["async"] == "async"
    assert _KEYWORD_TO_MOD["static"] == "staticmethod"
    assert _KEYWORD_TO_MOD["abstractmethod"] == "abstract"


# ---------------------------------------------------------------------------
# _detect_deprecated
# ---------------------------------------------------------------------------


def test_detect_deprecated_false() -> None:
    """Returns False when no versionmodified node is present."""
    desc = addnodes.desc()
    assert not _detect_deprecated(desc)


def test_detect_deprecated_true() -> None:
    """Returns True when a deprecated versionmodified node is present."""
    desc = addnodes.desc()
    content = addnodes.desc_content()
    vm = addnodes.versionmodified()
    vm["type"] = "deprecated"
    content += vm
    desc += content
    assert _detect_deprecated(desc)


def test_detect_deprecated_ignores_versionadded() -> None:
    """Returns False for versionadded — only deprecated triggers."""
    desc = addnodes.desc()
    content = addnodes.desc_content()
    vm = addnodes.versionmodified()
    vm["type"] = "versionadded"
    content += vm
    desc += content
    assert not _detect_deprecated(desc)


# ---------------------------------------------------------------------------
# _inject_badges
# ---------------------------------------------------------------------------


def test_inject_badges_sets_flag() -> None:
    """_inject_badges sets gas_badges_injected flag on signature."""
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "my_func")
    _inject_badges(sig, "function")
    assert sig.get("gas_badges_injected") is True


def test_inject_badges_idempotent() -> None:
    """Calling _inject_badges twice doesn't duplicate badges."""
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "my_func")
    _inject_badges(sig, "function")
    badge_count_1 = len(list(sig.findall(BadgeNode)))
    _inject_badges(sig, "function")
    badge_count_2 = len(list(sig.findall(BadgeNode)))
    assert badge_count_1 == badge_count_2


def test_inject_badges_adds_badge_slot_with_badge_group() -> None:
    """A badge slot containing the badge group is added to the signature."""
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "my_func")
    _inject_badges(sig, "function")
    slots = [
        c for c in sig.children if isinstance(c, api_slot) and c.get("slot") == "badges"
    ]
    assert len(slots) == 1
    groups = list(slots[0].findall(nodes.inline))
    badge_groups = [g for g in groups if _CSS.BADGE_GROUP in g.get("classes", [])]
    assert len(badge_groups) == 1


def test_inject_badges_detects_deprecated_parent() -> None:
    """Deprecated modifier is detected from parent desc node."""
    desc = addnodes.desc()
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "old_func")
    desc += sig
    content = addnodes.desc_content()
    vm = addnodes.versionmodified()
    vm["type"] = "deprecated"
    content += vm
    desc += content

    _inject_badges(sig, "function")

    badges = list(sig.findall(BadgeNode))
    labels = [b.astext() for b in badges]
    assert "deprecated" in labels


def test_inject_badges_adds_source_slot_for_viewcode() -> None:
    """Viewcode [source] link moves into a dedicated source-link slot."""
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "my_func")
    viewcode_span = nodes.inline(classes=["viewcode-link"])
    viewcode_span += nodes.Text("[source]")
    viewcode_ref = nodes.reference("", "", viewcode_span, internal=False)
    sig += viewcode_ref

    _inject_badges(sig, "function")

    slots = [c for c in sig.children if isinstance(c, api_slot)]
    assert [slot.get("slot") for slot in slots] == ["badges", "source-link"]
    source_slot = slots[1]
    assert isinstance(source_slot.children[0], nodes.reference)


def test_inject_badges_headerlink_not_moved_into_slots() -> None:
    """Headerlink stays as a direct child of sig, never inside a layout slot.

    Sphinx's HTML writer adds the headerlink as raw HTML during
    ``depart_desc_signature``, so it's not a doctree node during our
    transform. But if a theme or extension adds one as a node, we must
    leave it alone — layout owns its final position separately from the
    badge and source slots.
    """
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "Server")

    headerlink = nodes.reference(
        "", "\u00b6", refuri="#libtmux.Server", classes=["headerlink"]
    )
    sig += headerlink

    viewcode_span = nodes.inline(classes=["viewcode-link"])
    viewcode_span += nodes.Text("[source]")
    viewcode_ref = nodes.reference("", "", viewcode_span, internal=False)
    sig += viewcode_ref

    _inject_badges(sig, "class")

    slots = [c for c in sig.children if isinstance(c, api_slot)]
    for slot in slots:
        slot_refs = list(slot.findall(nodes.reference))
        for ref in slot_refs:
            assert "headerlink" not in ref.get("classes", []), (
                "headerlink must not be inside an api_slot"
            )

    sig_direct_refs = [
        c
        for c in sig.children
        if isinstance(c, nodes.reference) and "headerlink" in c.get("classes", [])
    ]
    assert len(sig_direct_refs) == 1, "headerlink should remain a direct child of sig"


# ---------------------------------------------------------------------------
# _prune_empty_desc_content
# ---------------------------------------------------------------------------


def test_prune_empty_desc_content_removes_empty() -> None:
    """Empty desc_content is removed from the desc node."""
    desc = addnodes.desc()
    desc += addnodes.desc_signature()
    desc += addnodes.desc_content()  # empty — no children

    _prune_empty_desc_content(desc)

    assert not any(isinstance(c, addnodes.desc_content) for c in desc.children)


def test_prune_empty_desc_content_keeps_nonempty() -> None:
    """desc_content with children is not removed."""
    desc = addnodes.desc()
    content = addnodes.desc_content()
    content += nodes.paragraph("", "Has content.")
    desc += addnodes.desc_signature()
    desc += content

    _prune_empty_desc_content(desc)

    assert any(isinstance(c, addnodes.desc_content) for c in desc.children)


def test_on_doctree_resolved_prunes_empty_desc_content() -> None:
    """on_doctree_resolved removes empty desc_content via full pipeline."""
    from unittest.mock import MagicMock

    app = MagicMock()
    doc = nodes.document(None, None)  # type: ignore[arg-type]
    desc = addnodes.desc()
    desc["domain"] = "py"
    desc["objtype"] = "attribute"
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "session_id")
    desc += sig
    desc += addnodes.desc_content()  # empty — simulates undocumented attribute

    doc += desc
    on_doctree_resolved(app, doc, "index")

    assert not any(isinstance(c, addnodes.desc_content) for c in desc.children)


# ---------------------------------------------------------------------------
# on_doctree_resolved
# ---------------------------------------------------------------------------


def test_on_doctree_resolved_processes_py_desc(monkeypatch: t.Any) -> None:
    """on_doctree_resolved injects badges into py function desc nodes."""
    from unittest.mock import MagicMock

    app = MagicMock()
    doc = nodes.document(None, None)  # type: ignore[arg-type]
    desc = addnodes.desc()
    desc["domain"] = "py"
    desc["objtype"] = "function"
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "my_func")
    desc += sig
    desc += addnodes.desc_content()
    doc += desc

    on_doctree_resolved(app, doc, "index")

    assert sig.get("gas_badges_injected") is True


def test_on_doctree_resolved_skips_fixture() -> None:
    """on_doctree_resolved skips fixture objtypes."""
    from unittest.mock import MagicMock

    app = MagicMock()
    doc = nodes.document(None, None)  # type: ignore[arg-type]
    desc = addnodes.desc()
    desc["domain"] = "py"
    desc["objtype"] = "fixture"
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "my_fixture")
    desc += sig
    doc += desc

    on_doctree_resolved(app, doc, "index")

    assert sig.get("gas_badges_injected") is None


def test_on_doctree_resolved_skips_non_py() -> None:
    """on_doctree_resolved skips non-Python domain entries."""
    from unittest.mock import MagicMock

    app = MagicMock()
    doc = nodes.document(None, None)  # type: ignore[arg-type]
    desc = addnodes.desc()
    desc["domain"] = "c"
    desc["objtype"] = "function"
    sig = addnodes.desc_signature()
    sig += addnodes.desc_name("", "c_func")
    desc += sig
    doc += desc

    on_doctree_resolved(app, doc, "index")

    assert sig.get("gas_badges_injected") is None


def test_setup_auto_loads_layout() -> None:
    """setup() loads layout alongside autodoc and badges."""
    setup_extensions: list[str] = []

    app = t.cast(
        t.Any,
        types.SimpleNamespace(
            setup_extension=setup_extensions.append,
            connect=lambda *args, **kwargs: None,
            add_css_file=lambda *args, **kwargs: None,
            config=types.SimpleNamespace(html_static_path=[]),
        ),
    )

    sphinx_autodoc_api_style.setup(app)

    assert setup_extensions == [
        "sphinx.ext.autodoc",
        "sphinx_autodoc_badges",
        "sphinx_autodoc_layout",
    ]


def test_on_doctree_resolved_handles_multiple() -> None:
    """on_doctree_resolved processes all qualifying desc nodes."""
    from unittest.mock import MagicMock

    app = MagicMock()
    doc = nodes.document(None, None)  # type: ignore[arg-type]

    for objtype in ("function", "class", "method"):
        desc = addnodes.desc()
        desc["domain"] = "py"
        desc["objtype"] = objtype
        sig = addnodes.desc_signature()
        sig += addnodes.desc_name("", f"obj_{objtype}")
        desc += sig
        desc += addnodes.desc_content()
        doc += desc

    on_doctree_resolved(app, doc, "index")

    for desc in doc.findall(addnodes.desc):
        for sig in desc.findall(addnodes.desc_signature):
            assert sig.get("gas_badges_injected") is True


# ---------------------------------------------------------------------------
# Handled vs skipped objtypes
# ---------------------------------------------------------------------------


def test_handled_objtypes_comprehensive() -> None:
    """_HANDLED_OBJTYPES covers all standard Python domain types."""
    expected_minimum = {
        "function",
        "class",
        "method",
        "property",
        "attribute",
        "data",
        "exception",
    }
    assert expected_minimum.issubset(_HANDLED_OBJTYPES)


def test_skip_objtypes_includes_fixture() -> None:
    """_SKIP_OBJTYPES includes fixture to avoid conflict."""
    assert "fixture" in _SKIP_OBJTYPES
