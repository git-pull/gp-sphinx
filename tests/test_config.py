"""Tests for gp_sphinx.config module."""

from __future__ import annotations

import gp_sphinx
from gp_sphinx.config import deep_merge, make_linkcode_resolve, merge_sphinx_config
from gp_sphinx.defaults import DEFAULT_EXTENSIONS, DEFAULT_MYST_EXTENSIONS


def test_merge_sphinx_config_returns_dict() -> None:
    """merge_sphinx_config returns a dict."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert isinstance(result, dict)


def test_merge_sphinx_config_required_params() -> None:
    """Required params populate correctly in the result."""
    result = merge_sphinx_config(
        project="my-project",
        version="2.0.0",
        copyright="2026, Test Author",
    )
    assert result["project"] == "my-project"
    assert result["version"] == "2.0.0"
    assert result["copyright"] == "2026, Test Author"


def test_merge_sphinx_config_default_extensions() -> None:
    """Default extension list matches DEFAULT_EXTENSIONS."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert result["extensions"] == DEFAULT_EXTENSIONS


def test_merge_sphinx_config_extra_extensions() -> None:
    """extra_extensions appends to the default list."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        extra_extensions=["argparse_exemplar", "sphinx_click"],
    )
    assert "argparse_exemplar" in result["extensions"]
    assert "sphinx_click" in result["extensions"]
    # Defaults still present
    assert "myst_parser" in result["extensions"]


def test_merge_sphinx_config_remove_extensions() -> None:
    """remove_extensions filters specific extensions from defaults."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        remove_extensions=["sphinx_design", "sphinx_copybutton"],
    )
    assert "sphinx_design" not in result["extensions"]
    assert "sphinx_copybutton" not in result["extensions"]
    # Others still present
    assert "myst_parser" in result["extensions"]


def test_merge_sphinx_config_replace_extensions() -> None:
    """Extensions param replaces the entire default list."""
    custom = ["sphinx.ext.autodoc", "myst_parser"]
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        extensions=custom,
    )
    assert result["extensions"] == custom


def test_merge_sphinx_config_theme_options_deep_merge() -> None:
    """theme_options deep-merges with defaults."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        theme_options={"custom_key": "custom_value"},
    )
    # Custom key present
    assert result["html_theme_options"]["custom_key"] == "custom_value"
    # Defaults still present
    assert "source_branch" in result["html_theme_options"]


def test_merge_sphinx_config_source_repository() -> None:
    """source_repository propagates to theme_options."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        source_repository="https://github.com/test/repo/",
    )
    opts = result["html_theme_options"]
    assert opts["source_repository"] == "https://github.com/test/repo/"
    # Footer icon URL updated
    github_icon = next(i for i in opts["footer_icons"] if i["name"] == "GitHub")
    assert github_icon["url"] == "https://github.com/test/repo/"


def test_merge_sphinx_config_logos() -> None:
    """light_logo and dark_logo propagate to theme_options."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        light_logo="img/logo.svg",
        dark_logo="img/logo-dark.svg",
    )
    opts = result["html_theme_options"]
    assert opts["light_logo"] == "img/logo.svg"
    assert opts["dark_logo"] == "img/logo-dark.svg"


def test_merge_sphinx_config_intersphinx_mapping() -> None:
    """intersphinx_mapping passes through to config."""
    mapping = {
        "py": ("https://docs.python.org/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    }
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        intersphinx_mapping=mapping,
    )
    assert result["intersphinx_mapping"] == mapping


def test_merge_sphinx_config_overrides() -> None:
    """**overrides set arbitrary Sphinx config values."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        html_favicon="_static/favicon.ico",
        html_static_path=["_static"],
    )
    assert result["html_favicon"] == "_static/favicon.ico"
    assert result["html_static_path"] == ["_static"]


def test_merge_sphinx_config_has_setup_function() -> None:
    """Returned config includes a callable setup function."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert "setup" in result
    assert callable(result["setup"])


def test_merge_sphinx_config_default_myst_config() -> None:
    """Default MyST config is present."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert result["myst_heading_anchors"] == 4
    assert result["myst_enable_extensions"] == DEFAULT_MYST_EXTENSIONS


def test_merge_sphinx_config_default_fonts() -> None:
    """Default font configuration is present."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert len(result["sphinx_fonts"]) == 2
    assert result["sphinx_fonts"][0]["family"] == "IBM Plex Sans"
    assert len(result["sphinx_font_preload"]) == 3
    assert len(result["sphinx_font_fallbacks"]) == 2
    assert "--font-stack" in result["sphinx_font_css_variables"]


def test_deep_merge_nested_dicts() -> None:
    """deep_merge recursively merges nested dicts."""
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    override = {"a": {"y": 20, "z": 30}}
    result = deep_merge(base, override)
    assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}


def test_deep_merge_override_wins() -> None:
    """deep_merge lets override values replace non-dict values."""
    base = {"a": [1, 2], "b": "hello"}
    override = {"a": [3, 4], "c": "new"}
    result = deep_merge(base, override)
    assert result == {"a": [3, 4], "b": "hello", "c": "new"}


def test_merge_sphinx_config_uses_gp_sphinx_theme() -> None:
    """Default theme is gp-sphinx (Furo child theme)."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert result["html_theme"] == "gp-sphinx"


def test_merge_sphinx_config_no_sidebars() -> None:
    """Theme provides sidebars — config should not include html_sidebars."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert "html_sidebars" not in result


def test_make_linkcode_resolve_returns_callable() -> None:
    """make_linkcode_resolve returns a callable."""
    resolver = make_linkcode_resolve(
        gp_sphinx,
        "https://github.com/git-pull/gp-sphinx",
    )
    assert callable(resolver)


def test_make_linkcode_resolve_non_py_domain() -> None:
    """Resolver returns None for non-Python domains."""
    resolver = make_linkcode_resolve(
        gp_sphinx,
        "https://github.com/git-pull/gp-sphinx",
    )
    assert resolver("c", {"module": "gp_sphinx", "fullname": "foo"}) is None


def test_merge_sphinx_config_autodoc_class_signature() -> None:
    """Default autodoc_class_signature is 'separated'."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert result["autodoc_class_signature"] == "separated"


def test_merge_sphinx_config_suppress_warnings() -> None:
    """Default suppress_warnings includes autodoc_typehints forward_reference."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert "sphinx_autodoc_typehints.forward_reference" in result["suppress_warnings"]


def test_merge_sphinx_config_linkcode_auto_added() -> None:
    """sphinx.ext.linkcode auto-added when linkcode_resolve is provided."""
    resolver = make_linkcode_resolve(
        gp_sphinx,
        "https://github.com/git-pull/gp-sphinx",
    )
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        linkcode_resolve=resolver,
    )
    assert "sphinx.ext.linkcode" in result["extensions"]


def test_merge_sphinx_config_no_linkcode_without_resolver() -> None:
    """sphinx.ext.linkcode not in extensions when no resolver provided."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert "sphinx.ext.linkcode" not in result["extensions"]


def test_merge_sphinx_config_auto_issue_url_tpl() -> None:
    """issue_url_tpl auto-computed from source_repository."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        source_repository="https://github.com/org/test/",
    )
    assert result["issue_url_tpl"] == "https://github.com/org/test/issues/{issue_id}"


def test_merge_sphinx_config_no_issue_url_without_repo() -> None:
    """issue_url_tpl not set when source_repository is not provided."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert "issue_url_tpl" not in result


def test_merge_sphinx_config_auto_ogp() -> None:
    """ogp_* auto-computed from docs_url and project."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        docs_url="https://test.git-pull.com",
    )
    assert result["ogp_site_url"] == "https://test.git-pull.com"
    assert result["ogp_site_name"] == "test"
    assert result["ogp_image"] == "_static/img/icons/icon-192x192.png"


def test_merge_sphinx_config_no_ogp_without_docs_url() -> None:
    """ogp_* not set when docs_url is not provided."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
    )
    assert "ogp_site_url" not in result


def test_merge_sphinx_config_override_auto_computed() -> None:
    """Manual overrides take precedence over auto-computed values."""
    result = merge_sphinx_config(
        project="test",
        version="1.0",
        copyright="2026",
        source_repository="https://github.com/org/test/",
        issue_url_tpl="https://custom.example.com/{issue_id}",
    )
    assert result["issue_url_tpl"] == "https://custom.example.com/{issue_id}"
