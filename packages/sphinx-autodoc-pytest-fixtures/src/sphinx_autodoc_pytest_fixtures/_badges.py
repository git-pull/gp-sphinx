"""Badge group rendering helpers for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

from docutils import nodes

from sphinx_autodoc_pytest_fixtures._constants import _SUPPRESSED_SCOPES
from sphinx_ux_badges import SAB, BadgeSpec, build_badge_group_from_specs

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


def _fixture_badge_specs(
    scope: str,
    kind: str,
    autouse: bool,
    *,
    deprecated: bool = False,
    show_fixture_badge: bool = True,
) -> list[BadgeSpec]:
    """Return typed badge specs for one fixture entry."""
    badges: list[BadgeSpec] = []

    if deprecated:
        badges.append(
            BadgeSpec(
                "deprecated",
                tooltip=_BADGE_TOOLTIPS["deprecated"],
                classes=(SAB.BADGE, SAB.BADGE_STATE, SAB.STATE_DEPRECATED),
                fill="filled",
            )
        )

    if scope and scope not in _SUPPRESSED_SCOPES:
        badges.append(
            BadgeSpec(
                scope,
                tooltip=_BADGE_TOOLTIPS.get(scope, f"Scope: {scope}"),
                classes=(SAB.BADGE, SAB.BADGE_SCOPE, SAB.scope(scope)),
            )
        )

    if autouse:
        badges.append(
            BadgeSpec(
                "auto",
                tooltip=_BADGE_TOOLTIPS["autouse"],
                classes=(SAB.BADGE, SAB.BADGE_STATE, SAB.STATE_AUTOUSE),
                fill="outline",
            )
        )
    elif kind == "factory":
        badges.append(
            BadgeSpec(
                "factory",
                tooltip=_BADGE_TOOLTIPS["factory"],
                classes=(SAB.BADGE, SAB.BADGE_KIND, SAB.STATE_FACTORY),
                fill="outline",
            )
        )
    elif kind == "override_hook":
        badges.append(
            BadgeSpec(
                "override",
                tooltip=_BADGE_TOOLTIPS["override_hook"],
                classes=(SAB.BADGE, SAB.BADGE_KIND, SAB.STATE_OVERRIDE),
                fill="outline",
            )
        )

    if show_fixture_badge:
        badges.append(
            BadgeSpec(
                "fixture",
                tooltip=_BADGE_TOOLTIPS["fixture"],
                classes=(SAB.BADGE, SAB.BADGE_FIXTURE, SAB.TYPE_FIXTURE),
            )
        )

    return badges


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
    return build_badge_group_from_specs(
        _fixture_badge_specs(
            scope,
            kind,
            autouse,
            deprecated=deprecated,
            show_fixture_badge=show_fixture_badge,
        ),
        classes=[SAB.BADGE_GROUP],
    )
