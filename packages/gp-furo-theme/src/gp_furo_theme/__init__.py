"""gp-furo-theme — Tailwind-v4-driven port of the Furo Sphinx theme.

Ported from furo 2025.12.19 (b788b8a), MIT (Pradyun Gedam). See LICENSE-FURO at the
package root. Theme name registers as ``gp-furo`` (vs upstream's ``furo``);
the ``__version__`` follows the gp-sphinx workspace lock-step. Jinja
context variables retain their upstream ``furo_*`` names so the ported
templates render byte-equivalently.

Examples
--------
>>> theme_path = get_theme_path()
>>> theme_path.is_dir()
True

>>> (theme_path / "theme.conf").is_file()
True
"""

from __future__ import annotations

import hashlib
import logging
import os
import pathlib
import typing as t
from functools import cache, lru_cache

import sphinx.application
from docutils import nodes
from pygments.formatters import HtmlFormatter
from pygments.style import Style
from pygments.token import Text
from sphinx.builders.dirhtml import DirectoryHTMLBuilder
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment.adapters.toctree import TocTree
from sphinx.errors import ConfigError
from sphinx.highlighting import PygmentsBridge
from sphinx.transforms.post_transforms import SphinxPostTransform

from .navigation import get_navigation_tree

__version__ = "0.0.1a16"

THEME_NAME = "gp-furo"
THEME_PATH = (pathlib.Path(__file__).parent / "theme" / THEME_NAME).resolve()

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# GLOBAL STATE — populated by ``_builder_inited`` and consumed by
# ``_html_page_context`` + ``_overwrite_pygments_css``. Values are Pygments
# style *classes* (subclasses of ``Style``), not instances; that is how
# ``PygmentsBridge.formatter_args["style"]`` stores them, even though
# upstream Furo's typing on this dict is loose.
_KNOWN_STYLES_IN_USE: dict[str, type[Style] | None] = {
    "light": None,
    "dark": None,
}


class WrapTableAndMathInAContainerTransform(SphinxPostTransform):
    """A Sphinx post-transform that wraps `table` and `div.math` in a container `div`.

    This makes it possible to handle these overflowing the content-width, which is
    necessary in a responsive theme.
    """

    formats = ("html",)
    default_priority = 500

    def run(self, **kwargs: t.Any) -> None:
        """Perform the post-transform on `self.document`."""
        get_nodes = (
            self.document.findall  # docutils 0.18+
            if hasattr(self.document, "findall")
            else self.document.traverse  # docutils <= 0.17.x
        )
        for table_node in list(get_nodes(nodes.table)):
            new_node = nodes.container(classes=["table-wrapper"])
            new_node.update_all_atts(table_node)
            table_node.parent.replace(table_node, new_node)
            new_node.append(table_node)

        for math_node in list(get_nodes(nodes.math_block)):
            new_node = nodes.container(classes=["math-wrapper"])
            new_node.update_all_atts(math_node)
            math_node.parent.replace(math_node, new_node)
            new_node.append(math_node)


def has_not_enough_items_to_show_toc(
    builder: StandaloneHTMLBuilder, docname: str
) -> bool:
    """Check if the toc has one or fewer items."""
    assert builder.env

    toctree = TocTree(builder.env).get_toc_for(docname, builder)
    try:
        self_toctree = toctree[0][1]  # type: ignore[index]
    except IndexError:
        val = True
    else:
        # There's only the page's own toctree(s) in there.
        val = all(entry.tagname == "toctree" for entry in self_toctree)
    return val


def get_pygments_style_colors(
    style: type[Style], *, fallbacks: dict[str, str]
) -> dict[str, str]:
    """Get background/foreground colors for given pygments style."""
    background = style.background_color
    text_colors = style.style_for_token(Text)
    foreground = text_colors["color"]

    if not background:
        background = fallbacks["background"]

    foreground = fallbacks["foreground"] if not foreground else f"#{foreground}"

    return {"background": background, "foreground": foreground}


@lru_cache(maxsize=2)
def get_colors_for_codeblocks(
    highlighter: PygmentsBridge, *, fg: str, bg: str
) -> dict[str, str]:
    """Get background/foreground colors for given pygments style."""
    return get_pygments_style_colors(
        highlighter.formatter_args["style"],
        fallbacks={
            "foreground": fg,
            "background": bg,
        },
    )


def _compute_navigation_tree(context: dict[str, t.Any]) -> str:
    # The navigation tree, generated from the sphinx-provided ToC tree.
    if "toctree" in context:
        toctree = context["toctree"]
        toctree_html = toctree(
            collapse=False,
            titles_only=True,
            maxdepth=-1,
            includehidden=True,
        )
    else:
        toctree_html = ""

    return get_navigation_tree(toctree_html)


def _compute_hide_toc(
    context: dict[str, t.Any],
    *,
    builder: StandaloneHTMLBuilder,
    docname: str,
) -> bool:
    # Should the table of contents be hidden?
    file_meta = context.get("meta") or {}
    if "hide-toc" in file_meta:
        return True
    if "toc" not in context:
        return True
    if not context["toc"]:
        return True

    return has_not_enough_items_to_show_toc(builder, docname)


@cache
def _asset_hash(path: str) -> str:
    """Append a `?digest=` to an url based on the file content."""
    full_path = THEME_PATH / "static" / path
    digest = hashlib.sha1(full_path.read_bytes()).hexdigest()

    return f"_static/{path}?digest={digest}"


def _add_asset_hashes(static: list[str], add_digest_to: list[str]) -> None:
    if sphinx.version_info >= (7, 1):
        # https://github.com/sphinx-doc/sphinx/pull/11415 added the relevant
        # functionality to Sphinx, so we don't need to do anything.
        return

    for asset in add_digest_to:
        try:
            index = static.index("_static/" + asset)
        except ValueError as exc:
            msg = (
                "gp-furo-theme is trying to add a digest to an asset that is "
                f"not in the static files: {asset}. Please check conf.py for "
                "overrides of theme-provided assets such as `html_style`."
            )
            raise ConfigError(msg) from exc

        # Make this idempotent
        if "?digest=" in static[index].filename:  # type: ignore[attr-defined]
            continue
        static[index].filename = _asset_hash(asset)  # type: ignore[attr-defined]


def _fix_canonical_url(
    app: sphinx.application.Sphinx, pagename: str, context: dict[str, t.Any]
) -> None:
    """Fix the canonical URL when using the dirhtml builder.

    Sphinx builds a canonical URL if ``html_baseurl`` config is set. However,
    it builds a URL ending with ".html" when using the dirhtml builder, which is
    incorrect. Detect this and generate the correct URL for each page.
    """
    if (
        not app.config.html_baseurl
        or not isinstance(app.builder, DirectoryHTMLBuilder)
        or not context["pageurl"]
        or not context["pageurl"].endswith(".html")
    ):
        return

    target = app.builder.get_target_uri(pagename)
    context["pageurl"] = app.config.html_baseurl + target


def _html_page_context(
    app: sphinx.application.Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, t.Any],
    doctree: t.Any,
) -> None:
    if "css_files" in context:
        # Sphinx 7.1+ handles cache-bust hashing natively, so this is a
        # no-op call (see _add_asset_hashes early-return at line 181).
        # Kept for the < 7.1 compatibility branch; the list reflects
        # what we actually ship — only styles/furo-tw.css since the
        # SCSS pipeline was dropped in step 9.14 of the 2026-04-30 pivot.
        _add_asset_hashes(
            context["css_files"],
            ["styles/furo-tw.css"],
        )
    if "scripts" in context:
        _add_asset_hashes(
            context["scripts"],
            ["scripts/furo.js"],
        )

    _fix_canonical_url(app, pagename, context)

    # Basic constants — preserve upstream Furo's ``furo_*`` keys so the
    # ported Jinja templates render byte-equivalently.
    context["furo_version"] = __version__

    # Values computed from page-level context.
    context["furo_navigation_tree"] = _compute_navigation_tree(context)
    context["furo_hide_toc"] = _compute_hide_toc(
        context,
        builder=t.cast("StandaloneHTMLBuilder", app.builder),
        docname=pagename,
    )

    assert _KNOWN_STYLES_IN_USE["light"]
    assert _KNOWN_STYLES_IN_USE["dark"]
    # Inject information about styles
    context["furo_pygments"] = {
        "light": get_pygments_style_colors(
            _KNOWN_STYLES_IN_USE["light"],
            fallbacks={"foreground": "black", "background": "white"},
        ),
        "dark": get_pygments_style_colors(
            _KNOWN_STYLES_IN_USE["dark"],
            fallbacks={"foreground": "white", "background": "black"},
        ),
    }


def _builder_inited(app: sphinx.application.Sphinx) -> None:
    if "gp_furo_theme" in app.config.extensions:
        # Loading us as both an extension and a theme would re-run setup() and
        # double-register hooks. Match upstream Furo's ConfigError on the
        # equivalent misconfiguration.
        msg = (
            "Did you list 'gp_furo_theme' in the `extensions` in conf.py? "
            "If so, please remove it. gp-furo-theme does not work with "
            "non-HTML builders and specifying it as an `html_theme` is "
            "sufficient."
        )
        raise ConfigError(msg)

    looks_like_html_builder = isinstance(app.builder, StandaloneHTMLBuilder) or (
        app.builder.name in {"html", "dirhtml"}
    )
    if not looks_like_html_builder:
        msg = (
            "gp-furo-theme is being used as an extension in a non-HTML build. "
            "This should not happen."
        )
        raise ConfigError(msg)

    # Our JS file needs to be loaded as soon as possible.
    app.add_js_file("scripts/furo.js", priority=200)

    # NOTE: pre-pivot we also added "styles/furo-extensions.css" via
    # add_css_file (priority=600) for sphinx-design / inline-tabs /
    # copybutton / readthedocs styles.  Step 9.9 bundled all of those
    # into the main entry (web/src/styles/components/extensions.css ->
    # imported by index.css -> compiles into furo-tw.css), so the
    # secondary stylesheet is no longer needed.

    builder = app.builder
    assert (
        builder.highlighter is not None  # type: ignore[attr-defined]
    ), "there should be a default style known to Sphinx"
    assert (
        builder.dark_highlighter is None  # type: ignore[attr-defined]
    ), "this shouldn't be a dark style known to Sphinx"
    update_known_styles_state(app)

    def _update_default(key: str, *, new_default: t.Any) -> None:
        try:
            conf_py_settings = app.config._raw_config
        except AttributeError:
            pass  # Sphinx's config has changed.
        else:
            if key not in conf_py_settings:
                app.config._raw_config.setdefault(key, new_default)

    # Change the default permalinks icon
    _update_default("html_permalinks_icon", new_default="#")


def update_known_styles_state(app: sphinx.application.Sphinx) -> None:
    """Update a global store of known styles of this application."""
    global _KNOWN_STYLES_IN_USE

    _KNOWN_STYLES_IN_USE = {
        "light": _get_light_style(app),
        "dark": _get_dark_style(app),
    }


def _get_light_style(app: sphinx.application.Sphinx) -> type[Style]:
    return t.cast(
        "type[Style]",
        app.builder.highlighter.formatter_args["style"],  # type: ignore[attr-defined]
    )


def _get_dark_style(app: sphinx.application.Sphinx) -> type[Style]:
    dark_style = app.config.pygments_dark_style
    return t.cast(
        "type[Style]",
        PygmentsBridge("html", dark_style).formatter_args["style"],
    )


def _get_styles(formatter: HtmlFormatter[str], *, prefix: str) -> t.Iterator[str]:
    """Get styles out of a formatter, where everything has the correct prefix."""
    for line in formatter.get_linenos_style_defs():  # type: ignore[no-untyped-call]
        yield f"{prefix} {line}"
    yield from formatter.get_background_style_defs(prefix)  # type: ignore[no-untyped-call]
    yield from formatter.get_token_style_defs(prefix)  # type: ignore[no-untyped-call]


def get_pygments_stylesheet() -> str:
    """Generate the theme-specific pygments.css.

    There is no way to tell Sphinx how the theme handles dark mode at this time,
    so we generate a stylesheet that supports both light and dark via
    ``body[data-theme]`` and ``prefers-color-scheme``.
    """
    light_style = _KNOWN_STYLES_IN_USE["light"]
    dark_style = _KNOWN_STYLES_IN_USE["dark"]
    assert light_style is not None, "_builder_inited has not run"
    assert dark_style is not None, "_builder_inited has not run"
    light_formatter = PygmentsBridge.html_formatter(style=light_style)
    dark_formatter = PygmentsBridge.html_formatter(style=dark_style)

    lines: list[str] = []

    lines.extend(_get_styles(light_formatter, prefix=".highlight"))

    lines.append("@media not print {")

    dark_prefix = 'body[data-theme="dark"] .highlight'
    lines.extend(_get_styles(dark_formatter, prefix=dark_prefix))

    not_light_prefix = 'body:not([data-theme="light"]) .highlight'
    lines.append("@media (prefers-color-scheme: dark) {")
    lines.extend(_get_styles(dark_formatter, prefix=not_light_prefix))
    lines.append("}")

    lines.append("}")

    return "\n".join(lines)


# Yup, we overwrite the default pygments.css file, because it can't possibly respect
# the needs of this theme.
def _overwrite_pygments_css(
    app: sphinx.application.Sphinx,
    exception: Exception | None,
) -> None:
    if exception is not None:
        return

    assert app.builder
    pygments_css = pathlib.Path(app.builder.outdir) / "_static" / "pygments.css"
    pygments_css.write_text(get_pygments_stylesheet(), encoding="utf-8")


def get_vite_root() -> pathlib.Path | None:
    """Locate the ``web/`` directory containing ``package.json`` + ``vite.config.ts``.

    Returns the path when running from a workspace checkout (where the
    Vite source files live alongside the Python package), or ``None``
    when running from an installed wheel (the wheel ships pre-built
    static assets but not the SCSS/TS sources).

    Intended for use by ``sphinx-vite-builder`` consumers — set
    ``sphinx_vite_builder_root = gp_furo_theme.get_vite_root()`` in
    ``conf.py`` (or wire it through :func:`gp_sphinx.config.merge_sphinx_config`)
    so the orchestration finds the right ``cwd`` to spawn ``vite`` in.

    Returns
    -------
    pathlib.Path | None
        Absolute path to the ``web/`` directory, or ``None`` if it is
        not present (typical for installed wheels).

    Examples
    --------
    >>> root = get_vite_root()
    >>> root is None or root.is_dir()
    True
    """
    candidate = pathlib.Path(__file__).resolve().parents[2] / "web"
    return candidate if candidate.is_dir() else None


def get_theme_path() -> pathlib.Path:
    """Return the absolute path to the bundled ``gp-furo`` theme directory.

    Returns
    -------
    pathlib.Path
        Directory containing ``theme.conf`` and the ported Jinja templates +
        Vite-built assets.

    Examples
    --------
    >>> theme_path = get_theme_path()
    >>> (theme_path / "theme.conf").exists()
    True
    """
    return THEME_PATH


def setup(app: sphinx.application.Sphinx) -> dict[str, bool | str]:
    """Register the ``gp-furo`` theme with Sphinx.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    dict[str, bool | str]
        Extension metadata: ``parallel_read_safe`` and
        ``parallel_write_safe`` are both ``True`` (matching upstream Furo's
        guarantees), and ``version`` reports the package version.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.themes: list[tuple[str, pathlib.Path]] = []
    ...         self.post_transforms: list[type] = []
    ...         self.events: list[str] = []
    ...         self.config_values: list[str] = []
    ...     def require_sphinx(self, version: str) -> None:
    ...         pass
    ...     def add_config_value(self, name: str, **kwargs: object) -> None:
    ...         self.config_values.append(name)
    ...     def add_html_theme(self, name: str, theme_path: pathlib.Path) -> None:
    ...         self.themes.append((name, theme_path))
    ...     def add_post_transform(self, transform: type) -> None:
    ...         self.post_transforms.append(transform)
    ...     def connect(self, event: str, callback: object) -> None:
    ...         self.events.append(event)
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> fake.themes[0][0]
    'gp-furo'
    >>> "pygments_dark_style" in fake.config_values
    True
    >>> sorted(fake.events)
    ['build-finished', 'builder-inited', 'html-page-context']
    >>> metadata["parallel_read_safe"]
    True
    """
    app.require_sphinx("8.1")

    app.add_config_value(
        "pygments_dark_style", default="native", rebuild="env", types=[str]
    )

    app.add_html_theme(THEME_NAME, str(THEME_PATH))

    app.add_post_transform(WrapTableAndMathInAContainerTransform)

    app.connect("html-page-context", _html_page_context)
    app.connect("builder-inited", _builder_inited)
    app.connect("build-finished", _overwrite_pygments_css)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": __version__,
    }
