"""Sphinx extension for self-hosted fonts via Fontsource CDN.

Downloads font files at build time, caches them locally, and passes
structured font data to the template context for inline @font-face CSS.

Examples
--------
>>> from sphinx_fonts import _cache_dir

>>> _cache_dir().name
'sphinx-fonts'
"""

from __future__ import annotations

import logging
import pathlib
import shutil
import typing as t
import urllib.error
import urllib.request

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
__version__ = "0.0.1a1"

CDN_TEMPLATE = (
    "https://cdn.jsdelivr.net/npm/{package}@{version}"
    "/files/{font_id}-{subset}-{weight}-{style}.woff2"
)


class SetupDict(t.TypedDict):
    """Return type for Sphinx extension setup()."""

    version: str
    parallel_read_safe: bool
    parallel_write_safe: bool


class _FontConfigRequired(t.TypedDict):
    family: str
    package: str
    version: str
    weights: list[int]
    styles: list[str]


class FontConfig(_FontConfigRequired, total=False):
    """A single font family configuration entry.

    Required keys: ``family``, ``package``, ``version``, ``weights``, ``styles``.
    Optional key: ``subset`` (defaults to ``"latin"`` when omitted).
    """

    subset: str


def _cache_dir() -> pathlib.Path:
    """Return the local font cache directory.

    Returns
    -------
    pathlib.Path
        Path to ``~/.cache/sphinx-fonts``.

    Examples
    --------
    >>> _cache_dir().name
    'sphinx-fonts'
    """
    return pathlib.Path.home() / ".cache" / "sphinx-fonts"


def _cdn_url(
    package: str,
    version: str,
    font_id: str,
    subset: str,
    weight: int,
    style: str,
) -> str:
    """Build a Fontsource CDN URL for a specific font variant.

    Parameters
    ----------
    package : str
        Fontsource npm package name (e.g., ``@fontsource/ibm-plex-sans``).
    version : str
        Package version.
    font_id : str
        Font identifier (last segment of package name).
    subset : str
        Unicode subset (e.g., ``latin``).
    weight : int
        Font weight (e.g., 400, 700).
    style : str
        Font style (e.g., ``normal``, ``italic``).

    Returns
    -------
    str
        Full CDN URL.

    Examples
    --------
    >>> url = _cdn_url(
    ...     "@fontsource/ibm-plex-sans", "5.2.8",
    ...     "ibm-plex-sans", "latin", 400, "normal",
    ... )
    >>> "ibm-plex-sans-latin-400-normal.woff2" in url
    True
    """
    return CDN_TEMPLATE.format(
        package=package,
        version=version,
        font_id=font_id,
        subset=subset,
        weight=weight,
        style=style,
    )


def _download_font(url: str, dest: pathlib.Path) -> bool:
    """Download a font file from the CDN, using local cache.

    Parameters
    ----------
    url : str
        URL to download from.
    dest : pathlib.Path
        Local path to write the file to.

    Returns
    -------
    bool
        True if the file is available (downloaded or cached).
    """
    if dest.exists():
        logger.debug("font cached: %s", dest.name)
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        logger.info("downloaded font: %s", dest.name)
    except (urllib.error.URLError, OSError):
        if dest.exists():
            dest.unlink()
        logger.warning("failed to download font: %s", url)
        return False
    return True


def _on_builder_inited(app: Sphinx) -> None:
    """Download fonts and prepare template context data on builder init."""
    if app.builder.format != "html":
        return

    fonts: list[FontConfig] = app.config.sphinx_fonts
    variables: dict[str, str] = app.config.sphinx_font_css_variables
    if not fonts:
        return

    cache = _cache_dir()
    static_dir = pathlib.Path(app.outdir) / "_static"
    fonts_dir = static_dir / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    font_faces: list[dict[str, str]] = []
    for font in fonts:
        font_id = font["package"].split("/")[-1]
        version = font["version"]
        package = font["package"]
        subset = font.get("subset", "latin")
        for weight in font["weights"]:
            for style in font["styles"]:
                filename = f"{font_id}-{subset}-{weight}-{style}.woff2"
                cached = cache / filename
                url = _cdn_url(package, version, font_id, subset, weight, style)
                if _download_font(url, cached):
                    shutil.copy2(cached, fonts_dir / filename)
                    font_faces.append(
                        {
                            "family": font["family"],
                            "style": style,
                            "weight": str(weight),
                            "filename": filename,
                        }
                    )

    preload_hrefs: list[str] = []
    preload_specs: list[tuple[str, int, str]] = app.config.sphinx_font_preload
    for family_name, weight, style in preload_specs:
        for font in fonts:
            if font["family"] == family_name:
                font_id = font["package"].split("/")[-1]
                subset = font.get("subset", "latin")
                filename = f"{font_id}-{subset}-{weight}-{style}.woff2"
                preload_hrefs.append(filename)
                break

    fallbacks: list[dict[str, str]] = app.config.sphinx_font_fallbacks

    app._font_preload_hrefs = preload_hrefs  # type: ignore[attr-defined]
    app._font_faces = font_faces  # type: ignore[attr-defined]
    app._font_fallbacks = fallbacks  # type: ignore[attr-defined]
    app._font_css_variables = variables  # type: ignore[attr-defined]


def _on_html_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, t.Any],
    doctree: t.Any,
) -> None:
    """Inject font data into Jinja2 template context."""
    context["font_preload_hrefs"] = getattr(app, "_font_preload_hrefs", [])
    context["font_faces"] = getattr(app, "_font_faces", [])
    context["font_fallbacks"] = getattr(app, "_font_fallbacks", [])
    context["font_css_variables"] = getattr(app, "_font_css_variables", {})


def setup(app: Sphinx) -> SetupDict:
    """Register config values, events, and return extension metadata.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    SetupDict
        Extension metadata.
    """
    app.add_config_value(
        "sphinx_fonts",
        [],
        "html",
        description="Font family dicts (family, package, version, weights, styles).",
    )
    app.add_config_value(
        "sphinx_font_fallbacks",
        [],
        "html",
        description="Fallback @font-face declarations with metric overrides for CLS.",
    )
    app.add_config_value(
        "sphinx_font_css_variables",
        {},
        "html",
        description="CSS custom properties for Furo font stacks (e.g. --font-stack)",
    )
    app.add_config_value(
        "sphinx_font_preload",
        [],
        "html",
        description="Critical font variants to preload (family, weight, style).",
    )
    app.connect("builder-inited", _on_builder_inited)
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
