"""Tests for the sphinx_typehints_gp extension."""

from __future__ import annotations

from sphinx_typehints_gp.extension import get_module_imports, resolve_annotation_string


def test_get_module_imports() -> None:
    """Test extracting imports from a module."""
    import sphinx.util.typing  # noqa: F401

    aliases = get_module_imports("sphinx.util.typing")
    assert "Any" in aliases
    assert aliases["Any"] == "typing.Any"


def test_resolve_annotation_string() -> None:
    """Test resolving a string annotation."""
    aliases = {"List": "typing.List", "MyClass": "other.MyClass"}
    resolved = resolve_annotation_string("List[MyClass]", "my_module", aliases)
    assert resolved == "~typing.List[~other.MyClass]"


def test_resolve_annotation_string_local() -> None:
    """Test resolving a local class annotation."""
    aliases = {"List": "typing.List"}
    resolved = resolve_annotation_string("List[LocalClass]", "my_module", aliases)
    assert resolved == "~typing.List[~my_module.LocalClass]"


def test_resolve_annotation_string_builtin() -> None:
    """Test resolving a builtin annotation."""
    aliases = {"List": "typing.List"}
    resolved = resolve_annotation_string("List[str]", "my_module", aliases)
    assert resolved == "~typing.List[str]"
