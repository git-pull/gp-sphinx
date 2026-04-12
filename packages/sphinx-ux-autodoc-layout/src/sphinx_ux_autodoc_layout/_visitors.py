"""HTML visitors for autodoc layout nodes.

The extension keeps Sphinx's outer ``dl / dt / dd`` shell, then renders
explicit API subcomponents inside those nodes.

Examples
--------
>>> callable(visit_api_component)
True
>>> callable(visit_api_permalink)
True
>>> callable(visit_desc_signature_html)
True
"""

from __future__ import annotations

import html
import typing as t

from docutils import nodes
from sphinx.locale import _
from sphinx.writers.html5 import HTML5Translator as SphinxHTML5Translator

if t.TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator

_LEGACY_SECTION_COMPONENTS: dict[str, str] = {
    "narrative": "api-description",
    "fields": "api-parameters",
    "members": "api-footer",
}


def _html_attrs(node: nodes.Element) -> dict[str, str]:
    """Return sanitized HTML attributes stored on a custom node."""
    attrs: t.Any = node.get("html_attrs", {})
    return {str(key): str(value) for key, value in attrs.items()}


def visit_api_region(self: HTML5Translator, node: nodes.Element) -> None:
    """Open a legacy region wrapper ``<div>``."""
    kind = node.get("kind", "narrative")
    component = _LEGACY_SECTION_COMPONENTS.get(kind)
    classes = ["api-region", f"api-region--{kind}"]
    if component is not None:
        classes.insert(0, component)
    self.body.append(self.starttag(node, "div", "", classes=classes))


def depart_api_region(self: HTML5Translator, node: nodes.Element) -> None:
    """Close the legacy region wrapper."""
    self.body.append("</div>")


def visit_api_component(self: HTML5Translator, node: nodes.Element) -> None:
    """Open an API component wrapper element."""
    tag = node.get("tag", "div")
    attrs = _html_attrs(node)
    ids = [attrs.pop("id")] if "id" in attrs else []
    starttag = t.cast(t.Any, self).starttag
    self.body.append(starttag(node, tag, "", ids=ids, **attrs))


def depart_api_component(self: HTML5Translator, node: nodes.Element) -> None:
    """Close an API component wrapper element."""
    self.body.append(f"</{node.get('tag', 'div')}>")


def visit_api_permalink(self: HTML5Translator, node: nodes.Element) -> None:
    """Open a managed permalink anchor."""
    self.body.append(
        self.starttag(
            node,
            "a",
            "",
            href=node.get("href", "#"),
            title=node.get("title", _("Link to this definition")),
        )
    )
    self.body.append(node.get("text", self.config.html_permalinks_icon))


def depart_api_permalink(self: HTML5Translator, node: nodes.Element) -> None:
    """Close the managed permalink anchor."""
    self.body.append("</a>")


def visit_api_fold(self: HTML5Translator, node: nodes.Element) -> None:
    """Open a ``<details>`` disclosure element."""
    summary = node.get("summary", "")
    kind = node.get("kind", "")
    open_attr = " open" if node.get("open", False) else ""
    self.body.append(
        f'<details class="api-fold api-fold--{kind}"{open_attr}>'
        f'<summary class="api-fold-summary">{html.escape(summary)}</summary>'
    )


def depart_api_fold(self: HTML5Translator, node: nodes.Element) -> None:
    """Close the ``</details>`` element."""
    self.body.append("</details>")


def visit_api_sig_fold(self: HTML5Translator, node: nodes.Element) -> None:
    """Open the custom signature disclosure toggle button."""
    first = html.escape(node.get("first_param", ""))
    panel_id = node.get("panel_id", "")
    preview = first if first else "..."
    starttag = t.cast(t.Any, self).starttag
    self.body.append(
        starttag(
            node,
            "button",
            "",
            type="button",
            classes=["api-signature-toggle", "api-sig-toggle"],
            **{
                "aria-controls": panel_id,
                "aria-expanded": "false",
            },
        )
    )
    self.body.append('<span class="sig-paren">(</span>')
    self.body.append(
        f'<span class="api-signature-preview api-sig-preview">{preview}, [...]</span>'
    )
    self.body.append('<span class="sig-paren">)</span>')


def depart_api_sig_fold(self: HTML5Translator, node: nodes.Element) -> None:
    """Close the custom signature disclosure toggle button."""
    self.body.append("</button>")


def visit_desc_signature_html(self: HTML5Translator, node: nodes.Element) -> None:
    """Render managed desc signatures without Sphinx's default permalink."""
    if not node.get("api_managed", False):
        SphinxHTML5Translator.visit_desc_signature(self, node)
        return

    attrs = _html_attrs(node)
    starttag = t.cast(t.Any, self).starttag
    self.body.append(starttag(node, "dt", **attrs))
    self.protect_literal_text += 1


def depart_desc_signature_html(self: HTML5Translator, node: nodes.Element) -> None:
    """Close managed desc signatures while skipping Sphinx's auto permalink."""
    if not node.get("api_managed", False):
        SphinxHTML5Translator.depart_desc_signature(self, node)
        return
    self.protect_literal_text -= 1
    self.body.append("</dt>\n")


def passthrough_visit(self: t.Any, node: nodes.Element) -> None:
    """No-op visit for non-HTML builders.

    Examples
    --------
    >>> passthrough_visit(None, None)
    """


def passthrough_depart(self: t.Any, node: nodes.Element) -> None:
    """No-op depart for non-HTML builders.

    Examples
    --------
    >>> passthrough_depart(None, None)
    """
