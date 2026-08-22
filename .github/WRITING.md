# Writing

How this project writes prose, for humans and agents alike. It governs
`README.md`, `CHANGES`, commit messages, docstrings, source comments, and
every `docs/` page — including the MyST and Sphinx conventions downstream
repositories inherit through `merge_sphinx_config()`.

For environment setup, the gates, and pull request workflow, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Voice

Three surfaces, one voice. A docstring says what a caller may rely on; a
`CHANGES` entry says what changed; prose says what happens. All three are
present tense, lead with the thing being described, and stop. Why it was
built that way belongs in the commit message, which is timestamped and
attached to the diff.

The most useful editing operation is deleting the introductory sentence.

Lead with verbs and name concrete things. Put identifiers in backticks.
Prefer short declarative sentences, one operational fact each. Do not
explain Python to Python developers; do explain this project's semantics.

Type annotations describe shape. Documentation describes meaning. A
sentence that restates a signature has said nothing.

Use MUST, SHOULD, and MAY only where the normative sense is meant. Say what
actually happens rather than that something is "supported".

| Instead of                       | Prefer                            |
| --------------------------------- | --------------------------------- |
| "We added…"                      | "`merge_sphinx_config()` now accepts…" |
| "New and improved"               | "`DEFAULT_EXTENSIONS` now…"       |
| "powerful", "seamless"           | state the capability              |
| "easily", "simply", "just"       | omit                              |
| "simple", "obvious", "intuitive" | omit                              |
| "robust"                         | name the failure that is handled  |
| "comprehensive"                  | name what is covered              |
| "production-ready"               | state the guarantee               |
| "optimized", "blazingly fast"    | give the magnitude                |
| "various fixes"                  | name the components               |
| "under the hood"                 | omit unless observable            |
| "please note that", "note that"  | state the fact                    |
| "leverage", "utilize"            | "use"                             |
| "delve into"                     | "read", or omit                   |
| "best practices"                 | name the practice                 |
| "in order to"                    | "to"                              |

## Who you are writing for

The default reader is fluent in Python and new to this workspace. They can
read a signature; they cannot guess gp-sphinx's semantics. Serve them
first.

A second, smaller reader works *on* the workspace: adding a package,
extending an autodoc extension, touching `gp-furo-theme`'s `web/src`
assets or the `sphinx-vite-builder` backend. Serve them too, but mark
their material opt-in — "for workspace contributors", "advanced" — so the
default reader knows they can stop.

Rules that follow:

- **Second person, present tense, active.** "You pass `docs_url`", not "SEO
  values are derived". Address the reader doing the thing.
- **Concept before API surface.** Open by saying what the object or
  function *is* and what it does for the reader. The signature, or the
  kwarg list, is the last detail they need, not the first. A page that
  opens with "pass these keyword arguments" has buried the idea under its
  mechanics.
- **Say when they can stop.** Lead with the default and the reassurance:
  the ~10-line `merge_sphinx_config()` call is the whole integration;
  everything past it is optional. Let a skimmer leave after one
  paragraph.
- **Grant permission, do not demand attention.** "Reach for this when…"
  tells readers they are in the right place without implying they must
  read on.
- **Progressive disclosure.** Order by how many readers need it: the
  coordinator call → the one kwarg a few will tune (`docs_url`,
  `extra_extensions`) → a single package's own options → workspace
  internals. Each step is for a smaller audience than the last.
- **Lean on the merge order.** The reader's mental model of
  `merge_sphinx_config()` is a pipeline: shared `DEFAULT_*` constants,
  then values auto-computed from `source_repository` and `docs_url`, then
  `**overrides` applied last — an explicit value always wins. Reinforce
  that order when explaining who sets what. On package pages the
  equivalent is the tier map: shared infrastructure → autodoc extensions
  → theme and coordinator.
- **Name the trade-off.** If a call or option costs something — an extra
  round trip, a stale object needing a refresh, a polling wait — say so,
  and say what it buys. `vite_orchestration=True` spawns a pnpm/Vite
  watcher under `sphinx-autobuild`: contributors need Node, wheel
  consumers don't. State it; do not sell it.
- **Frame by concept, not by mechanism.** Do not headline a feature by its
  kwarg or CSS custom property in prose; that names the implementation
  surface, the reader's last concern. Name the concept. The mechanics
  vocabulary — a Parameter/Type/Default table, a `DEFAULT_*` constant —
  is correct in `docs/configuration.md`'s reference tables, and only
  there.

### What stays precise

Warm the framing, never the facts. Parameter tables, auto-computed value
mappings, `DEFAULT_*` constant tables, exact extension names, and
cross-references carry meaning in their exact form — leave them alone.
The friendly voice belongs in the sentences *around* a precise block,
introducing it, not inside it paraphrasing it into vagueness.

### Keeping examples honest

The `conf.py` snippets on `docs/` pages are illustrative — no test
executes them (see
[Documented examples that run](#documented-examples-that-run)), so every
kwarg shown must exist in `merge_sphinx_config()`'s real signature. The
nearest thing to a test: this site is its own flagship consumer, so
building the docs exercises what the snippets promise. What *does* run:
the gallery renders live from the demo modules in `docs/_ext/` — nothing
is mocked — and those modules' doctests execute as part of `pytest`.
Keep them passing.

### Generated pages

Every `docs/packages/<name>/` page gets its "Copyable config snippet" and
"Package metadata" sections from the `{package-landing}` and
`{package-reference}` directives (`docs/_ext/package_reference.py`),
which read live workspace metadata — do not hand-write what they
generate; a new `packages/<name>/pyproject.toml` appears on the next
build with no code change. Surface documentation for config values,
directives, and roles belongs to `autoconfigvalues`, `autodirective`,
and `autorole`; invoke them instead of transcribing it into prose.

### Cross-references

Point the advanced reader at the deep-dive rather than inlining it, and
put the link where their interest peaks — on the phrase that made them
curious ("write your own autodoc extension") — not as a footnote the eye
skips. See [Sphinx and MyST conventions](#sphinx-and-myst-conventions)
for which role to reach for.

Link the first prose mention of any symbol that has a useful destination
on that page: Python objects, gp-sphinx APIs, workspace package pages,
configuration anchors, and external tools or projects. After the first
linked mention on a page, later mentions can stay plain unless distance
or context makes another link useful. Do not rely on a later reference
section to satisfy the first-mention rule — if the first occurrence would
be a heading, grid-card teaser, or introductory sentence, link that
occurrence or retitle the heading. Leave command examples, code blocks,
and literal configuration values as code; link the surrounding prose
instead.

A `{ref}` must match its target's anchor exactly — anchors mix hyphen and
underscore forms, sometimes inside one anchor (`from-docs_url`). Building
the docs catches a broken `{ref}`; nothing else does. A py-domain role
(`{py:class}`, `{py:data}`, …) is not covered by that check —
`nitpicky` is unset, so an unresolved one renders as plain text and the
build stays silent. Confirm by opening the built page and checking the
name sits inside an `<a>`.

### A page that does this

`docs/packages/gp-sphinx/how-to.md` is the worked example — the concept
before the config, the trade-off named, the deep dive linked instead of
inlined. Read it before reshaping another page.

## README

A README is the shortest path from "what is this?" to competent use, not
the project's autobiography.

The first sentence is a contract. It says what abstraction the reader has
been handed, concretely enough to tell this package apart from the
neighbouring one.

Get to a runnable command or snippet before anything the reader can skip.
A logo, a mission statement, a comparison matrix and three paragraphs of
history in front of the install line all cost the same thing.

State the minimum Python version and meaningful platform constraints in
prose, not only in badges. `requires-python` in `pyproject.toml` is the
authority; the README must agree with it.

Name the distribution, the import, and the executable separately wherever
they differ. That distinction prevents a Python-specific class of
confusion.

Examples are executable, not illustrative fiction. Never
`your-command <some-options>`. See
[Documented examples that run](#documented-examples-that-run) for which
blocks are executed and how to write one that qualifies.

Document the semantic model, not the flag list. What it cannot say is
precedence, filesystem effects, what goes to stdout versus stderr, and
what a non-zero exit means.

State defaults explicitly — defaults are API. State negative guarantees
where they exist: "does not modify your configuration file", "no network
access", "never writes outside the destination". They establish
boundaries faster than any amount of description.

Headings stay conventional and stable, because people deep-link them.
Badges are few and load-bearing.

## Documented examples that run

Examples in this fleet are tests, where the collector reaches them. This
section is the contract for writing one the test suite can actually see
**in this repository**.

**A fence tag is cosmetic. Only a `>>> ` prompt executes, and only inside
a Python module.** `pytest`'s `--doctest-modules` flag (set in
`pyproject.toml`'s `addopts`) collects doctests from importable `.py`
files under `testpaths` — the workspace `tests/`, `docs/` (its `_ext/`
demo and extension modules), and every `packages/*/src`. It does **not**
collect Markdown or reStructuredText: gp-sphinx has no `doctest-glob` or
RST doctest plugin configured, so a `>>> ` block inside `README.md` or a
page under `docs/` is prose that looks like a test. Nothing runs it.

This matters more here than elsewhere in the fleet, because gp-sphinx's
own docs (`docs/packages/*/how-to.md`) are full of fenced `python`
blocks written to *look* like the docstring examples they document. That
resemblance is intentional — see
[Keeping examples honest](#keeping-examples-honest) — but it is
illustration, not a test. Do not add a `>>> ` prompt to a Markdown page
expecting it to run; add it to the docstring the page is illustrating.

**The fence tag is `python`.** Not `pycon`, not bare. This stays uniform
even for illustrative blocks, so a reader cannot tell test from
illustration by fence tag alone — only by whether the file is a `.py`
module under `testpaths`.

**`# doctest: +SKIP` is not permitted.** It is a workaround that tests
nothing. Use the fixtures.

**Do not downgrade a doctest to a non-executed block to make it pass.** A
`.. code-block::` or an unprompted fence does not run. If an example
cannot pass, fix the example or fix the code.

**Option flags.** `ELLIPSIS` and `NORMALIZE_WHITESPACE` are enabled
globally, so `...` elides variable output and whitespace differences do
not fail a comparison. Reach for an inline `# doctest: +FLAG` only for
the block that needs it. `sphinx-autodoc-typehints-gp` additionally
recognizes `# doctest: +HIDE` to drop incidental setup lines — socket
paths, environment scaffolding — from the *rendered* docstring on an API
page without touching the source; it has no effect under plain `pytest`.

**Docstring examples** use the NumPy `Examples` section. A public
function carries one where a short call demonstrates the behaviour
clearly:

    Examples
    --------
    >>> from gp_sphinx.defaults import DEFAULT_EXTENSIONS
    >>> "myst_parser" in DEFAULT_EXTENSIONS
    True

Treat a function without one as unfinished documentation, not as a
policy violation to block on — nothing in CI enforces a doctest on every
function, and inventing one that exercises nothing but plumbing is worse
than no example.

**The doctest namespace is scoped to `tests/`, not the fleet.** A
`doctest_namespace` fixture in `tests/conftest.py` injects `tmp_path` (a
session-scoped writable directory) for doctests collected under `tests/`.
pytest's conftest discovery does not cross into sibling trees, so a
doctest under `packages/*/src` or `docs/_ext/` cannot rely on it — those
examples must stay self-contained or build what they need inline. Add a
name to `tests/conftest.py`'s `_doctest_namespace` fixture only if you
also confirm, by running the suite, which directories can actually see
it.

## The changelog

`CHANGES` is the changelog. Not `CHANGELOG.md`. It is rendered as the
project's changelog page, and follows Django's release-notes shape:
deliverables get titles and prose, not bullets.

**Release entry boilerplate.** Every release header is
`## gp-sphinx X.Y.Z (YYYY-MM-DD)`. The file opens with a
`## gp-sphinx X.Y.Z (unreleased)` block prefaced by a single
`<!-- To maintainers and contributors: Please add notes for the
forthcoming version below -->` HTML comment — new release entries land
below the most recent released entry, never between the comment and the
unreleased header.

**Open with a multi-sentence lead paragraph.** Plain prose, no italic.
Open with the version as sentence subject ("gp-sphinx X.Y.Z ships …") so
the lead is self-contained when excerpted. Two to four sentences telling
the reader what shipped and who cares — user-visible takeaways, not
internal mechanism. Cross-reference detail docs with `{ref}` to keep the
lead compact.

**Lead paragraphs are release-time material — off-limits to branches and
PRs.** The unreleased entry carries no lead paragraph and no version
summary: sections only (`### Breaking changes`, `### What's new`
deliverables, `### Fixes`, …). Speaking for the release — what the
version "is", "ships", or "focuses on" — is presumptuous before its
scope is final; only the person cutting the release writes that, and
only when the user explicitly asks to release. Never write or edit a
lead from a feature branch, and never ask or imply that a release should
happen.

**Each deliverable is a section, not a bullet.** Inside `### What's new`,
every distinct deliverable gets a `#### Deliverable title` heading naming
it in user vocabulary, followed by one to three prose paragraphs
explaining what shipped. Do not wrap a paragraph in `- ` — bullets are
for enumerable lists, not paragraph containers. Cross-link detail docs
("See {ref}`foo` for details.") so prose stays focused.

**The deliverable test.** Before writing an entry, ask: "What's the
deliverable, in user vocabulary?" If you cannot answer in one sentence,
the entry is not ready. Mechanism — helper internals, byte counters,
schema-validation locations — belongs in PR descriptions and code
comments, not the changelog.

**Fixed subheadings**, in this order when present: `### Breaking
changes`, `### Dependencies`, `### What's new`, `### Fixes`,
`### Documentation`, `### Development`. Dev tooling (helper scripts,
internal automation) lives under `### Development`. For breaking
changes, show the migration path with concrete inline code (a `# Before`
/ `# After` fenced block). Dependency floor bumps use the form
`` Minimum `pkg>=X.Y.Z` (was `>=X.Y.W`) ``.

**PR refs `(#NN)`** sit at the end of each deliverable's prose body, not
in the `####` heading.

**When bullets are appropriate.** Catch-all sections (`### Fixes`,
occasionally `### Documentation`) with three or more genuinely small
items use bullets — one line each, never paragraphs. If a bullet swells
past two lines, promote it to a `#### Title` heading with prose body.

**Anti-patterns.** Fragile metrics that go stale silently — token
ceilings, third-party version pins, percent benchmarks, exact byte
counts. Describe the capability, not the math. Internal jargon: private
symbols (leading-underscore identifiers), algorithm names exposed for
the first time, backend scaffolding. Walls of text dressed up as
bullets. Buried breaking changes — give them their own subheading at the
top of the entry.

**Always link autodoc'd APIs.** Any class, method, function, exception,
or attribute with its own rendered page is cited via the matching role —
never plain backticks. Doc pages without an explicit ref label use
`{doc}`. Plain backticks are correct for code syntax, env vars,
parameter names, and file paths that are not doc pages. See
[Sphinx and MyST conventions](#sphinx-and-myst-conventions) for the role
list.

## Docstrings

The prime directive: never restate the type. The annotation is the
source of truth; the docstring carries what the annotation cannot.

This is documentation debt wearing a docstring:

    def get_project_name(config: dict[str, str]) -> str:
        """Get the project name.

        Parameters
        ----------
        config : dict[str, str]
            The config.

        Returns
        -------
        str
            The name.
        """

Document instead the dimensions the type system cannot encode:

- **Mutation.** What it changes in place.
- **Ownership.** What the caller must close, release, or keep alive.
- **Ordering.** Whether results come back in a guaranteed order.
- **Timing.** What has finished by the time the call returns.
- **Failure.** Which exceptions are raised and what triggers each.
- **Idempotence.** Whether calling twice does anything the second time.
- **Concurrency.** Whether calls are coalesced, queued, or independent.
- **Units and ranges.** What a number means and what values are
  accepted.
- **Boundary behaviour.** What zero, empty, and the maximum do.
- **Platform.** Behaviour that differs by Sphinx or docutils version —
  see `_compat.py` for the floors this workspace already works around.
- **Security boundary.** What is executed, and what is only read — load
  bearing wherever a directive introspects a user's own modules
  (autodoc, argparse, fastmcp, pytest-fixtures extensions).

The first sentence stands alone; tooling truncates there. PEP 257
applies: triple double quotes, an imperative one-line summary ending in
a period, a blank line before any extended description. Do not repeat an
introspectable signature.

NumPy docstring style is the one dialect this repository uses, enforced
by `ruff`'s `pydocstyle` convention rather than relitigated in review:

    """Short description of the function or class.

    Detailed description using reStructuredText format.

    Parameters
    ----------
    param1 : type
        Description of param1.

    Returns
    -------
    type
        Description of return value.
    """

**Class-level names get exactly one description each.** Every name a
class declares that autodoc renders — `NamedTuple` fields, dataclass
fields including `InitVar`, `TypedDict` keys, `Enum` members, `ClassVar`s,
and plain constants — needs a description. The shape does not change the
rule. Three styles count, and `tests/docs/test_docstring_policy.py`
enforces them: a NumPy `Attributes` entry in the class docstring, a
docstring under the assignment, or a `#:` comment above it. Prefer
`Attributes`:

    class ToctreeSection(t.NamedTuple):
        """One section of pages grouped by toctree caption.

        Attributes
        ----------
        caption : str | None
            Toctree caption, or ``None`` for an uncaptioned toctree.
        docnames : list[str]
            Docnames listed under the caption, in toctree order.
        """

A `Parameters` section does **not** describe attributes — it documents
the initializer, and the attribute entries still render bare beneath it.
A field nobody describes reaches the reference as a bare name. A
`ClassVar` nobody describes is withheld from it entirely, so an
undescribed one is silently missing rather than visibly empty.

## Sphinx and MyST conventions

gp-sphinx owns `DEFAULT_EXTENSIONS`
(`packages/gp-sphinx/src/gp_sphinx/defaults.py`) — the extension list
every repository in the fleet inherits through `merge_sphinx_config()`.
This section is the authoring contract that list implies for `docs/`
pages here and, by inheritance, downstream.

**MyST roles.** Class references use `{class}` (or the explicit
`{py:class}` this repository prefers on its own pages), methods
`{meth}`, functions `{func}`, exceptions `{exc}`, attributes `{attr}`,
modules `{py:mod}`, config values `{py:data}` or `{confval}`, internal
anchors `{ref}`, doc-path links `{doc}`. Use the most specific target
available; a Markdown link is correct only for something with no
autodoc destination — an external project or tool.

**MyST parser extensions.** `DEFAULT_EXTENSIONS` turns on `colon_fence`
(the `:::` admonition and grid-card syntax used throughout `docs/`),
`substitution`, `replacements`, `strikethrough`, and `linkify`. Grid
cards (`sphinx_design`) are the standard way to present a set of
sibling links — see `docs/project/index.md` or any `docs/packages/*`
landing page for the pattern.

**`{include}` does not carry relative links across a directory
boundary.** MyST rewrites an included file's relative links, but if the
included file lives outside the including page's directory tree,
Sphinx resolves the rewritten targets as internal cross-references and
emits dead anchors instead of following them out. `AGENTS.md` and
`CLAUDE.md` are also in `docs/conf.py`'s `exclude_patterns`, which rules
out including either directly. Where a docs page used to host content
that now lives in `.github/`, make it a short pointer page instead: keep
any `(label)=` anchor and the page title, then link the canonical file
on GitHub.

**Generated surface documentation.** Config values, directives, and
roles that ship in this workspace are documented via `autoconfigvalues`,
`autodirective`, and `autorole` rather than transcribed into prose —
see [Generated pages](#generated-pages).

## CSS and directive naming

Every class, custom property, and MyST directive name a workspace
package adds lives under the `gp-sphinx-*` namespace — the naming
vocabulary downstream themes and doc authors read and depend on:

- **Tier A (shared concepts)** — `gp-sphinx-<concept>` (`gp-sphinx-badge`,
  `gp-sphinx-toolbar`). Used by multiple packages.
- **Tier B (package-owned)** — `gp-sphinx-<pkg>__<thing>` BEM-style
  (`gp-sphinx-fastmcp__safety-readonly`,
  `gp-sphinx-pytest-fixtures__fixture-index`).
- **Modifiers** — axis-value pairs `--<axis>-<value>`
  (`gp-sphinx-badge--size-xs`, `gp-sphinx-badge--type-function`).
- **Custom properties** mirror the class namespace:
  `--gp-sphinx-<pkg>-<token>`. Furo-owned variables (`--color-api-*`,
  `--font-stack--*`) stay untouched.

A package's own CSS must style every class its Python code emits.
Cross-package **reuse** of a shared class is fine; cross-package
**dependence** — a feature rendering correctly only because a sibling
package happens to be loaded — is not. A downstream user installing one
extension standalone must get the correct visual result.

## Terminology and capitalization

Pick the domain noun and keep it. If the code calls something a
`docname`, do not call it a "page path" in one paragraph and a "doc ID"
in the next. If the function is `merge_sphinx_config`, write "merge"
everywhere rather than alternating with "combine", "build", and
"assemble".

Stable vocabulary is what makes search, deep links, and an agent's
retrieval work at all.

Python and PyPI keep their own capitalisation. Distribution names are
written as they are published.

Do not write counts into prose — how many packages this workspace has,
how many tests there are. They go stale silently and no reader needs
them. Counts that pin a fixture or guard an invariant are different, and
belong in code.

## Markdown

Prose wraps at 80 columns. Table rows, badge lines, and long links are
exempt, because breaking them harms rendering. A pull request or issue
body does not wrap at all: GitHub renders a single newline as a space in
a file and as a line break in a comment, so a wrapped comment body
arrives as ragged stubs.

GitHub alert blocks — `> [!NOTE]`, `> [!WARNING]` — render as literal
text outside GitHub, so reserve them for at most one load-bearing
warning per document. Write the sentence so it carries the fact on its
own, and a renderer that drops the marker loses nothing.

Do not use a local absolute path or an email address in anything
published.

## Code blocks

Code blocks are paste-and-run units: pasting one block runs exactly one
intended action. Executed examples are exempt — the test suite runs
them, nobody pastes them.

- **One command per block.** Multiple steps may share a block only when
  explicitly chained with `&&`, `;`, or `\` continuations — the chain is
  then one logical command.
- **Explanations go in prose above the block**, never as `#` comments
  inside it.
- **Command menus are per-command blocks with prose lead-ins**, not
  tables.
- **Shell commands use the `console` tag with a `$ ` prefix.** This
  separates interactive commands from scripts and enables prompt-aware
  copy.
- **Split long commands with `\`** — one flag or flag+value pair per
  indented continuation line, positional arguments last.

Good — show the last ten commits as a graph:

```console
$ git log \
    --max-count=10 \
    --graph \
    --oneline
```

Bad:

```console
# Show the last ten commits as a graph
$ git log --max-count=10 --graph --oneline
```

## Commits

```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.

what:
- Specific technical changes made
- Focused on a single topic
```

Keep the subject to 50 characters or fewer, excluding any trailing
`(#NN)` pull request reference, and wrap body lines at 72. Separate the
`why:` and `what:` blocks with a blank line.

Routine maintenance commits drop the colon and take a capitalised
description, which is what distinguishes them at a glance in
`git log --oneline`:

```
py(deps[dev]) Bump dev packages
ai(rules[AGENTS]) Judge comments by three gates
```

Everything that changes behaviour keeps the colon.

Common types:

- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **ci**: Workflow and pipeline changes
- **py(deps)**: Dependencies
- **py(deps[dev])**: Dev dependencies
- **ai(rules[AGENTS])**: AI rule updates
- **ai(claude[rules])**: Claude Code rules (`CLAUDE.md`)
- **ai(claude[command])**: Claude Code command changes

Example:

```
config(feat[merge]): Add deep-merge support for theme options

why: Enable per-project theme overrides without replacing entire dict.

what:
- Add deep_merge() helper for nested dict merging
- Update merge_sphinx_config() to deep-merge theme_options
- Add tests for nested override behavior
```

For a multi-line message, use a heredoc so the formatting survives:

```console
$ git commit -m "$(cat <<'EOF'
Scope(feat[detail]): Concise description

why: Explanation of the change.

what:
- First change
- Second change
EOF
)"
```

### Release commits

Never create tags. Never push tags. The owner handles tagging and tag
pushes, because a tag triggers the PyPI publish workflow.

A release commit subject is plain and short: `Tag v<version>`. The
detailed why and what go in the body. Do not use the
`Scope(type[detail]):` format for a release — it buries the lede.

## Slop prevention

Treat AI slop as review-hostile noise, not as proof that text or code is
wrong. The goal is to maximise information density.

- **AI signatures.** No "Generated by", no conversational filler, no
  unexplained emoji, no tool metadata.
- **Brittle references.** No hard-coded line numbers, fragile file
  counts, dated "as of" claims, bare SHAs, or local absolute paths —
  unless they are strict evidentiary artefacts such as a benchmark log.
- **Diff narration.** Do not restate what moved, was renamed, or was
  removed in anything the reader holds alongside the diff: code,
  docstrings, README, `CHANGES`, or a pull request description. The diff
  and the commit message already carry it.
- **Branch-internal narrative.** Do not mention intermediate states,
  abandoned approaches, or "no longer" behaviour unless users of a
  published release actually experienced the old state — did users of
  the most recently published release ever experience this old name,
  old behaviour, or bug? If not, it belongs in the commit message, not
  the artefact.
- **Low-value scaffolding.** No ownerless TODOs, unused
  future-proofing, debug artefacts, or defensive wrappers around
  failure modes nothing can reach.
- **Prose inflation.** The diction table under [Voice](#voice) governs;
  replace an inflated word with a concrete description of behaviour,
  constraints, or trade-offs.
- **Coded labels.** Write rules and findings as plain imperatives. No
  `[R1]`, `Option B`, or any index a reader has to decode.

Preserve the "why". Never delete a comment documenting an invariant, a
protocol constraint, a platform quirk, or an upstream workaround — those
are the facts [Source comments](#source-comments) keeps, and every other
comment is judged by it. Preserve exact counts, dates, and SHAs when they
serve as evidence in benchmark results, `CHANGES` entries, or lockfiles.

### Durable source links

Link to a pinned revision, never to trunk, when citing source in prose an
agent or contributor will read later — a `blob/main/…` link rots
silently as the file moves and lines shift while the link keeps
resolving, landing on unrelated code.

- Prefer a release tag (`blob/v0.1.0a37/…`). Most durable, and it tells
  the reader which released version the claim held for.
- Otherwise use a 7-character commit SHA (`blob/9a29b1a/…`) reachable
  from `main`. Use when there is no tag or the claim is about
  unreleased code. Never a PR-head SHA — it can be rebased or
  garbage-collected.
- Reserve `blob/main/…` for living documents meant to always show the
  latest state, such as this file or `CONTRIBUTING.md`.
- Line anchors (`#L120-L145`) are only safe on a pinned ref.

## Source comments

A comment ships only if it passes all three gates. Fail any: delete or
rewrite. Borderline: delete — borderline means the information is
reconstructible, which is what makes deletion cheap.

**Loss.** Three years from now, would losing this cost a maintainer real
time rediscovering intent, an invariant, a constraint, or a failure mode
the code and tests do not already make obvious?

**Elite.** Would SQLite, Redis, the Go standard library, or CPython
write this comment, at this length? Those projects state the constraint
and stop. They do not argue with an imagined objector.

**Upkeep.** Will it stay true without maintenance? A comment that
hand-syncs a value the code owns — a count, an offset, a line reference,
a duplicated constant — is false the first time that value moves.

### Ceiling

One or two lines. A comment reaching four is either carrying several
facts, in which case split it, or arguing, in which case cut it to the
fact.

Rationale, alternatives weighed, and the story of how the code got here
belong in the commit message: timestamped, attached to the exact diff,
and free to maintain.

A comment often holds both a constraint and the deliberation that found
it. Keep the constraint, cut the deliberation. "Runs at most once per
second" survives; "this is the right trade for now" does not.

### Keep

- Why over how: upstream quirks, protocol and compatibility constraints,
  performance tradeoffs still part of the contract.
- Invariants, preconditions, ordering, lifetime, and concurrency
  requirements that types and tests cannot express.
- Code that looks wrong but is not, so a later cleanup does not
  reintroduce the bug.
- A high-level sketch of an algorithm whose local operations do not
  reveal the whole.

### Delete

- Narration of the next lines; code translated into English.
- Restated names, types, defaults, or control flow.
- Values duplicated from the code and hand-synced.
- Justification, hedging, or apology for a choice.
- Speculation about future requirements.
- History version control already holds, including commented-out code.
- Ticket and issue numbers. They say nothing to a reader without tracker
  access, and they rot when the tracker moves. Unfinished work goes in
  the tracker, not the source.
- Transient observations — "currently", "for now", "the latest
  release" — that go stale with no nearby edit.

### The upkeep gate in practice

It reaches values that track our own code. It does not reach frozen
external facts.

Bad (Delete):

```python
# There are 321 tests to complete for servers.
```

Good (Keep):

```python
# Sphinx < 8.1 has no typed env.domains accessors, so this branch
# falls back to env.get_domain("py").
```

### Documentation exception

Doctests, minimal usage examples, and `Parameters`, `Returns`, and
`Attributes` entries on public API are exempt from the loss gate — they
serve the caller, not the maintainer. They are exempt from nothing else.
Ceiling: a good man page entry. Autodoc ships every field whether or not
you describe it, and a doctest that runs is also a test, so an
undescribed field or an unrun example is a documentation gap, not a
slop violation.
