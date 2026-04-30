"""Pygments styles bundled with sphinx-gp-theme.

Defines :class:`GpSphinxLightStyle`, a light syntax-highlighting style derived
from the CodeMirror light palette used by the Microviz design system. The
style is registered through the ``pygments.styles`` entry point declared in
``pyproject.toml``, which makes it discoverable as ``"gp-sphinx-light"`` via
:func:`pygments.styles.get_style_by_name`.

Furo emits a single combined ``pygments.css`` whose unscoped rules apply in
light mode and whose ``body[data-theme="dark"]``-scoped rules apply in dark
mode, so pairing this light style with a dark Pygments style (e.g. ``monokai``)
is enough to render distinct light- and dark-mode code blocks.

Examples
--------
>>> from pygments.styles import get_style_by_name
>>> style = get_style_by_name("gp-sphinx-light")
>>> style.background_color
'#f8fafc'
>>> style.__name__
'GpSphinxLightStyle'
"""

from __future__ import annotations

import typing as t

from pygments import style, token

__all__ = ["GpSphinxLightStyle"]


class GpSphinxLightStyle(style.Style):
    """Light Pygments style mirroring the Microviz CodeMirror light palette.

    The token-to-color mapping follows the OKLCH-derived palette used by the
    CodeMirror editor in ``social-embed`` and ``microviz``: slate-900 text on
    a slate-50 background, with purple keywords, yellow strings, blue numbers,
    orange built-ins, red HTML tags, and slate-500 italic comments.

    Examples
    --------
    >>> GpSphinxLightStyle.name
    'gp-sphinx-light'
    >>> GpSphinxLightStyle.background_color
    '#f8fafc'
    >>> GpSphinxLightStyle.styles[token.Keyword]
    'bold #7c3aed'
    >>> GpSphinxLightStyle.styles[token.String]
    '#ca8a04'
    >>> GpSphinxLightStyle.styles[token.Comment]
    'italic #64748b'
    """

    name = "gp-sphinx-light"

    background_color = "#f8fafc"
    highlight_color = "#dbeafe"
    line_number_color = "#64748b"
    line_number_background_color = "#f1f5f9"
    line_number_special_color = "#0f172a"
    line_number_special_background_color = "#dbeafe"

    styles: t.ClassVar[dict[token._TokenType, str]] = {
        token.Whitespace: "#cbd5e1",
        token.Text: "#0f172a",
        token.Error: "border:#dc2626 #dc2626",
        token.Other: "#0f172a",
        token.Comment: "italic #64748b",
        token.Comment.Hashbang: "italic #64748b",
        token.Comment.Multiline: "italic #64748b",
        token.Comment.Preproc: "noitalic #7c3aed",
        token.Comment.PreprocFile: "noitalic #ca8a04",
        token.Comment.Single: "italic #64748b",
        token.Comment.Special: "italic bold #64748b",
        token.Keyword: "bold #7c3aed",
        token.Keyword.Constant: "bold #ea580c",
        token.Keyword.Declaration: "bold #7c3aed",
        token.Keyword.Namespace: "bold #7c3aed",
        token.Keyword.Pseudo: "nobold #7c3aed",
        token.Keyword.Reserved: "bold #7c3aed",
        token.Keyword.Type: "nobold #a855f7",
        token.Operator: "#0f172a",
        token.Operator.Word: "bold #7c3aed",
        token.Punctuation: "#0f172a",
        token.Name: "#0f172a",
        token.Name.Attribute: "#a855f7",
        token.Name.Builtin: "#ea580c",
        token.Name.Builtin.Pseudo: "#ea580c",
        token.Name.Class: "bold #0f172a",
        token.Name.Constant: "#ea580c",
        token.Name.Decorator: "#a855f7",
        token.Name.Entity: "bold #dc2626",
        token.Name.Exception: "bold #dc2626",
        token.Name.Function: "#0f172a",
        token.Name.Function.Magic: "#a855f7",
        token.Name.Label: "#475569",
        token.Name.Namespace: "bold #0f172a",
        token.Name.Other: "#0f172a",
        token.Name.Tag: "#dc2626",
        token.Name.Variable: "#0f172a",
        token.Name.Variable.Class: "#0f172a",
        token.Name.Variable.Global: "#0f172a",
        token.Name.Variable.Instance: "#0f172a",
        token.Name.Variable.Magic: "#a855f7",
        token.Number: "#3b82f6",
        token.Number.Bin: "#3b82f6",
        token.Number.Float: "#3b82f6",
        token.Number.Hex: "#3b82f6",
        token.Number.Integer: "#3b82f6",
        token.Number.Integer.Long: "#3b82f6",
        token.Number.Oct: "#3b82f6",
        token.Literal: "#0f172a",
        token.Literal.Date: "#ca8a04",
        token.String: "#ca8a04",
        token.String.Affix: "bold #ca8a04",
        token.String.Backtick: "#ca8a04",
        token.String.Char: "#ca8a04",
        token.String.Delimiter: "#ca8a04",
        token.String.Doc: "italic #64748b",
        token.String.Double: "#ca8a04",
        token.String.Escape: "bold #b45309",
        token.String.Heredoc: "#ca8a04",
        token.String.Interpol: "bold #b45309",
        token.String.Other: "#ca8a04",
        token.String.Regex: "#ea580c",
        token.String.Single: "#ca8a04",
        token.String.Symbol: "#ca8a04",
        token.Generic: "#0f172a",
        token.Generic.Deleted: "#dc2626",
        token.Generic.Emph: "italic",
        token.Generic.Error: "#dc2626",
        token.Generic.Heading: "bold #0f172a",
        token.Generic.Inserted: "#16a34a",
        token.Generic.Output: "#475569",
        token.Generic.Prompt: "bold #475569",
        token.Generic.Strong: "bold",
        token.Generic.EmphStrong: "bold italic",
        token.Generic.Subheading: "bold #475569",
        token.Generic.Traceback: "#dc2626",
    }
