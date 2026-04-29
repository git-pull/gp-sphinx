"""Cross-reference inventory emission.

Two artefacts are emitted from the same source data — the set of objects
this build exposes, walked from ``env.domains``:

- ``objects.inv`` (Sphinx's standard zlib-compressed inventory) so other
  Sphinx sites can ``intersphinx_mapping`` into our build.
- ``xref-index.json`` (typed JSON array of :class:`XrefEntry`) so the
  Astro side can resolve ``:py:func:``-style references at build time
  through a remark plugin.
"""

from __future__ import annotations

import typing as t

from gp_sphinx_astro_builder.models import XrefEntry

if t.TYPE_CHECKING:
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


def build_xref_index_entries(
    env: BuildEnvironment,
    builder: Builder,
) -> list[XrefEntry]:
    """Walk every domain's ``get_objects()`` into a sorted list of entries.

    The walk mirrors :meth:`sphinx.util.inventory.InventoryFile.dump`:
    each domain yields ``(fullname, dispname, role, docname, anchor,
    priority)`` tuples and we turn each into a typed :class:`XrefEntry`
    whose ``href`` combines :meth:`Builder.get_target_uri` with the
    optional anchor.

    Parameters
    ----------
    env
        The Sphinx build environment.
    builder
        The Sphinx builder. ``builder.get_target_uri`` produces the per-doc
        URI that combines with the anchor to make the ``href``.

    Returns
    -------
    list[XrefEntry]
        Sorted by ``(domain, role, target)`` so the emitted JSON is
        byte-stable across builds with the same inventory.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.intersphinx import build_xref_index_entries
    >>> callable(build_xref_index_entries)
    True
    """
    entries: list[XrefEntry] = []
    for domain in env.domains.sorted():
        for fullname, dispname, role, docname, anchor, priority in sorted(
            domain.get_objects(),
            key=_object_sort_key,
        ):
            href = builder.get_target_uri(docname)
            if anchor:
                href = f"{href}#{anchor}"
            # ``dispname`` may be a ``sphinx.locale._TranslationProxy``;
            # cast through ``str()`` so Pydantic gets a plain ``str``.
            display_str = str(dispname) if dispname else ""
            display = display_str if display_str and display_str != fullname else None
            entries.append(
                XrefEntry(
                    id=f"{domain.name}:{role}:{fullname}",
                    domain=domain.name,
                    role=role,
                    target=fullname,
                    href=href,
                    display=display,
                    priority=priority,
                ),
            )
    return entries


def _object_sort_key(
    item: tuple[str, t.Any, str, str, str, int],
) -> tuple[str, str, str]:
    """Stable sort key over ``(fullname, role, anchor)``.

    The default tuple ordering Sphinx itself uses includes ``dispname`` in
    position 1, which can be a ``_TranslationProxy`` that isn't comparable
    with ``str``. Stripping it from the key avoids spurious ``TypeError``
    raises during the sort.
    """
    fullname, _dispname, role, _docname, anchor, _priority = item
    return (fullname, role, anchor)
