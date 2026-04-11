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


def test_usage_section_names_match_ids_without_prefix() -> None:
    """Without a prefix, usage section ``names`` equal its ``ids``."""
    section = ArgparseRenderer().render_usage_section(_make_parser_info())
    assert section["ids"] == ["usage"]
    assert section["names"] == ["usage"]


def test_usage_section_names_match_ids_with_prefix() -> None:
    """With a prefix, usage section ``names`` are scoped the same as ``ids``."""
    section = ArgparseRenderer().render_usage_section(
        _make_parser_info(), id_prefix="load"
    )
    assert section["ids"] == ["load-usage"]
    assert section["names"] == ["load-usage"]


def test_group_section_names_match_ids_without_prefix() -> None:
    """Without a prefix, group section ``names`` equal its ``ids``."""
    section = ArgparseRenderer().render_group_section(_make_positional_group())
    assert section["ids"] == ["positional-arguments"]
    assert section["names"] == ["positional-arguments"]


def test_group_section_names_match_ids_with_prefix() -> None:
    """With a prefix, group section ``names`` are scoped the same as ``ids``."""
    section = ArgparseRenderer().render_group_section(
        _make_positional_group(), id_prefix="load"
    )
    assert section["ids"] == ["load-positional-arguments"]
    assert section["names"] == ["load-positional-arguments"]


def test_multi_page_usage_sections_do_not_collide() -> None:
    """Two pages' usage sections must produce disjoint implicit targets."""
    renderer = ArgparseRenderer()
    page_a = renderer.render_usage_section(_make_parser_info(), id_prefix="page-a")
    page_b = renderer.render_usage_section(_make_parser_info(), id_prefix="page-b")
    assert set(page_a["names"]).isdisjoint(page_b["names"])
    assert set(page_a["ids"]).isdisjoint(page_b["ids"])


def test_multi_page_group_sections_do_not_collide() -> None:
    """Two pages' group sections must produce disjoint implicit targets."""
    renderer = ArgparseRenderer()
    page_a = renderer.render_group_section(_make_positional_group(), id_prefix="page-a")
    page_b = renderer.render_group_section(_make_positional_group(), id_prefix="page-b")
    assert set(page_a["names"]).isdisjoint(page_b["names"])
    assert set(page_a["ids"]).isdisjoint(page_b["ids"])
