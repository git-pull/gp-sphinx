"""Badge helpers for sphinx_autodoc_docutils reference entries."""

from __future__ import annotations

from docutils import nodes

from sphinx_ux_badges import SAB, BadgeSpec, build_badge_group_from_specs

_GROUP_CLASS = SAB.BADGE_GROUP

_KIND_CLASSES: dict[str, str] = {
    "directive": SAB.TYPE_DIRECTIVE,
    "role": SAB.TYPE_ROLE,
    "option": SAB.TYPE_OPTION,
}


def build_kind_badge_group(kind: str) -> nodes.inline:
    """Return header badges for one documented docutils object.

    Parameters
    ----------
    kind : str
        Entry kind such as ``"directive"``, ``"role"``, or ``"option"``.

    Returns
    -------
    nodes.inline
        Badge group for the entry header.
    """
    colour_class = _KIND_CLASSES.get(kind, SAB.TYPE_DIRECTIVE)
    return build_badge_group_from_specs(
        [
            BadgeSpec(
                kind,
                tooltip=f"Docutils {kind}",
                classes=(colour_class,),
            ),
        ],
        classes=[_GROUP_CLASS],
    )
