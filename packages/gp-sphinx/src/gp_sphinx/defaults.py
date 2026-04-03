"""Default configuration constants for shared Sphinx documentation platform.

All constants are extracted from the common configuration used across 14+
git-pull project ``docs/conf.py`` files. These serve as the single source
of truth for shared extensions, theme options, MyST config, and font config.

Examples
--------
>>> from gp_sphinx.defaults import DEFAULT_EXTENSIONS
>>> "myst_parser" in DEFAULT_EXTENSIONS
True

>>> from gp_sphinx.defaults import DEFAULT_MYST_EXTENSIONS
>>> "colon_fence" in DEFAULT_MYST_EXTENSIONS
True
"""

from __future__ import annotations

import typing as t

FooterIconDict = t.TypedDict(
    "FooterIconDict",
    {"name": str, "url": str, "html": str, "class": str},
)
"""A footer icon entry for Furo's ``footer_icons`` theme option."""


class FuroThemeOptions(t.TypedDict, total=False):
    """Typed subset of Furo theme options used by gp-sphinx.

    All keys are optional — pass only what you want to override.
    """

    footer_icons: list[FooterIconDict]
    source_repository: str
    source_branch: str
    source_directory: str
    light_logo: str
    dark_logo: str
    mask_icon: str


class _FontConfigRequired(t.TypedDict):
    family: str
    package: str
    version: str
    weights: list[int]
    styles: list[str]


class FontConfig(_FontConfigRequired, total=False):
    """A single font family configuration entry for sphinx-fonts.

    Required keys: ``family``, ``package``, ``version``, ``weights``, ``styles``.
    Optional key: ``subset`` (defaults to ``"latin"`` when omitted).
    """

    subset: str


GITHUB_SVG_ICON: str = (
    '<svg stroke="currentColor" fill="currentColor" stroke-width="0"'
    ' viewBox="0 0 16 16">'
    '<path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29'
    " 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01"
    ".37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52"
    "-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52"
    ".28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82"
    "-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32"
    "-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1"
    ".16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65"
    " 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46"
    '.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>'
    "</svg>"
)
"""SVG markup for the GitHub icon used in footer links."""

DEFAULT_EXTENSIONS: list[str] = [
    "sphinx.ext.autodoc",
    "sphinx_fonts",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
    "sphinxext.opengraph",
    "sphinxext.rediraffe",
    "sphinx_design",
    "myst_parser",
    "linkify_issues",
]
"""Shared Sphinx extension list used across all git-pull projects.

Examples
--------
>>> len(DEFAULT_EXTENSIONS)
13

>>> DEFAULT_EXTENSIONS[0]
'sphinx.ext.autodoc'
"""

DEFAULT_THEME: str = "sphinx-gptheme"
"""Default Sphinx HTML theme (Furo child theme bundled in this package)."""

DEFAULT_THEME_OPTIONS: FuroThemeOptions = {
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "",
            "html": GITHUB_SVG_ICON,
            "class": "",
        },
    ],
    "source_repository": "",
    "source_branch": "master",
    "source_directory": "docs/",
}
"""Default Furo theme options.

The ``source_repository`` and footer icon ``url`` are set per-project
by :func:`~gp_sphinx.config.merge_sphinx_config`.

Examples
--------
>>> DEFAULT_THEME_OPTIONS["source_branch"]
'master'

>>> DEFAULT_THEME_OPTIONS["source_directory"]
'docs/'
"""

DEFAULT_MYST_HEADING_ANCHORS: int = 4
"""Default heading anchor depth for MyST parser."""

DEFAULT_MYST_EXTENSIONS: list[str] = [
    "colon_fence",
    "substitution",
    "replacements",
    "strikethrough",
    "linkify",
]
"""Default MyST parser extensions.

Examples
--------
>>> len(DEFAULT_MYST_EXTENSIONS)
5
"""

DEFAULT_SOURCE_SUFFIX: dict[str, str] = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
"""Default source suffix mapping for Sphinx.

Examples
--------
>>> DEFAULT_SOURCE_SUFFIX[".md"]
'markdown'
"""

DEFAULT_HTML_STATIC_PATH: list[str] = ["_static"]
"""Default path(s) to project-specific static files (CSS, images, JS).

Resolved relative to the docs source directory (``docs/_static/``).

Examples
--------
>>> DEFAULT_HTML_STATIC_PATH
['_static']
"""

DEFAULT_TEMPLATES_PATH: list[str] = ["_templates"]
"""Default path(s) to Jinja2 template overrides.

Resolved relative to the docs source directory (``docs/_templates/``).

Examples
--------
>>> DEFAULT_TEMPLATES_PATH
['_templates']
"""

DEFAULT_PYGMENTS_STYLE: str = "monokai"
"""Default Pygments syntax highlighting style."""

DEFAULT_PYGMENTS_DARK_STYLE: str = "monokai"
"""Default Pygments syntax highlighting style for dark mode."""

DEFAULT_SPHINX_FONTS: list[FontConfig] = [
    {
        "family": "IBM Plex Sans",
        "package": "@fontsource/ibm-plex-sans",
        "version": "5.2.8",
        "weights": [400, 500, 600, 700],
        "styles": ["normal", "italic"],
        "subset": "latin",
    },
    {
        "family": "IBM Plex Mono",
        "package": "@fontsource/ibm-plex-mono",
        "version": "5.2.7",
        "weights": [400],
        "styles": ["normal", "italic"],
        "subset": "latin",
    },
]
"""Default sphinx-fonts configuration for IBM Plex font families.

Examples
--------
>>> len(DEFAULT_SPHINX_FONTS)
2

>>> DEFAULT_SPHINX_FONTS[0]["family"]
'IBM Plex Sans'
"""

DEFAULT_SPHINX_FONT_PRELOAD: list[tuple[str, int, str]] = [
    ("IBM Plex Sans", 400, "normal"),
    ("IBM Plex Sans", 700, "normal"),
    ("IBM Plex Mono", 400, "normal"),
]
"""Font preload hints for critical rendering path.

Examples
--------
>>> len(DEFAULT_SPHINX_FONT_PRELOAD)
3
"""

DEFAULT_SPHINX_FONT_FALLBACKS: list[dict[str, str]] = [
    {
        "family": "IBM Plex Sans Fallback",
        "src": 'local("Arial"), local("Helvetica Neue"), local("Helvetica")',
        "size_adjust": "110.6%",
        "ascent_override": "92.7%",
        "descent_override": "24.9%",
        "line_gap_override": "0%",
    },
    {
        "family": "IBM Plex Mono Fallback",
        "src": 'local("Courier New"), local("Courier")',
        "size_adjust": "100%",
        "ascent_override": "102.5%",
        "descent_override": "27.5%",
        "line_gap_override": "0%",
    },
]
"""Font fallback definitions with metric overrides to minimize CLS.

Examples
--------
>>> len(DEFAULT_SPHINX_FONT_FALLBACKS)
2

>>> DEFAULT_SPHINX_FONT_FALLBACKS[0]["family"]
'IBM Plex Sans Fallback'
"""

DEFAULT_SPHINX_FONT_CSS_VARIABLES: dict[str, str] = {
    "--font-stack": (
        '"IBM Plex Sans", "IBM Plex Sans Fallback",'
        " -apple-system, BlinkMacSystemFont, sans-serif"
    ),
    "--font-stack--monospace": (
        '"IBM Plex Mono", "IBM Plex Mono Fallback",'
        " SFMono-Regular, Menlo, Consolas, monospace"
    ),
    "--font-stack--headings": "var(--font-stack)",
}
"""CSS custom property overrides for Furo font stacks.

Examples
--------
>>> "--font-stack" in DEFAULT_SPHINX_FONT_CSS_VARIABLES
True
"""

DEFAULT_COPYBUTTON_PROMPT_TEXT: str = (
    r">>> |\.\.\. |> |\$ |\# | In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
)
"""Regex pattern for sphinx-copybutton prompt detection."""

DEFAULT_COPYBUTTON_PROMPT_IS_REGEXP: bool = True
"""Whether the copybutton prompt text is a regular expression."""

DEFAULT_COPYBUTTON_REMOVE_PROMPTS: bool = True
"""Whether sphinx-copybutton should strip prompts when copying."""

DEFAULT_AUTODOC_OPTIONS: dict[str, bool | str] = {
    "undoc-members": True,
    "members": True,
    "private-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
"""Default autodoc options for all documented classes/modules.

Examples
--------
>>> DEFAULT_AUTODOC_OPTIONS["member-order"]
'bysource'
"""

DEFAULT_AUTOCLASS_CONTENT: str = "both"
"""Default autodoc autoclass_content setting (show __init__ and class docstring)."""

DEFAULT_AUTODOC_MEMBER_ORDER: str = "bysource"
"""Default autodoc member ordering."""

DEFAULT_AUTODOC_CLASS_SIGNATURE: str = "separated"
"""Display class signature separately from docstring.

Examples
--------
>>> DEFAULT_AUTODOC_CLASS_SIGNATURE
'separated'
"""

DEFAULT_AUTODOC_TYPEHINTS: str = "description"
"""Show type hints in doc body instead of signature.

Examples
--------
>>> DEFAULT_AUTODOC_TYPEHINTS
'description'
"""

DEFAULT_NAPOLEON_GOOGLE_DOCSTRING: bool = True
"""Enable Google-style docstring parsing in napoleon."""

DEFAULT_NAPOLEON_INCLUDE_INIT_WITH_DOC: bool = False
"""Include __init__ docstring in class documentation.

Default is ``False`` to match napoleon's built-in default. Most downstream
projects never set this explicitly, so ``True`` would change rendered output.
"""

DEFAULT_COPYBUTTON_LINE_CONTINUATION_CHARACTER: str = "\\"
"""Line continuation character for sphinx-copybutton."""

DEFAULT_TOC_OBJECT_ENTRIES_SHOW_PARENTS: str = "hide"
"""Hide parent module path in TOC object entries.

Keeps the API reference sidebar clean by showing only the object name
(e.g. ``merge_sphinx_config``) instead of the full dotted path.

Examples
--------
>>> DEFAULT_TOC_OBJECT_ENTRIES_SHOW_PARENTS
'hide'
"""

DEFAULT_SUPPRESS_WARNINGS: list[str] = [
    "sphinx_autodoc_typehints.forward_reference",
]
"""Warnings to suppress by default.

Examples
--------
>>> len(DEFAULT_SUPPRESS_WARNINGS)
1
"""
