"""Eliminate flash-of-wrong-selection on synced ``gp-sphinx-tabs`` restore.

The package's :mod:`~sphinx_ux_tabs._static.js.sphinx_ux_tabs_sync` bundle
restores a saved selection from ``localStorage`` (and applies URL params
like ``?shell=bash``) once the DOM is ready.  On first paint the user
briefly sees the server-rendered default tab before the JS swaps to the
saved selection — a visible flash on every page load and on every
gp-sphinx SPA navigation.

This module emits two artefacts into ``<head>`` (via Furo's ``metatags``
slot) on every page that hosts a sync'd tab set:

* An inline ``<script data-cfasync="false">`` that, for each distinct
  ``data-sync-group`` value on the page, reads
  ``localStorage["gp-sphinx-tabs.sync.<group>"]`` and the URL query
  string (both ``?<group>=<id>`` and ``?tabs=<label>`` forms — the
  latter is honoured by the JS but not by this prehydrate), then sets
  ``<html data-gp-sphinx-tabs-sync-<group>="<id>">`` before any
  stylesheet loads.  ``data-cfasync="false"`` opts the inline script
  out of Cloudflare Rocket Loader so it runs synchronously as written.

* A ``<style>`` block under ``@layer gp-sphinx-tabs-prehydrate`` whose
  attribute selectors paint the matching label and panel directly
  from those ``<html>`` data attributes.  The radio ``<input>`` itself
  cannot be ``:checked`` from a CSS attribute selector, but the visual
  outcome (active label colour + visible panel) is what eliminates
  the flash.  Once the JS hydrates, the standard ``:checked + label +
  panel`` adjacency selectors take over.

A page with no sync'd tabs gets no prehydrate payload — the env walk
in :class:`~sphinx_ux_tabs._transforms.TabsPostTransform` collects an
empty set, and :func:`inject_tabs_prehydrate` short-circuits.

Examples
--------
>>> _build_style([("shell", "bash"), ("shell", "zsh")]).startswith("<style>")
True

>>> "@layer gp-sphinx-tabs-prehydrate" in _build_style([("shell", "bash")])
True

>>> 'data-cfasync="false"' in _script({"shell"})
True

>>> _build_style([])
''

>>> _script(set())
''
"""

from __future__ import annotations

import json
import typing as t

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

#: Attribute name used on :class:`sphinx.environment.BuildEnvironment` to
#: stash the per-docname set of ``(sync_group, sync_id)`` pairs collected
#: during the post-transform pass.  Read at ``html-page-context`` time.
ENV_ATTR = "gp_sphinx_tabs_sync_pairs"

#: CSS cascade layer name for the prehydrate rules.  Distinct from the
#: package's main ``@layer gp-sphinx`` layer so the prehydrate rules can
#: be ordered independently and addressed by tests.
LAYER_NAME = "gp-sphinx-tabs-prehydrate"

#: Prefix for the ``<html>`` data attribute that carries the saved
#: ``sync_id`` for a given sync group.  Example: ``shell`` →
#: ``data-gp-sphinx-tabs-sync-shell``.
HTML_ATTR_PREFIX = "data-gp-sphinx-tabs-sync-"

#: Prefix for the ``localStorage`` key the inline script reads.  Mirrors
#: ``STORAGE_PREFIX`` in ``sphinx_ux_tabs_sync.js`` — keep in sync.
STORAGE_PREFIX = "gp-sphinx-tabs.sync."


def _build_style(pairs: t.Iterable[tuple[str, str]]) -> str:
    """Return the ``<style>`` block that paints active labels and panels.

    For each ``(group, id)`` pair the function emits two attribute-selector
    rules: one styling the matching ``.gp-sphinx-tabs__label`` like the
    standard ``:checked + label`` rule, and one revealing the matching
    ``.gp-sphinx-tabs__panel`` (``display: block``).  Both rules key on
    ``html[data-gp-sphinx-tabs-sync-<group>="<id>"]`` so the inline
    script's single ``<html>`` mutation drives the whole page.

    All declarations are wrapped in ``@layer gp-sphinx-tabs-prehydrate``.
    The dedicated layer keeps the rules ordered independently of the
    package's main ``@layer gp-sphinx`` styles.

    Parameters
    ----------
    pairs : Iterable[tuple[str, str]]
        ``(sync_group, sync_id)`` pairs collected from the page.  An
        empty iterable yields the empty string so the caller can append
        unconditionally.

    Returns
    -------
    str
        A ``<style>...</style>`` block, or ``""`` when ``pairs`` is empty.

    Examples
    --------
    >>> style = _build_style([("shell", "bash")])
    >>> 'html[data-gp-sphinx-tabs-sync-shell="bash"]' in style
    True

    >>> '.gp-sphinx-tabs__label[data-sync-id="bash"]' in style
    True

    >>> 'display: block' in style
    True
    """
    seen = list(dict.fromkeys(pairs))
    if not seen:
        return ""

    rules: list[str] = []
    for group, sync_id in seen:
        html_attr = f'html[{HTML_ATTR_PREFIX}{group}="{sync_id}"]'
        label_sel = (
            f"{html_attr} .gp-sphinx-tabs__label"
            f'[data-sync-id="{sync_id}"][data-sync-group="{group}"]'
        )
        panel_sel = (
            f"{html_attr} .gp-sphinx-tabs__panel"
            f'[data-sync-id="{sync_id}"][data-sync-group="{group}"]'
        )
        rules.append(
            f"{label_sel} {{"
            "color: var(--color-brand-primary);"
            "border-bottom-color: var(--color-brand-primary);"
            "background: var(--color-background-primary);"
            "}"
        )
        rules.append(f"{panel_sel} {{display: block;}}")
    return f"<style>@layer {LAYER_NAME} {{{''.join(rules)}}}</style>"


def _script(groups: t.Iterable[str]) -> str:
    r"""Return the inline ``<head>`` script that mirrors saved state onto ``<html>``.

    For each distinct ``sync_group`` value on the page the script reads
    ``localStorage["gp-sphinx-tabs.sync.<group>"]`` and the URL query
    parameter ``?<group>=<id>``, with the URL value winning (matches the
    precedence in ``sphinx_ux_tabs_sync.js``).  Each resolved value is
    written to ``<html data-gp-sphinx-tabs-sync-<group>="<id>">`` before
    any stylesheet loads, so the prehydrate CSS rules match on first
    paint.

    Storage and URL access are wrapped in ``try/catch`` so the script
    fails silent in private-browsing or sandboxed contexts.  The
    ``data-cfasync="false"`` attribute opts the script out of Cloudflare
    Rocket Loader (which rewrites inline scripts to defer-load
    asynchronously).

    The groups array is serialized via :func:`json.dumps` so any
    pathological group name (quotes, backslashes, control characters)
    is correctly escaped — a hand-rolled ``"x"`` concat would emit a
    syntactically invalid JS literal for a group named ``a"b``, killing
    the inline script at parse time (the outer ``try/catch`` cannot
    catch parse-time ``SyntaxError``).

    Inside the loop, ``setAttribute`` is gated on a
    ``/^[A-Za-z0-9_-]+$/`` test against the group name.  HTML attribute
    names cannot contain spaces, ``"``, ``'``, ``>``, ``/``, or ``=``;
    an invalid name makes ``setAttribute`` throw, which (because the
    ``try/catch`` wraps the whole IIFE) would abort the loop and lose
    every remaining group's restore.  Author-controlled RST option
    parsing already restricts the alphabet in practice, so the guard
    is a defence-in-depth measure.

    Parameters
    ----------
    groups : Iterable[str]
        Distinct ``sync_group`` values on the page.

    Returns
    -------
    str
        A ``<script>...</script>`` block, or ``""`` when ``groups`` is
        empty.

    Examples
    --------
    >>> script = _script({"shell"})
    >>> 'data-cfasync="false"' in script
    True

    >>> "localStorage.getItem" in script
    True

    >>> "gp-sphinx-tabs.sync." in script
    True

    >>> "try" in script and "catch" in script
    True

    A group name containing a double-quote is JSON-escaped, not
    splatted raw into the array literal:

    >>> snippet = _script(['a"b'])
    >>> r'"a\"b"' in snippet
    True

    The ``setAttribute`` call is gated on a regex so invalid HTML
    attribute-name chars cannot throw ``DOMException``:

    >>> "/^[A-Za-z0-9_-]+$/.test(k)" in _script({"shell"})
    True
    """
    # Deterministic order so the emitted script is stable across builds —
    # eases snapshot diffs and inline ``<head>`` review.
    sorted_groups = sorted({g for g in groups if g})
    if not sorted_groups:
        return ""
    # json.dumps escapes quotes, backslashes, and control characters so
    # the embedded array literal is always a valid JS expression.
    groups_literal = json.dumps(sorted_groups)
    return (
        '<script data-cfasync="false">(function(){'
        "try{"
        "var h=document.documentElement;"
        "var p=null;"
        "try{p=new URLSearchParams(window.location.search);}catch(_){}"
        f"var g={groups_literal};"
        "for(var i=0;i<g.length;i++){"
        "var k=g[i];"
        "var v=null;"
        "if(p){v=p.get(k);}"
        'if(!v){try{v=localStorage.getItem("' + STORAGE_PREFIX + '"+k);}catch(_){}}'
        "if(v && /^[A-Za-z0-9_-]+$/.test(k)){"
        'h.setAttribute("' + HTML_ATTR_PREFIX + '"+k,v);'
        "}"
        "}"
        "}catch(_){}"
        "})();</script>"
    )


def init_env_store(env: t.Any) -> dict[str, set[tuple[str, str]]]:
    """Return (creating if needed) the per-docname pair store on ``env``.

    The store maps ``docname`` → ``set[(sync_group, sync_id)]``.  Use this
    helper to read or write the env attribute without scattering
    ``getattr`` defaults throughout the package.

    Parameters
    ----------
    env : Any
        The Sphinx build environment.

    Returns
    -------
    dict[str, set[tuple[str, str]]]
        The mutable store dict.

    Examples
    --------
    >>> class E: pass
    >>> e = E()
    >>> store = init_env_store(e)
    >>> store == {}
    True

    >>> store["index"] = {("shell", "bash")}
    >>> init_env_store(e)["index"]
    {('shell', 'bash')}
    """
    store: dict[str, set[tuple[str, str]]] | None = getattr(env, ENV_ATTR, None)
    if store is None:
        store = {}
        setattr(env, ENV_ATTR, store)
    return store


def record_pair(env: t.Any, docname: str, group: str, sync_id: str) -> None:
    """Record one ``(group, sync_id)`` pair against ``docname``.

    No-op when either ``group`` or ``sync_id`` is empty — tabs without a
    ``:sync:`` directive option don't participate in the prehydrate.

    Parameters
    ----------
    env : Any
        The Sphinx build environment.
    docname : str
        The current document name (``env.docname`` during the
        post-transform pass).
    group : str
        Sync-group identifier (``data-sync-group``).
    sync_id : str
        Tab-item sync id (``data-sync-id``).

    Examples
    --------
    >>> class E: pass
    >>> e = E()
    >>> record_pair(e, "index", "shell", "bash")
    >>> init_env_store(e)["index"]
    {('shell', 'bash')}

    >>> record_pair(e, "index", "", "bash")  # empty group → ignored
    >>> init_env_store(e)["index"]
    {('shell', 'bash')}
    """
    if not group or not sync_id:
        return
    init_env_store(env).setdefault(docname, set()).add((group, sync_id))


def purge_doc(env: t.Any, docname: str) -> None:
    """Drop the recorded pair set for ``docname``.

    Wired to the ``env-purge-doc`` Sphinx event so incremental rebuilds
    don't carry stale sync pairs from a previous read of the same page.

    Parameters
    ----------
    env : Any
        The Sphinx build environment.
    docname : str
        The document being re-read.

    Examples
    --------
    >>> class E: pass
    >>> e = E()
    >>> record_pair(e, "index", "shell", "bash")
    >>> purge_doc(e, "index")
    >>> init_env_store(e)
    {}
    """
    store = init_env_store(env)
    store.pop(docname, None)


def merge_info(env: t.Any, other_env: t.Any) -> None:
    """Merge pair records from a parallel-build sub-environment.

    Wired to the ``env-merge-info`` event.  Parallel builds shard the
    doc set across worker processes; this hook copies each worker's
    records into the primary env.

    Parameters
    ----------
    env : Any
        The primary (receiving) build environment.
    other_env : Any
        The worker env whose records merge into ``env``.

    Examples
    --------
    >>> class E: pass
    >>> primary, worker = E(), E()
    >>> record_pair(worker, "index", "shell", "bash")
    >>> merge_info(primary, worker)
    >>> init_env_store(primary)["index"]
    {('shell', 'bash')}
    """
    other_store = getattr(other_env, ENV_ATTR, None)
    if not other_store:
        return
    store = init_env_store(env)
    for docname, pairs in other_store.items():
        store.setdefault(docname, set()).update(pairs)


def inject_tabs_prehydrate(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, t.Any],
    doctree: object,
) -> None:
    """Inject the prehydrate ``<style>`` + ``<script>`` into Furo's ``<head>``.

    Reads the pair set recorded for ``pagename`` from
    :data:`ENV_ATTR` on ``app.env``.  Bails early (no ``metatags``
    mutation) when the set is empty so pages without sync'd tabs carry
    zero prehydrate payload.

    Otherwise builds the per-page CSS via :func:`_build_style` and the
    per-page inline script via :func:`_script`, and appends both to
    ``context["metatags"]`` — Furo renders that slot inside ``<head>``
    before any stylesheet loads.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application.
    pagename : str
        Name of the page being rendered.
    templatename : str
        Name of the template being used (unused).
    context : dict[str, Any]
        Rendering context passed to the template.
    doctree : object
        Doctree for the page (unused).

    Examples
    --------
    >>> inject_tabs_prehydrate.__name__
    'inject_tabs_prehydrate'
    """
    del templatename, doctree
    store: dict[str, set[tuple[str, str]]] | None = getattr(app.env, ENV_ATTR, None)
    if not store:
        return
    pairs = store.get(pagename)
    if not pairs:
        return
    groups = {group for group, _id in pairs}
    snippet = _build_style(sorted(pairs)) + _script(groups)
    if not snippet:
        return
    context["metatags"] = context.get("metatags", "") + snippet


__all__ = [
    "ENV_ATTR",
    "HTML_ATTR_PREFIX",
    "LAYER_NAME",
    "STORAGE_PREFIX",
    "_build_style",
    "_script",
    "init_env_store",
    "inject_tabs_prehydrate",
    "merge_info",
    "purge_doc",
    "record_pair",
]
