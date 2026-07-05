"""CSS regression tests for sphinx-gp-mermaid responsive policies."""

from __future__ import annotations

import pathlib

_MERMAID_CSS = pathlib.Path(
    "packages/sphinx-gp-mermaid/src/sphinx_gp_mermaid/_static/css/sphinx_gp_mermaid.css"
)


def test_fit_policy_scales_svg_to_column() -> None:
    """The default fit policy keeps the existing scale-down behavior."""
    css = _MERMAID_CSS.read_text(encoding="utf-8")

    assert (
        ".gp-sphinx-mermaid--fit .gp-sphinx-mermaid__variant svg {\n"
        "  max-width: 100%;\n"
        "  height: auto;\n"
        "}"
    ) in css


def test_preserve_policy_keeps_intrinsic_svg_width() -> None:
    """The preserve policy lets wide diagrams scroll at intrinsic width."""
    css = _MERMAID_CSS.read_text(encoding="utf-8")

    assert (
        ".gp-sphinx-mermaid--preserve .gp-sphinx-mermaid__variant svg {\n"
        "  max-width: none;\n"
        "}"
    ) in css
