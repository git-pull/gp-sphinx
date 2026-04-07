"""Badge group rendering helpers for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

from docutils import nodes
from sphinx_autodoc_badges import BadgeNode, build_badge

from sphinx_autodoc_pytest_fixtures._constants import _SUPPRESSED_SCOPES
from sphinx_autodoc_pytest_fixtures._css import _CSS

_BADGE_TOOLTIPS: dict[str, str] = {
    "session": "Scope: session \u2014 created once per test session",
    "module": "Scope: module \u2014 created once per test module",
    "class": "Scope: class \u2014 created once per test class",
    "factory": "Factory \u2014 returns a callable that creates instances",
    "override_hook": "Override hook \u2014 customize in conftest.py",
    "fixture": "pytest fixture \u2014 injected by name into test functions",
    "autouse": "Runs automatically for every test (autouse=True)",
    "deprecated": "Deprecated \u2014 see docs for replacement",
}


def _build_badge_group_node(
    scope: str,
    kind: str,
    autouse: bool,
    *,
    deprecated: bool = False,
    show_fixture_badge: bool = True,
) -> nodes.inline:
    """Return a badge group with shared BadgeNode children.

    Badge slots (left-to-right in visual order):

    * Slot 0 (deprecated): shown when fixture is deprecated
    * Slot 1 (scope):   shown when ``scope != "function"``
    * Slot 2 (kind):    shown for ``"factory"`` / ``"override_hook"``; or
                        state badge (``"autouse"``) when ``autouse=True``
    * Slot 3 (FIXTURE): shown when ``show_fixture_badge=True`` (default)

    Parameters
    ----------
    scope : str
        Fixture scope string.
    kind : str
        Fixture kind string.
    autouse : bool
        When True, renders AUTO state badge instead of a kind badge.
    deprecated : bool
        When True, renders a deprecated badge at slot 0 (leftmost).
    show_fixture_badge : bool
        When False, suppresses the FIXTURE badge at slot 3.

    Returns
    -------
    nodes.inline
        Badge group container with BadgeNode children.
    """
    group = nodes.inline(classes=[_CSS.BADGE_GROUP])
    badges: list[BadgeNode] = []

    if deprecated:
        badges.append(
            build_badge(
                "deprecated",
                tooltip=_BADGE_TOOLTIPS["deprecated"],
                classes=[_CSS.BADGE, _CSS.BADGE_STATE, _CSS.DEPRECATED],
            )
        )

    if scope and scope not in _SUPPRESSED_SCOPES:
        badges.append(
            build_badge(
                scope,
                tooltip=_BADGE_TOOLTIPS.get(scope, f"Scope: {scope}"),
                classes=[_CSS.BADGE, _CSS.BADGE_SCOPE, _CSS.scope(scope)],
            )
        )

    if autouse:
        badges.append(
            build_badge(
                "auto",
                tooltip=_BADGE_TOOLTIPS["autouse"],
                classes=[_CSS.BADGE, _CSS.BADGE_STATE, _CSS.AUTOUSE],
            )
        )
    elif kind == "factory":
        badges.append(
            build_badge(
                "factory",
                tooltip=_BADGE_TOOLTIPS["factory"],
                classes=[_CSS.BADGE, _CSS.BADGE_KIND, _CSS.FACTORY],
            )
        )
    elif kind == "override_hook":
        badges.append(
            build_badge(
                "override",
                tooltip=_BADGE_TOOLTIPS["override_hook"],
                classes=[_CSS.BADGE, _CSS.BADGE_KIND, _CSS.OVERRIDE],
            )
        )

    if show_fixture_badge:
        badges.append(
            build_badge(
                "fixture",
                tooltip=_BADGE_TOOLTIPS["fixture"],
                classes=[_CSS.BADGE, _CSS.BADGE_FIXTURE],
            )
        )

    for i, badge in enumerate(badges):
        group += badge
        if i < len(badges) - 1:
            group += nodes.Text(" ")

    return group
