"""Badge helpers for sphinx_autodoc_docutils reference entries."""

from __future__ import annotations

from docutils import nodes
from sphinx_autodoc_badges import BadgeSpec, build_badge_group_from_specs

_GROUP_CLASS = "sadoc-badge-group"
_TYPE_CLASS = "sadoc-badge--type"


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
    return build_badge_group_from_specs(
        [
            BadgeSpec(
                kind,
                tooltip=f"Docutils {kind}",
                classes=(_TYPE_CLASS,),
            ),
        ],
        classes=[_GROUP_CLASS],
    )
