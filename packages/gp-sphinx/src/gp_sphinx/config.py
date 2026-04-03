"""Configuration builder for shared Sphinx documentation platform.

Provides :func:`merge_sphinx_config` to build a complete Sphinx configuration
namespace from shared defaults with per-project overrides, and
:func:`make_linkcode_resolve` to generate per-project source link resolvers.

Examples
--------
>>> from gp_sphinx.config import merge_sphinx_config

>>> conf = merge_sphinx_config(
...     project="my-project",
...     version="1.0.0",
...     copyright="2026, Tony Narlock",
... )
>>> conf["project"]
'my-project'

>>> conf["html_theme"]
'sphinx-gptheme'

>>> "myst_parser" in conf["extensions"]
True
"""

from __future__ import annotations

import contextlib
import copy
import inspect
import logging
import os.path
import pathlib
import types
import typing as t

from gp_sphinx.defaults import (
    DEFAULT_AUTOCLASS_CONTENT,
    DEFAULT_AUTODOC_CLASS_SIGNATURE,
    DEFAULT_AUTODOC_MEMBER_ORDER,
    DEFAULT_AUTODOC_OPTIONS,
    DEFAULT_AUTODOC_TYPEHINTS,
    DEFAULT_COPYBUTTON_LINE_CONTINUATION_CHARACTER,
    DEFAULT_COPYBUTTON_PROMPT_IS_REGEXP,
    DEFAULT_COPYBUTTON_PROMPT_TEXT,
    DEFAULT_COPYBUTTON_REMOVE_PROMPTS,
    DEFAULT_EXTENSIONS,
    DEFAULT_HTML_STATIC_PATH,
    DEFAULT_MYST_EXTENSIONS,
    DEFAULT_MYST_HEADING_ANCHORS,
    DEFAULT_NAPOLEON_GOOGLE_DOCSTRING,
    DEFAULT_NAPOLEON_INCLUDE_INIT_WITH_DOC,
    DEFAULT_PYGMENTS_DARK_STYLE,
    DEFAULT_PYGMENTS_STYLE,
    DEFAULT_SOURCE_SUFFIX,
    DEFAULT_SPHINX_FONT_CSS_VARIABLES,
    DEFAULT_SPHINX_FONT_FALLBACKS,
    DEFAULT_SPHINX_FONT_PRELOAD,
    DEFAULT_SPHINX_FONTS,
    DEFAULT_SUPPRESS_WARNINGS,
    DEFAULT_TEMPLATES_PATH,
    DEFAULT_THEME,
    DEFAULT_THEME_OPTIONS,
    DEFAULT_TOC_OBJECT_ENTRIES_SHOW_PARENTS,
)

if t.TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


def deep_merge(base: dict[str, t.Any], override: dict[str, t.Any]) -> dict[str, t.Any]:
    """Recursively merge *override* into *base*, returning a new dict.

    When both values for a key are dicts, they are merged recursively.
    Otherwise the value from *override* wins.

    Parameters
    ----------
    base : dict
        The base dictionary.
    override : dict
        The dictionary whose values take precedence.

    Returns
    -------
    dict
        A new merged dictionary.

    Examples
    --------
    >>> deep_merge({"a": 1, "b": {"x": 10}}, {"b": {"y": 20}})
    {'a': 1, 'b': {'x': 10, 'y': 20}}

    >>> deep_merge({"a": 1}, {"a": 2, "c": 3})
    {'a': 2, 'c': 3}
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def make_linkcode_resolve(
    package_module: types.ModuleType,
    github_url: str,
    src_dir: str = "src",
) -> Callable[[str, dict[str, str]], str | None]:
    """Create a ``linkcode_resolve`` function for ``sphinx.ext.linkcode``.

    Generates a resolver that maps Python objects to their source location
    on GitHub. The returned function follows the interface expected by
    ``sphinx.ext.linkcode``.

    Parameters
    ----------
    package_module : types.ModuleType
        The top-level package module (e.g., ``import libtmux; libtmux``).
        Used to compute relative file paths.
    github_url : str
        Base GitHub repository URL (e.g.,
        ``"https://github.com/tmux-python/libtmux"``).
    src_dir : str
        Directory containing the source package (default ``"src"``).

    Returns
    -------
    Callable[[str, dict[str, str]], str | None]
        A function suitable for ``linkcode_resolve`` in Sphinx config.

    Examples
    --------
    >>> import gp_sphinx

    >>> resolver = make_linkcode_resolve(
    ...     gp_sphinx,
    ...     "https://github.com/git-pull/gp-sphinx",
    ... )
    >>> callable(resolver)
    True
    """

    def linkcode_resolve(domain: str, info: dict[str, str]) -> str | None:
        if domain != "py":
            return None

        modname = info["module"]
        fullname = info["fullname"]

        import sys

        submod = sys.modules.get(modname)
        if submod is None:
            return None

        obj: object = submod
        for part in fullname.split("."):
            try:
                obj = getattr(obj, part)
            except Exception:  # noqa: PERF203
                return None

        try:
            unwrap = inspect.unwrap
        except AttributeError:
            pass
        else:
            if callable(obj):
                obj = unwrap(obj)

        try:
            fn = inspect.getsourcefile(obj)  # type: ignore[arg-type]
        except Exception:
            fn = None
        if not fn:
            return None

        try:
            source, lineno = inspect.getsourcelines(obj)  # type: ignore[arg-type]
        except Exception:
            lineno = None

        linespec = f"#L{lineno}-L{lineno + len(source) - 1}" if lineno else ""

        pkg_file = package_module.__file__
        if pkg_file is None:
            return None
        package_root = pathlib.Path(pkg_file).resolve().parent
        fn = os.path.relpath(fn, start=package_root.parent)

        version = getattr(package_module, "__version__", "")
        if "dev" in version:
            return f"{github_url}/blob/master/{src_dir}/{fn}{linespec}"
        return f"{github_url}/blob/v{version}/{src_dir}/{fn}{linespec}"

    return linkcode_resolve


def merge_sphinx_config(
    *,
    project: str,
    version: str,
    copyright: str,  # noqa: A002
    extensions: list[str] | None = None,
    extra_extensions: list[str] | None = None,
    remove_extensions: list[str] | None = None,
    theme_options: dict[str, t.Any] | None = None,
    source_repository: str | None = None,
    source_branch: str = "master",
    light_logo: str | None = None,
    dark_logo: str | None = None,
    docs_url: str | None = None,
    intersphinx_mapping: t.Mapping[str, tuple[str, str | None]] | None = None,
    **overrides: t.Any,
) -> dict[str, t.Any]:
    """Build a complete Sphinx conf namespace from shared defaults.

    Returns a flat dictionary suitable for injection into a ``docs/conf.py``
    module namespace via ``globals().update(conf)``.

    The default theme is ``sphinx-gptheme`` (a Furo child theme bundled in this
    package). Sidebars, templates, CSS, and JS are provided by the theme
    automatically.

    When ``source_repository`` is provided, ``issue_url_tpl`` is auto-computed
    for the ``linkify_issues`` extension. When ``docs_url`` is provided,
    ``ogp_site_url``, ``ogp_image``, and ``ogp_site_name`` are auto-computed
    for ``sphinxext.opengraph``. All auto-computed values can be overridden
    via ``**overrides``.

    Parameters
    ----------
    project : str
        Sphinx project name.
    version : str
        Project version string.
    copyright : str
        Copyright string.
    extensions : list[str] | None
        Replace the default extension list entirely. Usually not needed.
    extra_extensions : list[str] | None
        Add extensions to the defaults (e.g., ``["argparse_exemplar"]``).
    remove_extensions : list[str] | None
        Remove specific defaults (e.g., ``["sphinx_design"]``).
    theme_options : dict | None
        Deep-merged with default theme options.
    source_repository : str | None
        GitHub repository URL.
    source_branch : str
        Default branch name.
    light_logo : str | None
        Path to light-mode logo.
    dark_logo : str | None
        Path to dark-mode logo.
    docs_url : str | None
        Documentation site URL (e.g., ``"https://libtmux.git-pull.com"``).
        Used to auto-compute ``ogp_site_url`` and ``ogp_site_name``.
    intersphinx_mapping : dict | None
        Intersphinx targets.
    **overrides
        Any additional Sphinx config values.

    Returns
    -------
    dict[str, Any]
        Complete Sphinx configuration namespace including a ``setup``
        function for workaround hooks.

    Examples
    --------
    >>> conf = merge_sphinx_config(
    ...     project="test",
    ...     version="1.0",
    ...     copyright="2026",
    ... )
    >>> conf["project"]
    'test'

    >>> conf["version"]
    '1.0'

    >>> conf["html_theme"]
    'sphinx-gptheme'

    >>> len(conf["extensions"]) >= 13
    True

    >>> callable(conf["setup"])
    True

    Extra extensions are appended:

    >>> conf = merge_sphinx_config(
    ...     project="test",
    ...     version="1.0",
    ...     copyright="2026",
    ...     extra_extensions=["my_ext"],
    ... )
    >>> "my_ext" in conf["extensions"]
    True

    Extensions can be removed:

    >>> conf = merge_sphinx_config(
    ...     project="test",
    ...     version="1.0",
    ...     copyright="2026",
    ...     remove_extensions=["sphinx_design"],
    ... )
    >>> "sphinx_design" in conf["extensions"]
    False

    Auto-computed values from source_repository and docs_url:

    >>> conf = merge_sphinx_config(
    ...     project="test",
    ...     version="1.0",
    ...     copyright="2026",
    ...     source_repository="https://github.com/org/test/",
    ...     docs_url="https://test.org",
    ... )
    >>> conf["issue_url_tpl"]
    'https://github.com/org/test/issues/{issue_id}'

    >>> conf["ogp_site_url"]
    'https://test.org'
    """
    # Extensions
    ext_list = list(extensions) if extensions is not None else list(DEFAULT_EXTENSIONS)

    if extra_extensions:
        ext_list.extend(extra_extensions)

    if remove_extensions:
        remove_set = set(remove_extensions)
        ext_list = [e for e in ext_list if e not in remove_set]

    # Theme options — start from typed defaults, then widen for arbitrary overrides.
    # dict() conversion before deepcopy keeps the type as dict[str, Any] since
    # FuroThemeOptions (TypedDict) is not directly assignable to dict[str, Any].
    merged_theme_options: dict[str, t.Any] = copy.deepcopy(dict(DEFAULT_THEME_OPTIONS))
    if source_repository:
        merged_theme_options["source_repository"] = source_repository
        # Update footer icon URL
        for icon in merged_theme_options.get("footer_icons", []):
            if icon.get("name") == "GitHub" and not icon.get("url"):
                icon["url"] = source_repository
    merged_theme_options["source_branch"] = source_branch

    if light_logo:
        merged_theme_options["light_logo"] = light_logo
    if dark_logo:
        merged_theme_options["dark_logo"] = dark_logo

    if theme_options:
        merged_theme_options = deep_merge(merged_theme_options, theme_options)

    # Build config namespace
    conf: dict[str, t.Any] = {
        # Core
        "project": project,
        "version": version,
        "release": version,
        "copyright": copyright,
        "extensions": ext_list,
        "master_doc": "index",
        # Source
        "source_suffix": dict(DEFAULT_SOURCE_SUFFIX),
        # Static files and templates
        "html_static_path": list(DEFAULT_HTML_STATIC_PATH),
        "templates_path": list(DEFAULT_TEMPLATES_PATH),
        # Theme (gp-sphinx child theme provides sidebars, templates, CSS, JS)
        "html_theme": DEFAULT_THEME,
        "html_theme_path": [],
        "html_theme_options": merged_theme_options,
        # Pygments
        "pygments_style": DEFAULT_PYGMENTS_STYLE,
        "pygments_dark_style": DEFAULT_PYGMENTS_DARK_STYLE,
        # MyST
        "myst_heading_anchors": DEFAULT_MYST_HEADING_ANCHORS,
        "myst_enable_extensions": list(DEFAULT_MYST_EXTENSIONS),
        # Fonts
        "sphinx_fonts": copy.deepcopy(DEFAULT_SPHINX_FONTS),
        "sphinx_font_preload": list(DEFAULT_SPHINX_FONT_PRELOAD),
        "sphinx_font_fallbacks": copy.deepcopy(DEFAULT_SPHINX_FONT_FALLBACKS),
        "sphinx_font_css_variables": dict(DEFAULT_SPHINX_FONT_CSS_VARIABLES),
        # Autodoc
        "autoclass_content": DEFAULT_AUTOCLASS_CONTENT,
        "autodoc_member_order": DEFAULT_AUTODOC_MEMBER_ORDER,
        "autodoc_class_signature": DEFAULT_AUTODOC_CLASS_SIGNATURE,
        "autodoc_typehints": DEFAULT_AUTODOC_TYPEHINTS,
        "toc_object_entries_show_parents": DEFAULT_TOC_OBJECT_ENTRIES_SHOW_PARENTS,
        "autodoc_default_options": dict(DEFAULT_AUTODOC_OPTIONS),
        # Napoleon
        "napoleon_google_docstring": DEFAULT_NAPOLEON_GOOGLE_DOCSTRING,
        "napoleon_include_init_with_doc": DEFAULT_NAPOLEON_INCLUDE_INIT_WITH_DOC,
        # Copybutton
        "copybutton_prompt_text": DEFAULT_COPYBUTTON_PROMPT_TEXT,
        "copybutton_prompt_is_regexp": DEFAULT_COPYBUTTON_PROMPT_IS_REGEXP,
        "copybutton_remove_prompts": DEFAULT_COPYBUTTON_REMOVE_PROMPTS,
        "copybutton_line_continuation_character": (
            DEFAULT_COPYBUTTON_LINE_CONTINUATION_CHARACTER
        ),
        # Rediraffe
        "rediraffe_redirects": {},
        "rediraffe_branch": "master~1",
        # Warnings
        "suppress_warnings": list(DEFAULT_SUPPRESS_WARNINGS),
        # Exclude patterns
        "exclude_patterns": ["_build"],
        # Workaround hooks
        "setup": setup,
    }

    # Intersphinx
    if intersphinx_mapping is not None:
        conf["intersphinx_mapping"] = dict(intersphinx_mapping)

    # Auto-compute linkify_issues config
    if source_repository:
        repo = source_repository.rstrip("/")
        conf["issue_url_tpl"] = f"{repo}/issues/{{issue_id}}"

    # Auto-compute sphinxext.opengraph config
    if docs_url:
        conf["ogp_site_url"] = docs_url
        conf["ogp_site_name"] = project
        conf["ogp_image"] = "_static/img/icons/icon-192x192.png"

    # Apply overrides last (can override auto-computed values)
    conf.update(overrides)

    # Auto-add sphinx.ext.linkcode when linkcode_resolve is provided
    if "linkcode_resolve" in conf and "sphinx.ext.linkcode" not in conf["extensions"]:
        conf["extensions"].append("sphinx.ext.linkcode")

    logger.debug("sphinx config merged for %s", project)
    return conf


def remove_tabs_js(app: Sphinx, exc: Exception | None) -> None:
    """Remove ``tabs.js`` from ``_static`` after build.

    Workaround for ``sphinx-inline-tabs#18``. The extension ships a
    ``tabs.js`` that conflicts with SPA navigation.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.
    exc : Exception | None
        Build exception, if any.
    """
    if app.builder.format == "html" and not exc:
        tabs_js = pathlib.Path(app.builder.outdir) / "_static" / "tabs.js"
        with contextlib.suppress(FileNotFoundError):
            tabs_js.unlink()


def setup(app: Sphinx) -> None:
    """Configure Sphinx app hooks for gp-sphinx workarounds.

    Registers the bundled ``spa-nav.js`` script and connects the
    ``remove_tabs_js`` post-build hook.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.
    """
    app.add_js_file("js/spa-nav.js", loading_method="defer")
    app.connect("build-finished", remove_tabs_js)
