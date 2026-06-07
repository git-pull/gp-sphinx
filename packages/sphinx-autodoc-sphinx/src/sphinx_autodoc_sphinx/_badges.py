"""Badge helpers for sphinx_autodoc_sphinx config-value entries."""

from __future__ import annotations

import typing as t

from docutils import nodes

from sphinx_ux_badges import SAB, BadgeSpec, build_badge_group_from_specs

if t.TYPE_CHECKING:
    from sphinx_autodoc_sphinx._directives import SphinxConfigValue

_GROUP_CLASS = SAB.BADGE_GROUP


def build_config_badge_group(value: SphinxConfigValue) -> nodes.inline:
    """Return header badges for one documented config value.

    Parameters
    ----------
    value : SphinxConfigValue
        Config value metadata captured from the extension ``setup()`` hook.

    Returns
    -------
    nodes.inline
        Badge group containing the config kind and rebuild mode badges.
    """
    rebuild = value.rebuild or "none"
    return build_badge_group_from_specs(
        [
            BadgeSpec(
                "config",
                tooltip="Sphinx config value",
                classes=(SAB.TYPE_CONFIG,),
            ),
            BadgeSpec(
                rebuild,
                tooltip=f"Rebuild mode: {rebuild}",
                classes=(SAB.MOD_REBUILD,),
                fill="outline",
            ),
        ],
        classes=[_GROUP_CLASS],
    )


def build_domain_badge_group(domain_name: str = "") -> nodes.inline:
    """Return header badges for one documented Sphinx domain.

    Parameters
    ----------
    domain_name : str
        The domain's registered name (its role prefix); rendered as an
        outlined secondary badge when non-empty.

    Returns
    -------
    nodes.inline
        Badge group for the entry header.

    Examples
    --------
    >>> group = build_domain_badge_group("argparse")
    >>> "domain" in group.astext()
    True
    >>> "argparse" in group.astext()
    True
    >>> build_domain_badge_group("").astext()
    'domain'
    """
    specs = [
        BadgeSpec(
            "domain",
            tooltip="Sphinx domain",
            classes=(SAB.TYPE_DOMAIN,),
        ),
    ]
    if domain_name:
        specs.append(
            BadgeSpec(
                domain_name,
                tooltip=f"Domain name: {domain_name}",
                classes=(SAB.MOD_DOMAIN_NAME,),
                fill="outline",
            ),
        )
    return build_badge_group_from_specs(specs, classes=[_GROUP_CLASS])


def build_builder_badge_group(output_format: str = "") -> nodes.inline:
    """Return header badges for one documented Sphinx builder.

    Parameters
    ----------
    output_format : str
        The builder's ``format`` attribute; rendered as an outlined
        secondary badge when non-empty.

    Returns
    -------
    nodes.inline
        Badge group for the entry header.

    Examples
    --------
    >>> group = build_builder_badge_group("html")
    >>> "builder" in group.astext()
    True
    >>> "html" in group.astext()
    True
    >>> build_builder_badge_group("").astext()
    'builder'
    """
    specs = [
        BadgeSpec(
            "builder",
            tooltip="Sphinx builder",
            classes=(SAB.TYPE_BUILDER,),
        ),
    ]
    if output_format:
        specs.append(
            BadgeSpec(
                output_format,
                tooltip=f"Output format: {output_format}",
                classes=(SAB.MOD_FORMAT,),
                fill="outline",
            ),
        )
    return build_badge_group_from_specs(specs, classes=[_GROUP_CLASS])
