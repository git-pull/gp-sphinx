"""MyST ``{bdg-*}`` role factory and registration.

Provides 22 drop-in roles -- ``{bdg-<color>}`` and ``{bdg-<color>-line}`` --
that emit a :class:`BadgeNode` carrying the gp-sphinx-* color classes from
``sab_palettes.css``. Each role accepts the literal role text as the visible
badge label, matching sphinx-design's authoring surface.

Examples
--------
>>> _BDG_COLORS[0]
'primary'

>>> len(_BDG_COLORS)
11

>>> role = _make_bdg_role("primary", outline=False)
>>> nodes_, messages = role(
...     "bdg-primary",
...     "{bdg-primary}`Hi`",
...     "Hi",
...     0,
...     None,  # type: ignore[arg-type]
... )
>>> badge = nodes_[0]
>>> badge.astext()
'Hi'

>>> "gp-sphinx-badge--color-primary" in badge["classes"]
True

>>> "gp-sphinx-badge--filled" in badge["classes"]
True

>>> outline_role = _make_bdg_role("danger", outline=True)
>>> outline_nodes, _ = outline_role(
...     "bdg-danger-line",
...     "{bdg-danger-line}`Hot`",
...     "Hot",
...     0,
...     None,  # type: ignore[arg-type]
... )
>>> "gp-sphinx-badge--outline" in outline_nodes[0]["classes"]
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_ux_badges._css import SAB
from sphinx_ux_badges._nodes import BadgeNode

if t.TYPE_CHECKING:
    from docutils.parsers.rst.states import Inliner
    from sphinx.application import Sphinx
    from sphinx.util.typing import RoleFunction


_BDG_COLORS: tuple[str, ...] = (
    "primary",
    "secondary",
    "success",
    "info",
    "warning",
    "danger",
    "light",
    "muted",
    "dark",
    "white",
    "black",
)


def _make_bdg_role(color: str, *, outline: bool) -> RoleFunction:
    """Return a docutils role function for ``{bdg-<color>}`` markup.

    Parameters
    ----------
    color : str
        Semantic color name (e.g. ``"primary"``, ``"danger"``).
    outline : bool
        When ``True`` the badge gets :attr:`SAB.OUTLINE`; otherwise
        :attr:`SAB.FILLED`.

    Returns
    -------
    RoleFunction
        Callable suitable for :meth:`sphinx.application.Sphinx.add_role`.

    Examples
    --------
    >>> role = _make_bdg_role("success", outline=False)
    >>> callable(role)
    True
    """
    fill_class = SAB.OUTLINE if outline else SAB.FILLED
    color_class = f"gp-sphinx-badge--color-{color}"

    def role(
        name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Inliner,
        /,
        options: dict[str, t.Any] | None = None,
        content: t.Sequence[str] = (),
    ) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        badge = BadgeNode(
            text,
            classes=[color_class, fill_class],
        )
        return [badge], []

    role.__name__ = f"bdg_{color}{'_line' if outline else ''}_role"
    role.__qualname__ = role.__name__
    return role


def register_bdg_roles(app: Sphinx) -> None:
    """Register all ``{bdg-<color>}`` and ``{bdg-<color>-line}`` roles.

    Parameters
    ----------
    app : Sphinx
        Sphinx application.

    Examples
    --------
    >>> from sphinx_ux_badges._roles import register_bdg_roles
    >>> callable(register_bdg_roles)
    True
    """
    for color in _BDG_COLORS:
        app.add_role(f"bdg-{color}", _make_bdg_role(color, outline=False))
        app.add_role(
            f"bdg-{color}-line",
            _make_bdg_role(color, outline=True),
        )
