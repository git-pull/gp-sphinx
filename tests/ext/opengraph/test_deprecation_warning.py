"""Warning-emission tests for gp_opengraph.

``ogp_social_cards`` is accepted-but-ignored in gp-opengraph. Setting it
must emit a one-line warning pointing users at the static-image
workflow.
"""

from __future__ import annotations

import logging
import typing as t

import pytest

from gp_opengraph import _warn_if_social_cards_used


class WarnCase(t.NamedTuple):
    """One warning-emission case."""

    test_id: str
    ogp_social_cards: t.Any
    should_warn: bool


CASES: tuple[WarnCase, ...] = (
    WarnCase(
        test_id="empty-dict-triggers-no-warning",
        ogp_social_cards={},
        should_warn=False,
    ),
    WarnCase(
        test_id="none-triggers-no-warning",
        ogp_social_cards=None,
        should_warn=False,
    ),
    WarnCase(
        test_id="enable-true-warns",
        ogp_social_cards={"enable": True},
        should_warn=True,
    ),
    WarnCase(
        test_id="populated-dict-warns",
        ogp_social_cards={"image": "path/to/img.png", "description_length": 100},
        should_warn=True,
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[c.test_id for c in CASES])
def test_deprecation_warning(
    case: WarnCase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The warning fires iff ogp_social_cards carries a non-empty value."""

    class _Config:
        ogp_social_cards = case.ogp_social_cards

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="gp_opengraph"):
        _warn_if_social_cards_used(
            app=None,  # type: ignore[arg-type]
            config=t.cast("t.Any", _Config()),
        )
    warnings = [
        record.message for record in caplog.records if record.levelno >= logging.WARNING
    ]
    if case.should_warn:
        assert warnings, f"{case.test_id}: expected a warning, got none"
        assert any("ogp_social_cards" in m for m in warnings), (
            f"{case.test_id}: no 'ogp_social_cards' text in {warnings!r}"
        )
    else:
        assert not warnings, f"{case.test_id}: unexpected warning {warnings!r}"
