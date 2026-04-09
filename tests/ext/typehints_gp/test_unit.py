"""Unit tests for sphinx_typehints_gp helpers."""

from __future__ import annotations

from sphinx_typehints_gp.extension import get_module_imports, resolve_annotation_string


def test_get_module_imports_finds_typing_aliases() -> None:
    """get_module_imports extracts typing aliases from a module."""
    import sphinx.util.typing  # noqa: F401

    aliases = get_module_imports("sphinx.util.typing")
    assert "Any" in aliases
    assert aliases["Any"] == "typing.Any"


def test_get_module_imports_cached_on_repeat_call() -> None:
    """get_module_imports returns the same dict object on repeat calls."""
    import sphinx.util.typing  # noqa: F401

    first = get_module_imports("sphinx.util.typing")
    second = get_module_imports("sphinx.util.typing")
    assert first is second


def test_get_module_imports_missing_module_returns_empty() -> None:
    """get_module_imports returns empty dict for an unknown module name."""
    result = get_module_imports("__nonexistent_module__")
    assert result == {}


def test_resolve_annotation_string_qualified_names() -> None:
    """resolve_annotation_string replaces aliases with qualified paths."""
    aliases = {"List": "typing.List", "MyClass": "other.MyClass"}
    resolved = resolve_annotation_string("List[MyClass]", "my_module", aliases)
    assert resolved == "~typing.List[~other.MyClass]"


def test_resolve_annotation_string_local_class() -> None:
    """resolve_annotation_string qualifies an unknown local class."""
    aliases = {"List": "typing.List"}
    resolved = resolve_annotation_string("List[LocalClass]", "my_module", aliases)
    assert resolved == "~typing.List[~my_module.LocalClass]"


def test_resolve_annotation_string_builtin_unchanged() -> None:
    """resolve_annotation_string leaves builtin names unqualified."""
    aliases = {"List": "typing.List"}
    resolved = resolve_annotation_string("List[str]", "my_module", aliases)
    assert resolved == "~typing.List[str]"


def test_resolve_annotation_string_syntax_error_returns_original() -> None:
    """resolve_annotation_string returns the original string on SyntaxError."""
    result = resolve_annotation_string("not valid[python]syntax!!!", "mod", {})
    assert result == "not valid[python]syntax!!!"
