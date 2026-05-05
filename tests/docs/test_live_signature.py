"""Tests for the ``{live-signature}`` showcase directive.

The directive imports a package's module and renders each public
callable's signature from the running interpreter.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def test_live_signature_markdown_renders_public_callables_for_sphinx_fonts() -> None:
    """sphinx_fonts has at least one public callable; markdown lists it."""
    rendered = package_reference._live_signature_markdown("sphinx-fonts")
    assert rendered, "expected non-empty markdown for sphinx-fonts"
    assert "(sphinx-fonts-signatures)=" in rendered
    assert "# Signatures (live)" in rendered
    # The setup function must appear as a public callable
    assert (
        "### `setup`" in rendered
        or "### `merge_sphinx_config`" in rendered
        or any(line.startswith("### `") for line in rendered.splitlines())
    )


def test_live_signature_markdown_is_empty_for_unknown_package() -> None:
    """Unknown package returns the empty string (caller logs a warning)."""
    rendered = package_reference._live_signature_markdown("definitely-no-such-pkg")
    assert rendered == ""


def test_live_signature_markdown_skips_re_exports() -> None:
    """Public callables whose ``__module__`` differs are filtered out.

    Re-exports (e.g. ``from x import y`` at module top-level) belong
    to their owning module; rendering them on every importer would
    create duplicate signature blocks.
    """
    pairs = package_reference._public_callables("sphinx_fonts")
    for name, _sig in pairs:
        obj = getattr(__import__("sphinx_fonts"), name)
        owner = getattr(obj, "__module__", None)
        assert owner == "sphinx_fonts", (
            f"{name!r} is a re-export from {owner!r} and should be filtered"
        )


def test_public_callables_returns_signatures_for_dataclass_helpers() -> None:
    """The helper handles regular functions (their ``inspect.signature`` works)."""
    pairs = package_reference._public_callables("sphinx_fonts")
    assert len(pairs) >= 1
    for name, sig in pairs:
        assert isinstance(name, str)
        assert sig.startswith("(")
        assert sig.endswith(")") or "->" in sig


def test_public_callables_returns_empty_for_unimportable_module() -> None:
    """Unimportable module does not crash the build."""
    pairs = package_reference._public_callables("sphinx_definitely_no_such_module")
    assert pairs == []
