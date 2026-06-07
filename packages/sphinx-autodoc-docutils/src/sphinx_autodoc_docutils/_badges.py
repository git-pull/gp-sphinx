"""Badge helpers for sphinx_autodoc_docutils reference entries."""

from __future__ import annotations

from docutils import nodes

from sphinx_ux_badges import SAB, BadgeSpec, build_badge_group_from_specs

_GROUP_CLASS = SAB.BADGE_GROUP

_KIND_CLASSES: dict[str, str] = {
    "directive": SAB.TYPE_DIRECTIVE,
    "role": SAB.TYPE_ROLE,
    "option": SAB.TYPE_OPTION,
    "transform": SAB.TYPE_TRANSFORM,
    "reader": SAB.TYPE_READER,
    "parser": SAB.TYPE_PARSER,
    "writer": SAB.TYPE_WRITER,
    "node": SAB.TYPE_NODE,
    "translator": SAB.TYPE_TRANSLATOR,
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

    Examples
    --------
    >>> "directive" in build_kind_badge_group("directive").astext()
    True
    >>> "reader" in build_kind_badge_group("reader").astext()
    True

    Unknown kinds keep their label and fall back to the directive
    colour class:

    >>> "mystery" in build_kind_badge_group("mystery").astext()
    True
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


def build_translator_badge_group(*, override: bool = False) -> nodes.inline:
    """Return header badges for one documented docutils translator.

    Parameters
    ----------
    override : bool
        Whether the translator was registered with
        ``set_translator(..., override=True)``; rendered as an outlined
        secondary badge.

    Returns
    -------
    nodes.inline
        Badge group for the entry header.

    Examples
    --------
    >>> "translator" in build_translator_badge_group().astext()
    True
    >>> "override" in build_translator_badge_group(override=True).astext()
    True
    >>> "override" in build_translator_badge_group().astext()
    False
    """
    specs = [
        BadgeSpec(
            "translator",
            tooltip="Docutils translator",
            classes=(SAB.TYPE_TRANSLATOR,),
        ),
    ]
    if override:
        specs.append(
            BadgeSpec(
                "override",
                tooltip="Registered with set_translator(override=True)",
                classes=(SAB.STATE_OVERRIDE,),
                fill="outline",
            ),
        )
    return build_badge_group_from_specs(specs, classes=[_GROUP_CLASS])


def build_transform_badge_group(priority: int | None = None) -> nodes.inline:
    """Return header badges for one documented docutils transform.

    Parameters
    ----------
    priority : int | None
        The transform's ``default_priority``; rendered as an outlined
        secondary badge when set.

    Returns
    -------
    nodes.inline
        Badge group for the entry header.

    Examples
    --------
    >>> group = build_transform_badge_group(830)
    >>> "transform" in group.astext()
    True
    >>> "priority 830" in group.astext()
    True
    >>> "priority" in build_transform_badge_group(None).astext()
    False
    """
    specs = [
        BadgeSpec(
            "transform",
            tooltip="Docutils transform",
            classes=(SAB.TYPE_TRANSFORM,),
        ),
    ]
    if priority is not None:
        specs.append(
            BadgeSpec(
                f"priority {priority}",
                tooltip="Transform default_priority",
                classes=(SAB.MOD_PRIORITY,),
                fill="outline",
            ),
        )
    return build_badge_group_from_specs(specs, classes=[_GROUP_CLASS])
