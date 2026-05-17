"""Docutils-tree tests for sphinx_ux_grid directives.

Invokes each directive against a minimal stub state machine and asserts on
the resulting :class:`docutils.nodes.container` tree — class names, inlined
``style=`` attributes, and (for ``{grid-item-card}`` with ``:link:``) the
chosen wrapper node type.
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import frontend, nodes, utils
from docutils.parsers.rst import Parser
from docutils.statemachine import StringList
from sphinx import addnodes

from sphinx_ux_grid._css import SUG
from sphinx_ux_grid._directives import (
    GridDirective,
    GridItemCardDirective,
    GridItemDirective,
)


def _make_document() -> nodes.document:
    settings = frontend.OptionParser(components=(Parser,)).get_default_values()
    return utils.new_document("<test>", settings)


def _parse(source: str) -> nodes.document:
    """Parse a small reST snippet into a document tree."""
    document = _make_document()
    # Register the directives locally for parsing.
    from docutils.parsers.rst import directives as rst_directives

    rst_directives.register_directive("grid", GridDirective)
    rst_directives.register_directive("grid-item", GridItemDirective)
    rst_directives.register_directive("grid-item-card", GridItemCardDirective)
    Parser().parse(source, document)
    return document


def _find_first(
    document: nodes.Node,
    matcher: t.Callable[[nodes.Node], bool],
) -> nodes.Node:
    for node in document.findall():
        if matcher(node):
            return node
    msg = "no matching node found"
    raise AssertionError(msg)


def _first_container_with_class(
    document: nodes.Node,
    class_name: str,
) -> nodes.container:
    node = _find_first(
        document,
        lambda n: isinstance(n, nodes.container) and class_name in n.get("classes", []),
    )
    assert isinstance(node, nodes.container)
    return node


def test_grid_default_single_column() -> None:
    """A bare ``{grid}`` defaults all breakpoints to one column."""
    document = _parse(
        ".. grid::\n\n   .. grid-item::\n\n      placeholder body\n",
    )
    grid = _first_container_with_class(document, SUG.GRID)
    style = grid.get("style", "")
    assert "--gp-sphinx-grid-cols-xs: 1" in style
    assert "--gp-sphinx-grid-cols-lg: 1" in style


def test_grid_four_breakpoints_inlines_style() -> None:
    """A four-int ``{grid}`` argument emits four cols-* custom properties."""
    document = _parse(
        ".. grid:: 1 2 3 4\n\n   .. grid-item::\n\n      placeholder body\n",
    )
    grid = _first_container_with_class(document, SUG.GRID)
    style = grid.get("style", "")
    assert "--gp-sphinx-grid-cols-xs: 1" in style
    assert "--gp-sphinx-grid-cols-sm: 2" in style
    assert "--gp-sphinx-grid-cols-md: 3" in style
    assert "--gp-sphinx-grid-cols-lg: 4" in style


def test_grid_gutter_maps_to_css_length() -> None:
    """``:gutter: 3`` resolves to ``--gp-sphinx-grid-gutter: 1rem``."""
    document = _parse(
        ".. grid:: 1\n   :gutter: 3\n\n   .. grid-item::\n\n      placeholder body\n",
    )
    grid = _first_container_with_class(document, SUG.GRID)
    style = grid.get("style", "")
    assert "--gp-sphinx-grid-gutter: 1rem" in style


def test_grid_outline_reverse_classes() -> None:
    """``:outline:`` and ``:reverse:`` flags add the matching modifier classes."""
    document = _parse(
        ".. grid:: 1\n"
        "   :outline:\n"
        "   :reverse:\n\n"
        "   .. grid-item::\n\n"
        "      placeholder body\n",
    )
    grid = _first_container_with_class(document, SUG.GRID)
    classes: list[str] = grid.get("classes", [])
    assert SUG.OUTLINE_GRID in classes
    assert SUG.REVERSE in classes


def test_grid_class_container_extends_classes() -> None:
    """``:class-container:`` extra classes survive on the container."""
    document = _parse(
        ".. grid:: 1\n"
        "   :class-container: my-extra-class\n\n"
        "   .. grid-item::\n\n"
        "      placeholder body\n",
    )
    grid = _first_container_with_class(document, SUG.GRID)
    assert "my-extra-class" in grid.get("classes", [])


def test_grid_item_columns_inlines_span_style() -> None:
    """``:columns: 6`` on a grid-item inlines four ``--…-item-span-*`` props."""
    document = _parse(
        ".. grid:: 12\n\n"
        "   .. grid-item::\n"
        "      :columns: 6\n\n"
        "      placeholder body\n",
    )
    item = _first_container_with_class(document, SUG.ITEM)
    style = item.get("style", "")
    assert "--gp-sphinx-grid-item-span-xs: 6" in style
    assert "--gp-sphinx-grid-item-span-lg: 6" in style


def test_grid_item_card_emits_card_and_body() -> None:
    """``{grid-item-card}`` emits a card container with a body and title."""
    document = _parse(
        ".. grid:: 1\n\n   .. grid-item-card:: My title\n\n      Body text.\n",
    )
    card = _first_container_with_class(document, SUG.CARD)
    classes: list[str] = card.get("classes", [])
    # Default shadow is sm.
    assert SUG.shadow("sm") in classes

    body = _first_container_with_class(document, SUG.CARD_BODY)
    assert body is not None

    title = _first_container_with_class(document, SUG.CARD_TITLE)
    # The title text appears as a child Text node somewhere under title.
    title_text = "".join(n.astext() for n in title.findall(nodes.Text))
    assert "My title" in title_text


def test_grid_item_card_header_and_footer_split() -> None:
    """``^^^`` and ``+++`` split off header/footer sections."""
    document = _parse(
        ".. grid:: 1\n\n"
        "   .. grid-item-card:: Demo\n\n"
        "      Header text\n"
        "      ^^^\n"
        "      Body text\n"
        "      +++\n"
        "      Footer text\n",
    )
    header = _first_container_with_class(document, SUG.CARD_HEADER)
    footer = _first_container_with_class(document, SUG.CARD_FOOTER)
    body = _first_container_with_class(document, SUG.CARD_BODY)
    assert "Header text" in "".join(n.astext() for n in header.findall(nodes.Text))
    assert "Body text" in "".join(n.astext() for n in body.findall(nodes.Text))
    assert "Footer text" in "".join(n.astext() for n in footer.findall(nodes.Text))


def test_grid_item_card_link_url_emits_stretched_reference() -> None:
    """``:link: …`` with ``:link-type: url`` emits a stretched ``nodes.reference``.

    The reference lives inside the card as a stretched-link overlay
    (positioned via the bundled CSS), not as a wrapper around the card.
    """
    document = _parse(
        ".. grid:: 1\n\n"
        "   .. grid-item-card:: External\n"
        "      :link: https://example.com\n"
        "      :link-type: url\n\n"
        "      Body.\n",
    )
    reference = _find_first(
        document,
        lambda n: (
            isinstance(n, nodes.reference) and SUG.CARD_LINK in n.get("classes", [])
        ),
    )
    assert isinstance(reference, nodes.reference)
    assert reference["refuri"] == "https://example.com"
    # The card carries the hover-affordance class.
    card = _first_container_with_class(document, SUG.CARD)
    assert SUG.CARD_HOVER in card.get("classes", [])


def test_grid_item_card_link_doc_emits_pending_xref() -> None:
    """``:link-type: doc`` produces an :class:`addnodes.pending_xref` overlay."""
    document = _parse(
        ".. grid:: 1\n\n"
        "   .. grid-item-card:: Internal\n"
        "      :link: foo\n"
        "      :link-type: doc\n\n"
        "      Body.\n",
    )
    xref = _find_first(
        document,
        lambda n: (
            isinstance(n, addnodes.pending_xref)
            and SUG.CARD_LINK in n.get("classes", [])
        ),
    )
    assert isinstance(xref, addnodes.pending_xref)
    assert xref["reftype"] == "doc"
    assert xref["reftarget"] == "foo"


def test_grid_item_card_shadow_none_drops_class() -> None:
    """``:shadow: none`` strips the shadow modifier entirely."""
    document = _parse(
        ".. grid:: 1\n\n"
        "   .. grid-item-card:: Plain\n"
        "      :shadow: none\n\n"
        "      Body.\n",
    )
    card = _first_container_with_class(document, SUG.CARD)
    classes: list[str] = card.get("classes", [])
    assert not any(c.startswith("gp-sphinx-grid-card--shadow-") for c in classes)


@pytest.mark.parametrize(
    ("level", "expected_class"),
    [
        ("sm", "gp-sphinx-grid-card--shadow-sm"),
        ("md", "gp-sphinx-grid-card--shadow-md"),
        ("lg", "gp-sphinx-grid-card--shadow-lg"),
    ],
)
def test_grid_item_card_shadow_levels(level: str, expected_class: str) -> None:
    """Each named shadow level lands on the card as a single modifier."""
    document = _parse(
        ".. grid:: 1\n\n"
        f"   .. grid-item-card::\n"
        f"      :shadow: {level}\n\n"
        f"      Body.\n",
    )
    card = _first_container_with_class(document, SUG.CARD)
    assert expected_class in card.get("classes", [])


def test_grid_item_card_image_top_attaches_image_node() -> None:
    """``:img-top:`` attaches a ``nodes.image`` with the matching class."""
    document = _parse(
        ".. grid:: 1\n\n"
        "   .. grid-item-card::\n"
        "      :img-top: hero.png\n"
        "      :img-alt: alt-text\n\n"
        "      Body.\n",
    )
    img = _find_first(
        document,
        lambda n: (
            isinstance(n, nodes.image) and SUG.CARD_IMG_TOP in n.get("classes", [])
        ),
    )
    assert isinstance(img, nodes.image)
    assert img["uri"] == "hero.png"
    assert img["alt"] == "alt-text"


def test_columns_to_style_round_trip() -> None:
    """The four breakpoints are inlined in xs/sm/md/lg order."""
    from sphinx_ux_grid._directives import _columns_to_style

    style = _columns_to_style((2, 4, 6, 8))
    parts = [p.strip() for p in style.split(";")]
    assert parts == [
        "--gp-sphinx-grid-cols-xs: 2",
        "--gp-sphinx-grid-cols-sm: 4",
        "--gp-sphinx-grid-cols-md: 6",
        "--gp-sphinx-grid-cols-lg: 8",
    ]


def test_split_card_content_no_markers() -> None:
    """When neither marker is present, body == content and header/footer are None."""
    from sphinx_ux_grid._directives import _split_card_content

    content = StringList(["line1", "line2"], source="<test>")
    result = _split_card_content(content, offset=10)
    assert result.header is None
    assert result.footer is None
    assert list(result.body) == ["line1", "line2"]
    assert result.body_offset == 10


class SpacingFixture(t.NamedTuple):
    """Test case for ``:margin:`` / ``:padding:`` style emission."""

    test_id: str
    source: str
    target_class: str
    expected_fragments: tuple[str, ...]


_SPACING_FIXTURES: list[SpacingFixture] = [
    SpacingFixture(
        test_id="grid-margin-single",
        source=".. grid:: 1\n   :margin: 3\n\n   .. grid-item::\n\n      body\n",
        target_class=SUG.GRID,
        expected_fragments=(
            "--gp-sphinx-grid-margin-xs: 1rem",
            "--gp-sphinx-grid-margin-sm: 1rem",
            "--gp-sphinx-grid-margin-md: 1rem",
            "--gp-sphinx-grid-margin-lg: 1rem",
        ),
    ),
    SpacingFixture(
        test_id="grid-margin-four-breakpoints",
        source=".. grid:: 1\n   :margin: 1 2 3 4\n\n   .. grid-item::\n\n      body\n",
        target_class=SUG.GRID,
        expected_fragments=(
            "--gp-sphinx-grid-margin-xs: 0.25rem",
            "--gp-sphinx-grid-margin-sm: 0.5rem",
            "--gp-sphinx-grid-margin-md: 1rem",
            "--gp-sphinx-grid-margin-lg: 1.5rem",
        ),
    ),
    SpacingFixture(
        test_id="grid-padding-single",
        source=".. grid:: 1\n   :padding: 2\n\n   .. grid-item::\n\n      body\n",
        target_class=SUG.GRID,
        expected_fragments=(
            "--gp-sphinx-grid-padding-xs: 0.5rem",
            "--gp-sphinx-grid-padding-lg: 0.5rem",
        ),
    ),
    SpacingFixture(
        test_id="item-margin-auto",
        source=(
            ".. grid:: 1\n\n   .. grid-item::\n      :margin: auto\n\n      body\n"
        ),
        target_class=SUG.ITEM,
        expected_fragments=(
            "--gp-sphinx-grid-margin-xs: auto",
            "--gp-sphinx-grid-margin-lg: auto",
        ),
    ),
    SpacingFixture(
        test_id="item-padding-single",
        source=(".. grid:: 1\n\n   .. grid-item::\n      :padding: 4\n\n      body\n"),
        target_class=SUG.ITEM,
        expected_fragments=(
            "--gp-sphinx-grid-padding-xs: 1.5rem",
            "--gp-sphinx-grid-padding-lg: 1.5rem",
        ),
    ),
    SpacingFixture(
        test_id="card-margin-single",
        source=(
            ".. grid:: 1\n\n   .. grid-item-card::\n      :margin: 5\n\n      body\n"
        ),
        target_class=SUG.CARD,
        expected_fragments=(
            "--gp-sphinx-grid-margin-xs: 3rem",
            "--gp-sphinx-grid-margin-lg: 3rem",
        ),
    ),
    SpacingFixture(
        test_id="card-margin-four-breakpoints",
        source=(
            ".. grid:: 1\n\n"
            "   .. grid-item-card::\n"
            "      :margin: 1 2 3 4\n\n"
            "      body\n"
        ),
        target_class=SUG.CARD,
        expected_fragments=(
            "--gp-sphinx-grid-margin-xs: 0.25rem",
            "--gp-sphinx-grid-margin-sm: 0.5rem",
            "--gp-sphinx-grid-margin-md: 1rem",
            "--gp-sphinx-grid-margin-lg: 1.5rem",
        ),
    ),
]


@pytest.mark.parametrize(
    list(SpacingFixture._fields),
    _SPACING_FIXTURES,
    ids=[f.test_id for f in _SPACING_FIXTURES],
)
def test_spacing_options_inline_custom_properties(
    test_id: str,
    source: str,
    target_class: str,
    expected_fragments: tuple[str, ...],
) -> None:
    """:margin: / :padding: emit per-breakpoint custom properties on style=."""
    document = _parse(source)
    container = _first_container_with_class(document, target_class)
    style = container.get("style", "")
    for fragment in expected_fragments:
        assert fragment in style, f"{test_id}: expected {fragment!r} in style {style!r}"


def test_grid_item_card_direction_align_use_sug_helpers() -> None:
    """``:child-direction:`` / ``:child-align:`` flow through SUG helpers."""
    document = _parse(
        ".. grid:: 1\n\n"
        "   .. grid-item-card::\n"
        "      :child-direction: row\n"
        "      :child-align: center\n\n"
        "      body\n",
    )
    item = _first_container_with_class(document, SUG.ITEM)
    classes: list[str] = item.get("classes", [])
    assert SUG.item_direction("row") in classes
    assert SUG.item_align("center") in classes
