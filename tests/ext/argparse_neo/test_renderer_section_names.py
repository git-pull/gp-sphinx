"""Regression tests for section ``names`` scoping in the argparse_neo renderer.

Prior to the fix, ``render_usage_section`` and ``render_group_section``
correctly namespaced ``section["ids"]`` by the caller-supplied ``id_prefix``
but left ``section["names"]`` unscoped. docutils converts ``names`` into
implicit hyperlink targets, so multi-page docs using ``.. argparse::`` on
more than one page collided on ``usage`` / ``options`` / ``positional
arguments``, producing one ``duplicate label`` warning per collision. See
https://github.com/git-pull/gp-sphinx/issues/15.
"""

from __future__ import annotations

import typing as t

import pytest
from docutils import nodes

from sphinx_argparse_neo.parser import (
    ArgumentGroup,
    ArgumentInfo,
    ParserInfo,
)
from sphinx_argparse_neo.renderer import ArgparseRenderer


def _make_parser_info() -> ParserInfo:
    return ParserInfo(
        prog="myapp",
        usage=None,
        bare_usage="myapp [-h]",
        description=None,
        epilog=None,
        argument_groups=[],
        subcommands=None,
        subcommand_dest=None,
    )


def _make_positional_group() -> ArgumentGroup:
    return ArgumentGroup(
        title="positional arguments",
        description=None,
        arguments=[
            ArgumentInfo(
                names=["filename"],
                help="Input file",
                default=None,
                default_string="None",
                choices=None,
                required=True,
                metavar=None,
                nargs=None,
                action="store",
                type_name=None,
                const=None,
                dest="filename",
            ),
        ],
        mutually_exclusive=[],
    )


def _render_usage(id_prefix: str) -> nodes.section:
    return ArgparseRenderer().render_usage_section(
        _make_parser_info(), id_prefix=id_prefix
    )


def _render_group(id_prefix: str) -> nodes.section:
    return ArgparseRenderer().render_group_section(
        _make_positional_group(), id_prefix=id_prefix
    )


class SectionNameCase(t.NamedTuple):
    """Inputs and expectations for one names-match-ids assertion."""

    test_id: str
    make_section: t.Callable[[str], nodes.section]
    id_prefix: str
    expected_id: str


_SECTION_NAME_CASES: list[SectionNameCase] = [
    SectionNameCase(
        test_id="usage-no-prefix",
        make_section=_render_usage,
        id_prefix="",
        expected_id="usage",
    ),
    SectionNameCase(
        test_id="usage-with-prefix",
        make_section=_render_usage,
        id_prefix="load",
        expected_id="load-usage",
    ),
    SectionNameCase(
        test_id="group-no-prefix",
        make_section=_render_group,
        id_prefix="",
        expected_id="positional-arguments",
    ),
    SectionNameCase(
        test_id="group-with-prefix",
        make_section=_render_group,
        id_prefix="load",
        expected_id="load-positional-arguments",
    ),
]


@pytest.mark.parametrize(
    "case",
    _SECTION_NAME_CASES,
    ids=[c.test_id for c in _SECTION_NAME_CASES],
)
def test_section_names_match_ids(case: SectionNameCase) -> None:
    """``section["names"]`` mirrors ``section["ids"]`` under every prefix mode.

    This is the core property the fix guarantees: the implicit hyperlink
    target docutils derives from ``section["names"]`` carries the same
    scoping that ``section["ids"]`` already had.
    """
    section = case.make_section(case.id_prefix)
    assert section["ids"] == [case.expected_id]
    assert section["names"] == [case.expected_id]


class CollisionCase(t.NamedTuple):
    """Inputs for one two-page cross-collision assertion."""

    test_id: str
    make_section: t.Callable[[str], nodes.section]


_COLLISION_CASES: list[CollisionCase] = [
    CollisionCase(test_id="usage-sections", make_section=_render_usage),
    CollisionCase(test_id="group-sections", make_section=_render_group),
]


@pytest.mark.parametrize(
    "case",
    _COLLISION_CASES,
    ids=[c.test_id for c in _COLLISION_CASES],
)
def test_multi_page_sections_do_not_collide(case: CollisionCase) -> None:
    """Two pages emitting the same helper must produce disjoint targets.

    This is derivable from :func:`test_section_names_match_ids`, but asserting
    it directly documents the regression-test intent and gives a clearer
    failure mode when the fix regresses.
    """
    page_a = case.make_section("page-a")
    page_b = case.make_section("page-b")
    assert set(page_a["names"]).isdisjoint(page_b["names"])
    assert set(page_a["ids"]).isdisjoint(page_b["ids"])
