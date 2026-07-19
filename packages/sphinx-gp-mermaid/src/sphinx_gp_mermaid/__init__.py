"""Build-time mermaid rendering for Sphinx, producing inline SVG.

Renders fenced ``mermaid`` blocks to inline ``<svg>`` at build time via
``mmdc`` (`@mermaid-js/mermaid-cli`_), so diagrams paint with the page: there
is no client-side mermaid runtime, no asynchronous pop-in, and no layout
shift. The finished SVG ships as regular page DOM, so it also rides through
gp-sphinx's SPA navigation with zero re-initialisation.

Each diagram is rendered twice — a light and a dark variant — and both are
inlined, toggled by CSS on ``body[data-theme]`` (see
``_static/css/sphinx_gp_mermaid.css``). Mermaid bakes literal colours into an
id-scoped, ``!important`` ``<style>`` block, so a single SVG cannot be
re-themed by external CSS; shipping both variants is the zero-JavaScript path
that stays correct across theme switches and SPA swaps.

Authoring uses the ``{mermaid}`` directive via MyST colon or brace fences;
plain ``` ```mermaid ``` fences route here too when
``myst_fence_as_directive = ["mermaid"]`` is set::

    :::{mermaid}
    :caption: How it flows.
    :responsive: fit

    flowchart LR
        a --> b
    :::

Examples
--------
>>> from sphinx_gp_mermaid import setup
>>> callable(setup)
True

.. _`@mermaid-js/mermaid-cli`: https://github.com/mermaid-js/mermaid-cli
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import typing as t

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata
    from sphinx.writers.html5 import HTML5Translator
    from sphinx.writers.latex import LaTeXTranslator
    from sphinx.writers.manpage import ManualPageTranslator
    from sphinx.writers.texinfo import TexinfoTranslator
    from sphinx.writers.text import TextTranslator

__all__ = [
    "MermaidDirective",
    "MermaidError",
    "MermaidRenderError",
    "MermaidRendererMissing",
    "mermaid_inline",
    "setup",
]

logger = getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a35"

#: Bump to invalidate the on-disk render cache when render arguments change.
_RENDER_VERSION = "mmdc11-furo-svg-v4"

#: Logical names for the two inlined variants (cache key, SVG id, CSS class).
_THEME_LIGHT = "light"
_THEME_DARK = "dark"

#: Author-facing responsive policies. ``fit`` scales the SVG down to the
#: available column; ``preserve`` keeps its intrinsic width and lets the figure
#: scroll horizontally.
_RESPONSIVE_FIT = "fit"
_RESPONSIVE_PRESERVE = "preserve"
_RESPONSIVE_POLICIES = (_RESPONSIVE_FIT, _RESPONSIVE_PRESERVE)

#: System font stack matching gp-furo's body font (gp-furo-tokens --font-stack).
_FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"
)

#: mermaid ``base``-theme variables mapped to gp-furo's light/dark colour tokens
#: (gp-furo-tokens: light.ts / dark.ts) so diagrams match the site palette.
#: Colour does not affect layout, so both variants share geometry.
_PALETTES: dict[str, dict[str, str]] = {
    _THEME_LIGHT: {
        "primaryColor": "#f8f9fb",
        "primaryBorderColor": "#0a4bff",
        "primaryTextColor": "#000000",
        "lineColor": "#6b6f76",
        "textColor": "#000000",
        "background": "#ffffff",
        "edgeLabelBackground": "#f8f9fb",
        "secondaryColor": "#ffffff",
        "tertiaryColor": "#f8f9fb",
        "fontFamily": _FONT_STACK,
    },
    _THEME_DARK: {
        "primaryColor": "#1a1c1e",
        "primaryBorderColor": "#3d94ff",
        "primaryTextColor": "#cfd0d0",
        "lineColor": "#81868d",
        "textColor": "#cfd0d0",
        "background": "#131416",
        "edgeLabelBackground": "#1a1c1e",
        "secondaryColor": "#131416",
        "tertiaryColor": "#1a1c1e",
        "fontFamily": _FONT_STACK,
    },
}

#: Monospace stack matching gp-furo's ``--font-stack--monospace``.
_MONO_STACK = "'SFMono-Regular', Menlo, Consolas, Monaco, 'Liberation Mono', monospace"


def _theme_css(theme: str) -> str:
    """Return the CSS injected into a rendered SVG for the given theme.

    Renders ``:::cmd`` nodes in a monospace font so commands read as code;
    centres each node label in its box; and collapses mermaid's three stacked
    edge-label backgrounds into one padded chip in the theme's label colour.

    Centering uses ``display: table`` + ``margin: 0 auto`` rather than a width
    or flex rule: the build's headless Chrome may render the font at a different
    width than the visitor's browser, leaving the shrink-to-fit ``table-cell``
    narrower than the measured box (so it falls left), but anything that
    *resizes* the label corrupts mermaid's build-time measurement pass. A table
    with auto margins re-centres without changing the measured size.
    ``white-space: normal`` lets a padded edge label wrap instead of
    overflowing its measured box.

    >>> "monospace" in _theme_css("light")
    True
    >>> "#f8f9fb" in _theme_css("light")
    True
    """
    bg = _PALETTES[theme]["edgeLabelBackground"]
    return (
        ".cmd .nodeLabel { font-family: " + _MONO_STACK + " !important; }"
        " .nodeLabel, .nodeLabel p { text-align: center !important; }"
        " .node foreignObject > div {"
        " display: table !important;"
        " margin: 0 auto !important;"
        " }"
        " .edgeLabel rect { opacity: 0 !important; }"
        " .labelBkg { background: transparent !important; }"
        " .edgeLabel { background: transparent !important; }"
        " .edgeLabel p {"
        " background: " + bg + " !important;"
        " padding: 3px 10px !important;"
        " border-radius: 4px !important;"
        " white-space: normal !important;"
        " }"
    )


#: mermaid hardcodes this id on every rendered SVG and scopes its CSS and
#: arrowhead markers to it; it is rewritten per diagram+theme to avoid
#: duplicate-id collisions when both variants are inlined on one page.
_MERMAID_DEFAULT_ID = "my-svg"

#: The id token in id-token position only: attribute values (``id="my-svg"``,
#: ``id="my-svg_marker"``), ``#``-refs (CSS selectors, ``url(#my-svg_...)``),
#: and mermaid's a11y ids (``chart-desc-my-svg``/``chart-title-my-svg``) —
#: never visible label text.
_MERMAID_ID_TOKEN_RE = re.compile(
    r'(["#]|chart-(?:desc|title)-)' + re.escape(_MERMAID_DEFAULT_ID),
)

# Width/height are the 3rd/4th viewBox numbers of the ROOT <svg> tag. Anchoring
# to ``<svg ... >`` (no ``>`` in between) avoids matching an inner element's
# viewBox, and the min-x/min-y may be negative (block diagrams use e.g.
# ``viewBox="-5 -97 148 194"``).
_VIEWBOX_RE = re.compile(r'<svg\b[^>]*?\bviewBox="-?[\d.]+ -?[\d.]+ ([\d.]+) ([\d.]+)"')

#: Builder attribute guarding the "renderer missing/failed" warning so it
#: fires once per writer process, not per node (parallel-write safe, unlike a
#: module global).
_WARNED_ATTR = "_sphinx_gp_mermaid_warned"

#: Translator attribute counting digest occurrences per page, so repeats of
#: the same diagram source get distinct SVG ids (the translator is created
#: fresh per document, making the counts naturally per-page).
_ID_COUNTS_ATTR = "_sphinx_gp_mermaid_id_counts"


class MermaidError(Exception):
    """Base class for build-time mermaid rendering failures."""


class MermaidRendererMissing(MermaidError):
    """``mmdc`` could not be located in the docs toolchain."""


class MermaidRenderError(MermaidError):
    """``mmdc`` ran but failed to produce an SVG."""


class mermaid_inline(nodes.General, nodes.Element):
    """Doctree node carrying mermaid source until the HTML write phase."""


def _diagram_digest(
    source: str,
    theme: str,
    *,
    version: str = _RENDER_VERSION,
    extra: str = "",
) -> str:
    """Return a stable content hash that keys the render cache.

    The hash covers the render version, the theme, the source, and ``extra``
    (the full mermaid config JSON) — so light and dark variants cache
    separately and any styling change, not just a source change, busts the
    cache.

    >>> a = _diagram_digest("flowchart LR a-->b", "default")
    >>> a == _diagram_digest("flowchart LR a-->b", "default")
    True
    >>> a != _diagram_digest("flowchart LR a-->b", "dark")
    True
    >>> a != _diagram_digest("flowchart LR a-->b", "default", extra="{}")
    True
    >>> len(a)
    40
    """
    payload = f"{version}\x00{theme}\x00{extra}\x00{source}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _svg_element_id(digest: str, theme: str, *, occurrence: int = 0) -> str:
    """Return a per-diagram, per-theme SVG id replacing mermaid's ``my-svg``.

    ``occurrence`` disambiguates repeats of the same source on one page;
    the first occurrence keeps the unsuffixed id.

    >>> _svg_element_id("abcdef1234567890", "light")
    'mermaid-abcdef123456-light'
    >>> _svg_element_id("abcdef1234567890", "light", occurrence=2)
    'mermaid-abcdef123456-2-light'
    """
    suffix = f"-{occurrence}" if occurrence else ""
    return f"mermaid-{digest[:12]}{suffix}-{theme}"


def _svg_dimensions(svg: str) -> tuple[str, str] | None:
    """Return root SVG ``viewBox`` width and height, if available.

    >>> _svg_dimensions('<svg viewBox="0 0 120 40"></svg>')
    ('120', '40')
    >>> _svg_dimensions('<svg viewBox="-5 -97 148 194"></svg>')
    ('148', '194')
    >>> _svg_dimensions("<svg></svg>") is None
    True
    """
    match = _VIEWBOX_RE.search(svg)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _normalize_svg(svg: str, *, svg_id: str) -> str:
    """Make an ``mmdc`` SVG safe to inline: unique id, explicit size, no max-width.

    Three fixes are applied to mermaid's default output:

    1. The hardcoded ``my-svg`` id token — used by the id attribute, the
       id-scoped ``<style>`` rules, ``url(#my-svg_...)`` marker references,
       and ``chart-desc-``/``chart-title-`` a11y ids — is rewritten to
       ``svg_id`` so two variants never collide on duplicate ids. Only
       id-token positions are rewritten; label text is left intact.
    2. The root ``width="100%"`` (mermaid emits no ``height``) is replaced with
       explicit ``width``/``height`` taken from the ``viewBox``, so the browser
       reserves the diagram's box in the first layout pass — before any script.
    3. The inline ``max-width: NNpx`` is stripped so the stylesheet, not
       mermaid's inline style, controls the figure's responsive policy.

    >>> svg = (
    ...     '<svg id="my-svg" width="100%" '
    ...     'style="max-width: 120px; background-color: transparent;" '
    ...     'viewBox="0 0 120 40"><style>#my-svg{fill:#333;}</style>'
    ...     '<g marker-end="url(#my-svg_end)"/></svg>'
    ... )
    >>> out = _normalize_svg(svg, svg_id="mermaid-abc-light")
    >>> "my-svg" in out
    False
    >>> 'width="120"' in out and 'height="40"' in out
    True
    >>> "max-width" in out
    False
    >>> 'id="mermaid-abc-light"' in out and "url(#mermaid-abc-light_end)" in out
    True

    Block diagrams use a negative viewBox origin and carry inner viewBoxes;
    the root's width/height (3rd/4th numbers) win, not an inner ``0 0 10 10``:

    >>> block = (
    ...     '<svg id="my-svg" width="100%" viewBox="-5 -97 148 194">'
    ...     '<marker viewBox="0 0 10 10"/></svg>'
    ... )
    >>> out = _normalize_svg(block, svg_id="x")
    >>> 'width="148"' in out and 'height="194"' in out
    True

    Label text containing the literal token survives untouched:

    >>> label = (
    ...     '<svg id="my-svg" width="100%" viewBox="0 0 10 10">'
    ...     '<p>Deploy my-svg-viewer</p></svg>'
    ... )
    >>> out = _normalize_svg(label, svg_id="x")
    >>> 'id="x"' in out and "Deploy my-svg-viewer" in out
    True
    """
    svg = _MERMAID_ID_TOKEN_RE.sub(rf"\g<1>{svg_id}", svg)
    dimensions = _svg_dimensions(svg)
    if dimensions is not None:
        width, height = dimensions
        svg = re.sub(r'(<svg\b[^>]*?)\s+width="[^"]*"', r"\1", svg, count=1)
        svg = re.sub(r"<svg\b", f'<svg width="{width}" height="{height}"', svg, count=1)
    return re.sub(r"\s*max-width:\s*[\d.]+px;?", "", svg, count=1)


def _responsive_policy(argument: str) -> str:
    """Validate a Mermaid diagram responsive policy.

    >>> _responsive_policy("fit")
    'fit'
    >>> _responsive_policy("PRESERVE")
    'preserve'
    >>> _responsive_policy("auto")
    Traceback (most recent call last):
    ...
    ValueError: "auto" unknown; choose from "fit", or "preserve"
    """
    return directives.choice(argument, _RESPONSIVE_POLICIES)


class MermaidDirective(SphinxDirective):
    """Stash a mermaid fence's source on a node for the write phase to render.

    Options
    -------
    caption : str
        Optional figure caption.
    alt : str
        Accessible label for the rendered figure. Falls back to ``caption``.
    name : str
        Cross-reference target for the figure.
    class : str
        Extra CSS class or classes on the outer ``<figure>``.
    responsive : {"fit", "preserve"}
        ``fit`` scales the SVG down to the column; ``preserve`` keeps the
        intrinsic SVG width and scrolls horizontally when needed.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec: t.ClassVar[dict[str, t.Callable[[str], t.Any]]] = {
        "caption": directives.unchanged,
        "alt": directives.unchanged,
        "name": directives.unchanged,
        "class": directives.class_option,
        "responsive": _responsive_policy,
    }

    def run(self) -> list[nodes.Node]:
        """Return a single :class:`mermaid_inline` node carrying the source."""
        if not self.content:
            warning = self.state.document.reporter.warning(
                "mermaid directive has no content",
                line=self.lineno,
            )
            return [warning]
        node = mermaid_inline()
        node["mermaid_source"] = "\n".join(self.content)
        node["caption"] = self.options.get("caption", "")
        node["alt"] = self.options.get("alt", "")
        node["responsive"] = self.options.get("responsive", _RESPONSIVE_FIT)
        node["classes"].extend(self.options.get("class", []))
        self.add_name(node)
        self.set_source_info(node)
        return [node]


def _chrome_glob(platform: str) -> str:
    """Return the puppeteer-cache glob for Chrome on the given ``sys.platform``.

    Puppeteer lays the binary out per platform under ``chrome/<build>/``.

    >>> _chrome_glob("linux")
    '*/chrome-linux64/chrome'
    >>> _chrome_glob("win32")
    '*/chrome-win64/chrome.exe'
    >>> _chrome_glob("darwin").startswith("*/chrome-mac-")
    True
    """
    if platform.startswith("win"):
        return "*/chrome-win64/chrome.exe"
    if platform == "darwin":
        return (
            "*/chrome-mac-*/Google Chrome for Testing.app"
            "/Contents/MacOS/Google Chrome for Testing"
        )
    return "*/chrome-linux64/chrome"


def _discover_chrome() -> str | None:
    """Return a Chrome installed by ``puppeteer browsers install``, if any.

    Puppeteer's automatic resolution can miss the cached browser (its cache dir
    is computed relative to the install location); pointing ``executablePath`` at
    the discovered binary sidesteps that.
    """
    cache = pathlib.Path.home() / ".cache" / "puppeteer" / "chrome"
    if not cache.is_dir():
        return None
    candidates = sorted(cache.glob(_chrome_glob(sys.platform)))
    return str(candidates[-1]) if candidates else None


def _resolve_mmdc(app: Sphinx) -> list[str] | None:
    """Locate the ``mmdc`` executable: config, then docs-local, then ``PATH``."""
    configured: str = app.config.mermaid_cmd
    if configured:
        found = shutil.which(configured)
        if found:
            return [found]
        path = pathlib.Path(configured)
        if path.exists():
            return [str(path)]
    local = pathlib.Path(app.confdir) / "node_modules" / ".bin" / "mmdc"
    if local.exists():
        return [str(local)]
    found = shutil.which("mmdc")
    return [found] if found else None


def _puppeteer_config_file(app: Sphinx, tmpdir: pathlib.Path) -> pathlib.Path:
    """Write a puppeteer config (``--no-sandbox`` + resolved Chrome) and return it.

    An explicit ``mermaid_puppeteer_config`` wins; otherwise a minimal
    config is generated, adding ``executablePath`` from
    ``PUPPETEER_EXECUTABLE_PATH`` or a discovered cached Chrome.
    """
    configured: str = app.config.mermaid_puppeteer_config
    if configured:
        return pathlib.Path(configured)
    data: dict[str, t.Any] = {
        "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    }
    executable = os.environ.get("PUPPETEER_EXECUTABLE_PATH") or _discover_chrome()
    if executable:
        data["executablePath"] = executable
    out = tmpdir / "puppeteer.json"
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


def _mermaid_config(theme: str) -> dict[str, t.Any]:
    """Return the mermaid ``-c`` config: base theme + furo palette + themeCSS.

    ``block.padding: 0`` tiles block-beta panes contiguously; other diagram
    types ignore the ``block`` key.

    >>> cfg = _mermaid_config("light")
    >>> cfg["theme"], "themeVariables" in cfg, cfg["block"]["padding"]
    ('base', True, 0)
    """
    return {
        "theme": "base",
        "block": {"padding": 0},
        "themeVariables": _PALETTES[theme],
        "themeCSS": _theme_css(theme),
    }


def _render(app: Sphinx, source: str, config_json: str) -> str:
    """Render ``source`` to an SVG string via ``mmdc`` using ``config_json``."""
    mmdc = _resolve_mmdc(app)
    if mmdc is None:
        msg = (
            "mmdc (@mermaid-js/mermaid-cli) not found; install it in the docs "
            "toolchain or set the mermaid_cmd config value"
        )
        raise MermaidRendererMissing(msg)
    with tempfile.TemporaryDirectory(prefix="sphinx-gp-mermaid-") as td:
        tmpdir = pathlib.Path(td)
        in_file = tmpdir / "diagram.mmd"
        out_file = tmpdir / "diagram.svg"
        config_file = tmpdir / "config.json"
        in_file.write_text(source, encoding="utf-8")
        config_file.write_text(config_json, encoding="utf-8")
        argv = [
            *mmdc,
            "-i",
            str(in_file),
            "-o",
            str(out_file),
            "-b",
            "transparent",
            "-c",
            str(config_file),
            "-p",
            str(_puppeteer_config_file(app, tmpdir)),
        ]
        try:
            subprocess.run(
                argv,
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except OSError as exc:  # mmdc vanished after resolve, or isn't executable
            raise MermaidRendererMissing(str(exc)) from exc
        except subprocess.SubprocessError as exc:
            stderr = getattr(exc, "stderr", "") or ""
            msg = f"mmdc failed: {exc}\n{stderr}"
            raise MermaidRenderError(msg) from exc
        if not out_file.is_file():
            msg = "mmdc produced no SVG output"
            raise MermaidRenderError(msg)
        return out_file.read_text(encoding="utf-8")


def _render_cached(app: Sphinx, source: str, theme: str) -> str:
    """Return a rendered SVG, reading/writing a content-hashed on-disk cache.

    The cache lives outside ``_build`` (under the confdir) so it survives the
    ``rm -rf docs/_build`` that precedes a full build. The write is a
    pid-suffixed temp file moved into place with :meth:`pathlib.Path.replace`,
    so a parallel writer racing on the same digest never reads a torn SVG.
    """
    config_json = json.dumps(_mermaid_config(theme), sort_keys=True)
    digest = _diagram_digest(source, theme, extra=config_json)
    cache_dir = pathlib.Path(app.confdir) / "_mermaid_cache"
    cache_file = cache_dir / f"{digest}.svg"
    if cache_file.is_file():
        return cache_file.read_text(encoding="utf-8")
    svg = _render(app, source, config_json)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = cache_file.with_name(f"{digest}.{os.getpid()}.tmp")
    tmp_file.write_text(svg, encoding="utf-8")
    tmp_file.replace(cache_file)
    return svg


def _warn_render_failure(builder: Builder, node: nodes.Node, exc: MermaidError) -> None:
    """Emit a single build warning when rendering is unavailable or fails.

    The once-only memo lives on the builder (imgmath's pattern), so parallel
    writer processes each warn at most once and a fresh build starts clean.
    """
    if getattr(builder, _WARNED_ATTR, False):
        return
    setattr(builder, _WARNED_ATTR, True)
    logger.warning(
        "mermaid render unavailable; emitting diagram source as text: %s",
        exc,
        location=node,
    )


def html_visit_mermaid_inline(self: HTML5Translator, node: mermaid_inline) -> None:
    """Render the diagram and append dual light/dark inline SVG, then skip."""
    source: str = node["mermaid_source"]
    app = self.builder.app
    ids: list[str] = node.get("ids", [])
    fig_id = f' id="{ids[0]}"' if ids else ""
    try:
        light = _render_cached(app, source, _THEME_LIGHT)
        dark = _render_cached(app, source, _THEME_DARK)
    except MermaidError as exc:
        _warn_render_failure(self.builder, node, exc)
        self.body.append(
            f'<pre class="gp-sphinx-mermaid__fallback"{fig_id}>'
            + html.escape(source)
            + "</pre>",
        )
        raise nodes.SkipNode from None

    digest = _diagram_digest(source, "")
    counts: dict[str, int] = getattr(self, _ID_COUNTS_ATTR, {})
    occurrence = counts.get(digest, 0)
    counts[digest] = occurrence + 1
    setattr(self, _ID_COUNTS_ATTR, counts)
    light = _normalize_svg(
        light,
        svg_id=_svg_element_id(digest, _THEME_LIGHT, occurrence=occurrence),
    )
    dark = _normalize_svg(
        dark,
        svg_id=_svg_element_id(digest, _THEME_DARK, occurrence=occurrence),
    )

    caption: str = node.get("caption", "")
    alt = node.get("alt", "") or caption
    aria = f' aria-label="{html.escape(alt, quote=True)}"' if alt else ""
    responsive: str = node.get("responsive", _RESPONSIVE_FIT)
    attrs = {
        "data-mermaid-responsive": responsive,
    }
    dimensions = _svg_dimensions(light)
    if dimensions is not None:
        width, height = dimensions
        attrs["data-mermaid-width"] = width
        attrs["data-mermaid-height"] = height
    starttag = t.cast("t.Any", self.starttag)

    parts = [
        starttag(
            node,
            "figure",
            "",
            CLASS=f"gp-sphinx-mermaid gp-sphinx-mermaid--{responsive}",
            **attrs,
        ),
        (
            '<div class="gp-sphinx-mermaid__variant '
            f'gp-sphinx-mermaid__variant--theme-light" role="img"{aria}>{light}</div>'
        ),
        (
            '<div class="gp-sphinx-mermaid__variant '
            'gp-sphinx-mermaid__variant--theme-dark" role="img" '
            f'aria-hidden="true">{dark}</div>'
        ),
    ]
    if caption:
        parts.append(f"<figcaption>{html.escape(caption)}</figcaption>")
    parts.append("</figure>")
    self.body.append("".join(parts))
    raise nodes.SkipNode


def _depart_mermaid_inline(self: HTML5Translator, node: mermaid_inline) -> None:
    """No-op; :func:`html_visit_mermaid_inline` raises ``SkipNode``."""


def _diagram_fallback_text(node: mermaid_inline) -> str:
    """Return the alt-text stand-in non-HTML builders emit for a diagram.

    >>> node = mermaid_inline()
    >>> node["alt"] = "session holds windows"
    >>> _diagram_fallback_text(node)
    '[diagram: session holds windows]'
    >>> _diagram_fallback_text(mermaid_inline())
    '[diagram]'
    """
    alt: str = node.get("alt", "") or node.get("caption", "")
    return f"[diagram: {alt}]" if alt else "[diagram]"


def text_visit_mermaid_inline(self: TextTranslator, node: mermaid_inline) -> None:
    """Emit the alt-text stand-in for the text builder, then skip."""
    self.add_text(_diagram_fallback_text(node))
    raise nodes.SkipNode


def man_visit_mermaid_inline(
    self: ManualPageTranslator,
    node: mermaid_inline,
) -> None:
    """Emit the alt-text stand-in for the man builder, then skip."""
    self.body.append(_diagram_fallback_text(node))
    raise nodes.SkipNode


def latex_visit_mermaid_inline(self: LaTeXTranslator, node: mermaid_inline) -> None:
    """Emit the escaped alt-text stand-in for the LaTeX builder, then skip."""
    self.body.append(self.encode(_diagram_fallback_text(node)))
    raise nodes.SkipNode


def texinfo_visit_mermaid_inline(
    self: TexinfoTranslator,
    node: mermaid_inline,
) -> None:
    """Emit the escaped alt-text stand-in for the texinfo builder, then skip."""
    self.body.append(self.escape(_diagram_fallback_text(node)))
    raise nodes.SkipNode


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the directive, node, config values, and stylesheet.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Returns
    -------
    ExtensionMetadata
        Extension metadata with version and parallel-build flags.

    Examples
    --------
    >>> from sphinx_gp_mermaid import setup
    >>> callable(setup)
    True
    """
    app.add_node(
        mermaid_inline,
        html=(html_visit_mermaid_inline, _depart_mermaid_inline),
        text=(text_visit_mermaid_inline, None),
        man=(man_visit_mermaid_inline, None),
        latex=(latex_visit_mermaid_inline, None),
        texinfo=(texinfo_visit_mermaid_inline, None),
    )
    app.add_directive("mermaid", MermaidDirective)
    app.add_config_value("mermaid_cmd", "", "env")
    app.add_config_value("mermaid_puppeteer_config", "", "env")

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    def _exclude_cache_dir(app: Sphinx, config: Config) -> None:
        # The render cache lives under the confdir (outside _build) so it
        # survives clean builds; keep Sphinx from treating it as sources.
        if "_mermaid_cache" not in config.exclude_patterns:
            config.exclude_patterns.append("_mermaid_cache")

    app.connect("config-inited", _exclude_cache_dir)
    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_gp_mermaid.css")

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
