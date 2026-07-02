# Documentation voice

This file covers the *voice* of prose under `docs/` — how to frame a
page so a reader meets the idea before its configuration. It
complements the repository-root `AGENTS.md`, which already governs
code blocks, shell-command formatting, doctests, changelog
conventions, and MyST roles. When the two overlap, the root file
wins; this one only answers: how should the prose sound?

## Who you are writing for

The default reader maintains another project's docs site and wires
`merge_sphinx_config()` into that project's `docs/conf.py`. They are
fluent in Sphinx itself — `conf.py`, extensions, themes, MyST
Markdown — but you cannot assume they know gp-sphinx's internals: the
workspace tier map, the merge order (`DEFAULT_*` constants, then
values auto-computed from `source_repository` and `docs_url`, then
`**overrides`), or the theme's Vite asset pipeline.

A second, smaller reader works *on* the workspace: adding a package,
extending an autodoc extension, touching `gp-furo-theme`'s `web/src`
assets or the `sphinx-vite-builder` backend. Serve them too, but mark
their material opt-in ("for workspace contributors", "advanced") so
the default reader knows they can stop. Never make the common case
pay a comprehension tax for the advanced one.

## Voice

- **Second person, present tense, active.** "You pass `docs_url`",
  not "SEO values are derived". Address the reader doing the thing.
- **Concept before configuration.** Open by saying what the thing
  *is* and what it does for the reader's site. The kwarg surface is
  the last detail they need, not the first. A page that opens with
  "pass these keyword arguments" has buried the idea under its
  mechanics.
- **Say when they can stop.** Lead with the default and the
  reassurance: the ~10-line `merge_sphinx_config()` call is the whole
  integration; everything past it is optional. Let a skimmer leave
  after one paragraph.
- **Progressive disclosure.** Order by how many readers need it: the
  coordinator call → the one kwarg a few will tune (`docs_url`,
  `extra_extensions`) → a single package's own options → workspace
  internals. Each step is for a smaller audience than the last.
- **Lean on the merge order.** The reader's mental model of
  `merge_sphinx_config()` is a pipeline: shared defaults, then values
  auto-computed from `source_repository` and `docs_url`, then
  `**overrides` applied last — an explicit value always wins.
  Reinforce that order when you explain who sets what. On package
  pages the equivalent is the tier map: shared infrastructure →
  autodoc extensions → theme and coordinator.
- **Name the trade-off.** If an option costs something, say so, and
  say what it buys: `vite_orchestration=True` spawns a pnpm/Vite
  watcher under `sphinx-autobuild` — contributors need Node, wheel
  consumers don't. State it; don't sell it.
- **Frame by concept, not by mechanism.** Don't headline a feature by
  its kwarg or CSS custom property in prose; that names the
  implementation surface, the reader's last concern. Name the
  concept. The mechanics vocabulary — a Parameter/Type/Default table,
  a `DEFAULT_*` constant — is correct in the `docs/configuration.md`
  reference tables, and only there.

## What stays precise

Warm the framing, never the facts. Parameter tables, auto-computed
value mappings, `DEFAULT_*` constant tables, exact extension names,
and cross-references carry meaning in their exact form — leave them
alone. The friendly voice belongs in the sentences *around* a precise
block, introducing it, not inside it paraphrasing it into vagueness.

## Keeping examples honest

The `conf.py` snippets on docs pages are illustrative — no test
executes them, so every kwarg you show must exist in
`merge_sphinx_config()`'s real signature. The nearest thing to a
test: this site is its own flagship consumer, so `just build-docs`
exercises what the snippets promise. What *does* run: the gallery
renders live from the demo modules in `docs/_ext/` (nothing is
mocked), and pytest collects those modules' doctests (`testpaths`
includes `docs`; `addopts` carries `--doctest-modules`) — keep them
passing.

## Generated pages

Every `docs/packages/<name>/` page gets its "Copyable config snippet"
and "Package metadata" sections from the `{package-landing}` and
`{package-reference}` directives (`docs/_ext/package_reference.py`),
which read live workspace metadata — don't hand-write what they
generate; a new `packages/<name>/pyproject.toml` appears on the next
build with no code change. Surface documentation — config values,
directives, roles — belongs to `autoconfigvalues`, `autodirective`,
and `autorole`; invoke them instead of transcribing it into prose.

## Cross-references

Point the advanced reader at the deep-dive rather than inlining it,
and put the link where their interest peaks — on the phrase that made
them curious ("write your own autodoc extension") — not as a footnote
the eye skips. Use the MyST roles listed in the
root `AGENTS.md`; docs pages here usually spell the py-domain forms
explicitly (`{py:func}`, `{py:data}`, `{py:mod}`). A `{ref}` must
match its target's anchor exactly — anchors mix hyphen and underscore
forms, sometimes inside one anchor (`from-docs_url`). `just
build-docs` catches a broken cross-reference; nothing else does — so
build the docs before you commit.

Link the first prose mention of any symbol that has a useful
destination on that page. This includes Python objects, gp-sphinx
APIs, workspace package pages, configuration anchors, and external
tools or projects. Use the most specific target available:
`{py:func}`, `{py:class}`, `{py:mod}`, or `{py:data}` for API
objects; `{ref}` or `{doc}` for documentation pages and section
anchors; and a Markdown link for external projects. After the first
linked mention on a page, later mentions can stay plain unless the
distance or context makes another link useful.

Do not rely on a later reference section to satisfy the first-mention
rule. If the first occurrence would be a heading, grid-card teaser,
or introductory sentence, link that occurrence or retitle the heading
so the first prose mention can carry the link. Leave command
examples, code blocks, and literal configuration values as code; link
the surrounding prose instead.

## A page that does this

`docs/packages/gp-sphinx/how-to.md` is the worked example: it opens
with the exact downstream `conf.py` the default reader came to copy,
says what the call injects in reader vocabulary, reassures that
passing `docs_url` is the only step SEO needs, defers precise key
mappings to the configuration reference, and ends with a live-example
admonition pointing at this site's own `docs/conf.py`. Read it before
reshaping another page.

## Before you commit

- Does the page open with what the feature *is*, or how to configure
  it?
- Can a reader who needs only the ~10-line call stop after one
  paragraph?
- Is anything framed as "the kwargs" that should be named by concept?
- Are the workspace-internal and advanced parts marked opt-in?
- Did you leave every table, anchor, extension name, and
  cross-reference exact — and generated sections to their directives?
- Did `just build-docs` stay clean — no new warning, no broken
  cross-reference?
