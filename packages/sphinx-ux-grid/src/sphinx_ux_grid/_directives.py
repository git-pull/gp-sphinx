"""Directive implementations for ``{grid}``, ``{grid-item}``, and ``{grid-item-card}``.

Each directive emits plain :class:`docutils.nodes.container` nodes carrying
CSS classes from :mod:`sphinx_ux_grid._css`.  Breakpoint-specific values
(column counts, gutter) are inlined as CSS custom-property overrides on
the container's ``style`` attribute; the package's stylesheet reads those
custom properties to drive a CSS Grid layout — no Bootstrap-derived float
classes are emitted.

Examples
--------
>>> _columns_option("3")
(3, 3, 3, 3)

>>> _columns_option("1 2 3 4")
(1, 2, 3, 4)

>>> _gutter_to_length("3")
'1rem'
"""

from __future__ import annotations

import re
import typing as t

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective

from sphinx_ux_grid._css import SUG
from sphinx_ux_grid._nodes import LinkPassthrough

_BREAKPOINTS: tuple[str, str, str, str] = ("xs", "sm", "md", "lg")

# Bootstrap-style 0..5 spacing scale mapped to fixed CSS lengths.
_GUTTER_SCALE: dict[str, str] = {
    "0": "0",
    "1": "0.25rem",
    "2": "0.5rem",
    "3": "1rem",
    "4": "1.5rem",
    "5": "3rem",
}

# Margin/padding share the gutter scale plus the ``auto`` keyword for margins.
_SPACING_SCALE: dict[str, str] = {**_GUTTER_SCALE, "auto": "auto"}

_CSS_LENGTH_RE = re.compile(
    r"^-?\d*\.?\d+(?:px|rem|em|%|vh|vw|ch|pt|cm|mm|in)$",
)

_HEADER_RE = re.compile(r"^\^{3,}\s*$")
_FOOTER_RE = re.compile(r"^\+{3,}\s*$")

_TEXT_ALIGN_VALUES = ("left", "right", "center", "justify")
_WIDTH_VALUES = ("auto", "25%", "50%", "75%", "100%")
_LINK_TYPE_VALUES = ("url", "any", "ref", "doc")
_SHADOW_VALUES = ("none", "sm", "md", "lg")
_CHILD_DIRECTION_VALUES = ("column", "row")
_CHILD_ALIGN_VALUES = ("start", "end", "center", "justify", "spaced")
_MARGIN_VALUES = ("auto", "0", "1", "2", "3", "4", "5")
_PADDING_VALUES = ("0", "1", "2", "3", "4", "5")


def _columns_option(argument: str | None) -> tuple[int, int, int, int]:
    """Parse a column-count spec into a four-int tuple ``(xs, sm, md, lg)``.

    Accepts either a single integer ``"N"`` (applied to all breakpoints)
    or four space-separated integers ``"xs sm md lg"``.  Each value must
    lie in ``[1..12]``.

    Parameters
    ----------
    argument : str or None
        The directive argument string.

    Returns
    -------
    tuple[int, int, int, int]
        Four column counts in ``(xs, sm, md, lg)`` order.

    Raises
    ------
    ValueError
        If ``argument`` is ``None``, empty, contains a non-integer, has
        the wrong arity, or a value outside ``[1..12]``.

    Examples
    --------
    >>> _columns_option("3")
    (3, 3, 3, 3)

    >>> _columns_option("1 2 3 4")
    (1, 2, 3, 4)
    """
    msg = "argument must be 1 or 4 space-separated integers in [1..12] (xs sm md lg)"
    if argument is None:
        raise ValueError(msg)
    parts = argument.strip().split()
    if not parts:
        raise ValueError(msg)
    if len(parts) == 1:
        parts = parts * 4
    if len(parts) != 4:
        raise ValueError(msg)
    try:
        values = tuple(int(p) for p in parts)
    except ValueError as exc:
        raise ValueError(msg) from exc
    for value in values:
        if not (1 <= value <= 12):
            raise ValueError(msg)
    return (values[0], values[1], values[2], values[3])


def _item_columns_option(argument: str | None) -> tuple[int, int, int, int]:
    """Parse a ``:columns:`` value on ``{grid-item}`` / ``{grid-item-card}``.

    Same shape as :func:`_columns_option` — a single int or four ints in
    ``[1..12]`` mapping to ``(xs, sm, md, lg)`` column spans.

    Parameters
    ----------
    argument : str or None
        The option value.

    Returns
    -------
    tuple[int, int, int, int]
        Column spans in ``(xs, sm, md, lg)`` order.

    Examples
    --------
    >>> _item_columns_option("6")
    (6, 6, 6, 6)
    """
    return _columns_option(argument)


def _gutter_to_length(argument: str | None) -> str:
    """Map a ``:gutter:`` value to a concrete CSS length.

    Integers ``0..5`` map to a fixed scale (``0``, ``0.25rem``, ``0.5rem``,
    ``1rem``, ``1.5rem``, ``3rem``).  Any other token shaped like a CSS
    length (``1rem``, ``16px``, ``50%``) is passed through unchanged.
    When the argument has multiple whitespace-separated values, the
    first is used — per-breakpoint gutters collapse to a single grid gap.

    Parameters
    ----------
    argument : str or None
        The gutter spec.

    Returns
    -------
    str
        A concrete CSS length suitable for ``--gp-sphinx-grid-gutter``.

    Raises
    ------
    ValueError
        If ``argument`` is ``None``, empty, or neither a 0..5 scale int
        nor a recognized CSS length.

    Examples
    --------
    >>> _gutter_to_length("3")
    '1rem'

    >>> _gutter_to_length("2rem")
    '2rem'
    """
    msg_required = "gutter argument required"
    if argument is None:
        raise ValueError(msg_required)
    parts = argument.strip().split()
    if not parts:
        raise ValueError(msg_required)
    head = parts[0]
    if head in _GUTTER_SCALE:
        return _GUTTER_SCALE[head]
    if _CSS_LENGTH_RE.match(head):
        return head
    msg = f"gutter value {head!r} is not a 0..5 scale int or a CSS length"
    raise ValueError(msg)


def _spacing_option(argument: str | None, *, allowed: tuple[str, ...]) -> list[str]:
    """Validate a margin/padding spec — one (all) or four (xs sm md lg) values.

    Examples
    --------
    >>> _spacing_option("3", allowed=_PADDING_VALUES)
    ['3']

    >>> _spacing_option("1 2 3 4", allowed=_PADDING_VALUES)
    ['1', '2', '3', '4']

    >>> _spacing_option("auto", allowed=_MARGIN_VALUES)
    ['auto']

    >>> _spacing_option("9", allowed=_PADDING_VALUES)
    Traceback (most recent call last):
        ...
    ValueError: '9' not in ('0', '1', '2', '3', '4', '5')
    """
    msg_required = "argument required"
    if argument is None:
        raise ValueError(msg_required)
    values = argument.split()
    for value in values:
        if value not in allowed:
            msg = f"{value!r} not in {allowed}"
            raise ValueError(msg)
    if len(values) not in (1, 4):
        msg_arity = "margin/padding must be 1 (all) or 4 (xs sm md lg) values"
        raise ValueError(msg_arity)
    return values


def _margin_option(argument: str | None) -> list[str]:
    """Validate the ``:margin:`` option (0..5 or 'auto').

    Examples
    --------
    >>> _margin_option("3")
    ['3']

    >>> _margin_option("auto auto 0 0")
    ['auto', 'auto', '0', '0']
    """
    return _spacing_option(argument, allowed=_MARGIN_VALUES)


def _padding_option(argument: str | None) -> list[str]:
    """Validate the ``:padding:`` option (0..5).

    Examples
    --------
    >>> _padding_option("2")
    ['2']

    >>> _padding_option("0 1 2 3")
    ['0', '1', '2', '3']
    """
    return _spacing_option(argument, allowed=_PADDING_VALUES)


def _spacing_to_length(value: str) -> str:
    """Map a single margin/padding token to a CSS length (or ``auto``).

    Examples
    --------
    >>> _spacing_to_length("3")
    '1rem'

    >>> _spacing_to_length("auto")
    'auto'
    """
    return _SPACING_SCALE[value]


def _spacing_to_style(prefix: str, values: list[str]) -> str:
    """Render a margin/padding spec as ``--<prefix>-<bp>: <length>`` pairs.

    ``values`` is either a 1-element list (applied to every breakpoint) or a
    4-element list in ``(xs, sm, md, lg)`` order.  ``prefix`` is the CSS
    custom-property root, e.g. ``"--gp-sphinx-grid-margin"``.

    Examples
    --------
    A single token expands to all four breakpoints (``NORMALIZE_WHITESPACE``
    is enabled, so the wrapped expected output below still matches the
    single-line return value):

    >>> _spacing_to_style("--gp-sphinx-grid-margin", ["3"])
    '--gp-sphinx-grid-margin-xs: 1rem;
     --gp-sphinx-grid-margin-sm: 1rem;
     --gp-sphinx-grid-margin-md: 1rem;
     --gp-sphinx-grid-margin-lg: 1rem'

    A four-token list maps positionally to ``(xs, sm, md, lg)``:

    >>> _spacing_to_style("--gp-sphinx-grid-margin", ["1", "2", "3", "4"])
    '--gp-sphinx-grid-margin-xs: 0.25rem;
     --gp-sphinx-grid-margin-sm: 0.5rem;
     --gp-sphinx-grid-margin-md: 1rem;
     --gp-sphinx-grid-margin-lg: 1.5rem'

    The ``auto`` keyword passes through (margins only):

    >>> _spacing_to_style("--gp-sphinx-grid-margin", ["auto"])
    '--gp-sphinx-grid-margin-xs: auto;
     --gp-sphinx-grid-margin-sm: auto;
     --gp-sphinx-grid-margin-md: auto;
     --gp-sphinx-grid-margin-lg: auto'
    """
    per_breakpoint = [values[0]] * 4 if len(values) == 1 else values
    return _style_from_pairs(
        (f"{prefix}-{bp}", _spacing_to_length(token))
        for bp, token in zip(_BREAKPOINTS, per_breakpoint, strict=True)
    )


def _choice(values: tuple[str, ...]) -> t.Callable[[str | None], str]:
    """Build a ``directives.choice``-style validator from a fixed value set."""

    def _validator(argument: str | None) -> str:
        return directives.choice(argument or "", list(values))

    return _validator


def _style_from_pairs(pairs: t.Iterable[tuple[str, str]]) -> str:
    """Render an inline ``style`` string from ``(property, value)`` pairs.

    Examples
    --------
    >>> _style_from_pairs([("a", "1"), ("b", "2")])
    'a: 1; b: 2'

    >>> _style_from_pairs([])
    ''
    """
    return "; ".join(f"{name}: {value}" for name, value in pairs)


def _columns_to_style(columns: tuple[int, int, int, int]) -> str:
    """Render a column-count tuple as a ``--gp-sphinx-grid-cols-*`` style string.

    Parameters
    ----------
    columns : tuple[int, int, int, int]
        Column counts in ``(xs, sm, md, lg)`` order.

    Returns
    -------
    str
        Inline ``style`` value, e.g.
        ``"--gp-sphinx-grid-cols-xs: 1; --gp-sphinx-grid-cols-sm: 2; …"``.

    Examples
    --------
    >>> _columns_to_style((1, 2, 3, 4)).startswith("--gp-sphinx-grid-cols-xs: 1")
    True

    >>> _columns_to_style((1, 2, 3, 4)).endswith("--gp-sphinx-grid-cols-lg: 4")
    True
    """
    return _style_from_pairs(
        (f"--gp-sphinx-grid-cols-{bp}", str(count))
        for bp, count in zip(_BREAKPOINTS, columns, strict=True)
    )


def _item_span_to_style(columns: tuple[int, int, int, int]) -> str:
    """Render an item-span tuple as a ``--gp-sphinx-grid-item-span-*`` style string.

    Parameters
    ----------
    columns : tuple[int, int, int, int]
        Column-span counts in ``(xs, sm, md, lg)`` order.

    Returns
    -------
    str
        Inline ``style`` value driving per-breakpoint ``grid-column: span N``.

    Examples
    --------
    >>> _item_span_to_style((6, 6, 4, 3)).startswith("--gp-sphinx-grid-item-span-xs: 6")
    True

    >>> "--gp-sphinx-grid-item-span-lg: 3" in _item_span_to_style((6, 6, 4, 3))
    True
    """
    return _style_from_pairs(
        (f"--gp-sphinx-grid-item-span-{bp}", str(count))
        for bp, count in zip(_BREAKPOINTS, columns, strict=True)
    )


def _merge_styles(*parts: str) -> str:
    """Join non-empty inline ``style`` fragments with ``; `` separators.

    Examples
    --------
    >>> _merge_styles("a: 1", "", "b: 2")
    'a: 1; b: 2'

    >>> _merge_styles("", "")
    ''
    """
    return "; ".join(p for p in parts if p)


class _CardContent(t.NamedTuple):
    """Result of splitting a card body into optional header/body/footer."""

    body_offset: int
    body: StringList
    header_offset: int | None
    header: StringList | None
    footer_offset: int | None
    footer: StringList | None


def _split_card_content(
    content: StringList,
    offset: int,
) -> _CardContent:
    """Split ``content`` on ``^^^`` (header) and ``+++`` (footer) markers.

    Mirrors sphinx-design's splitter shape — the first ``^^^`` separates
    a header block from the body, and the last ``+++`` separates a footer
    block from the body.

    Parameters
    ----------
    content : StringList
        The directive content lines.
    offset : int
        The starting line offset (``self.content_offset``).

    Returns
    -------
    _CardContent
        Body, header, and footer slices with their line offsets.

    Examples
    --------
    >>> from docutils.statemachine import StringList
    >>> lines = StringList(["head", "^^^", "body", "+++", "foot"], source="<t>")
    >>> result = _split_card_content(lines, offset=0)
    >>> list(result.header), list(result.body), list(result.footer)
    (['head'], ['body'], ['foot'])

    >>> bare = StringList(["only body"], source="<t>")
    >>> bare_result = _split_card_content(bare, offset=0)
    >>> bare_result.header is None, list(bare_result.body), bare_result.footer is None
    (True, ['only body'], True)
    """
    header_index: int | None = None
    footer_index: int | None = None
    for index, line in enumerate(content):
        if header_index is None and _HEADER_RE.match(line):
            header_index = index
        if _FOOTER_RE.match(line):
            footer_index = index

    body_offset = offset
    header_offset: int | None = None
    header: StringList | None = None
    footer_offset: int | None = None
    footer: StringList | None = None

    if header_index is not None:
        header_offset = offset
        header = content[:header_index]
        body_offset = offset + header_index + 1
    body_start = (header_index + 1) if header_index is not None else 0
    if footer_index is not None:
        footer_offset = offset + footer_index + 1
        footer = content[footer_index + 1 :]
        body = content[body_start:footer_index]
    else:
        body = content[body_start:]
    return _CardContent(
        body_offset=body_offset,
        body=body,
        header_offset=header_offset,
        header=header,
        footer_offset=footer_offset,
        footer=footer,
    )


def _make_container(
    classes: t.Sequence[str],
    *,
    style: str = "",
    **attributes: t.Any,
) -> nodes.container:
    """Build a ``nodes.container`` with class/style/extra attributes.

    Examples
    --------
    >>> node = _make_container(["a", "", "b"], style="x: 1")
    >>> node["classes"], node["style"], node["is_div"]
    (['a', 'b'], 'x: 1', True)

    >>> bare = _make_container(["c"])
    >>> "style" in bare.attributes
    False
    """
    class_list = [c for c in classes if c]
    attrs: dict[str, t.Any] = {"is_div": True, "classes": class_list, **attributes}
    if style:
        attrs["style"] = style
    return nodes.container("", **attrs)


class GridDirective(SphinxDirective):
    """The ``{grid}`` directive — container for ``{grid-item*}`` children.

    Argument (optional): a column-count spec — ``"N"`` or ``"xs sm md lg"``.
    Defaults to one column at every breakpoint when omitted.

    Examples
    --------
    >>> GridDirective.has_content
    True
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec: t.ClassVar[dict[str, t.Callable[..., t.Any]]] = {
        "gutter": directives.unchanged,
        "margin": _margin_option,
        "padding": _padding_option,
        "outline": directives.flag,
        "reverse": directives.flag,
        "class-container": directives.class_option,
        "class-row": directives.class_option,
    }

    def run(self) -> list[nodes.Node]:
        """Build the grid container and recurse into the directive body.

        Examples
        --------
        >>> GridDirective.run.__qualname__
        'GridDirective.run'
        """
        try:
            columns = (
                _columns_option(self.arguments[0]) if self.arguments else (1, 1, 1, 1)
            )
        except ValueError as exc:
            msg = f"Invalid {{grid}} argument: {exc}"
            raise self.error(msg) from exc
        try:
            gutter = (
                _gutter_to_length(self.options["gutter"])
                if "gutter" in self.options
                else None
            )
        except ValueError as exc:
            msg = f"Invalid :gutter: option: {exc}"
            raise self.error(msg) from exc

        column_style = _columns_to_style(columns)
        gutter_style = (
            f"--gp-sphinx-grid-gutter: {gutter}" if gutter is not None else ""
        )
        margin_style = (
            _spacing_to_style("--gp-sphinx-grid-margin", self.options["margin"])
            if "margin" in self.options
            else ""
        )
        padding_style = (
            _spacing_to_style("--gp-sphinx-grid-padding", self.options["padding"])
            if "padding" in self.options
            else ""
        )

        classes: list[str] = [SUG.GRID]
        if "outline" in self.options:
            classes.append(SUG.OUTLINE_GRID)
        if "reverse" in self.options:
            classes.append(SUG.REVERSE)
        classes.extend(self.options.get("class-container", []))
        classes.extend(self.options.get("class-row", []))

        container = _make_container(
            classes,
            style=_merge_styles(
                column_style, gutter_style, margin_style, padding_style
            ),
        )
        self.set_source_info(container)
        self.state.nested_parse(self.content, self.content_offset, container)
        return [container]


class GridItemDirective(SphinxDirective):
    """The ``{grid-item}`` directive — a span inside a ``{grid}``.

    Examples
    --------
    >>> GridItemDirective.has_content
    True
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec: t.ClassVar[dict[str, t.Callable[..., t.Any]]] = {
        "columns": _item_columns_option,
        "child-direction": _choice(_CHILD_DIRECTION_VALUES),
        "child-align": _choice(_CHILD_ALIGN_VALUES),
        "margin": _margin_option,
        "padding": _padding_option,
        "outline": directives.flag,
        "class": directives.class_option,
    }

    def run(self) -> list[nodes.Node]:
        """Build the grid-item container.

        Examples
        --------
        >>> GridItemDirective.run.__qualname__
        'GridItemDirective.run'
        """
        columns = self.options.get("columns")
        span_style = _item_span_to_style(columns) if columns else ""
        margin_style = (
            _spacing_to_style("--gp-sphinx-grid-margin", self.options["margin"])
            if "margin" in self.options
            else ""
        )
        padding_style = (
            _spacing_to_style("--gp-sphinx-grid-padding", self.options["padding"])
            if "padding" in self.options
            else ""
        )

        classes: list[str] = [SUG.ITEM]
        if "outline" in self.options:
            classes.append(SUG.OUTLINE_ITEM)
        if "child-direction" in self.options:
            classes.append(SUG.item_direction(self.options["child-direction"]))
        if "child-align" in self.options:
            classes.append(SUG.item_align(self.options["child-align"]))
        classes.extend(self.options.get("class", []))

        container = _make_container(
            classes,
            style=_merge_styles(span_style, margin_style, padding_style),
        )
        self.set_source_info(container)
        self.state.nested_parse(self.content, self.content_offset, container)
        return [container]


class GridItemCardDirective(SphinxDirective):
    """The ``{grid-item-card}`` directive — a card inside a grid item.

    Argument (optional): the card title.  The body may include
    ``^^^``-delimited header and ``+++``-delimited footer regions.

    Examples
    --------
    >>> GridItemCardDirective.has_content
    True
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec: t.ClassVar[dict[str, t.Callable[..., t.Any]]] = {
        # grid-item options
        "columns": _item_columns_option,
        "child-direction": _choice(_CHILD_DIRECTION_VALUES),
        "child-align": _choice(_CHILD_ALIGN_VALUES),
        "margin": _margin_option,
        "padding": _padding_option,
        "outline": directives.flag,
        "class-item": directives.class_option,
        # card options
        "width": _choice(_WIDTH_VALUES),
        "text-align": _choice(_TEXT_ALIGN_VALUES),
        "img-top": directives.uri,
        "img-bottom": directives.uri,
        "img-background": directives.uri,
        "img-alt": directives.unchanged,
        "link": directives.uri,
        "link-type": _choice(_LINK_TYPE_VALUES),
        "link-alt": directives.unchanged,
        "shadow": _choice(_SHADOW_VALUES),
        "class-card": directives.class_option,
        "class-body": directives.class_option,
        "class-title": directives.class_option,
        "class-header": directives.class_option,
        "class-footer": directives.class_option,
        "class-img-top": directives.class_option,
        "class-img-bottom": directives.class_option,
    }

    def run(self) -> list[nodes.Node]:
        """Build the grid-item wrapper, the card, and any header/footer.

        Examples
        --------
        >>> GridItemCardDirective.run.__qualname__
        'GridItemCardDirective.run'
        """
        item = self._build_item_wrapper()
        card_or_link = self._build_card()
        item += card_or_link
        return [item]

    def _build_item_wrapper(self) -> nodes.container:
        columns = self.options.get("columns")
        span_style = _item_span_to_style(columns) if columns else ""

        classes: list[str] = [SUG.ITEM]
        if "outline" in self.options:
            classes.append(SUG.OUTLINE_ITEM)
        if "child-direction" in self.options:
            classes.append(SUG.item_direction(self.options["child-direction"]))
        if "child-align" in self.options:
            classes.append(SUG.item_align(self.options["child-align"]))
        classes.extend(self.options.get("class-item", []))

        item = _make_container(classes, style=span_style)
        self.set_source_info(item)
        return item

    def _build_card(self) -> nodes.Node:
        card = self._build_card_container()
        self._populate_card(card)
        link = self.options.get("link")
        if link is not None:
            card.append(self._build_link(link))
        return card

    def _build_card_container(self) -> nodes.container:
        classes: list[str] = [SUG.CARD]
        shadow_class = SUG.shadow(self.options.get("shadow", "sm"))
        if shadow_class:
            classes.append(shadow_class)
        if "outline" in self.options:
            classes.append(SUG.OUTLINE)
        if "text-align" in self.options:
            classes.append(SUG.text_align(self.options["text-align"]))
        if "width" in self.options:
            classes.append(SUG.width(self.options["width"]))
        if "link" in self.options:
            classes.append(SUG.CARD_HOVER)
        classes.extend(self.options.get("class-card", []))

        margin_style = (
            _spacing_to_style("--gp-sphinx-grid-margin", self.options["margin"])
            if "margin" in self.options
            else ""
        )
        padding_style = (
            _spacing_to_style("--gp-sphinx-grid-padding", self.options["padding"])
            if "padding" in self.options
            else ""
        )

        card = _make_container(
            classes, style=_merge_styles(margin_style, padding_style)
        )
        self.set_source_info(card)
        return card

    def _populate_card(self, card: nodes.container) -> None:
        components = _split_card_content(self.content, self.content_offset)
        img_alt = self.options.get("img-alt") or ""
        container: nodes.Element = card

        if "img-background" in self.options:
            card.append(
                nodes.image(
                    "",
                    uri=self.options["img-background"],
                    alt=img_alt,
                    classes=[SUG.CARD_IMG_BACKGROUND],
                ),
            )
            overlay = _make_container([SUG.CARD_IMG_OVERLAY])
            self.set_source_info(overlay)
            card.append(overlay)
            container = overlay

        if "img-top" in self.options:
            container.append(
                nodes.image(
                    "",
                    uri=self.options["img-top"],
                    alt=img_alt,
                    classes=[
                        SUG.CARD_IMG_TOP,
                        *self.options.get("class-img-top", []),
                    ],
                ),
            )

        if components.header is not None and components.header_offset is not None:
            container.append(
                self._build_section(
                    "header",
                    components.header,
                    components.header_offset,
                ),
            )

        body = self._build_section("body", components.body, components.body_offset)
        if self.arguments:
            body.insert(0, self._build_title(self.arguments[0]))
        container.append(body)

        if components.footer is not None and components.footer_offset is not None:
            container.append(
                self._build_section(
                    "footer",
                    components.footer,
                    components.footer_offset,
                ),
            )

        if "img-bottom" in self.options:
            container.append(
                nodes.image(
                    "",
                    uri=self.options["img-bottom"],
                    alt=img_alt,
                    classes=[
                        SUG.CARD_IMG_BOTTOM,
                        *self.options.get("class-img-bottom", []),
                    ],
                ),
            )

    _SECTION_CLASS: t.ClassVar[dict[str, str]] = {
        "body": SUG.CARD_BODY,
        "header": SUG.CARD_HEADER,
        "footer": SUG.CARD_FOOTER,
    }

    def _build_section(
        self,
        name: str,
        content: StringList,
        offset: int,
    ) -> nodes.container:
        classes = [
            self._SECTION_CLASS[name],
            *self.options.get(f"class-{name}", []),
        ]
        section = _make_container(classes)
        self.set_source_info(section)
        self.state.nested_parse(content, offset, section)
        return section

    def _build_title(self, raw: str) -> nodes.container:
        classes = [
            SUG.CARD_TITLE,
            *self.options.get("class-title", []),
        ]
        title = _make_container(classes)
        text_nodes, _ = self.state.inline_text(raw, self.lineno)
        title.extend(text_nodes)
        self.set_source_info(title)
        return title

    def _build_link(self, target: str) -> nodes.Element:
        """Build a stretched-link node that overlays the parent card.

        The link is appended as the last child of the card; CSS positions
        it ``inset: 0`` so the entire card surface becomes clickable.
        For ``:link-type: url`` the wrapper is a :class:`nodes.reference`;
        for ``ref`` / ``doc`` / ``any`` it is an
        :class:`addnodes.pending_xref` that Sphinx resolves during the
        post-transform pass.

        The xref / reference is wrapped in an ``_LinkPassthrough`` (a
        thin :class:`nodes.TextElement` subclass) so the HTML5 writer
        satisfies its ``len(node) == 1 and isinstance(node[0], image)``
        assertion path for non-image references.
        """
        link_type = self.options.get("link-type", "any")
        alt = self.options.get("link-alt") or target
        classes = [SUG.CARD_LINK]
        inline_label = nodes.inline(alt, alt)

        link: nodes.Element
        if link_type == "url":
            link = nodes.reference(
                alt,
                "",
                inline_label,
                refuri=target,
                classes=classes,
            )
        else:
            # ``self.env`` is unavailable outside a Sphinx build (e.g.
            # when the directive runs under a bare docutils parser in
            # unit tests); fall back to an empty docname so the xref
            # still has the shape the resolver expects.
            try:
                refdoc = self.env.docname
            except AttributeError:
                refdoc = ""
            link = addnodes.pending_xref(
                alt,
                inline_label,
                classes=classes,
                reftarget=target,
                refdoc=refdoc,
                refdomain="" if link_type == "any" else "std",
                reftype=link_type,
                refexplicit="link-alt" in self.options,
                refwarn=True,
            )
        self.set_source_info(link)
        wrapper = LinkPassthrough()
        wrapper.append(link)
        return wrapper
