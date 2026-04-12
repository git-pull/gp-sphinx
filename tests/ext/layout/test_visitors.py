"""Tests for sphinx_ux_autodoc_layout HTML visitors."""

from __future__ import annotations

import typing as t

from sphinx import addnodes

from sphinx_ux_autodoc_layout._nodes import build_api_component
from sphinx_ux_autodoc_layout._visitors import (
    visit_api_component,
    visit_desc_signature_html,
)


class _DummyTranslator:
    """Minimal HTML translator stub for visitor tests."""

    def __init__(self) -> None:
        self.body: list[str] = []
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.protect_literal_text = 0

    def starttag(
        self,
        node: addnodes.desc_signature,
        tagname: str,
        suffix: str = "\n",
        **attributes: str,
    ) -> str:
        self.calls.append((tagname, attributes))
        return f"<{tagname}>{suffix}"


def test_visit_desc_signature_html_emits_managed_header_attrs() -> None:
    sig = addnodes.desc_signature(ids=["demo.func"])
    sig["classes"] = ["sig", "gp-sphinx-api-header"]
    sig["api_managed"] = True
    sig["html_attrs"] = {"data-signature-expanded": "false"}

    translator = _DummyTranslator()

    visit_desc_signature_html(t.cast(t.Any, translator), sig)

    assert translator.calls == [("dt", {"data-signature-expanded": "false"})]
    assert translator.body == ["<dt>\n"]
    assert translator.protect_literal_text == 1


def test_visit_api_component_emits_generic_header_attrs() -> None:
    header = build_api_component(
        "gp-sphinx-api-header",
        html_attrs={"data-profile": "confval"},
    )

    translator = _DummyTranslator()

    visit_api_component(t.cast(t.Any, translator), header)

    assert translator.calls == [("div", {"ids": [], "data-profile": "confval"})]
    assert translator.body == ["<div>"]
