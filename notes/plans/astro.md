# Astro Documentation Stack for gp-sphinx — Final Plan

**Status:** Final plan, ready for Phase-0 spike commit
**Date:** 2026-04-26
**Branch:** `astro-2026-04-26`
**Target landing path:** `notes/plans/astro.md`
**Scope:** A parallel Astro/TypeScript documentation stack that ships
alongside the existing Sphinx pipeline in the gp-sphinx monorepo.
The first proving-ground site documents gp-sphinx itself across
all 14 packages. Public npm package names (`gp-sphinx-tsx-builder`,
`gp-sphinx-astro-builder`, `gp-sphinx-astro-theme`) are fixed by
user constraint. The 14 sphinx-* packages — `gp-sphinx`,
`sphinx-gp-theme`, `sphinx-fonts`, `sphinx-ux-badges`,
`sphinx-ux-autodoc-layout`, `sphinx-autodoc-api-style`,
`sphinx-autodoc-typehints-gp`, `sphinx-autodoc-argparse`,
`sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-docutils`,
`sphinx-autodoc-sphinx`, `sphinx-autodoc-fastmcp`,
`sphinx-gp-opengraph`, `sphinx-gp-sitemap` — continue shipping
unchanged. None are deprecated by this plan.

---

## Decisions at the top

This plan commits to:

- **Architecture P** (parallel sidecar) as the developed-in-detail
  default, with a Phase 0 spike that may switch to S, P-minimal, or
  H based on falsifiable thresholds.
- **Two-version contract**: wire `schemaVersion` (JSON envelope)
  split from in-memory `protocolVersion` (Python `SymbolContributor`
  Protocol).
- **Mirror existing AWS infrastructure** (S3 + CloudFront +
  Cloudflare DNS) for both preview and production. No second cloud
  provider.
- **`gp-sphinx-sidecar`** workspace-private under
  `packages/gp-sphinx-sidecar/`, PyPI in Phase 5 with both gates.
- **Two internal TS packages**: `@gp-sphinx-astro/schema` and
  `@gp-sphinx-astro/intersphinx`.
- **`tsconfig.base.json` extends `astro/tsconfigs/strictest`**.
- **Zod 4** (`z.$ZodType<T>` for recursive types).
- **Static parser** is Python `ast` (stdlib), not tree-sitter.
- **Python ≥3.10,<4.0** floor (matches gp-sphinx's existing floor).
- **Snapshot workflow**: two-tier (`pnpm snapshots:bless` for the
  wire contract; `vitest -u` for the renderer surface).
- **HMR invalidation** via `astro:server:setup` exposing
  `ViteDevServer` plus `server.moduleGraph.invalidateModule`,
  composed with the content-layer `refreshContent`.
- **Per-root cache files** keyed by `<root-slug>-<content-hash>.json`
  with sibling `last-good.json` discipline.
- The seven `sphinx-autodoc-*` packages become contributor-protocol
  plugins via Python entry points.

The single live user decision is **Q9: MyST vs MDX as the default
prose format**. The plan recommends MyST, with the rationale and
the case for MDX both surfaced in §13. Everything else is closed.

---

## Table of contents

1. Premise and scope
2. Phase 0 — source-of-truth spike
3. Naming, tier map, CSS namespace
4. Monorepo layout
5. Zod 4 schema contract — and the two-version contract
6. Pipeline architecture (P default; S divergence noted)
7. Contributor protocol — autodoc packages as sidecar plugins
8. Per-package responsibilities
9. The example consumer site — `apps/gp-sphinx-docs`
10. Testing strategy
11. Build, lint, CI integration (mirroring the AWS deploy path)
12. Migration phases
13. Open-question dispositions and the one user decision
14. Explicit rejections

Appendices:
- A. File:line citation index for every load-bearing claim

---

## 1. Premise and scope

gp-sphinx is a *meta* documentation platform: 14 Python packages
that exist to make Sphinx-rendered docs look and behave better
across the git-pull ecosystem. This plan adds an Astro/TypeScript
parallel stack — Vite-fast, component-driven, owns its markup top
to bottom — that reuses the visual language proven in
`~/work/tony.sh/` (pnpm 10.33.2 + Astro ^6.1.9 + Tailwind ^4.2.4 +
Fontsource IBM Plex + OKLCH tokens).

The first dogfood site documents **gp-sphinx itself across all 14
packages** — not libtmux, not vcspull, not any downstream consumer.
This matters because the 14 packages contain the hard symbol kinds
(Sphinx config values, docutils directives, pytest fixtures,
FastMCP tools, argparse parsers) that a generic Python-only stack
would silently fail on. If the autodoc components can render
`sphinx-autodoc-pytest-fixtures` and `sphinx-autodoc-fastmcp`,
they can render most things.

The existing Sphinx documentation continues to build and deploy.
Current CI treats docs as a strict Sphinx build with warnings as
errors:

```console
$ uv run sphinx-build -W -b dirhtml docs docs/_build/html
```

Verified at `/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:72`.

### 1.1 The contrarian counter, acknowledged

`sphinxcontrib.serializinghtml` is loaded as a built-in extension —
the `_first_party_extensions` tuple at
`~/study/python/sphinx/sphinx/application.py:128-141` includes
`'sphinxcontrib.serializinghtml'` at line 133, and unions into
`builtin_extensions` at line 141. So `sphinx-build -b json` works
without any user-side config. But the upstream Sphinx docs literally
describe the JSON builder output as "mostly HTML fragments and TOC
information" (`~/study/python/sphinx/doc/usage/builders/index.rst:425-440`,
literal phrase at line 427). `JSONHTMLBuilder` at
`~/study/python/sphinx/sphinxcontrib/serializinghtml/__init__.py:153`
inherits from `SerializingHTMLBuilder` (line 38), which inherits
from `StandaloneHTMLBuilder`; `out_suffix = '.fjson'` at line 164.
Output is HTML body fragments per page.

The complementary fact: Sphinx's Python domain stores objects in a
form much closer to what we need.
`ObjectEntry(NamedTuple)` at
`~/study/python/sphinx/sphinx/domains/python/__init__.py:60-65`
exposes typed `docname`, `node_id`, `objtype`, `aliased`, and
`PythonDomain.get_objects()` at `:1056-1065` yields the inventory
tuple shape `(name, dispname, objtype, docname, anchor, priority)`.
Inventory format is stable: Sphinx reads v1/v2 and writes v2
(`~/study/python/sphinx/sphinx/util/inventory.py:43-63` reader,
`:175-207` writer; `# Sphinx inventory version 2` literal at line
185).

So *some* of the data is structured, *some* is HTML. Phase 0
settles which of the dogfood symbol kinds yield schema-shaped
records without scraping body fragments. We do not pre-commit.

---

## 2. Phase 0 — source-of-truth spike

**Cost:** one engineer-day, two at most.
**Output:** `notes/plans/astro-phase-0-verdict.md` plus committed
fixtures in `astro/fixtures/spike/` that back the verdict and seed
the §11 wire-contract snapshots.

Phase 0's question is narrower than "S vs P." It is:

> For each symbol kind this docs platform actually needs to render,
> what is the smallest source of truth that emits schema-shaped data
> *without parsing rendered HTML*?

Architectures still in play:

- **S** — Sphinx-as-source. Stitch `.fjson` body fragments,
  `objects.inv`, typed `env.domains.python_domain.data["objects"]`,
  doctree walks, and extension-owned env stores into a flat typed
  `ApiIndex`. No new sidecar.
- **P** — Parallel sidecar. New Python process introspects the
  packages, emits schema-shaped JSON. Existing autodoc packages add
  small entry-point shims (the contributor protocol, §7).
- **H** — Hybrid. Sphinx export covers what it covers cleanly;
  contributor protocol shims fill the gaps for symbol kinds whose
  metadata already lives in package-specific code.
- **P-minimal** — Parallel stack, sidecar re-implements
  introspection where contributors aren't ready. Fallback, not goal.
- **Deferred-H** — Phase 0 produces fixtures and a provisional P
  scaffold, but the architecture is **re-scored at Phase 4** once
  the Astro integration has a real cache/HMR loop. Deferred-H is
  not "H but uncertain": H has already proven both halves — Sphinx
  carries the common API data and contributor adapters carry
  extension-specific data. Deferred-H has proven only the first
  half (S/A2 works for ordinary Python API objects on at least the
  gp-sphinx subset) and has a *bounded* deferral for the second
  half (the libtmux must-pass set or the extension-owned-metadata
  cases). The deferral is bounded by an explicit Phase-4 re-score
  of §2.2 against a real libtmux+Astro+sidecar build, with the
  re-score date written into the verdict YAML. Without the dated
  re-score, "Deferred-H" collapses back into "H but unsure" — the
  failure mode this cell exists to prevent. If the failures are
  not extension-owned metadata or do not lend themselves to a
  Phase-4 re-test, the verdict is **P**, not Deferred-H.

The fifth cell is intentional. The original four-cell partition
forced a binary verdict in cases where the evidence is lopsided —
Sphinx may be clearly good for libtmux classes/functions while
clearly weak for FastMCP or pytest metadata. Forcing P (or H)
before the renderer has consumed the first fixtures throws away
one engineer-week of architectural information.

### 2.1 Reproducibility gate (run *before* scoring)

The spike command itself does not run cleanly on the gp-sphinx
docs site as currently configured. Verified at HEAD
(`5b750aae44c6af1d70f37f24b1fe542614f9527b`). The blocker is a
producer/consumer mismatch on the `pagename` context key:

| Component | File:line | Behaviour |
|---|---|---|
| `sphinx.builders.html.StandaloneHTMLBuilder.update_page_context` (control — standard HTML builder) | `.venv/lib/python3.14/site-packages/sphinx/builders/html/__init__.py:1083` (`ctx['pagename'] = ctx['current_page_name'] = pagename`) | Writes **both** `pagename` and `current_page_name`. This is why the consumer mismatch has gone undetected in production HTML builds. |
| `sphinxcontrib.serializinghtml.JSONHTMLBuilder.handle_page` (the spike's builder) | `.venv/lib/python3.14/site-packages/sphinxcontrib/serializinghtml/__init__.py:88-105` (assignment at `:90`: `ctx['current_page_name'] = pagename`) | Writes **only** `current_page_name`; never sets `pagename`. |
| `sphinx_gp_opengraph.get_tags` (workspace consumer) | `packages/sphinx-gp-opengraph/src/sphinx_gp_opengraph/__init__.py:144` (`builder.get_target_uri(context["pagename"])`) | Reads `context["pagename"]` directly. KeyError under `-b json`. |

**Workspace audit.** `rg -n 'context\["pagename"\]'
/home/d/work/python/gp-sphinx/packages/` returns exactly one hit —
the `sphinx_gp_opengraph` line above. The blocker is precisely
scoped to *one* extension. `sphinx_gp_sitemap` is unaffected
(it iterates `app.env.found_docs` at
`packages/sphinx-gp-sitemap/src/sphinx_gp_sitemap/__init__.py:268-275`,
not `html-page-context`). `sphinx_fonts`,
`gp_sphinx.config._inject_copybutton_bridge`, and the other
`html-page-context` consumers in the workspace receive `pagename`
as a positional argument from the event signature and never index
`context["pagename"]`. `sphinx_gp_opengraph` is in the default
extension list (`packages/gp-sphinx/src/gp_sphinx/defaults.py`)
and ships in every docs build that uses `merge_sphinx_config()`.

**Gate (mechanical, before scoring symbol coverage):**

```console
$ UV_CACHE_DIR=/tmp/uv-cache uv run sphinx-build \
    -E -a -b json \
    docs/ /tmp/gp-sphinx-fjson
```

Three legal outcomes:

1. **Clean exit, zero `KeyError`.** Proceed to §2.2.
2. **Clean exit, only after a documented workaround** — either a
   one-line patch in `sphinx_gp_opengraph` (`context.get("pagename")
   or context.get("current_page_name")`) or a spike-only
   `confoverrides={"extensions": [<filtered>]}` in the spike's
   `conf.py`. The exact workaround is recorded in
   `astro-phase-0-verdict.md` under "Reproducibility workarounds."
   Proceed to §2.2 with a flag noted in the verdict.
3. **Cannot run without disabling extensions whose output Astro
   needs** (e.g., must drop `sphinx_gp_opengraph` whose OpenGraph
   tags Astro must reproduce). **S cannot be the default
   architecture.** The verdict short-circuits to P — or to H once
   the JSON build runs after the one-line patch lands upstream.

This is a hard precondition. A spike that scores A1 and A2 against
a configuration the production docs site cannot use is theatre.

### 2.2 Spike A — what is the smallest path that emits structured data?

The committed §2.1 conflated two separable questions:

- **A1 — `-b json` baseline.** Does the JSON builder, plus
  `objects.inv`, plus `env.domains.python_domain.data["objects"]`,
  carry the fields a typed `SymbolCard` needs *without parsing the
  `.fjson` `body` HTML*? `ObjectEntry` is a 4-field NamedTuple at
  `~/study/python/sphinx/sphinx/domains/python/__init__.py:60-65`:

  ```python
  class ObjectEntry(NamedTuple):
      docname: str
      node_id: str
      objtype: str
      aliased: bool
  ```

  No signature. No parameter list. No return annotation. No
  docstring. Those live only in the rendered `desc` node tree that
  the JSON builder serializes *as HTML strings* in `body`. A1's
  expected outcome is therefore *partial pass on identity/linkage,
  fail on signature data*. We run it anyway because the recorded
  failure is what future readers need when they re-ask "why didn't
  we just use `-b json`?"

- **A2 — custom doctree-walk extension.** A small Sphinx extension
  that hooks `env-updated`, walks `env.get_doctree(docname)` for
  `addnodes.desc` nodes, reads extension env stores where
  available, and emits schema-shaped JSON directly *before*
  `JSONHTMLBuilder` flattens the body to HTML. This is the path S
  would actually use; the load-bearing question is whether the
  doctree carries enough structure to skip HTML rendering
  entirely.

#### 2.2.1 Step 0 — pin the source corpora (gp-sphinx **and** libtmux)

Spike A runs against **two** corpora:

| Corpus | Source root | conf | Why |
|---|---|---|---|
| gp-sphinx (dogfood) | `/home/d/work/python/gp-sphinx/docs/` | existing `docs/conf.py` | Dogfood site this plan eventually replaces. Production config; no overrides. |
| libtmux (external target) | `/home/d/work/python/libtmux/docs/` | existing `docs/conf.py` | The original target consumer. Read-only — vendor a minimal `conf.py` mirror into `astro/fixtures/spike/libtmux-conf.py` so the spike is reproducible without network access and never edits the libtmux tree. |

The libtmux read-only requirement is a CLAUDE.md
"project-read-only" constraint (cannot inject test fixtures into a
third-party repo during a spike). Synthetic `class
DummyCase(t.NamedTuple)` injection is rejected on this basis — and
is moot anyway, because libtmux has *zero* `NamedTuple` classes
and *zero* `async def` functions in `src/libtmux/*.py` (`rg -c
NamedTuple ~/work/python/libtmux/src/libtmux/` and `rg -c '^async
def' ~/work/python/libtmux/src/libtmux/` both return no hits).
gp-sphinx-only would skew the corpus toward directives, fixtures,
and config values that gp-sphinx itself produces — producer-side
bias against the external consumer that motivates this whole
effort.

#### 2.2.2 Step 1 — produce both artifacts in one run

For each corpus:

```console
$ uv run sphinx-build \
    -E -a -b json \
    docs/ /tmp/<corpus>-fjson \
    -D gp_sphinx_phase0_dump=/tmp/<corpus>-objects.json
```

The `-D gp_sphinx_phase0_dump=…` flag is consumed by a small
spike-only `conf.py` shim, committed to `astro/fixtures/spike/`,
not to either docs tree:

```python
# astro/fixtures/spike/_dump.py
from __future__ import annotations
import json
import pathlib
import typing as t

from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict[str, t.Any]:
    def _dump(app: Sphinx, env: t.Any) -> list[str]:
        target = app.config._raw_config.get("gp_sphinx_phase0_dump")
        if not target:
            return []
        py = env.domains.python_domain
        std = env.domains.standard_domain
        out: dict[str, t.Any] = {
            "py_objects": {
                name: {
                    "docname": e.docname,
                    "node_id": e.node_id,
                    "objtype": e.objtype,
                    "aliased": e.aliased,
                }
                for name, e in py.data["objects"].items()
            },
            "std_objects": {k: list(v) for k, v in std.data["objects"].items()},
            "modules": {
                name: {"docname": m.docname, "node_id": m.node_id}
                for name, m in py.data.get("modules", {}).items()
            },
        }
        pathlib.Path(target).write_text(json.dumps(out, indent=2))
        return []

    app.connect("env-updated", _dump)
    return {"version": "0", "parallel_read_safe": True}
```

`env.domains.python_domain` is the workspace-floor accessor (Sphinx
8.1+ `_DomainsContainer`; CLAUDE.md "Sphinx domain access"). The
dump is written before `JSONHTMLBuilder` ever serializes a body, so
it is a pristine view of what the Python domain knows.

#### 2.2.3 Step 2 — load the inventory (third evidence stream)

```console
$ uv run python -c \
    "from sphinx.util.inventory import InventoryFile; \
     import json, pathlib; \
     inv = InventoryFile.load( \
         open('/tmp/gp-sphinx-fjson/objects.inv','rb'), \
         '/tmp/gp-sphinx-fjson/', \
         lambda b, u: u + b.decode()); \
     pathlib.Path('/tmp/gp-sphinx-inv.json').write_text( \
         json.dumps({k: list(v) for k, v in inv.items()}, indent=2))"
```

`_InventoryItem` carries `(project_name, project_version, uri,
display_name)` — verified at
`~/study/python/sphinx/sphinx/util/inventory.py:245-264` (class
declared at `:245`, `__slots__` at `:246`, kw-only `__init__`
populating the four fields at `:253-264`). URI plus display name
only; signatures still cannot come from this stream.

#### 2.2.4 Step 3 — A2 doctree-walk extension prototype

A 50-LOC sibling extension to `_dump.py`, also committed under
`astro/fixtures/spike/`, that hooks `env-updated`, walks
`env.get_doctree(docname)` for `addnodes.desc` nodes, and emits a
parallel `api-index.json`. It is the *honest* test of S — the
pristine doctree before HTML rendering. The full `_extract()`
implementation is left to the spike runner, deliberately: the
author of the spike will encounter the doctree-shape surprises
that motivate the verdict, and pre-writing `_extract()` would
prejudge the answer.

#### 2.2.5 Step 4 — score each case against the rubric

For each case, inspect the matching `.fjson`, the dumped
`py_objects`/`std_objects` JSON, the `objects.inv` row, **and**
the A2 `api-index.json`. Record in the spike fixture:

- Which fields the structured streams (domain `data`,
  `objects.inv`, `searchindex.json`, A2 doctree walk) provide
  directly.
- Which fields require parsing the `.fjson` `body` HTML.
- For each field requiring HTML parsing, whether the markup is
  *structurally addressable* (a stable `id=` anchor on a
  `<dl class="py …">` element with predictable child selectors)
  or *visually addressable only*. **Structurally addressable HTML
  still counts as an "HTML scrape" failure** — the bar is whether
  the field is a value in a JSON/typed object, not whether the
  HTML selector happens to be stable.
- For each case that needs contributor cooperation (extension-
  owned env stores or per-symbol metadata attached to `desc`
  nodes), the smallest adapter LOC that would yield the field.
  This is the "adapter-not-invention" measurement that decides
  H vs P.

#### 2.2.6 Case set — six gp-sphinx + four libtmux

The matrix has 10 cases drawn from both corpora. The libtmux
selections were verified live; line numbers cite HEAD of
`/home/d/work/python/libtmux`:

| # | Corpus | Case | Verified source | Required card fields |
|---|---|---|---|---|
| 1 | gp-sphinx | Plain function | `gp_sphinx.config.merge_sphinx_config` (`packages/gp-sphinx/src/gp_sphinx/config.py:209`) | name, signature, params, return annotation, docstring |
| 2 | gp-sphinx | Type-annotated symbol | `sphinx-autodoc-typehints-gp` exports | raw annotation text, resolved cross-refs |
| 3 | gp-sphinx | Sphinx config value | `sphinx-autodoc-sphinx`, `sphinx-gp-opengraph` config registrations | name, type, default, scope, rebuild trigger |
| 4 | gp-sphinx | Custom docutils node | `sphinx-ux-badges` `BadgeNode` (registered via `app.add_node`, *not* `app.add_directive`, at `packages/sphinx-ux-badges/src/sphinx_ux_badges/__init__.py:73`) | node class, visit/depart payload, options |
| 5 | gp-sphinx | pytest fixture (env-store) | `sphinx-autodoc-pytest-fixtures` `FixtureMeta` at `packages/sphinx-autodoc-pytest-fixtures/src/sphinx_autodoc_pytest_fixtures/_models.py:35-90` — **16 stable-primitive fields**: `docname`, `canonical_name`, `public_name`, `source_name`, `scope`, `autouse`, `kind`, `return_display`, `deps`, `param_reprs`, `has_teardown`, `is_async`, `summary`, `deprecated`, `replacement`, `teardown_summary` | name, scope, autouse, kind, deps, param_reprs, has_teardown, is_async, summary, deprecated, replacement, teardown_summary |
| 6 | gp-sphinx | FastMCP tool | `sphinx-autodoc-fastmcp` self-doc (registered as plain `app.add_directive("fastmcp-tool", ...)` at `packages/sphinx-autodoc-fastmcp/src/sphinx_autodoc_fastmcp/__init__.py:190`; lands in the **std** domain, not py) | name, safety level, parameter schema |
| 7 | libtmux | Multi-mixin class | `libtmux.Server` at `~/work/python/libtmux/src/libtmux/server.py:49-53` (`class Server(EnvironmentMixin, OptionsMixin, HooksMixin):`); `__init__` signature at `:134-144` accepts seven named kwargs (`socket_name`, `socket_path`, `config_file`, `colors`, `on_init`, `socket_name_factory`, `tmux_bin`) plus `**kwargs: t.Any`; NumPy docstring with `Parameters`, `Examples`, `References` sections at `:54-112` | class hierarchy, `__init__` signature, `@property` list, NumPy docstring sections |
| 8 | libtmux | `enum.Enum` subclass | `libtmux.constants.OptionScope` at `~/work/python/libtmux/src/libtmux/constants.py:64` (4 members: `Server`, `Session`, `Window`, `Pane`) — plus 3 sibling enums `ResizeAdjustmentDirection` (`:8`), `WindowDirection` (`:25`), `PaneDirection` (`:38`) | enum name, member name/value pairs, member docstrings |
| 9 | libtmux | `@dataclasses.dataclass()` with mixins | `libtmux.session.Session` at `~/work/python/libtmux/src/libtmux/session.py:50` (`@dataclasses.dataclass()` decorator on a class that also inherits `Obj`, `EnvironmentMixin`, ...) — sibling dataclasses `Window` (`window.py:52`), `Pane` (`pane.py:47`), `neo.Obj` (`neo.py:29`) | dataclass name, field name/type/default tuples, dataclass options, mixin MRO |
| 10 | libtmux | pytest fixture **with embedded doctest** | `libtmux.pytest_plugin.server` fixture at `~/work/python/libtmux/src/libtmux/pytest_plugin.py:144-182` — `@pytest.fixture` decorator at `:144`, `def server(...)` at `:145`, visible doctest in docstring (`>>> def test_example(server: Server) -> None:` at `:154`), `.. ::` hidden meta-test block at `:160-173` that runs through `request._pyfuncitem.dtest.examples` | fixture name, scope, params, deps, the visible doctest preserved verbatim, the hidden `.. ::` block preserved or recoverable |

**Why these libtmux cases specifically.**

- Case 7 stresses MRO and mixins. `Server` inherits from
  `EnvironmentMixin`, `OptionsMixin`, `HooksMixin` and exposes a
  7-named-kwarg `__init__` (plus `**kwargs`). The Python domain
  emits these as `class` objects; whether the field annotations
  and mixin-inherited methods round-trip cleanly through A1/A2 is
  the spike's whole point. Note: `Server` is **not** a
  `@dataclasses.dataclass` — it is a multi-mixin class, distinct
  from case 9.
- Case 8 stresses `enum.Enum` rendering, which Sphinx's autodoc
  historically gets wrong (members surfaced as bare class
  attributes; missing member docstrings).
- Case 9 stresses dataclass-on-mixin-base field rendering — a
  different code path again.
- Case 10 stresses the **doctest-inside-fixture-docstring** pattern
  with hidden `.. ::` self-test blocks. Unique to libtmux among
  reference codebases. Exactly the kind of "weird shape" a
  contrived spike would miss.

Cases 4, 6, 8, and 10 are deliberately **non-py-domain** or
non-py-only symbols; they will not appear cleanly in
`env.domains.python_domain.data["objects"]`. They live in the
standard domain (4, 6), in `enum`'s class machinery (8), or in
fixture-layer metadata (5, 10) where contributor cooperation is the
question.

**Note on fabricated libtmux shapes.** Earlier brainstorm passes
anchored cases on libtmux `t.Self` annotations, NamedTuples, and
async functions. Verified false: the only real `-> Self`
annotation is at `~/work/python/libtmux/src/libtmux/window.py:116`
(`def __enter__(self) -> Self:`); libtmux exercises **fluent
chaining via concrete return types** (`-> Window`, `-> Pane`), not
`-> Self`. Async functions: zero in `src/libtmux/*.py`.
NamedTuple classes: zero. Do not include cases that depend on
shapes libtmux does not actually have. What libtmux *does* have,
beyond cases 7-10, that future Phase-1 work will need to revisit:
22 `LibTmuxException` subclasses (`exc.py`),
`@t.overload`-decorated methods with `t.Literal`-typed
discriminators (e.g., `Pane.display_message` at
`pane.py:476-490`), and 11 `@pytest.fixture`-decorated functions
in `pytest_plugin.py`. Cases 7-10 cover the four shapes that most
stress the JSON-export path; the others are Phase-1 follow-ups.

#### 2.2.7 Pass thresholds

**Spike A1 (`-b json`, structured streams only):** ≥ 7 of 10
cases yield structured data sufficient for a typed `SymbolCard`
*without parsing `.fjson["body"]` HTML* (structurally addressable
HTML still counts as a scrape — see §2.2.5). Recorded primarily
as counter-evidence. A1 ≥ 7/10 *might* permit an even simpler S
than A2 (no Sphinx-extension code at all); A1 < 7/10 is the
expected result.

**Spike A2 (custom doctree-walk extension):** all of the following:

- ≥ **8 of 10** cases extract the required fields from the
  doctree (`addnodes.desc`, contributor env-stores, std-domain
  data) without invoking HTML rendering. Threshold raised from the
  committed 5/6 because adding 4 libtmux cases makes 5/10
  trivially achievable on gp-sphinx alone — exactly the
  producer-side bias this spike now corrects.
- **No required libtmux case (7, 8, 9, 10) may be in the failing
  set.** libtmux is the original target consumer; passing
  gp-sphinx dogfood while failing libtmux is a *false positive*.
- **Cases 1 (plain function) and 5 (pytest fixture) must pass.**
  These are load-bearing for the existing 14 gp-sphinx packages.
- Dev-refresh cost is measured. If S requires a full Sphinx
  rebuild for every Python edit and cannot hit acceptable HMR
  feedback, S does not replace P even if its static export is
  accurate.

8/10 with the libtmux must-pass set and case-1/case-5 tiebreaker
replaces the committed 5/6. The bar increased because the case
set doubled in size and because we are now grading on the corpus
that matters.

### 2.3 Spike B — does the contributor protocol save work?

The committed §2.2 had a dual gate (LOC ≤ 80 *and* "no leakage").
LOC alone is a proxy; "no leakage" alone is judgment-leaky. The
refined version operationalises the dual gate's intent through two
complementary frames.

**Frame 1 — adapter, not invention.** The strongest Spike B framing
isn't "hand-write a new contributor in ≤ 80 LOC." It is:

> Can a small adapter convert existing
> `sphinx_autodoc_pytest_fixtures.FixtureMeta` records
> (`packages/sphinx-autodoc-pytest-fixtures/src/sphinx_autodoc_pytest_fixtures/_models.py:35-90`,
> 16 primitive fields including `scope`, `autouse`, `kind`,
> `deps`, `param_reprs`, `has_teardown`, `is_async`, `summary`,
> `deprecated`, `replacement`, `teardown_summary`) into the
> proposed `ContributorResult` shape?

If the answer is yes in ≤ **40 LOC**, pytest fixtures are not
evidence for P — they are evidence for **H**: Sphinx (or the
package) already owns the semantic metadata; the sidecar only
needs an adapter. The 80-LOC budget remains in force when the
contributor must construct the metadata from scratch. The
metadata builder that populates `FixtureMeta` lives at
`packages/sphinx-autodoc-pytest-fixtures/src/sphinx_autodoc_pytest_fixtures/_metadata.py:268-327`
— useful as the producer-side reference when designing the
adapter.

**Frame 2 — import discipline as the operational gate.** PR
reviewers apply a four-question mechanical checklist to the
standalone harness without reading pytest internals. Each check is
performable by a single `rg` invocation plus, where noted, one
runtime probe:

- **Q-Sem-1** *(import surface).* Does the script import any
  module whose dotted path begins with `_pytest.`,
  `pytest.fixtures`, `pytest.Function`, `pytest.FixtureDef`, or
  any module importable only after `import pytest`? *(Mechanical:
  `rg -nE '^(import|from)\s+(_pytest\.|pytest\.fixtures|pytest\.Function|pytest\.FixtureDef)' <script>`.)*
  If any hit → fail.
- **Q-Sem-2** *(internal-attribute surface).* Does the script
  reach into pytest's wrapper objects directly:
  `obj.__pytest_wrapped__`, `_fixturefunc`, `_fixturedef`, fixture
  marker dicts? *(Mechanical:
  `rg -nE '__pytest_wrapped__|_fixturefunc|_fixturedef' <script>`.)*
  If any hit → fail.
- **Q-Sem-3** *(genericity, two-part mechanical check).* The
  script must compile against an interface that does not name any
  package. Both subparts are `rg`-able and visible at the
  argparse-flag definition; neither requires a hypothetical
  contributor to exist:
  - **Q-Sem-3a (body grep).** `rg -n 'FixtureMeta|sphinx_autodoc_pytest_fixtures'
    <script>` must return no hits in the script body. The harness
    must not name any contributor package in its source. The only
    legal places `pytest`/`fixture` may appear are inside
    `--contributor`-style CLI argument names, argparse `help=`
    strings, or path strings.
  - **Q-Sem-3b (argparse inspection + entry-point loading).**
    The `--contributor` flag must accept an arbitrary dotted path
    and load contributors from config or entry points (e.g.,
    `[project.entry-points."gp_sphinx.contributors"]`). Read the
    argparse setup directly: if the flag hardcodes the
    `sphinx_autodoc_pytest_fixtures:FixtureContributor` entry
    rather than accepting an arbitrary dotted path, fail.
    Replacing the configured contributor with a future
    `sphinx_ux_badges:BadgeContributor` (or any other) must not
    require editing the harness body — the diff must be confined
    to the configured entry-point name or the `--contributor`
    argument value.

  Q-Sem-3 stays mechanical because both subparts are `rg`-able and
  inspectable at flag-definition time; it does not require a
  hypothetical contributor to be implemented.
- **Q-Sem-4** *(absence-tolerance probe).* If
  `sphinx-autodoc-pytest-fixtures` were uninstalled
  (`uv remove sphinx-autodoc-pytest-fixtures` in a scratch venv
  built from the harness manifest), would the script's `import`
  statements still resolve and produce a clear "no contributors
  registered" message rather than an `ImportError`? *(Mechanical:
  actually try it once.)* If `ImportError` → fail.

**Pass:** all four Q-Sem questions answered cleanly **and** either
(a) the adapter frame succeeds in ≤ 40 LOC, or (b) the
hand-written contributor frame succeeds in ≤ 80 LOC. LOC is
recorded as evidence — a 200-LOC script that imports only public
surface is fine — but the **import discipline gate is the binding
condition**. An AST or `_pytest.fixtures` introspection
copy-paste fails Q-Sem-1 and fails Spike B even if it hits the
LOC bar.

#### 2.3.1 AST / `_pytest` internals gate

The Q-Sem checklist above operationalises the "no AST or
`_pytest` internals copying" rule: Q-Sem-1 catches `_pytest.*`
imports and `_fixturedef` access; Q-Sem-2 catches
`__pytest_wrapped__` introspection. A 60-LOC shim that
re-implements `pytest._pytest.fixtures.FixtureManager.getfixtureclosure`
inside the sidecar is a Spike B *failure*, not a success — the
protocol has no value if it doesn't keep package-specific
knowledge inside the package.

### 2.4 Decision matrix

The five-cell partition replaces the committed four-cell matrix.
Cells are defined by Spike A2 outcome × libtmux must-pass set ×
Spike B outcome × tooling-debt evidence (recorded co-equally,
*not* used as a tie-breaker after the fact).

| Spike A2 (doctree-walk) | libtmux must-pass set (cases 7-10) | Spike B (Q-Sem + adapter/LOC) | Tooling debt | Decision |
|---|---|---|---|---|
| ≥ 8/10 with cases 1, 5 in passing set | **all four** of 7, 8, 9, 10 pass | any | low: no separate sidecar | **S** |
| ≥ 8/10 with cases 1, 5 passing | **all four** of 7, 8, 9, 10 pass | adapter passes (≤ 40 LOC) | medium: adapters per package, but no parallel introspection | **H** |
| ≥ 8/10 on gp-sphinx subset, **< 4/4** on libtmux, **and** the failing cases are extension-owned metadata cases re-testable through a real Astro+sidecar HMR loop | partial | passes | high: re-score deferred | **Deferred-H** (provisional P scaffold; re-run §2.2 at Phase 4 against actual libtmux build, with a *dated* re-score in the verdict YAML) |
| < 8/10, OR cases 1/5/7/8/9/10 fail in shapes that won't survive a Phase-4 re-test | any | passes | high: full sidecar + contributors | **P** |
| < 8/10 (or libtmux must-pass fails) | any | fails | very high: sidecar reimplements, debt tickets per duplicated collector | **P-minimal** |

**Why Deferred-H is genuinely distinct from H.** H requires the
libtmux must-pass set to be satisfied *now* — both the common-API
half (Sphinx export) and the extension-specific half (contributor
adapters) have proven themselves before the verdict commits.
Deferred-H exists for the asymmetric outcome where only the
common-API half has proven itself: S works on gp-sphinx, fails on
libtmux in shapes that look re-testable once the Astro+sidecar
HMR loop exists. The right next move there is "ship P now,
persist the spike fixtures, and re-run §2.2 against a real
Astro+sidecar build at Phase 4 when one exists." Without the
explicit, *dated* Phase-4 re-score gate (see §2.7's `re_score_date`
YAML field), "Deferred-H" would collapse back into "we hope it's
H." With the dated gate, it is a real architecture verdict that
records both what we ship and *when* we re-decide.

The verdict table records, for each surviving architecture:

| Axis | Measurement |
|---|---|
| CI commands | number of new CI commands required before first useful preview |
| Cache surfaces | number of new cache directories whose invalidation matters |
| Language bridges | Python→JSON, JSON→Zod, Sphinx→JSON counted separately |
| Contributor count | contributors required before gp-sphinx dogfood is useful |
| Fallback behavior | per-symbol, per-root, or whole-index degradation |
| Package/release burden | whether PyPI/npm release order affects local dogfood |

This is *evidence in the verdict*, not a tie-breaker.

**Default if Phase 0 is skipped: P** (unchanged from committed
plan; every section after §2 describes P, with §6.5 documenting
the S divergence). **Default if Phase 0 is inconclusive but meets
the strict Deferred-H definition above: Deferred-H.** Default for
all other inconclusive results: **P**. S-defer-as-default is
rejected because S-defer trades clarity for hedge — Deferred-H is
honest about what it is *and* commits a re-score date.

A1's role is informational: A1 ≥ 7/10 *might* eliminate the need
for any Sphinx extension at all, in which case the verdict prefers
A1 over A2. A1 < 7/10 is the expected outcome and does not change
the matrix.

### 2.5 What it would take to actually ship S

S survives only if Spike A2 produces a complete enough payload
that contributor protocols become unnecessary. Concretely, S wins
iff *all* of these hold:

1. `addnodes.desc.children[0]` (the signature) reliably contains
   parsed parameter nodes with annotation children for plain
   functions, methods, and properties. Verify against cases 1, 7.
2. `enum.Enum` rendering produces traversable member nodes with
   member docstrings, not a flattened table. Verify against case 8.
3. `@dataclasses.dataclass()` rendering exposes field defaults,
   types, and dataclass options as parsed nodes. Verify against
   case 9.
4. `sphinx-autodoc-pytest-fixtures` and `sphinx-autodoc-fastmcp`
   already write per-symbol metadata into doctree node attributes
   (e.g., a `gp_sphinx_metadata` dict on `desc`) **or** into env-
   stores (`FixtureMeta` already does this), *and* the sidecar
   can read those without `import pytest` / `import fastmcp`.

Item 4 is load-bearing. If those packages don't already attach
machine-readable metadata to their `desc` nodes or env-stores,
then under S we either (a) add a "metadata-only contributor" shim
to each — which is the contributor protocol with extra steps —
or (b) do post-hoc HTML/text scraping of their rendered output,
which is the exact thing we're trying to avoid. Spike A2 must
verify item 4 before declaring S viable. (`FixtureMeta` already
satisfies item 4 for pytest fixtures, verified at
`_models.py:35-90` — this is the load-bearing counter-example to
"S is structurally impossible".)

### 2.6 Why the spike is non-negotiable

Skipping Phase 0 commits the project to building and maintaining a
parallel Python introspection process the rest of its life on the
hypothesis that Sphinx export is insufficient. That hypothesis is
plausible but not free to assume — the Python domain has typed
`ObjectEntry` records (4 fields) and the inventory format is
stable, so a disciplined Sphinx-export-plus-env-store path *might*
cover the dogfood. One engineer-day of evidence is the right cost
to commit to the sidecar.

Running Phase 0 against gp-sphinx *only* commits the project to
that hypothesis on a corpus designed by the same author. The
libtmux co-equal frame is the difference between "we tested on the
easy case" and "we tested on the hard case." If S works on
libtmux, it works everywhere we care about. If S fails on libtmux
while working on gp-sphinx, that is Deferred-H, and we know it
upfront instead of discovering it at Phase 4 when the cost of
switching architectures is 100× higher.

The countervailing risk is also real: `ObjectEntry` carries no
signature or docstring. If signature data only survives the export
as HTML in the `.fjson` `body`, S degrades into a maintained HTML-
parsing path — which is what the "no HTML scraping" bar in §2.2.5
exists to detect.

### 2.7 Phase 0 exit criteria

Phase 0 is complete only when *all* of these exist:

- `notes/plans/astro-phase-0-verdict.md` lands with YAML
  front-matter:

  ```yaml
  architecture: S | H | P | P-minimal | Deferred-H
  reproducibility_gate: clean | workaround | blocked
  reproducibility_workaround: <description or "none">
  spike_a1: pass | fail
  spike_a2: pass | fail
  libtmux_must_pass_set: pass | fail
  case_1_5_tiebreaker: pass | fail
  spike_b: pass | fail | not_needed
  html_body_scraping: forbidden
  re_score_phase: none | 4
  re_score_date: <ISO date or "none">
  ```

  The `re_score_date` field is non-optional whenever
  `architecture: Deferred-H`. An empty or missing date for
  Deferred-H invalidates the verdict — that's the line that
  prevents Deferred-H from being a hedge.
- `astro/fixtures/spike/` populated with, for each of the 10
  cases:
  - The relevant `.fjson` file (or excerpt) from each corpus.
  - The corresponding entry from the dumped `py_objects` /
    `std_objects` JSON.
  - The corresponding `objects.inv` row.
  - The corresponding A2 doctree-walk output entry.
  - A one-paragraph "what was missing" note keyed to the §2.2.5
    rubric, including any `FixtureMeta`-style env-store row used
    in lieu of doctree data.
- `astro/fixtures/spike/_dump.py` and the A2 doctree-walk
  extension source, both committed alongside the verdict so the
  spike is reproducible.
- Spike B harness committed under
  `astro/fixtures/spike/contributors/`, with: the standalone
  script, its emitted JSON for one fixture, the four Q-Sem
  checklist responses (each citing the `rg` invocation that
  confirmed the result), and the LOC count recorded as evidence.
- For S, H, or Deferred-H verdicts: an acceptance test that
  produces **both** the `merge_sphinx_config` symbol card *and*
  the `libtmux.Server` symbol card in < 1 s wall-clock from a
  clean cache (running both because gp-sphinx-only would let the
  sampling bias back in).
- For P-minimal: one issue opened for each duplicated collector,
  with a Phase-4 re-score date.
- Phase-1 issue opened with the chosen architecture in the title.

The fixture requirement is *not* bookkeeping. These files are
promoted to seed data for `@gp-sphinx-astro/schema`, renderer
snapshots, and the first Astro route before the sidecar or Sphinx
integration is stable (see §13 Q12 for how this connects to the
two-tier snapshot blessing).

### 2.8 Scope of this section

This section commits to the reproducibility gate, the A1/A2 split,
the 8/10 threshold with libtmux must-pass + case-1/case-5
tiebreaker, the Q-Sem-1/2/3a/3b/4 checklist, the five-cell
decision matrix, and the dated re-score gate that distinguishes
Deferred-H from H-but-unsure. It defers the following to other
sections or to Phase-0 outcome:

- The `_extract()` body of the A2 doctree-walk extension: deferred
  to the spike runner. Pre-writing it would prejudge the answer;
  the doctree-shape surprises the runner encounters are the
  evidence the verdict needs.
- §6 architecture sections and §11 snapshot infrastructure: not
  redesigned here. The §2.1 reproducibility gate and the §2.7
  spike-fixtures-as-snapshot-seeds note are the only cross-section
  changes implied; both are forward references, not new design.
- Public package naming: the three names
  (`gp-sphinx-astro-builder`, `gp-sphinx-tsx-builder`,
  `gp-sphinx-astro-theme`) are fixed and not revisited.
- libtmux source-tree mutation: forbidden. All libtmux cases are
  read-only; the spike vendors a minimal `conf.py` mirror rather
  than editing libtmux's docs config.
- Synthetic-fixture injection into gp-sphinx itself: rejected on
  CLAUDE.md "project-read-only" grounds, and moot anyway because
  libtmux has zero `NamedTuple` classes and zero `async def`
  functions.

---

## 3. Naming, tier map, CSS namespace

### 3.1 Public packages (npm) — fixed by user constraint

| Package | Role |
|---|---|
| `gp-sphinx-tsx-builder` | TypeScript engine. Validated data → typed `ApiIndex` + `ApiGraph`. **No Astro coupling.** |
| `gp-sphinx-astro-builder` | Astro integration. Wraps the engine, exposes virtual modules + Content Loader. |
| `gp-sphinx-astro-theme` | Tailwind v4 plugin + Astro components for autodoc rendering. |

These three names are fixed and never to be renamed or dropped.
Any future component that wants public visibility lands inside one
of these three packages or as a fourth package in Phase 7+ (e.g.,
the deferred Furo bridge, §9.4).

### 3.2 Internal TypeScript packages — exactly two

```text
@gp-sphinx-astro/schema       — Zod 4 schemas + inferred types, zero runtime
@gp-sphinx-astro/intersphinx  — objects.inv parser + resolver
```

Each has a legitimate independent reuse story (a future linter
could import the schema; a "link my README to Python stdlib docs"
tool could import the resolver). We reject 5–7 internal packages
as scaffolding tax; reject 0 because then schema becomes private to
`tsx-builder`; reject 1 because schema and intersphinx share zero
code.

### 3.3 Python sidecar (P/H)

Workspace member at `packages/gp-sphinx-sidecar/`. The uv workspace
already declares `members = ["packages/*"]` at
`/home/d/work/python/gp-sphinx/pyproject.toml:16`, so adding the
package needs no root edit.

- Distribution name: `gp-sphinx-sidecar`
- Import name: `gp_sphinx_sidecar`
- Console script: `gp-sphinx-sidecar`
- `private = true` in pyproject for Phases 1–4; PyPI in Phase 5
  contingent on **both gates**: ≥3 contributors shipped against
  the protocol *and* one non-Astro consumer plausible

The convention `-sidecar` (rather than `-introspect`) names the
role the package plays in the pipeline, not the verb it performs.
Workspace-private means the integration tests `uv run` it from the
repo, but PyPI consumers cannot install it until the gates trip.

### 3.4 CSS and custom-property namespace

All new Astro CSS classes live under `gp-sphinx-astro-*`, mirroring
the project's existing `gp-sphinx-*` Tier A/B convention from
`CLAUDE.md` ("CSS Standards" section).

- **Tier A** (shared concepts): `gp-sphinx-astro-<concept>` — e.g.,
  `gp-sphinx-astro-symbol-card`, `gp-sphinx-astro-toolbar`
- **Tier B** (package-owned BEM): `gp-sphinx-astro-<pkg>__<thing>`
  — e.g., `gp-sphinx-astro-theme__sidebar-section`,
  `gp-sphinx-astro-builder__diagnostic-panel`
- **Modifiers**: axis-value pairs `--<axis>-<value>` — e.g.,
  `gp-sphinx-astro-symbol-card--kind-class`,
  `gp-sphinx-astro-symbol-card--density-compact`
- **Custom properties**: `--gp-sphinx-astro-<pkg>-<token>` — e.g.,
  `--gp-sphinx-astro-theme-color-accent`,
  `--gp-sphinx-astro-builder-toolbar-height`

Where a class is genuinely shared between Sphinx and Astro (e.g.,
`gp-sphinx-badge` from `sphinx-ux-badges`, palette at
`/home/d/work/python/gp-sphinx/packages/sphinx-ux-badges/src/sphinx_ux_badges/_static/css/sab_palettes.css:349-399`),
the Astro side reuses the class name and ports the CSS contract —
one CSS contract, two transports. Per `CLAUDE.md`'s "Package CSS
self-containment" rule, the Astro theme styles every class its
own components emit. Cross-package *reuse* of a shared class is
fine; cross-package *dependence* — where a feature only renders
correctly because a sibling package happens to be loaded — is not.

Furo-owned variables under
`~/study/python/furo/src/furo/assets/styles/` stay untouched. The
Sphinx theme remains separate.

---

## 4. Monorepo layout

### 4.1 Default — nested `astro/` directory (Option N)

```text
gp-sphinx/
├── pyproject.toml                   # unchanged
├── packages/                        # 14 Python packages + 1 sidecar
│   ├── gp-sphinx/
│   ├── sphinx-gp-theme/
│   ├── sphinx-fonts/
│   ├── sphinx-ux-badges/
│   ├── sphinx-ux-autodoc-layout/
│   ├── sphinx-autodoc-api-style/
│   ├── sphinx-autodoc-typehints-gp/
│   ├── sphinx-autodoc-argparse/
│   ├── sphinx-autodoc-pytest-fixtures/
│   ├── sphinx-autodoc-docutils/
│   ├── sphinx-autodoc-sphinx/
│   ├── sphinx-autodoc-fastmcp/
│   ├── sphinx-gp-opengraph/
│   ├── sphinx-gp-sitemap/
│   └── gp-sphinx-sidecar/           # NEW, uv workspace member
├── astro/                           # NEW pnpm workspace root
│   ├── pnpm-workspace.yaml          # packages: ['packages/*', 'apps/*']
│   ├── package.json
│   ├── tsconfig.base.json
│   ├── biome.json
│   ├── vitest.workspace.ts
│   ├── AGENTS.md
│   ├── packages/
│   │   ├── schema/                  # @gp-sphinx-astro/schema (private)
│   │   ├── intersphinx/             # @gp-sphinx-astro/intersphinx (private)
│   │   ├── tsx-builder/             # gp-sphinx-tsx-builder (PUBLIC)
│   │   ├── astro-builder/           # gp-sphinx-astro-builder (PUBLIC)
│   │   └── astro-theme/             # gp-sphinx-astro-theme (PUBLIC)
│   ├── fixtures/
│   │   ├── gp-sphinx-snapshot/      # vendored copy of gp-sphinx for integration tests
│   │   ├── inventories/             # real objects.inv files
│   │   └── spike/                   # Phase 0 evidence payload
│   └── apps/
│       └── gp-sphinx-docs/          # The dogfood consumer site
├── docs/                            # existing Sphinx docs (unchanged)
└── notes/
    └── plans/
        ├── astro.md                 # this plan
        └── astro-phase-0-verdict.md # produced by Phase 0
```

**Why nested.** A Python-only contributor never has to think about
pnpm or `node_modules` until they touch the Astro stack
explicitly. The cost of the bilingual root falls on the larger
contributor base.

**Critical sidecar placement.** Even under N, the sidecar package
goes under `packages/` (not `astro/python/`) so it sits next to
`sphinx-autodoc-*` packages and imports them as
`[project.optional-dependencies]` extras. It is Python code and
must follow uv workspace conventions; placing it under `astro/`
would also break uv workspace discovery
(`/home/d/work/python/gp-sphinx/pyproject.toml:16` — `members =
["packages/*"]`).

**Note divergence from tony.sh.** tony.sh's `pnpm-workspace.yaml`
declares only `packages: - packages/*` (verified at
`~/work/tony.sh/pnpm-workspace.yaml`). We add `apps/*` because the
Astro stack ships an `apps/gp-sphinx-docs` site; tony.sh has no
analogous app-vs-package split. This is intentional, not an
inheritance.

### 4.2 Option B — bilingual root, deferred to Phase 7+

Promotion path is a `git mv astro/* .` plus a workspace-config
rewrite, documented as a Phase-7+ option after the Astro stack
proves permanent. Demotion from B back to N is much harder once
histories entangle, which is why we start nested.

---

## 5. Zod 4 schema contract — and the two-version contract

The schema is the wire contract between the sidecar and the rest
of the stack. Without a versioned, validated shape the TS side has
to trust whatever the Python side prints.

**Important:** Astro 6.1.9 ships `zod ^4.3.6` (verified at
`~/study/typescript/astro/packages/astro/package.json:176`) and
uses Zod 4 idioms internally. The Astro Content Loader uses
`schema?: z.$ZodType` at
`~/study/typescript/astro/packages/astro/src/content/loaders/types.ts:65`
inside the `Loader` type at lines 57-74. Our schema must use Zod 4
syntax (`z.$ZodType<T>`, with leading `$`), not Zod 3's
`z.ZodType<T>`.

### 5.1 Hard rules

1. **Versioned envelope.** Every payload starts with both
   `schemaVersion` (wire) and `protocolVersion` (in-memory IPC)
   plus a `features: string[]` capability list (see §5.2 for the
   shape).
2. **No `z.any()` or `z.unknown()` in the public API.** Use a
   discriminated union with an explicit `kind: "unknown"` arm.
3. **Stable, deterministic IDs.**
   `id = "<package>:<dotted.module>:<qualname>:<kind>"`. No
   wall-clock, no random suffixes — the ID is reproducible from
   source.
4. **Source spans on every symbol.** `{ file, lineStart, lineEnd }`.
5. **Errors are first-class.** `AnalysisError` is a schema type
   carrying `{ id, kind, packageRoot, module, symbol, message,
   severity }`. The wire format always validates; failures go in
   `errors[]`, never thrown across the boundary except for
   whole-index failure (§6.4).
6. **Backwards-compatible additions only within a major.** Adding
   an optional field is fine; renaming or removing requires a
   major bump.
7. **`features: string[]` from day one.** Same wire cost as a
   single integer; consumers detect partial coverage without
   forcing major bumps.

### 5.2 The two-version contract

The plan needs **two** independent version axes that earlier passes
conflated:

| Axis | What it covers | Example value | Bump trigger |
|---|---|---|---|
| `schemaVersion` (wire) | Shape of the JSON `ApiIndex` payload | `1` | Field rename, type narrowing, removal |
| `protocolVersion` (Python in-memory) | Signature of `SymbolContributor.claims` / `describe` | `1` | Adding required Protocol method, changing parameter shape |

The wire version is checked by the JS bridge before parsing
(`gp-sphinx-sidecar schema-version` returns both). The protocol
version is checked by the sidecar at entry-point load time; an
older contributor loaded against a newer sidecar emits
`AnalysisError` with `kind: "contributor-protocol-mismatch"` and
is skipped, never crashing the build.

This separation matters because the wire format and the Python
Protocol API will not co-evolve. A new Protocol method (e.g.,
`describe_async`) doesn't change the shape of emitted JSON; a new
schema field (e.g., `Symbol.deprecated_since: str | null`) doesn't
change the Protocol signature. Lumping them is a recipe for
spurious major bumps.

This is the strongest invisible contribution of the planning
work. It is non-negotiable — both axes ship in v1.

### 5.3 The `SymbolKind` union — gp-sphinx-aware on day one

```typescript
import { z } from 'zod'

export const SymbolKind = z.enum([
  // Plain Python
  'package', 'module', 'class', 'function', 'method',
  'property', 'attribute', 'variable', 'constant',
  'type-alias', 'exception',
  // gp-sphinx-specific (matches what sphinx-ux-autodoc-layout
  // already recognizes: std:confval, rst:directive, rst:role,
  // rst:directive:option, mcp:tool — see _transforms.py:106-131)
  'directive', 'role', 'directive-option', 'config-value',
  'argparse-cli', 'argparse-command', 'argparse-subcommand',
  'argparse-argument',
  'pytest-fixture',
  'mcp-tool',
])
```

Phase 1 only needs `function | class | method | attribute | module
| package` to *land*; the gp-sphinx-specific kinds are
schema-defined-but-not-yet-emitted so adding contributors in
Phase 5/6 doesn't require a coordinated schema bump. This list is
not speculative — these are the kinds actually used across the 14
packages today (badge palettes at
`/home/d/work/python/gp-sphinx/packages/sphinx-ux-badges/src/sphinx_ux_badges/_static/css/sab_palettes.css:349-399`
already provision visual treatment for fixture scopes, config
values, and docutils directive/role/option classes).

### 5.4 Type references and the two-channel annotation model

Zod 4 recursive pattern uses the leading `$`. `z.ZodType<T>` is
Zod-3 syntax and will not type-check against Astro 6's bundled
Zod 4 (`~/study/typescript/astro/packages/astro/package.json:176`,
`zod ^4.3.6`).

```typescript
import { z } from 'zod'

interface TypeRef {
  raw: string
  kind: 'name' | 'subscript' | 'union' | 'callable' | 'tuple'
        | 'literal' | 'unknown'
}

const TypeRefBase = z.object({ raw: z.string() })

export const TypeRef: z.$ZodType<TypeRef> = z.lazy(() =>
  z.discriminatedUnion('kind', [
    TypeRefBase.extend({
      kind: z.literal('name'),
      target: z.string().nullable(),
    }),
    TypeRefBase.extend({
      kind: z.literal('subscript'),
      value: TypeRef,
      args: z.array(TypeRef),
    }),
    TypeRefBase.extend({
      kind: z.literal('union'),
      members: z.array(TypeRef),
    }),
    TypeRefBase.extend({
      kind: z.literal('callable'),
      params: z.array(TypeRef),
      returns: TypeRef,
    }),
    TypeRefBase.extend({
      kind: z.literal('tuple'),
      members: z.array(TypeRef),
      variadic: z.boolean(),
    }),
    TypeRefBase.extend({
      kind: z.literal('literal'),
      value: z.union([
        z.string(),
        z.number(),
        z.boolean(),
        z.null(),
      ]),
    }),
    TypeRefBase.extend({ kind: z.literal('unknown') }),
  ]),
)
```

Annotations carry both `annotationText: string | null` (always
populated when an annotation exists; on Python 3.14+ via
`annotationlib.Format.STRING`) and `annotationRef: TypeRef | null`
(structured form, populated only when evaluation succeeded). The
two-channel split is what lets the renderer always show *something*
even when type evaluation fails.

### 5.5 Top-level envelope

```typescript
import { z } from 'zod'
import {
  Package, Module, Symbol, AnalysisError, LinkIndex,
} from './nodes'

export const ApiIndex = z.object({
  schemaVersion: z.literal(1),
  protocolVersion: z.literal(1),
  features: z.array(z.string()),
  generatedAt: z.string(),               // ISO-8601 derived from content hash
  generator: z.object({
    name: z.string(),
    version: z.string(),
  }),
  project: z.object({
    name: z.string(),
    root: z.string(),
    packages: z.array(z.string()),
  }),
  packages: z.array(Package),
  modules: z.record(z.string(), Module),
  symbols: z.record(z.string(), Symbol),
  links: LinkIndex,
  errors: z.array(AnalysisError),
})

export type ApiIndex = z.infer<typeof ApiIndex>
```

The `features` array records partial capability — `core`,
`contributor.pytest-fixtures`, `contributor.argparse`,
`contributor.fastmcp`, `fallback.static`, `intersphinx.emit`. A
consumer that needs `contributor.fastmcp` can fail loudly if the
index doesn't advertise it.

### 5.6 Schema source-of-truth and drift control

| Phase | Path |
|---|---|
| **Phase 1–2** | Zod source of truth. Sidecar maintains `gp_sphinx_sidecar.schema` Pydantic v2 module by hand. CI validates representative payloads on both sides. |
| **Phase 5+** | `to-pydantic.ts` emits `schema.py` from the Zod schema. Generated file is committed (PyPI consumers don't need Node), pre-commit hook regenerates and CI fails if stale. |

We reject the "build a new Pydantic-based JSON Sphinx builder"
proposal: it introduces new Sphinx-side machinery while claiming to
reuse what Sphinx has. If Phase 0 chooses S, the existing
`JSONHTMLBuilder` plus a thin `gp_sphinx.export` stitcher is the
path.

---

## 6. Pipeline architecture (P default)

### 6.1 Two paths, one schema

| Path | Owner | Cost |
|---|---|---|
| **Static fast path** | Sidecar `--mode static`, walks files with stdlib `ast` | tens of ms per package |
| **Runtime truth path** | Sidecar `--mode runtime`, `inspect.signature` + `annotationlib` + contributors | seconds per package |

Default for dev: `hybrid`. Default for CI build: `hybrid`, with
whole-index failure as an error.

**Why Python `ast`, not `tree-sitter-python`.** Python `ast` is
stdlib, ships wherever the sidecar runs, and produces the right
shape on the first pass. Tree-sitter would mean a Node-side
Python parser whose grammar can lag the language, plus a native
dep. The static path running *in the sidecar* (not Node) keeps
both modes in one language so contributors can be reused between
them.

### 6.2 Sidecar lifecycle — one-shot subprocess

Universally rejected across brainstorm sources: a long-lived
stdin/stdout JSON-RPC daemon. Each invocation is a fresh Python
process; the bridge `execa`-spawns it and parses stdout. One-shot
subprocesses are simpler to reason about, easier to kill, and
compatible with dev-server refresh.

| Astro hook | Sidecar action | Reference |
|---|---|---|
| `astro:config:setup` | One `uv run gp-sphinx-sidecar introspect-package <root>` per configured root; output captured, validated, cached in memory | `~/study/typescript/astro/packages/astro/src/types/public/integrations.ts:341` |
| `astro:server:setup` | chokidar watcher on `**/*.py`; on change, debounced 250 ms, re-spawn for affected root, surgically invalidate (§6.6); the payload also exposes `refreshContent?` at line 367 for content-collection invalidation | `:363-368` (`server: ViteDevServer` at line 364) |
| `astro:build:start` | Single shot, cached on disk under `.astro/cache/api-index/<root-slug>-<root-content-hash>.json` (§6.7) | `:382` |
| `astro:build:done` | Print stats; crash with `allowEmptyApiIndex` guidance if index empty | `:400` |

### 6.3 Caching layers

| Layer | Key | TTL |
|---|---|---|
| In-memory | content-hash | dev session |
| `.astro/cache/api-index/<root-slug>-<root-content-hash>.json` | content hash + sidecar version + schema version + protocol version + contributor versions + uv.lock + pnpm-lock.yaml + relevant pyproject.toml hashes | until invalidated |
| `.astro/cache/api-index/last-good.json` | n/a — always the most recent schema-valid, non-empty payload | until manually wiped |
| GitHub Actions cache | lockfile + content-hash | per-commit |

### 6.4 Error budget

Per-symbol and per-module failures degrade through four levels:

1. Truth path succeeds → use `ApiIndex` from sidecar
2. Truth path fails for one module → record `AnalysisError`, fall
   back to static-path data
3. Truth path fails entirely (uv missing, Python missing) →
   static path only with prominent warning; site builds
4. Static path fails on one file → record `AnalysisError`, drop
   the file

**Whole-index failure is the exception.** If neither path produces
any usable data anywhere — every package emits empty — the build
**fails** unless the user opts in:

```typescript
gpSphinxAstro({
  packageRoot: '../../packages/gp-sphinx/src/gp_sphinx',
  allowEmptyApiIndex: false,    // default; whole-index failure crashes
  allowStaleApiIndex: false,    // default; do not serve last-good silently
})
```

Silent empty API pages are a worse failure mode than a loud build
error. The opt-ins exist for preview builds during sidecar-breaking
refactors.

`allowStaleApiIndex: true` opts in to serving the cached
`last-good.json` index in dev with a visible warning banner, and
in CI as a build warning. It is the sibling of
`allowEmptyApiIndex`. Default off because "the docs are
mysteriously not updating" is a worse experience than a loud
build failure.

### 6.5 Architecture S divergence

If Phase 0 picks S, the `gp_sphinx.export` hook is a new internal
subpackage of `gp-sphinx` (not a separate workspace package). It
consumes:

- `.fjson` payloads (per-page rendered HTML body + TOC + metadata)
- The resolved Python domain inventory —
  `env.domains.python_domain.data["objects"]` plus the typed
  `ObjectEntry` records (`~/study/python/sphinx/sphinx/domains/python/__init__.py:60-65`)
- `objects.inv` for inventory-compatible cross-links
  (`~/study/python/sphinx/sphinx/util/inventory.py:43-63`)

…and stitches them into the schema-shaped `ApiIndex`. The TS side
never imports Python; the contract is the JSON file on disk.

S removes the sidecar, the contributor protocol (§7), and the
two-path complexity (§6.1). Trade-off: dev-server feedback inherits
Sphinx's incremental-build latency (seconds for small changes),
whereas P's chokidar + per-root sidecar respawn is sub-second.

**Domain access in `gp_sphinx.export`** must use the typed
accessors `env.domains.python_domain` etc., not
`env.get_domain("py")` (verified at
`~/study/python/sphinx/sphinx/domains/_domains_container.py:144-153`,
introduced in Sphinx 8.1, the gp-sphinx workspace floor per
`CLAUDE.md`'s "Sphinx domain access" section).

### 6.6 Dev-server reload story

The dev path is six steps:

1. `pythonLoader` adds all configured package roots **and**
   sidecar/contributor files to the watcher. Watching contributor
   files matters: editing
   `packages/sphinx-autodoc-pytest-fixtures/src/sphinx_autodoc_pytest_fixtures/_sidecar.py`
   *must* refresh the docs even though it's not in any user's
   package root.
2. On a changed `.py`, debounce 250 ms.
3. Re-run sidecar only for the owning package root (mapped from
   the file path by ancestor walk).
4. Replace the affected package/module entries in the in-memory
   `store`.
5. Invalidate the bespoke virtual API module via Vite's module
   graph (the *how* of step 5; see code below).
6. Call `refreshContent({ context: { reason: "python-change",
   path } })` for content-collection-backed pages.

Step 5 in code, inside `astro:server:setup`:

```typescript
// inside astro:server:setup (server: ViteDevServer at line 364)
const mod = server.moduleGraph.getModuleById(
  '\0virtual:gp-sphinx-astro/api',
)
if (mod) {
  server.moduleGraph.invalidateModule(mod)
  server.ws.send({ type: 'full-reload' })
  // or per-page if we track which pages consume which roots
}
```

This is the surgical-invalidation path: only the virtual module is
busted, only pages that import it reload. A naive
`server.restart()` would drop dev-tool state across all pages and
is rejected.

The `refreshContent` call at step 6 covers content-collection
pages backed by the loader; the `moduleGraph.invalidateModule`
call at step 5 covers the bespoke `virtual:gp-sphinx-astro/api`
module that components import directly. They operate at different
levels and compose — both are required.

Roots that didn't change retain their cached data — no whole-index
re-spawn.

### 6.7 Per-root cache keying

Earlier drafts cached a single `.astro/cache/api-index.json` keyed
by the content hash of *all* `.py` files plus sidecar version plus
schema version. This is wrong for partial failure.

Failure mode it allows: sidecar fails for `sphinx-autodoc-fastmcp`
mid-build. Cache file gets written with `errors[]` for that root.
Next build, content hash hasn't changed, cache hits, error
persists, even after the user fixes the bug. The user has to
`rm -rf .astro/cache` to recover.

Fix: **one cache file per root.**

```text
.astro/cache/api-index/
├── gp-sphinx-<hash>.json
├── sphinx-gp-theme-<hash>.json
├── sphinx-fonts-<hash>.json
├── sphinx-ux-badges-<hash>.json
├── sphinx-ux-autodoc-layout-<hash>.json
├── sphinx-autodoc-api-style-<hash>.json
├── sphinx-autodoc-typehints-gp-<hash>.json
├── sphinx-autodoc-argparse-<hash>.json
├── sphinx-autodoc-pytest-fixtures-<hash>.json
├── sphinx-autodoc-docutils-<hash>.json
├── sphinx-autodoc-sphinx-<hash>.json
├── sphinx-autodoc-fastmcp-<hash>.json
├── sphinx-gp-opengraph-<hash>.json
├── sphinx-gp-sitemap-<hash>.json
└── last-good.json
```

A root only re-runs if its own content hash changed. Errors
localize. Recovery is per-root: deleting just the file for the
broken root forces a re-run while preserving 13 other cached
results.

### 6.8 `last-good` cache discipline

Per-root sharding is the *write granularity* fix. `last-good`
preservation is the *failure-recovery* fix. Both ship.

Policy:

- If the sidecar succeeds with errors for some modules, write
  `current` and keep `last-good`; build succeeds with warnings.
- If runtime fails but static succeeds, write `current` with
  `features: ["core", "fallback.static"]`; build succeeds with
  warnings.
- If the whole index is empty, fail unless `allowEmptyApiIndex:
  true`.
- If `allowStaleApiIndex: true` and current generation fails before
  any usable data exists, serve `last-good` with a visible warning
  banner in dev and a build warning in CI.
- **Never silently overwrite `last-good` with an empty or
  schema-invalid payload.** This is the load-bearing policy bullet
  — if `last-good` can be poisoned, the whole story collapses.

### 6.9 Build-cache survival during partial sidecar failure

`astro build` re-uses Vite's transform cache between runs. If the
sidecar emits valid JSON for 13 of 14 packages on one run and the
same 13 on the next, the per-page HTML for those 13 packages
should serve from Vite's cache without re-rendering.

This requires that the integration's virtual-module response is
*stable byte-for-byte* across runs when the underlying data hasn't
changed. JSON-stringify with sorted keys; ISO-8601 `generatedAt`
substituted with a value derived from the per-root content hash,
not wall-clock time (otherwise every run mints a new cache key).
Earlier drafts kept `generatedAt: <ISO>` as wall-clock; we keep
the field but *derive it from the content hash* (`hash → epoch
seconds → ISO-8601`) so it remains stable across rebuilds of
identical content.

---

## 7. Contributor protocol

Under P (and as fallback under H), the seven `sphinx-autodoc-*`
packages are *not* re-derived in the sidecar. They are imported
via an entry-point plugin protocol. The seven contributor packages
are: `sphinx-autodoc-api-style`, `sphinx-autodoc-typehints-gp`,
`sphinx-autodoc-argparse`, `sphinx-autodoc-pytest-fixtures`,
`sphinx-autodoc-docutils`, `sphinx-autodoc-sphinx`,
`sphinx-autodoc-fastmcp`.

### 7.1 The protocol

```python
# packages/gp-sphinx-sidecar/src/gp_sphinx_sidecar/contributors.py
from __future__ import annotations

import typing as t


class SymbolContributor(t.Protocol):
    """Symbol-introspection plugin discovered via entry points.

    Discovered via the ``gp_sphinx_sidecar.contributors``
    entry-point group. Each contributor opts in to introspecting
    specific Python objects and returns a payload that conforms to
    one variant of the schema's discriminated SymbolKind union.

    Attributes
    ----------
    name
        Stable identifier such as ``argparse``, ``pytest-fixtures``,
        ``fastmcp``. Used in the wire ``features`` array.
    protocol_version
        Integer matching the sidecar's ``protocolVersion`` (§5.2).
        Mismatches log a warning and skip the contributor; they
        never crash the build.

    Examples
    --------
    >>> import typing as t
    >>> from gp_sphinx_sidecar.contributors import SymbolContributor
    >>> class _Stub:
    ...     name = "stub"
    ...     protocol_version = 1
    ...     def claims(self, obj: object, parent: object | None) -> bool:
    ...         return False
    ...     def describe(
    ...         self, obj: object, parent: object | None,
    ...     ) -> dict[str, t.Any]:
    ...         return {"kind": "unknown"}
    >>> isinstance(_Stub(), SymbolContributor)
    True
    """

    name: str
    protocol_version: int

    def claims(self, obj: object, parent: object | None) -> bool:
        """Return True if this contributor wants to introspect *obj*."""

    def describe(
        self, obj: object, parent: object | None,
    ) -> dict[str, t.Any]:
        """Return a schema-shaped payload for *obj*."""
```

```toml
# packages/sphinx-autodoc-argparse/pyproject.toml
[project.entry-points."gp_sphinx_sidecar.contributors"]
argparse = "sphinx_autodoc_argparse._sidecar:ArgparseContributor"
```

The sidecar dispatches; it does **not** rediscover package-specific
semantics. `ContributorResult` payloads are validated against the
hand-maintained `gp_sphinx_sidecar.schema` Pydantic v2 module
before they enter the JSON envelope. Contributors never write JSON
themselves — that responsibility lives in the sidecar.

### 7.2 Why this is right *for this repo*

- **Single source of introspection truth.** When
  `sphinx-autodoc-pytest-fixtures` learns about a new pytest
  feature, the Astro stack picks it up automatically.
- **No duplication of introspection logic.** The reason
  `sphinx-autodoc-argparse` exists is to know about argparse
  internals; the sidecar should never replicate that knowledge.
- **Structural contract for directives.** Docutils directive
  classes already expose a known structural contract:
  `required_arguments`, `optional_arguments`,
  `final_argument_whitespace`, `option_spec`, `has_content`
  (`~/study/python/docutils/docutils/parsers/rst/__init__.py:210-318`).
  MyST's directive parser consumes those same attributes
  (`~/study/python/myst-parser/myst_parser/parsers/directives.py:79-154`).
  Modeling a `directive` symbol structurally is right because
  docutils itself treats them structurally.
- **CSS self-containment is preserved.** Python packages still own
  their CSS classes; the Astro theme imports the class names per
  the cross-package-reuse rule in `CLAUDE.md`.
- **Honest plugin model from day one.** Third parties can add
  contributors without forking gp-sphinx.

### 7.3 Costs and mitigations — extras-gated

```toml
# packages/gp-sphinx-sidecar/pyproject.toml
[project.optional-dependencies]
argparse         = ["sphinx-autodoc-argparse>=0.0.1a10"]
pytest-fixtures  = ["sphinx-autodoc-pytest-fixtures>=0.0.1a10"]
fastmcp          = ["sphinx-autodoc-fastmcp>=0.0.1a10"]
docutils-objects = ["sphinx-autodoc-docutils>=0.0.1a10"]
sphinx-config    = ["sphinx-autodoc-sphinx>=0.0.1a10"]
typehints        = ["sphinx-autodoc-typehints-gp>=0.0.1a10"]
api-style        = ["sphinx-autodoc-api-style>=0.0.1a10"]
all = [
  "gp-sphinx-sidecar[argparse,pytest-fixtures,fastmcp,docutils-objects,sphinx-config,typehints,api-style]",
]
```

The bare `gp-sphinx-sidecar` only depends on `pydantic>=2`,
`docutils`, and a tree-walk helper. Sphinx enters as a transitive
dep only when an extra is installed. A consumer who wants only
plain Python introspection installs `gp-sphinx-sidecar` with no
extras and never pulls in pytest/argparse/fastmcp.

### 7.4 Phase staging

Following the smoother slope from gpt-r2 (one in 5a, two in 5b,
four in Phase 6), retaining the Phase 0–7 numbering established
in this plan:

- **Phase 1** ships sidecar with **zero contributors**;
  `features: ["core"]`
- **Phase 5a** ships `pytest-fixtures` (single, lowest-risk
  contributor; lets us prove the protocol against one consumer)
- **Phase 5b** ships `argparse` and `fastmcp` (the two with the
  most distinctive symbol kinds — argparse-cli/argparse-command,
  mcp-tool)
- **Phase 6** ships the remaining four (`docutils-objects`,
  `sphinx-config`, `typehints`, `api-style`)

Each contributor ship adds one entry to the wire `features` array
and unlocks the matching `SymbolKind` arm in the renderer.

---

## 8. Per-package responsibilities

### 8.1 `@gp-sphinx-astro/schema`

**Role:** wire contract. Zod 4 schemas + inferred types, zero
runtime logic.

**Surface:** `SymbolKind, SourceSpan, TypeRef, Parameter, Signature,
Docstring, Function, Method, Class, Module, Package,
ConfigValueSymbol, DirectiveSymbol, RoleSymbol,
ArgparseCommandSymbol, PytestFixtureSymbol, McpToolSymbol, ApiIndex,
AnalysisError, parseApiIndex, ApiIndexParseError`.

**Deps:** `zod ^4.3.6` only (matches Astro 6.1's pinned version
verified at
`~/study/typescript/astro/packages/astro/package.json:176`). No
filesystem, no network, no Node-specific APIs.

**Tests:** parametrized fixture matrix (valid + invalid for every
shape), round-trip tests, strict-mode rejects-extra-keys.

### 8.2 `@gp-sphinx-astro/intersphinx`

**Role:** parse Sphinx `objects.inv`, resolve queries to URLs.

**Surface:** `parseInventory`, `loadInventoryFromFile`,
`loadInventoryFromUrl`, `createResolver`, and a Phase-5
`writeInventory(index, opts)` that emits `objects.inv` from an
`ApiIndex` — making the Astro site a peer in the intersphinx
ecosystem so third-party Sphinx projects can link in.

**Deps:** `node:zlib` (stdlib), `undici` for fetch with retry. No
tree-sitter, no Astro, no Zod.

**Behavior reference.** Mirror Sphinx's reader/writer contract
(`~/study/python/sphinx/sphinx/util/inventory.py:43-63` reader,
`:175-207` writer; line 185 emits `# Sphinx inventory version 2`):
read v1 and v2; write v2 only; fail with a clear error for unknown
versions.

**Tests:** committed real inventory fixtures under
`astro/fixtures/inventories/` (Python stdlib, Sphinx, pytest,
docutils). Snapshot the entire entry list per inventory.

### 8.3 `gp-sphinx-tsx-builder` (PUBLIC)

**Role:** TypeScript engine. Composes static + truth paths into
an `ApiIndex`. Composes the validated index with intersphinx data
into an `ApiGraph`. **No Astro coupling.**

**Surface:**

```typescript
import type {
  ApiIndex, Module, Class, Function,
} from '@gp-sphinx-astro/schema'

export interface AnalyzeOptions {
  packageRoot: string
  exclude?: readonly string[]
  annotationFormat?: 'STRING' | 'FORWARDREF' | 'VALUE'
  timeoutMs?: number
  uvProjectDir?: string
}

export async function analyzePackage(
  opts: AnalyzeOptions,
): Promise<ApiIndex>

export async function analyzeWorkspace(
  opts: { root: string; packages: readonly string[] },
): Promise<ApiIndex>

export interface ApiGraph {
  index: ApiIndex
  modulesInTopoOrder: readonly Module[]
  publicSurface: ReadonlySet<string>
  resolveLink(targetId: string): {
    url: string
    displayText: string
  } | null
  classesByBase: ReadonlyMap<string, readonly Class[]>
}

export function buildGraph(
  index: ApiIndex,
  intersphinx?: Resolver,
): ApiGraph

// Architecture S only:
export function loadApiExport(path: string): Promise<ApiIndex>
```

The builder owns subprocess hygiene (timeouts, stdout caps, stderr
capture, JSON parse boundaries, schema validation, structured
errors). It does not own Python introspection semantics.

**Deps:** `@gp-sphinx-astro/schema`, `@gp-sphinx-astro/intersphinx`,
`execa`, `fast-glob`, `chokidar`. **No tree-sitter, no Python
parser** — all parsing in the sidecar.

**Tests:** Vitest with three projects:

- `unit` — pure unit on graph helpers, public-surface algorithm
- `bridge` — `vi.mock('node:child_process')` for success, exit-1,
  exit-2, timeout, oversize stdout, malformed JSON,
  schema-mismatched JSON, killed mid-stream
- `integration` (`--project=integration`) — real `uv run` against
  `astro/fixtures/gp-sphinx-snapshot`. Snapshots the resulting
  `ApiIndex`. **The single most important test in the JS pipeline.**

### 8.4 `gp-sphinx-astro-builder` (PUBLIC)

**Role:** Astro integration. Wraps `tsx-builder`, exposes data via
virtual modules and the Astro Content Loader API.

**Surface:**

```typescript
export interface GpSphinxAstroOptions {
  packageRoot: string
  additionalRoots?: readonly string[]
  intersphinx?: readonly { name: string; url: string }[]
  annotationFormat?: AnalyzeOptions['annotationFormat']
  staticOnly?: boolean
  allowEmptyApiIndex?: boolean       // default: false; see §6.4
  allowStaleApiIndex?: boolean       // default: false; see §6.4
  emitObjectsInv?: {
    project: string
    version: string
    baseUrl: string
  }
}

export default function gpSphinxAstro(
  opts: GpSphinxAstroOptions,
): AstroIntegration

export function pythonLoader(opts: { root: string }): Loader
```

**Astro Content Loader.** The `pythonLoader` returns a `Loader`
matching the type at
`~/study/typescript/astro/packages/astro/src/content/loaders/types.ts:57-74`.
The optional `schema?: z.$ZodType` field at line 65 is where our
schema exports plug in. The leading `$` is load-bearing.

The integration does *not* force routes. Consumers write pages and
import from `virtual:gp-sphinx-astro/api`. Routing is the
consumer's call.

**Deps:** `gp-sphinx-tsx-builder`, `astro` (peer), `vite` (peer).

**Tests:** unit on the integration factory; one full `astro build`
against `apps/gp-sphinx-docs` in CI.

### 8.5 `gp-sphinx-astro-theme` (PUBLIC)

**Role:** visual layer. Tailwind v4 plugin + Astro components.

#### (a) Tailwind v4 plugin

Ports `~/work/tony.sh/packages/tailwind-plugin/` patterns:

- **OKLCH theme palettes** — `amber`, `emerald`, `purple`, `sky`
  (`~/work/tony.sh/packages/tailwind-plugin/src/tailwind-plugin.ts:50-72`)
- **Semantic aliases** via `[data-theme="amber"]` on `<html>`
- **Opacity utilities** — `text-theme-primary/40` via `color-mix()`
  (`~/work/tony.sh/packages/tailwind-plugin/src/tailwind-plugin.ts:87-99`)
- **Typography** — IBM Plex Sans / Mono via Fontsource (same files
  `sphinx-fonts` standardizes on)
- **Focus utilities** — `focus-visible:ring-2 ring-theme-primary/40`

#### (b) Layout components

`DocsLayout`, `TopNav`, `Sidebar`, `OnThisPage`, `MobileSidebar`,
`Footer`, plus prose components `Callout`, `CodeBlock` (wraps
`astro-expressive-code`), `Tabs`, `Badge`.

#### (c) Autodoc components

```text
ApiPackage, ApiModule, ApiClass, ApiFunction, ApiMethod,
ApiAttribute, ApiVariable, ApiSignature, ApiDocstring,
TypeAnnotation, Reference, BadgeStrip,
# Phase 5 additions:
ApiConfigValue, ApiDirective, ApiRole,
ApiArgparseCommand, ApiPytestFixture, ApiMcpTool
```

**CSS classes** these components emit are styled here, in the
theme's own CSS, per the `CLAUDE.md` "Package CSS
self-containment" rule. Classes are `gp-sphinx-astro-*` (Tier A
or Tier B per §3.4). Reuse of `gp-sphinx-badge` (from
`sphinx-ux-badges`) is fine; the theme styles its own
`gp-sphinx-astro-symbol-card` etc. classes itself.

**Deps:** `astro` (peer), `tailwindcss ^4.2.4` (peer),
`@tailwindcss/vite ^4.2.4` (peer), `@fontsource/ibm-plex-sans`,
`@fontsource/ibm-plex-mono`, `astro-expressive-code ^0.41.7`,
`gp-sphinx-tsx-builder` (peer, for prop types).

**Tests:** component snapshots via the experimental Astro
Container API (`experimental_AstroContainer` exported at
`~/study/typescript/astro/packages/astro/src/container/index.ts:287`).
Pin against a known Astro version range; document the
experimental status in the README.

### 8.6 `gp-sphinx-sidecar` (Python)

**Role:** import or AST-walk Python modules, dispatch to
contributors, return schema-shaped JSON on stdout. Single-shot CLI.

**Workspace placement:** uv member at `packages/gp-sphinx-sidecar/`.

**CLI:**

```text
gp-sphinx-sidecar introspect-package <root> [--mode static|runtime|hybrid]
                                            [--exclude PATTERN ...]
                                            [--format STRING|FORWARDREF|VALUE]
                                            [--output FILE]
gp-sphinx-sidecar introspect-module <dotted.path>
gp-sphinx-sidecar resolve-imports <name> [<name> ...]
gp-sphinx-sidecar rst-to-md <docstring-file>
gp-sphinx-sidecar list-contributors
gp-sphinx-sidecar schema-version           # reports BOTH schemaVersion + protocolVersion (§5.2)
```

**Module layout:**

```text
packages/gp-sphinx-sidecar/
├── pyproject.toml
└── src/gp_sphinx_sidecar/
    ├── __init__.py
    ├── __main__.py
    ├── _cli.py                   # argparse-based
    ├── _emit.py                  # JSON emit, schema version stamping
    ├── schema.py                 # hand-maintained Pydantic mirror → generated in Phase 5+
    ├── contributors.py           # SymbolContributor Protocol + entry-point loader
    ├── _introspect/
    │   ├── _package.py
    │   ├── _module_static.py     # stdlib `ast`
    │   ├── _module_runtime.py    # inspect + annotationlib
    │   ├── _signature.py
    │   ├── _annotations.py
    │   ├── _docstring.py
    │   └── _classify.py
    └── py.typed
```

**`CLAUDE.md` alignment** (binding for every file):

- `from __future__ import annotations` at the top of every module
- `import enum`, `import inspect`, `import typing as t` (namespace
  imports per CLAUDE.md "Imports" — `import enum` not `from enum
  import Enum`)
- NumPy-style docstrings on every public function
- Working doctests on every public function (no `+SKIP`, no
  commented-out function calls). Use `# doctest: +ELLIPSIS` for
  variable output.
- `logging.getLogger(__name__)` per module, lazy formatting
  (`logger.debug("loaded %s contributors", n)` not f-strings)
- Tests: `t.NamedTuple` parametrization, plain `def test_*`, fully
  type-annotated; `@pytest.mark.integration` for any test that
  constructs a `Sphinx` app
- Sphinx domain access via `env.domains.<name>_domain` (typed
  accessors at
  `~/study/python/sphinx/sphinx/domains/_domains_container.py:144-153`)

**Sample CLI module with working doctest:**

```python
# src/gp_sphinx_sidecar/_emit.py
from __future__ import annotations

import json
import typing as t

if t.TYPE_CHECKING:
    from .schema import ApiIndex

SCHEMA_VERSION: t.Final[int] = 1
PROTOCOL_VERSION: t.Final[int] = 1


def stamp_envelope(payload: dict[str, t.Any]) -> dict[str, t.Any]:
    """Add the two-version envelope fields to *payload*.

    Parameters
    ----------
    payload
        Mutable mapping representing a partial ``ApiIndex``.

    Returns
    -------
    dict[str, t.Any]
        The same mapping with ``schemaVersion`` and
        ``protocolVersion`` populated.

    Examples
    --------
    >>> stamped = stamp_envelope({"packages": []})
    >>> stamped["schemaVersion"]
    1
    >>> stamped["protocolVersion"]
    1
    """
    payload["schemaVersion"] = SCHEMA_VERSION
    payload["protocolVersion"] = PROTOCOL_VERSION
    return payload
```

**Annotation format policy:**

| Format | Behavior | Default |
|---|---|---|
| `STRING` | `annotationlib.Format.STRING` on 3.14+; raw `__annotations__` source on older. Never raises. | **yes (v1)** |
| `FORWARDREF` | Lazy proxies; types inspectable but not resolved. | opt-in |
| `VALUE` | Eager evaluation. Raises on unresolvable annotations. | strict mode only |

(`annotationlib.Format` membership confirmed via `python3 -c
"import annotationlib;
print(list(annotationlib.Format.__members__))"`: `['VALUE',
'VALUE_WITH_FAKE_GLOBALS', 'FORWARDREF', 'STRING']`. The CLI
exposes the public three; `VALUE_WITH_FAKE_GLOBALS` is internal.)

**Why `STRING` is the v1 default.** `STRING` never raises and
produces stable output regardless of resolver quality. `FORWARDREF`
should be opt-in until Phase 5 measures the resolver against
gp-sphinx's real intersphinx targets.

**Subprocess output contract:**

- stdout: a single JSON document, schema-validated
- stderr: human-readable progress and warnings (Sphinx-style)
- exit code: 0 on success; 1 on configuration error; 2 on runtime
  error (still emits JSON with `errors[]` populated, then exits
  non-zero so the bridge can decide)

---

## 9. The example consumer site — `apps/gp-sphinx-docs`

Documents **gp-sphinx itself** — the umbrella package plus all 14
sub-packages. Three purposes:

1. **Recursive dogfood.** If our autodoc components can render
   `sphinx-autodoc-pytest-fixtures` and `sphinx-autodoc-fastmcp`,
   they can render most things downstream consumers will throw at
   them.
2. **Hard-case forcing function.** Documenting gp-sphinx exercises
   directives, roles, config values, fixtures, MCP tools — the
   cases that quietly break a "Python-only" stack.
3. **Replacement candidate.** When the site is good enough, it
   replaces gp-sphinx's current Sphinx-built umbrella docs.
   Per-package docs continue shipping via Sphinx.

### 9.1 Site map

```text
/                                        Marketing-ish landing
/docs/quickstart                         Hand-written prose (.md, see §13 Q9)
/docs/configuration                      Hand-written prose
/docs/concepts/extensions                Hand-written prose
/docs/concepts/themes                    Hand-written prose
/docs/migration-from-sphinx              Hand-written prose

/api/                                    Auto-generated index
/api/<pkg>/                              Package overview (one of 14)
/api/<pkg>/<module>/                     Module page
/api/<pkg>/<module>/#<symbol>            Symbol anchors

/changelog/                              Aggregated CHANGES per package
/search                                  Pagefind
```

The 14 package pages cover every name in the public list:
`gp-sphinx`, `sphinx-gp-theme`, `sphinx-fonts`, `sphinx-ux-badges`,
`sphinx-ux-autodoc-layout`, `sphinx-autodoc-api-style`,
`sphinx-autodoc-typehints-gp`, `sphinx-autodoc-argparse`,
`sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-docutils`,
`sphinx-autodoc-sphinx`, `sphinx-autodoc-fastmcp`,
`sphinx-gp-opengraph`, `sphinx-gp-sitemap`.

Flat URL space — no `/v/<version>/` and no language prefix —
matches the existing gp-sphinx convention (`docs_url` auto-derives
`sitemap_url_scheme = "{link}"`, documented at
`/home/d/work/python/gp-sphinx/docs/configuration.md:60-75` and
`/home/d/work/python/gp-sphinx/docs/packages/sphinx-gp-sitemap.md:33-48`).

### 9.2 `astro.config.mjs`

```typescript
import { defineConfig } from 'astro/config'
import gpSphinxAstro from 'gp-sphinx-astro-builder'
import { theme } from 'gp-sphinx-astro-theme'
import tailwindcss from '@tailwindcss/vite'
import pagefind from 'astro-pagefind'

export default defineConfig({
  site: 'https://gp-sphinx.git-pull.com',
  integrations: [
    gpSphinxAstro({
      packageRoot: '../../packages/gp-sphinx/src/gp_sphinx',
      additionalRoots: [
        '../../packages/sphinx-gp-theme/src/sphinx_gp_theme',
        '../../packages/sphinx-fonts/src/sphinx_fonts',
        '../../packages/sphinx-ux-badges/src/sphinx_ux_badges',
        '../../packages/sphinx-ux-autodoc-layout/src/sphinx_ux_autodoc_layout',
        '../../packages/sphinx-autodoc-api-style/src/sphinx_autodoc_api_style',
        '../../packages/sphinx-autodoc-typehints-gp/src/sphinx_autodoc_typehints_gp',
        '../../packages/sphinx-autodoc-argparse/src/sphinx_autodoc_argparse',
        '../../packages/sphinx-autodoc-pytest-fixtures/src/sphinx_autodoc_pytest_fixtures',
        '../../packages/sphinx-autodoc-docutils/src/sphinx_autodoc_docutils',
        '../../packages/sphinx-autodoc-sphinx/src/sphinx_autodoc_sphinx',
        '../../packages/sphinx-autodoc-fastmcp/src/sphinx_autodoc_fastmcp',
        '../../packages/sphinx-gp-opengraph/src/sphinx_gp_opengraph',
        '../../packages/sphinx-gp-sitemap/src/sphinx_gp_sitemap',
      ],
      intersphinx: [
        { name: 'python', url: 'https://docs.python.org/3/' },
        { name: 'sphinx', url: 'https://www.sphinx-doc.org/en/master/' },
        { name: 'docutils', url: 'https://www.docutils.org/docs/' },
        { name: 'pytest', url: 'https://docs.pytest.org/en/stable/' },
        { name: 'myst', url: 'https://myst-parser.readthedocs.io/en/latest/' },
      ],
      annotationFormat: 'STRING',                // §8.6 — STRING is v1 default
      allowEmptyApiIndex: false,                 // §6.4 — fail loudly if no data
      allowStaleApiIndex: false,                 // §6.4 — never silently serve stale
      emitObjectsInv: {                          // Phase 5
        project: 'gp-sphinx',
        version: '0.0.1a10',
        baseUrl: 'https://gp-sphinx.git-pull.com',
      },
    }),
    pagefind(),
  ],
  vite: { plugins: [tailwindcss(), theme()] },
  markdown: {
    // MyST-flavored Markdown via remark plugins (see §13 Q9).
    // If user flips Q9 to MDX, this block is replaced by an
    // `@astrojs/mdx` integration import.
    remarkPlugins: [/* remark-myst-roles, remark-myst-directives */],
  },
})
```

The current `docs/conf.py` already injects each package's `src`
into `sys.path` (verified at
`/home/d/work/python/gp-sphinx/docs/conf.py:11-38`). The Astro
stack mirrors that as a declarative `additionalRoots` list, one
entry per sub-package.

### 9.3 The single API route

```astro
---
// apps/gp-sphinx-docs/src/pages/api/[pkg]/[...slug].astro
import DocsLayout from 'gp-sphinx-astro-theme/layout/DocsLayout.astro'
import { ApiModule, ApiPackage } from 'gp-sphinx-astro-theme/api'
import api from 'virtual:gp-sphinx-astro/api'

export function getStaticPaths() {
  const paths = []
  for (const pkg of api.packages) {
    paths.push({
      params: { pkg: pkg.name, slug: undefined },
      props: { kind: 'package', data: pkg },
    })
    for (const mod of pkg.modules) {
      paths.push({
        params: {
          pkg: pkg.name,
          slug: mod.name.split('.').slice(1).join('/'),
        },
        props: { kind: 'module', data: api.modules[mod.name] },
      })
    }
  }
  return paths
}

const { kind, data } = Astro.props
---
<DocsLayout title={data.name}>
  {kind === 'package' && <ApiPackage data={data} />}
  {kind === 'module' && <ApiModule data={data} />}
</DocsLayout>
```

One file, every API page across all 14 packages.

### 9.4 Furo bridge — explicitly deferred

A creative variant proposed shipping a fourth public package as a
Sphinx directive that embeds Astro components inside Furo pages.
Defer to Phase 7+: violates the 3-package constraint,
re-introduces cross-process complexity. Q6 records the trade-off.

---

## 10. Testing strategy

Vitest projects modeled at the `astro/` workspace root. Mirrors
gp-sphinx's "lightest sufficient test" principle from
`CLAUDE.md` "Test Level Hierarchy": pure unit < docutils tree unit
< snapshot < Sphinx integration.

| Type | Tool | When |
|---|---|---|
| **Unit** | Vitest | Pure functions, no I/O |
| **Snapshot** | Vitest `toMatchSnapshot` / `toMatchFileSnapshot` | Stable structural output |
| **Component** | Astro Container API (`experimental_AstroContainer`, `~/study/typescript/astro/packages/astro/src/container/index.ts:287`) | `.astro` rendering (`astro-theme` only) |
| **Bridge** | Vitest with `vi.mock('node:child_process')` | Subprocess error/timeout paths |
| **Integration** | Vitest with real `uv run` | One-shot end-to-end against fixture |
| **E2E** | Playwright (mirroring tony.sh's `tests/visual-parity.spec.ts`) | Full site smoke test |

`astro/fixtures/gp-sphinx-snapshot/` is **vendored** (not a
symlink to `packages/`) so edits to `packages/gp-sphinx/` don't
surprise-break the snapshot. Refresh script runs by hand.
`astro/fixtures/inventories/` contains real `objects.inv` files —
tiny, network-free, deterministic.

Coverage thresholds: ramp from 70 → 85 as packages mature.

### 10.1 Sidecar Python tests

The sidecar follows the gp-sphinx test conventions verbatim:

- Plain `def test_*` functions, every parameter and return type
  annotated
- `t.NamedTuple` for any `parametrize` with three or more inputs
- `test_id: str` is always the first field
- Fixture lists are `_FOO_FIXTURES` (module-private, all-caps)
- No `class TestFoo:` groupings
- No `unittest.mock.patch` — use `monkeypatch`
- No `tempfile.mkdtemp()` — use `tmp_path`
- `@pytest.mark.integration` on any test that constructs a
  `Sphinx` app (the contributor protocol tests will need this for
  end-to-end validation against a real Sphinx env)

Example:

```python
# packages/gp-sphinx-sidecar/tests/test_classify.py
from __future__ import annotations

import typing as t

import pytest

from gp_sphinx_sidecar._introspect._classify import classify_symbol


class _ClassifyFixture(t.NamedTuple):
    """Test case for classify_symbol()."""

    test_id: str
    qualname: str
    expected_kind: str


_CLASSIFY_FIXTURES: list[_ClassifyFixture] = [
    _ClassifyFixture(
        test_id="plain-function",
        qualname="my_module.do_thing",
        expected_kind="function",
    ),
    _ClassifyFixture(
        test_id="bound-method",
        qualname="my_module.MyClass.do_thing",
        expected_kind="method",
    ),
    _ClassifyFixture(
        test_id="module-constant",
        qualname="my_module.PI",
        expected_kind="constant",
    ),
]


@pytest.mark.parametrize(
    list(_ClassifyFixture._fields),
    _CLASSIFY_FIXTURES,
    ids=[f.test_id for f in _CLASSIFY_FIXTURES],
)
def test_classify_symbol(
    test_id: str,
    qualname: str,
    expected_kind: str,
) -> None:
    """classify_symbol returns the expected SymbolKind."""
    assert classify_symbol(qualname) == expected_kind
```

### 10.2 Snapshot blessing tiers

See §13 Q12 for the policy. Two npm scripts at the `astro/` root:

- `pnpm snapshots:bless` — wire contract (schema + tsx-builder
  integration `ApiIndex`). Updating these requires a `## Schema`
  section in the PR description; the schema-drift CI job (§11.6)
  enforces.
- `pnpm test -u` (per-package, via standard `vitest -u`) — renderer
  surface (component HTML, intersphinx parses). Reviewer catches
  unintentional churn during code review.

---

## 11. Build, lint, CI integration

### 11.1 `astro/package.json`

```json
{
  "name": "@gp-sphinx-astro/monorepo",
  "private": true,
  "type": "module",
  "engines": { "node": ">=24" },
  "packageManager": "pnpm@10.33.2",
  "scripts": {
    "build": "pnpm -r build",
    "dev": "pnpm --filter ./apps/gp-sphinx-docs dev",
    "test": "pnpm -r test",
    "test:unit": "pnpm -r test:unit",
    "test:integration": "pnpm -r test:integration",
    "test:e2e": "pnpm --filter ./apps/gp-sphinx-docs test:e2e",
    "type-check": "pnpm -r type-check",
    "lint": "biome check .",
    "lint:fix": "biome check --fix .",
    "format": "biome format --write .",
    "snapshots:bless": "pnpm --filter @gp-sphinx-astro/schema test -u && pnpm --filter gp-sphinx-tsx-builder test:integration -u",
    "snapshots:check": "pnpm -r test"
  },
  "devDependencies": {
    "@biomejs/biome": "2.4.12",
    "typescript": "^6.0.3"
  }
}
```

Versions verified against `~/work/tony.sh/package.json` (node
>=24, pnpm@10.33.2, biome 2.4.12, typescript ^6.0.3) and
`~/work/tony.sh/packages/astro/package.json` (vitest ^4.1.5,
tailwindcss ^4.2.4, astro-expressive-code ^0.41.7,
@fontsource/ibm-plex-sans ^5.2.8, @fontsource/ibm-plex-mono
^5.2.7).

The two snapshot scripts (`snapshots:bless` for the wire contract,
`snapshots:check` for the full test suite) implement Q12 (§13).
`vitest -u` invocations for the renderer surface happen
per-package via the standard `pnpm --filter <pkg> test -u`.

### 11.2 `pnpm-workspace.yaml`

```yaml
packages:
  - 'packages/*'
  - 'apps/*'

onlyBuiltDependencies:
  - esbuild
  - sharp
```

Glob form mirrors tony.sh (`~/work/tony.sh/pnpm-workspace.yaml`,
which has only `packages: - packages/*`); we add `apps/*` because
the Astro stack ships an app (see §4.1 note).

### 11.3 `tsconfig.base.json`

```json
{
  "extends": "astro/tsconfigs/strictest",
  "compilerOptions": {
    "target": "ES2024",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "verbatimModuleSyntax": true,
    "isolatedDeclarations": true,
    "lib": ["ES2024", "DOM"],
    "skipLibCheck": true
  }
}
```

`extends "astro/tsconfigs/strictest"` matches tony.sh's
`packages/astro/tsconfig.json:2`. The preset brings `strict`,
`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
`noImplicitReturns`, `noFallthroughCasesInSwitch` for free
(verified via the upstream Astro preset; tony.sh's repeat of these
flags at `~/work/tony.sh/packages/astro/tsconfig.json:14-19` is
defensive). Adding `isolatedDeclarations` enforces clean `.d.ts`
emit for downstream consumers of the public packages.

### 11.4 `biome.json`

Mirrors tony.sh; tab indentation, single quotes,
semicolons-as-needed. Excludes Python directories (ruff territory).

### 11.5 `astro/AGENTS.md`

Short JS-side companion to root `CLAUDE.md`: workspace layout,
pnpm scripts, TypeScript strictness rules and rationale, Vitest
project layout, snapshot policy (§13 Q12), CSS namespace
(`gp-sphinx-astro-*`), subprocess testing rules, checklist for
adding a new autodoc component, checklist for adding a new schema
field. Commit conventions point at root `CLAUDE.md`. New scopes:
`astro`, `tsx-builder`, `astro-builder`, `astro-theme`, `sidecar`,
`schema`, `intersphinx`.

### 11.6 CI shape

The Astro stack adds three new jobs and updates the existing
deploy job. The existing `docs.yml` (the production Sphinx deploy)
stays unchanged through Phase 6.

```yaml
# .github/workflows/ci.yml (sketch)
jobs:
  python:
    name: Python (uv)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
        with: { enable-cache: true }
      - run: uv sync --all-packages --all-extras --group dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src tests
      - run: uv run pytest

  js-unit:
    name: JS — unit + type-check + lint
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: astro } }
    steps:
      - uses: actions/checkout@v6
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '24'
          cache: 'pnpm'
          cache-dependency-path: astro/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm type-check
      - run: pnpm test:unit

  js-integration:
    name: JS — integration (real uv)
    needs: [python, js-unit]
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: astro } }
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '24'
          cache: 'pnpm'
          cache-dependency-path: astro/pnpm-lock.yaml
      - run: uv sync --package gp-sphinx-sidecar --extra dev
      - run: pnpm install --frozen-lockfile
      - run: pnpm test:integration
      - run: pnpm --filter ./apps/gp-sphinx-docs build

  schema-drift:
    name: Schema drift check
    needs: js-unit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - run: cd astro && pnpm install --frozen-lockfile
      - run: cd astro && pnpm --filter @gp-sphinx-astro/schema run codegen
      - run: git diff --exit-code packages/gp-sphinx-sidecar/src/gp_sphinx_sidecar/schema.py

  js-e2e:
    name: JS — Playwright smoke
    needs: js-integration
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: astro } }
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: '24' }
      - run: pnpm install --frozen-lockfile
      - run: pnpm exec playwright install --with-deps chromium
      - run: pnpm test:e2e
```

Two important properties:

1. **Python and JS unit pipelines are independent.** Path filters
   (`paths:`) gate so a Python-only change doesn't run JS tests.
2. **Integration depends on both.** It needs `uv` to spawn the
   sidecar against the real Python workspace.

The schema-drift job replaces a Phase-5+ pre-commit hook with a
CI gate so contributors don't need a Node toolchain locally.

### 11.7 Pre-commit hooks

Use `lefthook` or `simple-git-hooks` (no node-side framework).
`pre-commit`: `biome check --fix` on staged JS, `ruff format` on
staged Python. `commit-msg`: validate the `Scope(type[detail]):
description` format from `CLAUDE.md` "Git Commit Standards".

### 11.8 Deploy job — mirroring `docs.yml`

The Astro deploy follows the existing Sphinx deploy pattern
verbatim. The reference workflow is at
`/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:74-99`:

- OIDC role assumption at line 78
  (`role-to-assume: ${{ secrets.GP_SPHINX_DOCS_ROLE_ARN }}`)
- AWS S3 sync at lines 81-85, with `--delete --follow-symlinks`
  on line 85 (this is what makes the current docs site
  unversioned-on-disk; relevant to Q10 below)
- CloudFront invalidation at lines 87-92
- Cloudflare cache purge via `jakejarvis/cloudflare-purge-action@v0.3.0`
  at lines 94-99

The Astro preview job during Phases 4–6 writes to a parallel
preview bucket (`gp-sphinx-astro-preview`) under the same OIDC
role, served via either a CloudFront behavior on
`/preview/<branch>/*` or a subdomain
`astro-preview.gp-sphinx.git-pull.com`. The Phase 7 cutover
either redirects production into the existing
`secrets.GP_SPHINX_DOCS_BUCKET` or creates a new bucket plus
distribution at `astro.gp-sphinx.git-pull.com` if both sites stay
in production. **No new cloud provider, no second IAM surface.**

---

## 12. Migration phases

Eight phases (0 through 7). Phase 0 is the architecture-deciding
spike; Phases 1–6 build out under whichever architecture Phase 0
picked; Phase 7 is the cutover decision. Each phase is
independently shippable.

### Phase 0 — Source-of-truth spike (1–2 days)

See §2.

**Done when:**
- `notes/plans/astro-phase-0-verdict.md` lands with architecture
  chosen
- Representative payload checked in at `astro/fixtures/spike/`
- Acceptance test produces the `merge_sphinx_config` symbol card
  in <1 s wall-clock

### Phase 1 — Branch and scaffold (week 1)

- Create `astro/` directory, pnpm workspace, biome config,
  `tsconfig.base.json` (extending `astro/tsconfigs/strictest`),
  Vitest workspace
- Create `astro/AGENTS.md`
- Create empty `packages/gp-sphinx-sidecar` (uv member, one no-op
  `schema-version` command). Skip if Phase 0 chose S
- Get `pnpm install` + `pnpm test` + `pnpm type-check` + `pnpm
  lint` green doing nothing
- Get the JS CI pipeline running

**Done when:** A PR touching `astro/README.md` triggers JS CI and
it passes. `features: ["core"]`, zero contributors.

### Phase 2 — Schema and intersphinx (week 2)

- Build `@gp-sphinx-astro/schema` with the full Zod 4 object
  model including gp-sphinx-specific symbol kinds
- Build `@gp-sphinx-astro/intersphinx` with parser + resolver
- Commit fixture inventories under `astro/fixtures/inventories/`
- Vitest tests for both
- Hand-maintained `schema.py` Pydantic mirror in the sidecar
  (P/H)

**Done when:** Loading `python-3.13.inv` and resolving
`os.path.join` to
`https://docs.python.org/3/library/os.path.html#os.path.join`
works in unit tests.

### Phase 3 — TSX builder + sidecar static path (week 3)

- Sidecar `--mode static`: `ast`-based parsing, valid
  schema-shaped JSON. (Or under S: `gp_sphinx.export` produces
  equivalent `ApiIndex` JSON from `.fjson` + domain data.)
- Bridge in `tsx-builder/src/bridge/` with timeout, output cap,
  error handling
- `analyzePackage()` returns an `ApiIndex` with static-only data
- Snapshot test against `astro/fixtures/gp-sphinx-snapshot`

**Done when:** Static `ApiIndex` for `sphinx-autodoc-typehints-gp`
matches a snapshot and contains every public symbol.

### Phase 4 — Astro integration + skeleton site (week 4)

- Implement `gp-sphinx-astro-builder` integration with
  `astro:config:setup`, virtual modules, file watcher (with §6.6
  HMR invalidation, §6.7 per-root cache, §6.8 `last-good`
  discipline)
- Implement minimal Tailwind plugin and a half-dozen layout
  components in `gp-sphinx-astro-theme`
- Implement `<ApiModule>`, `<ApiClass>`, `<ApiFunction>` with
  static-only data
- Wire `apps/gp-sphinx-docs` against the static path
- First Astro preview deploy to the parallel preview bucket
  (§11.8)

**Done when:** `pnpm dev` shows a working site, and a PR-triggered
preview build lands at `astro-preview.gp-sphinx.git-pull.com`.

### Phase 5 — Truth path + first contributors + intersphinx wiring (weeks 5–6)

- Sidecar `--mode runtime`: `inspect.signature`, `annotationlib`,
  contributor dispatch (skip if S)
- **Phase 5a:** First contributor — `pytest-fixtures`. Lets us
  prove the protocol with one consumer.
- **Phase 5b:** Two more contributors — `argparse`, `fastmcp`.
  These have the most distinctive symbol kinds.
- Default `annotationFormat: 'STRING'` remains; document
  `'FORWARDREF'` opt-in once intersphinx hit rate is measured
  against gp-sphinx's intersphinx targets
- Wire intersphinx resolution into `<TypeAnnotation>` and
  `<Reference>`
- Codegen step lands: `schema.ts → schema.py`, committed, with CI
  drift check (§11.6)
- Astro stack emits `objects.inv` from the build
- Sidecar PyPI publish prep gate evaluation: ≥3 contributors
  shipped *and* one non-Astro consumer plausible? If yes,
  `private = false`

**Done when:** Visiting `/api/sphinx-autodoc-typehints-gp/` shows
evaluated types with cross-references; visiting
`/api/sphinx-autodoc-pytest-fixtures/` shows fixture symbols with
scopes and yield/return shapes.

### Phase 6 — Polish and remaining contributors (week 7)

- Pagefind search
- Theme switcher (amber / emerald / purple / sky)
- Aggregated `/changelog/` page
- "View source on GitHub" deep links via `SourceSpan`
- Remaining four contributors shipped: `docutils-objects`,
  `sphinx-config`, `typehints`, `api-style`
- Redirects from current Sphinx URL shape if cutting over

**Done when:** All 14 packages render correctly including
gp-sphinx-specific symbol kinds.

### Phase 7 — Cutover decision (week 8+)

- Open a meta-issue: "Should the Astro site replace the Sphinx
  site at `gp-sphinx.git-pull.com`?"
- If yes: configure deployment (per §11.8), set up redirects,
  archive the Sphinx build process for the umbrella docs (the 14
  per-package Sphinx sites continue shipping)
- If no: keep both running; the Astro site lives at a subdomain
  (e.g., `astro.gp-sphinx.git-pull.com`)
- Optional: evaluate Furo-bridge proposal (Q6); evaluate
  B-promotion (§4.2)

---

## 13. Open-question dispositions and the (one) user decision

Of twenty-three questions tracked across passes, the framing
"**19 closed**" oversold settled engineering. Revised count:

- **16 closed** with defensible defaults that survived stress-
  testing.
- **3 closed-with-reasoning-now-on-record** (Q21, Q22, Q23) —
  previously implicit choices inherited from tony.sh (test runner,
  package manager, schema validator), each now documented with a
  *load-bearing rationale* (the binding constraint that makes the
  choice non-substitutable) plus a *rejection rationale* (why the
  obvious alternatives don't fit). Both halves are required: the
  rejection rationale alone is "why not X"; the load-bearing
  rationale is "why Y is binding, not preference." Without both,
  these decisions get re-litigated.
- **1 user decision** (Q9), but the binary is **dissolved** —
  both formats first-class day-1 via Astro's
  `extendMarkdownConfig: true` default; the residual user
  decision is a much narrower "single-format enforcement vs
  both-first-class," default both.

### The (one, narrowed) open user decision

> **Q9-residual — Single-format enforcement vs both-formats-first-class.**
>
> **Default: both first-class.** Ship `**/*.{md,mdx}` glob,
> `mdx()` integration registered in `astro.config.mjs`,
> `extendMarkdownConfig: true` (Astro's default) so remark plugins
> flow through to MDX. Authors pick `.md` for prose, `.mdx` for
> component-heavy pages.
>
> **Override: single-format.** Drop `@astrojs/mdx`, narrow the
> glob to `**/*.md`. Reversible until any `.mdx` file exists.
>
> Case for both: lower friction, no per-page format-flip ceremony,
> matches tony.sh precedent (which already ships both first-class).
>
> Case for single: contributor-onboarding simplicity ("we only
> write Markdown here" norm), and a smaller dependency graph for
> `apps/gp-sphinx-docs`.

#### Why Q9's binary dissolves

Verified at
`~/study/typescript/astro/packages/integrations/mdx/src/index.ts:114`:

```ts
extendMarkdownConfig: true,
```

This is the default value of the option in `defaultMdxOptions`
(consumed by `applyDefaultOptions` at config-done time, line 141).
The semantic: remark plugins declared in `astro.config.mjs` under
`markdown.remarkPlugins` apply to **both** `.md` and `.mdx` files
(verified by reading the resolution at lines 86-117 — the config
is read from `config.markdown` when `extend` is on). Every
MyST-flavored Markdown plugin that `apps/gp-sphinx-docs` registers
for `.md` will also process `.mdx` content with no extra
configuration.

The original "MyST or MDX" binary was therefore solving a problem
we can avoid having. tony.sh already ships both formats
first-class
(`~/work/tony.sh/packages/astro/src/content.config.ts:7,15,26` use
`pattern: '**/*.{md,mdx}'`; `package.json:25` includes
`@astrojs/mdx ^5.0.4`; `astro.config.ts:64` includes `mdx()` in
`integrations`). The decision is not "MyST or MDX" but "do you
*allow* MDX day-1" — and the case for allowing is overwhelming
(one extra integration line, one `pnpm add`, no migration ever in
either direction).

#### Why MyST remains the default markdown flavour for `.md`

The gp-sphinx workspace standardises MyST. `myst_parser` is in
`DEFAULT_EXTENSIONS` at
`/home/d/work/python/gp-sphinx/packages/gp-sphinx/src/gp_sphinx/defaults.py:91`,
and `DEFAULT_MYST_EXTENSIONS` declares the active MyST extensions
(`colon_fence`, `substitution`, `replacements`, `strikethrough`,
`linkify`) at `:138-149`. The dogfood site documents `gp-sphinx`
itself, which means the first page a reader hits explains MyST
conventions used by the 14 sphinx-* packages. Authoring that
explainer in MDX while the packages it documents use MyST is
awkward. The sidecar's `rst-to-md` command (§8.6) emits MyST-
flavoured Markdown, not MDX — same emitter feeds both routes.

"Flip-to-MDX as default" is rejected: the argument ("Astro will
choke on MyST directives without remark-myst") applies equally
whether MyST is or isn't the default — it is not an argument for
making MDX *primary*.

#### Honest reversibility note (replaces "5-min flip recipe")

The original closure said "promoting one prose page from `.md` to
`.mdx` is a five-minute change." That is true *only* for pages
that contain **no MyST directive syntax**. A `.md` page using
`:::{tip}` colon-fence, `{ref}` cross-reference roles,
`{substitution-ref}`, or other MyST-only directive syntax cannot
be served as `.mdx` without rewriting each directive call as a JSX
component import — the MDX compiler does not understand MyST
directive syntax.

The actual cost of promote-to-MDX is therefore:

- **5 minutes** for a CommonMark-only `.md` page (rare in this
  codebase by design — MyST extensions are enabled in defaults).
- **15 minutes to several hours per page** for a `.md` page that
  uses MyST directives — proportional to how many directive
  invocations need to become `<Component>` imports.

Demote MDX→MyST is still strictly worse than that (a real
refactor, not a per-file action), so MyST remains the lower-regret
default markdown flavour — but the asymmetry is *smaller* than
the original closure implied. **Audit any page that uses
MyST-only directives, roles, substitutions, or Sphinx
cross-reference syntax before renaming it to `.mdx`.**

#### How to ship both first-class day-1 (corrected, complete recipe)

Six ordered steps, all verified against
`~/study/typescript/astro/packages/integrations/mdx/` at Astro
6.1.

1. **Add the integration as a dependency.** `pnpm add @astrojs/mdx`
   in `apps/gp-sphinx-docs`. Pin to `^5.0.4` to match tony.sh
   (`~/work/tony.sh/packages/astro/package.json:25`).
2. **Register the integration in `astro.config.mjs`.** Add
   `import mdx from '@astrojs/mdx'` and append `mdx()` to the
   `integrations` array. The integration's `astro:config:setup`
   hook then calls `addPageExtension('.mdx')` and
   `addContentEntryType({ extensions: ['.mdx'], ... })` —
   verified at
   `~/study/typescript/astro/packages/integrations/mdx/src/index.ts`
   (`addPageExtension('.mdx')` at line 59;
   `addContentEntryType({ extensions: ['.mdx'], ... })` at lines
   60-78). **Without this step, `.mdx` files in content
   collections emit "No entry type found for …" warnings** (the
   glob loader looks up the entry type at
   `~/study/typescript/astro/packages/astro/src/content/loaders/glob.ts:280`:
   `return entryTypes.get(\`.${ext}\`);`) **and are dropped
   silently from the store**.
3. **Update each content-collection glob.** Anywhere
   `pattern: '**/*.md'` appears in content config, change to
   `pattern: '**/*.{md,mdx}'`. The tony.sh pattern at
   `content.config.ts:7,15,26` is the working reference.
4. **`extendMarkdownConfig` defaults to `true` — leave it.** The
   MDX integration sets `extendMarkdownConfig: true` in
   `defaultMdxOptions`
   (`~/study/typescript/astro/packages/integrations/mdx/src/index.ts:113-117`),
   so `markdown.remarkPlugins` defined at the top of
   `astro.config.mjs` (§9.2) flow through to MDX rendering as
   well. If §9.2's plugin block is MyST-specific
   (`remark-myst-roles`, `remark-myst-directives`), they apply
   to both `.md` and `.mdx` automatically — so MyST-flavored
   authoring remains the default for any file. **No "replace the
   `markdown.remarkPlugins` block" step is needed**; the
   original recipe wording was misleading.
5. **Mind the type augmentation (no manual change required).**
   `@astrojs/mdx` ships `template/content-module-types.d.ts`
   (verified at
   `~/study/typescript/astro/packages/integrations/mdx/template/content-module-types.d.ts:1-10`)
   that augments `astro:content`'s `Render` interface with an
   `'.mdx'` entry. Registered automatically by the integration;
   no manual `tsconfig.json` change is needed. `astro check`
   will still fail at type-resolution time if the integration
   isn't in the integrations array. `extends:
   "astro/tsconfigs/strictest"` (Q17) doesn't need to change.
6. **No Vite plugin to add manually.** The integration registers
   `vitePluginMdx()` and `vitePluginMdxPostprocess()` itself
   (`~/study/typescript/astro/packages/integrations/mdx/src/index.ts:80-84`,
   the `updateConfig({ vite: { plugins: [...] } })` call). The
   site-level `vite.plugins` block in §9.2 stays untouched.

Aggregate cost: ≈ 10 minutes once (steps 1-3 are mechanical;
step 4 is verification; steps 5-6 are no-ops). Nothing in the
plan changes outside `apps/gp-sphinx-docs/`.

### Closures, revised where reasoning didn't survive stress

#### Q1 — Architecture (RESOLVED by Phase 0; default P; default-if-strict-Deferred-H Deferred-H)

S vs H vs P vs P-minimal vs Deferred-H decided by §2.4
thresholds. Default if Phase 0 skipped: P. Default if Phase 0
inconclusive but meets the strict Deferred-H definition (§2.0,
§2.4, §2.7 dated re-score gate): Deferred-H. Default for all
other inconclusive results: P. This makes "we have evidence S
works on gp-sphinx but unproven on libtmux" a real verdict, not a
punt.

#### Q2 — Workspace layout (RESOLVED: nested; promotion to root is not free)

Nested `astro/` (Option N) remains the default. Promote to a
broader root layout only after the Astro stack is kept past Phase
6 and at least one public package has been published.

The closure is **N→B promotion is real engineering, not a trivial
follow-up.** Budget the promotion as a half-day mechanical change
with a full CI re-run, including:

- `git mv astro/* .` rewrites every relative path inside
  `astro/packages/*/package.json` (`"main"`, `"types"`,
  workspace refs).
- `pnpm-workspace.yaml` rewrites: `packages: ['packages/*',
  'apps/*']` becomes ambiguous because `packages/*` already
  exists for Python — has to become e.g. `['ts-packages/*',
  'apps/*']` with corresponding directory renames, or keep
  nesting in name only.
- Every `tsconfig.json` `extends` and `paths` entry rewrites.
- Every Vitest `vitest.workspace.ts` glob rewrites.
- `apps/gp-sphinx-docs` `astro.config.mjs` `outDir` and `srcDir`
  rewrites.
- `.github/workflows/*` `working-directory: astro/...`
  references rewrite.

Default stays N because the *first-day* cost of N is lower for
Python-only contributors (zero `node_modules` until they touch
Astro). But "promote in Phase 7+" is real engineering.

#### Q3 — Sidecar packaging (RESOLVED: workspace-private; PyPI in Phase 5 with operationalised gates)

Sidecar stays workspace-private through Phase 4. PyPI promotion
in Phase 5+ is gated:

1. **Three contributors shipped, with the protocol stable across
   them.** "Shipped" = a git tag in the contributor's package
   repository that depends on `gp-sphinx-sidecar` from a non-
   `file:` spec. Counted across `sphinx-autodoc-typehints-gp`,
   `sphinx-autodoc-argparse`, `sphinx-autodoc-pytest-fixtures`,
   `sphinx-autodoc-docutils`, `sphinx-autodoc-sphinx`,
   `sphinx-autodoc-fastmcp` — six candidates, three of which
   must ship.
2. **At least one external user has filed an issue or PR**
   against `gp-sphinx-sidecar` requesting either (a) a protocol
   change or (b) a documented behaviour. "External" = author is
   not a gp-sphinx maintainer. "User" = has demonstrated a use
   case that isn't producing docs for the gp-sphinx workspace
   itself.

If after 12 months neither gate has fired, Phase 5+ closes as
"stay workspace-private indefinitely" — and `gp-sphinx-tsx-builder`
(the public TS builder) talks to a private Python helper, which is
a fine architecture but should be documented as such, not as
"PyPI release pending."

"PyPI day-1 as `0.0.0a0`" is rejected here as speculative for v1:
publishing to PyPI before any contributor exists creates
support-and-release-order pressure before the protocol has earned
it.

#### Q4 — Number of internal TS packages (RESOLVED: 2)

Unchanged. `@gp-sphinx-astro/schema`,
`@gp-sphinx-astro/intersphinx`. Each has independent reuse story.

#### Q5 — Schema versioning shape (RESOLVED: envelope with two-version contract)

Unchanged. `{ schemaVersion: 1, protocolVersion: 1, features:
string[], ... }`. The two-version split is non-negotiable per
§5.2.

#### Q6 — Furo bridge (RESOLVED: defer to Phase 7+)

Unchanged. Per-page migration is appealing but breaks the
3-public-package constraint.

#### Q7 — Static fast path (RESOLVED: sidecar `--mode static`)

Unchanged. Stdlib `ast`. Add Node tree-sitter only if HMR latency
proves intolerable.

#### Q8 — Python floor (RESOLVED: 3.10+, optimal on 3.14+)

Match gp-sphinx's `requires-python = ">=3.10,<4.0"` at
`/home/d/work/python/gp-sphinx/packages/gp-sphinx/pyproject.toml:5`.
3.14+ produces the best `annotationlib.Format` results and is the
version used in CI
(`/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:35-39`,
which sets `python-version: "3.14"`; the workflow's
`id-token: write` permission at `:10` enables the OIDC role
assumption at `:78`).

#### Q9 — Documentation source format (USER DECISION; binary dissolved)

See callout above. The "5-minute flip" framing is replaced with
the honest per-page cost; the user decision narrows to
"single-format enforcement vs both-first-class," default both.
MyST stays as the default markdown flavour for `.md`.

#### Q10 — Versioned docs (RESOLVED: unversioned for v1)

Match existing infrastructure parity — `aws s3 sync ... --delete
--follow-symlinks` at
`/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:84-85`
already deletes objects on every deploy, which means the current
docs site is already unversioned-on-disk. Adding versions to the
Astro site while the Sphinx site stays unversioned would be a
confusing mixed signal. The flat URL convention is documented at
`/home/d/work/python/gp-sphinx/docs/configuration.md` (the
"From `docs_url`" table starting at the section heading,
including `sitemap_url_scheme = "{link}"` and the explanation of
why the flat scheme overrides upstream's `"{lang}{version}{link}"`)
and re-explained at
`/home/d/work/python/gp-sphinx/docs/packages/sphinx-gp-sitemap.md`
(the auto-derivation table listing `site_url` and
`sitemap_url_scheme`, plus the "flat scheme overrides upstream
default" paragraph).

`ApiIndex.project.version` exists from day one. Routes do not
include `/v/<version>/` until promotion. **Promotion trigger:**
add versioned routes only when there are at least two actively
hosted versions or a release policy requiring old docs. If
versioning becomes a Phase 7+ requirement, Astro's content
collections offer the natural slot (`version` in the route
parameter, parallel to a locale prefix).

#### Q11 — Deployment target (RESOLVED: mirror existing AWS infra)

**Recommendation unchanged:** mirror the existing AWS S3 +
CloudFront + Cloudflare DNS infrastructure rather than
introducing a new host. For previews, use a parallel S3 bucket
gated by branch.

The closure stands on two independent legs:

1. **Infrastructure already exists, paid for, and wired into CI.**
   `/home/d/work/python/gp-sphinx/.github/workflows/docs.yml`:
   `id-token: write` at `:10`, OIDC role
   (`role-to-assume: ${{ secrets.GP_SPHINX_DOCS_ROLE_ARN }}`)
   at `:78`, S3 sync at `:81-85`
   (`aws s3 sync ... --delete --follow-symlinks`), CloudFront
   invalidation at `:87-92`
   (`--distribution-id "${{ secrets.GP_SPHINX_DOCS_DISTRIBUTION }}"`
   at `:91`), Cloudflare cache purge via
   `jakejarvis/cloudflare-purge-action@v0.3.0` at `:94-99`
   (`CLOUDFLARE_TOKEN` and `CLOUDFLARE_ZONE` at `:98-99`).
2. **The closest analog (tony.sh) deploys Astro the same way.**
   `~/work/tony.sh/.github/workflows/deploy.yml`: OIDC role at
   `:73`, S3 sync at `:84-88`
   (`aws s3 sync packages/astro/dist/ ... --follow-symlinks
   --delete`), CloudFront invalidation at `:89-94`, Cloudflare
   purge at `:95-100`. The only existing Astro project in the
   author's ecosystem already uses S3 + CloudFront + Cloudflare
   for an Astro build, *not* Cloudflare Pages.

Concrete plan unchanged:

| Stage | Host | Trigger |
|---|---|---|
| Phases 4–6 (preview) | New S3 bucket `gp-sphinx-astro-preview`, served via existing CloudFront with a behavior on `/preview/<branch>/*`, or subdomain `astro-preview.gp-sphinx.git-pull.com` | Every PR push |
| Phase 7 (cutover) | If the Astro site replaces the Sphinx site: write to existing `secrets.GP_SPHINX_DOCS_BUCKET` instead | After cutover decision |
| Phase 7 (parallel) | If both stay: new bucket `gp-sphinx-astro` + new CloudFront distribution at `astro.gp-sphinx.git-pull.com` | After cutover decision |

Cloudflare Pages would be lower friction *if starting from
scratch and previews-first*; we are not. The Pages-for-previews
case is genuinely attractive — automatic per-PR preview URLs
without custom S3 plumbing — but it would mean maintaining two
deploy targets in parallel during the cutover window, which is
the exact operational cost we're trying to avoid. A future
"previews on Cloudflare Pages, production on existing AWS" split
is permitted in Phase 7+ if PR-preview friction proves to be the
bottleneck; deferring that decision costs nothing.

#### Q12 — Snapshot update workflow (RESOLVED: two-tier blessing; spike fixtures seed wire-contract tier)

| Tier | Files | Update workflow |
|---|---|---|
| **Wire contract (gated)** | `@gp-sphinx-astro/schema` snapshots; `gp-sphinx-tsx-builder`'s integration `ApiIndex` snapshot against `astro/fixtures/spike/` (now permanent — see §2.7) | `pnpm snapshots:bless`. PR description must include a `## Schema` section explaining the change. PRs that change the full `ApiIndex` snapshot by more than 50 lines additionally require an `astro/fixtures/spike/CHANGELOG.md` entry. Schema-drift CI job (§11.6) gates breaking changes. |
| **Renderer surface (loose)** | Component HTML snapshots in `astro-theme`; intersphinx parsed-entry snapshots | Standard `vitest -u` per package. PR review catches unintentional changes. |

Reasoning unchanged. Note that there is no canonical Python
`--snapshot-update` analog in `vitest`'s shape (Python `syrupy`
uses `--snapshot-update`; `vitest` uses `-u`). The two-tier
blessing makes the JS-side distinction explicit instead of
relying on a single global toggle.

**Connection to §2.7:** the spike fixtures are the ground truth
for the wire-contract tier from day 1. There is no "rebuild
fixtures from a real build" intermediate step.

#### Q13 — Build-failure threshold (RESOLVED: fail with `allowEmptyApiIndex`/`allowStaleApiIndex` opt-ins)

Whole-index failure crashes `astro build` unless
`allowEmptyApiIndex: true`. Per-symbol/per-module failures
continue to degrade (§6.4). `allowStaleApiIndex: true` opts in
to serving the cached `last-good.json` index in dev with a
banner.

#### Q14 — Default annotation format (RESOLVED: STRING)

`STRING` for v1 because it never raises. `FORWARDREF` opt-in
until Phase 5 measures the resolver against gp-sphinx's real
intersphinx targets.

#### Q15 — Phase-0 thresholds (REVISED: per §2.2.7 + §2.3 + §2.4)

- **Reproducibility gate** (§2.1): JSON build runs cleanly, with
  any workaround documented in the verdict.
- **Spike A1**: ≥ 7/10 cases yield structured data without
  `.fjson["body"]` HTML parsing. (Recorded as counter-evidence.)
- **Spike A2**: ≥ 8/10 cases extract from doctree/env-store,
  with cases 1, 5 *and* the libtmux must-pass set (7, 8, 9, 10)
  in the passing set, AND item 4 of §2.5 satisfied.
- **Spike B**: all four Q-Sem checks pass (Q-Sem-3 split into
  3a body grep + 3b argparse inspection with entry-point
  loading), AND either ≤ 40-LOC adapter over existing
  env-store *or* ≤ 80-LOC hand-written contributor. LOC
  recorded as evidence; import discipline is the binding gate.
- **Tooling debt** recorded co-equally in the verdict (per §2.4
  axes).

#### Q16 — Zod recursive typing (RESOLVED: `z.$ZodType<T>`)

Astro 6.1 ships Zod 4 (`"zod": "^4.3.6"` at
`~/study/typescript/astro/packages/astro/package.json:176`);
`z.$ZodType<T>` is the correct recursive pattern. The Astro
Content Loader uses `schema?: z.$ZodType` at
`~/study/typescript/astro/packages/astro/src/content/loaders/types.ts:65`,
with the parallel `createSchema` returning the same type at
`types.ts:70`. The internal import is `import type * as z from
'zod/v4/core'` (line 2 of the same file).

#### Q17 — tsconfig source (RESOLVED: extends `astro/tsconfigs/strictest`)

Matches tony.sh and tracks the upstream Astro preset.

#### Q18 — pnpm workspace shape (RESOLVED: globs)

`packages: ['packages/*', 'apps/*']`. Note divergence from
tony.sh's `packages: - packages/*` only — we add `apps/*` for
our `apps/gp-sphinx-docs` site.

#### Q19 — Annotation enum exposure (RESOLVED: 3 of 4 members)

Sidecar CLI exposes `STRING | FORWARDREF | VALUE`; hides
`VALUE_WITH_FAKE_GLOBALS` (internal).

#### Q20 — Two-version contract (RESOLVED: split)

Wire `schemaVersion` (JSON envelope) is independent of
`protocolVersion` (Python `SymbolContributor` Protocol API).
Conflating them forces spurious major bumps when only one axis
changes. See §5.2.

### Closed-with-reasoning-now-on-record (previously implicit)

These are decisions the plan inherited from tony.sh / the broader
Astro ecosystem without surfacing the binding rationale. They are
not new opens — they are existing closures documented so future
reviewers do not re-litigate them. Each carries both a
*load-bearing rationale* (what makes the choice non-substitutable)
and a *rejection rationale* (why obvious alternatives don't fit).
Both halves are required: the load-bearing rationale defeats
"why not switch to ArkType?" cycles; the rejection rationale
defeats "you only chose this because tony.sh did" cycles.

#### Q21 — JS test runner (CLOSED: Vitest ^4.x)

Vitest. Inherited from tony.sh
(`~/work/tony.sh/packages/astro/package.json` includes
`"vitest": "^4.1.5"`, plus `@vitest/coverage-v8` and
`@vitest/ui` at the same version) and from the broader Astro
ecosystem (Astro's own integration tests use Vitest, e.g.
`~/study/typescript/astro/packages/integrations/mdx/test/*.test.ts`).

**Load-bearing rationale (binding constraint, not preference).**
The wire-contract snapshot tier (Q12) is the binding test
surface — the schema package's stability is enforced by snapshot
diffs, not by unit assertions. Vitest's `toMatchSnapshot` and
`toMatchFileSnapshot` behavior is what the wire-contract tier
expects, and Vitest's workspace-projects support matches the
multi-package shape of `astro/packages/*` directly. A different
runner means rebuilding the snapshot story for the binding test
surface.

**Rejection rationale for alternatives:**

- `node:test` (stdlib, zero deps) — attractive but the
  snapshot-test story is not as polished as Vitest's
  `toMatchSnapshot` + `toMatchFileSnapshot` integration; building
  a comparable harness for the wire-contract tier is real
  engineering, not a 1-day task.
- `bun:test` — adds a Bun runtime requirement that none of the
  gp-sphinx contributor base would otherwise have; the snapshot
  story is also younger.
- `uvu` — last released 2022; unmaintained signals.
- Vitest's Vite-adjacent mock and workspace-projects support
  matches the multi-package shape of `astro/packages/*`
  directly.

#### Q22 — JS package manager (CLOSED: pnpm)

pnpm. Inherited from tony.sh
(`~/work/tony.sh/package.json:32` pins
`"packageManager": "pnpm@10.33.2"` — the field Corepack actually
obeys; `~/work/tony.sh/pnpm-workspace.yaml` declares
`packages: - packages/*` for the workspace layout; CI at
`~/work/tony.sh/.github/workflows/deploy.yml:31` uses
`pnpm/action-setup@v4`).

**Load-bearing rationale (binding constraint, not preference).**
The intersphinx package depends on workspace-internal package-by-
package debugging during Phase 1 (§6.2). pnpm's symlink-based
`node_modules` layout makes "open the actual file resolved by an
import" work without `node_modules/.bin` indirection — material
for the per-package debug story even when the dependency graph is
small. The `packageManager` field at tony.sh `package.json:32` is
also what CI obeys via the Corepack contract; npm's hoisted
layout would not give the same per-package symlink targeting.

**Rejection rationale for alternatives:**

- npm — workspaces work, but disk-footprint and install-time
  differences from pnpm are material in CI; the symlink-debug
  benefit above does not exist with npm's hoisted layout.
- yarn — additional learning curve for contributors who already
  need to learn Astro+Vite.
- bun — same Bun-runtime concern as Q21.

The dogfood story does not strictly require pnpm; npm workspaces
would also work. pnpm is chosen for symlink-layout debugging plus
ecosystem-fit with tony.sh.

#### Q23 — Schema validator (CLOSED: Zod 4)

Zod 4. Already bundled by Astro 6.1
(`~/study/typescript/astro/packages/astro/package.json:176`); the
schema package can re-export `z.$ZodType<T>` directly.

**Load-bearing rationale (binding constraint, not preference).**
Astro's content collections accept a `schema?: z.$ZodType`
directly
(`~/study/typescript/astro/packages/astro/src/content/loaders/types.ts:65`),
and Astro's own `astro/zod` export re-exports `zod/v4` at
`~/study/typescript/astro/packages/astro/src/zod.ts:1-3`:

```ts
import * as mod from 'zod/v4';

export * from 'zod/v4';
export { mod as z };
```

This is Astro's *exported* Zod boundary, not just an internal
dependency — content collections type-check against this exact
export. A different validator would force an adapter at every
collection boundary (each `defineCollection({ schema: ... })`
call in `apps/gp-sphinx-docs/src/content/`). This is the binding
constraint, not author preference.

**Rejection rationale for alternatives:**

- ArkType — smaller bundle, faster parse, but adds a second
  schema vocabulary alongside Astro's content-collection Zod
  (which would require an adapter at every collection boundary).
- TypeBox — JSON-schema-first; great if we were planning to
  publish a JSON Schema for the wire contract, which we are not
  — the schema lives in TS source.
- valibot — modular, but the modularity benefit is irrelevant
  for a sidecar-emitted JSON validation use case, and the
  collection-boundary adapter cost still applies.

This decision was effectively forced by Q16 (Zod 4 is what Astro
ships) and by Astro's `astro/zod` re-export contract; Q23 makes
that explicit so a future "should we switch to ArkType?" question
has the rejection rationale on file.

### Closures unchanged from the previous draft

The following closures survived stress-testing as written and are
listed here to mark "unchanged": Q4 (2 internal TS packages),
Q5 (envelope schema), Q6 (Furo bridge deferred), Q7 (static fast
path), Q8 (Python floor), Q10 (unversioned v1), Q12 (two-tier
snapshot blessing), Q13 (`allowEmptyApiIndex`), Q14 (STRING
default), Q16 (Zod `z.$ZodType<T>`), Q17 (`astro/tsconfigs/strictest`),
Q18 (pnpm workspace globs), Q19 (3-of-4 enum members), Q20
(two-version contract).

### Summary of what moved relative to the committed plan

| ID | Committed plan | This pass | Reason |
|---|---|---|---|
| §2 framing | "S vs P spike" with 4-cell matrix | Reproducibility gate → A1+A2 split → 5-cell matrix with Deferred-H made distinct from H by an explicit *dated* Phase-4 re-score gate written into the verdict YAML | Verified blocker (`-b json` KeyErrors against `sphinx_gp_opengraph`); A1 vs A2 separates the question that matters; Deferred-H now distinguishable on the libtmux must-pass axis with a dated re-score that prevents collapse into "H but unsure" |
| §2 case set | 6 gp-sphinx cases, 5/6 bar | 6 gp-sphinx + 4 libtmux cases (7-10), 8/10 bar with libtmux must-pass + case-1/5 tiebreaker | gp-sphinx-only is producer-side bias (verified: same author as the sphinx-* packages it documents); libtmux is the original target consumer |
| §2 reproducibility blocker | implicit | Producer/consumer mismatch table: `sphinx_gp_opengraph.__init__.py:144` reads `context["pagename"]`; `sphinxcontrib/serializinghtml/__init__.py:90` writes only `current_page_name`; standard HTML builder writes both at `sphinx/builders/html/__init__.py:1083` (which is why it's gone undetected). Workspace audit (`rg -n 'context\["pagename"\]' packages/`) returns exactly one hit — blocker is precisely scoped to one extension. `sphinx_gp_sitemap` is unaffected (uses `app.env.found_docs`). | Producer/consumer mismatch verified across the workspace's 14 packages |
| §2 ObjectEntry citation | implicit | Explicit 4-field NamedTuple at `sphinx/domains/python/__init__.py:60-65` | Load-bearing for "no HTML scraping" gate |
| §2 `_InventoryItem` citation | wrong line numbers (previous citation `:87-92, :210-218` confused a usage site and the parent `_Inventory` class) | Corrected: declaration at `sphinx/util/inventory.py:245`, slot list at `:246`, fields populated by keyword in `__init__` at `:253-264` | Verified live |
| §2 FixtureMeta field count | "17 stable-primitive fields" | **16 fields**, named explicitly: `docname`, `canonical_name`, `public_name`, `source_name`, `scope`, `autouse`, `kind`, `return_display`, `deps`, `param_reprs`, `has_teardown`, `is_async`, `summary`, `deprecated`, `replacement`, `teardown_summary` | Direct count, `_models.py:35-90` |
| §2 `Server.__init__` citation | `:144-153` | Corrected: signature at `:134-144`, accepting 7 named kwargs (`socket_name`, `socket_path`, `config_file`, `colors`, `on_init`, `socket_name_factory`, `tmux_bin`) plus `**kwargs: t.Any`; `Server` class declaration at `:49-53` | Verified live; previous range pointed into the body |
| §2 Spike B gate | LOC ≤ 80 + "no leakage" | Q-Sem 4-question import-discipline checklist (each `rg`-able), plus adapter-LOC frame; Q-Sem-3 sharpened to two mechanical sub-checks (3a body grep, 3b argparse inspection + entry-point loading) so it does not depend on a hypothetical contributor existing | The original Q-Sem-3 leaked judgment because it referenced `BadgeNodeContributor` which is not yet implemented |
| Q1 default-if-inconclusive | P (always) | P by default; Deferred-H *only* when the strict definition holds (gp-sphinx subset passes, libtmux failures are extension-owned-metadata cases re-testable through Phase-4 HMR loop, dated `re_score_date` in YAML) | Deferred-H must be a real verdict, not a hedge |
| Q3 gates | "≥3 contributors, plausible non-Astro consumer" | Operationalised: 3 of 6 named packages must ship; 1 external user issue/PR | Counts the right thing |
| Q9 framing | Single binary user choice (MyST vs MDX) defaulted to MyST + 5-min flip recipe | Binary dissolved via `extendMarkdownConfig: true` (Astro default at `mdx/src/index.ts:114`); residual user decision is single-format-enforcement vs both-first-class, default both; MyST stays as default markdown flavour for `.md`; honest 5-min/15-min-hours-per-page reversibility note replaces "5-min flip recipe" | Verified Astro default; honest cost of MyST→MDX promote |
| Q9 flip recipe | 3 steps | 6 steps including `addContentEntryType`, `extendMarkdownConfig` default, type augmentation, no-Vite-plugin | Verification against Astro 6.1 |
| Q11 reasoning | Leaned on "two originals reached same conclusion" | Sentence excised; closure stands on infra-already-exists + tony.sh-uses-the-same-pattern (verified at `~/work/tony.sh/.github/workflows/deploy.yml:69-100`) | Appeal to consensus is not evidence |
| Q15 thresholds | 5/6 + LOC ≤ 80 + no-duplication | Reproducibility gate + A1 7/10 + A2 8/10 with libtmux must-pass + Q-Sem checklist (3a/3b split) + adapter-LOC | Roll-up of §2 changes |
| Q21 / Q22 / Q23 | not on record | Closed-with-reasoning, each with a *load-bearing* rationale (binding constraint) AND a *rejection* rationale (why-not-X). Q21 binds to Q12 wire-contract snapshot tier (Vitest's `toMatchSnapshot`+`toMatchFileSnapshot`); Q22 binds to per-package symlink-debug for Phase-1 work plus tony.sh `package.json:32` `"packageManager": "pnpm@10.33.2"` (Corepack contract); Q23 binds to Astro's `astro/zod` re-export at `astro/src/zod.ts:1-3` and content-collection Zod boundary at `loaders/types.ts:65` | Avoids "tony.sh-cargo-cult" failure mode; both halves required so future reviewers don't re-litigate |
| §13 framing header | "19 closed, 1 open" | "16 closed, 3 closed-with-reasoning-now-on-record, 1 narrowed user decision" | Honest count |
## 14. Explicit rejections

Recorded so future contributors don't re-litigate without new
evidence. The list is load-bearing — every item below has been
proposed at least once across the pass-1 brainstorm originals or
the pass-2 refinements.

- **Replacing Sphinx for per-package docs.** Each `sphinx-*`
  package keeps its own Sphinx-built docs. Only the umbrella
  `gp-sphinx` site gets the Astro treatment in Phase 7.
- **Auto-generating Astro pages.** Consumers write their own
  pages. The integration provides data via virtual modules;
  routing is the consumer's call.
- **Long-lived Python sidecar daemon.** Universally rejected
  across brainstorm sources. One-shot subprocesses are simpler
  and only marginally slower.
- **A new Pydantic-based JSON Sphinx builder.**
  Self-contradicting contrarian proposal — claims to reuse
  Sphinx while introducing new Sphinx-side machinery.
  Architecture S uses the existing `JSONHTMLBuilder` from
  `sphinxcontrib.serializinghtml` if chosen.
- **HTML scraping as a source of truth.** Per §2.1's pass
  criterion, S passes only if structured data exists *without*
  `cheerio`-style body reads.
- **MDX as the default prose format.** Per Q9: MyST is the
  default, MDX is allowed per file when needed. (User can flip
  Q9; this rejection captures the *plan's* default position, not
  a user constraint.)
- **A new deployment provider.** Per Q11: mirror existing AWS S3
  + CloudFront + Cloudflare DNS rather than spinning up
  Cloudflare Pages, Netlify, or GitHub Pages.
- **Cloudflare Pages preview.** Per Q11: introduces a second
  cloud provider's IAM surface for what the existing OIDC role
  already accomplishes.
- **Single-tier snapshot blessing.** Per Q12: wire contract is
  gated; renderer surface is loose. `vitest -u` everywhere is
  too coarse.
- **Schema-as-JSON-Schema export.** Easy to add later via
  `zod-to-json-schema`. Defer until a non-TS consumer asks.
- **Non-Python languages.** Schema scaffolding could extend, but
  everything else is Python-specific. A future
  `gp-sphinx-astro-rust` is a separate project.
- **Non-Furo theme parity for the Sphinx site.** The Astro stack
  does not require any change to `sphinx-gp-theme`.
- **Dependence on Furo-owned variables from Astro CSS.** The
  Astro theme uses its own `--gp-sphinx-astro-*` custom
  properties. Furo's `--color-*`, `--font-stack--*`, and sidebar
  variables stay untouched.
- **WASM Python in the browser (Pyodide).** Adds 10MB+ download
  for no payback on static doc sites.
- **React / interactive islands beyond minimum.** Tony.sh uses
  React 19; this stack uses Astro components only unless an
  interactive feature genuinely needs a framework island.
- **Tree-sitter Python parser in the Node bridge.** Per Q7.
  Revisit only if spawn-uv overhead measurably hurts HMR.
- **Root-level pnpm workspace from Phase 1.** Per §4.2. The B
  layout is a Phase-7+ promotion path.
- **Package renames.** The three public package names are fixed
  by user constraint.
- **Fourth public Furo bridge package before Phase 7.** Per §9.4.
- **Single global cache file.** Per §6.7: per-root cache files so
  partial sidecar failures localize.
- **Wall-clock `generatedAt` in the envelope.** Per §6.9: derive
  from content hash so identical content rebuilds are
  byte-stable.
- **Silent overwrite of `last-good` cache with empty or
  schema-invalid payload.** Per §6.8: never. Failure modes that
  poison the recovery path collapse the whole story.
- **Unversioned contributor dicts as the stable contract.** Per
  §7.1: contributors return Pydantic-validated `ContributorResult`,
  not raw dicts. The stable boundary is `protocolVersion +
  schemaVersion + validated payload`, not Python's `t.Protocol`
  call shape (which is structural, not nominal — not a stable
  integration boundary on its own).

---

## Appendix A — file:line citation index

Every load-bearing factual claim in this plan was verified by
direct file inspection. Format: `path:line` where the line is
the first relevant line of the cited region.

### gp-sphinx repo (this repository)

1. **gp-sphinx workspace structure.** 14 packages confirmed at
   `/home/d/work/python/gp-sphinx/packages/`. uv workspace
   declares `members = ["packages/*"]` at
   `/home/d/work/python/gp-sphinx/pyproject.toml:16`.
2. **gp-sphinx Python floor.** `requires-python = ">=3.10,<4.0"`
   at
   `/home/d/work/python/gp-sphinx/packages/gp-sphinx/pyproject.toml:5`.
3. **`merge_sphinx_config` exists.** Defined at
   `/home/d/work/python/gp-sphinx/packages/gp-sphinx/src/gp_sphinx/config.py:209`.
4. **MyST is the gp-sphinx default for hand-authored docs.**
   `myst_parser` is in `DEFAULT_EXTENSIONS` at
   `/home/d/work/python/gp-sphinx/packages/gp-sphinx/src/gp_sphinx/defaults.py:91`;
   `DEFAULT_MYST_EXTENSIONS` declared at
   `/home/d/work/python/gp-sphinx/packages/gp-sphinx/src/gp_sphinx/defaults.py:138`.
5. **`docs/conf.py` injects each package's src directory into
   `sys.path`.** Verified at
   `/home/d/work/python/gp-sphinx/docs/conf.py:11-38`.
6. **gp-sphinx prod docs deploy = AWS S3 + CloudFront +
   Cloudflare purge.** Verified at
   `/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:74-99`.
   Specifically:
   - `id-token: write` at line 10
   - OIDC role assumption at line 78
     (`role-to-assume: ${{ secrets.GP_SPHINX_DOCS_ROLE_ARN }}`)
   - AWS S3 sync at lines 81-85 (with `--delete
     --follow-symlinks` on line 85)
   - CloudFront invalidation at lines 87-92
     (`--distribution-id "${{ secrets.GP_SPHINX_DOCS_DISTRIBUTION }}"`
     at line 91)
   - Cloudflare cache purge via
     `jakejarvis/cloudflare-purge-action@v0.3.0` at lines 94-99
7. **CI builds Sphinx docs strict.** `uv run sphinx-build -W -b
   dirhtml docs docs/_build/html` at
   `/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:72`.
8. **CI Python version is 3.14.** `python-version: "3.14"` at
   `/home/d/work/python/gp-sphinx/.github/workflows/docs.yml:39`.
9. **gp-sphinx badge palette.**
   `/home/d/work/python/gp-sphinx/packages/sphinx-ux-badges/src/sphinx_ux_badges/_static/css/sab_palettes.css:349-399`.
10. **Sphinx layout already recognizes gp-sphinx-specific
    domains.** `std:confval`, `rst:directive`, `rst:role`,
    `rst:directive:option`, `mcp:tool` recognized at
    `/home/d/work/python/gp-sphinx/packages/sphinx-ux-autodoc-layout/src/sphinx_ux_autodoc_layout/_transforms.py:106-131`.
11. **Sitemap flat URL convention.** Documented at
    `/home/d/work/python/gp-sphinx/docs/configuration.md:60-75`
    and
    `/home/d/work/python/gp-sphinx/docs/packages/sphinx-gp-sitemap.md:33-48`.
12. **CSS self-containment rule.** `/home/d/work/python/gp-sphinx/CLAUDE.md`
    "Package CSS self-containment" section.

### Sphinx core (`~/study/python/sphinx/`)

13. **`sphinxcontrib.serializinghtml` is loaded as a built-in
    extension.** `_first_party_extensions` tuple at
    `~/study/python/sphinx/sphinx/application.py:128-141` includes
    `'sphinxcontrib.serializinghtml'` at line 133; unioned into
    `builtin_extensions` at line 141.
14. **Upstream Sphinx documentation describes JSON builder output
    as "mostly HTML fragments and TOC information"** —
    `~/study/python/sphinx/doc/usage/builders/index.rst:425-440`,
    literal text on line 427.
15. **`JSONHTMLBuilder` is per-page rendered HTML.**
    `SerializingHTMLBuilder` at
    `~/study/python/sphinx/sphinxcontrib/serializinghtml/__init__.py:38`
    (or in the live `.venv`),
    `JSONHTMLBuilder` at line 153, `out_suffix = '.fjson'` at
    line 164. All inherit from `StandaloneHTMLBuilder`.
16. **Sphinx PythonDomain `ObjectEntry` shape.**
    `~/study/python/sphinx/sphinx/domains/python/__init__.py:60-65`
    defines `class ObjectEntry(NamedTuple)` with fields `docname`,
    `node_id`, `objtype`, `aliased`.
17. **`PythonDomain.get_objects()`.**
    `~/study/python/sphinx/sphinx/domains/python/__init__.py:1056-1065`
    begins
    `def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:`.
18. **Sphinx inventory v1/v2 reader, v2 writer.**
    `~/study/python/sphinx/sphinx/util/inventory.py:43-63`
    reader; `:175-207` writer; line 185 emits `# Sphinx inventory
    version 2`.
19. **Sphinx typed domain accessors.**
    `~/study/python/sphinx/sphinx/domains/_domains_container.py:144-153`
    declares `standard_domain`, `c_domain`, `cpp_domain`,
    `javascript_domain`, `python_domain`, `restructuredtext_domain`,
    `changeset_domain`, `citation_domain`, `index_domain`,
    `math_domain`. Introduced in Sphinx 8.1.

### Docutils and MyST (`~/study/python/{docutils,myst-parser}/`)

20. **Docutils Directive class attributes.**
    `~/study/python/docutils/docutils/parsers/rst/__init__.py:210-318`
    documents `required_arguments`, `optional_arguments`,
    `final_argument_whitespace`, `option_spec`, `has_content`.
21. **MyST directives parser.**
    `~/study/python/myst-parser/myst_parser/parsers/directives.py:79-154`
    consumes the same docutils directive attributes.

### Astro (`~/study/typescript/astro/`)

22. **Astro 6 integration hooks.**
    `~/study/typescript/astro/packages/astro/src/types/public/integrations.ts`:
    - `astro:config:setup` at line 341
    - `astro:server:setup` at line 363, with `server: ViteDevServer`
      at line 364 and `refreshContent?` at line 367 (full block
      lines 363-368)
    - `astro:build:start` at line 382
    - `astro:build:done` at line 400
23. **Astro Container API.** `experimental_AstroContainer` at
    `~/study/typescript/astro/packages/astro/src/container/index.ts:287`.
24. **Astro Content Loader.**
    `~/study/typescript/astro/packages/astro/src/content/loaders/types.ts:57-74`
    defines the `Loader` type. `schema?: z.$ZodType` at line 65.
25. **Astro file loader watcher pattern.**
    `~/study/typescript/astro/packages/astro/src/content/loaders/file.ts:105-126`:
    line 108 destructures `{ config, logger, watcher }`, line 119
    is `watcher?.add(filePath)`, line 121 is `watcher?.on('change', ...)`.
26. **Astro glob loader watcher pattern.**
    `~/study/typescript/astro/packages/astro/src/content/loaders/glob.ts:329-373`.
27. **Astro 6.1 ships Zod 4.**
    `~/study/typescript/astro/packages/astro/package.json:176`
    declares `"zod": "^4.3.6"`.
28. **Astro internals use `zCore.$ZodType` from `zod/v4/core`.**
    `~/study/typescript/astro/packages/astro/src/content/runtime.ts:5`
    imports `* as zCore from 'zod/v4/core'`, used at lines 47, 57.

### tony.sh (`~/work/tony.sh/`)

29. **tony.sh stack versions.** `~/work/tony.sh/package.json`
    declares `"node": ">=24"`, `"packageManager": "pnpm@10.33.2"`,
    `"@biomejs/biome": "2.4.12"`, `"typescript": "^6.0.3"`.
30. **tony.sh Astro stack.**
    `~/work/tony.sh/packages/astro/package.json`: `astro ^6.1.9`,
    `vitest ^4.1.5`, `@tailwindcss/vite ^4.2.4`,
    `tailwindcss ^4.2.4`, `astro-expressive-code ^0.41.7`,
    `@fontsource/ibm-plex-sans ^5.2.8`,
    `@fontsource/ibm-plex-mono ^5.2.7`, `react ^19.2.5`,
    `@astrojs/mdx ^5.0.4` at line 25.
31. **tony.sh extends `astro/tsconfigs/strictest`.**
    `~/work/tony.sh/packages/astro/tsconfig.json:2` declares
    `"extends": "astro/tsconfigs/strictest"`.
32. **`pnpm-workspace.yaml` glob form in tony.sh.**
    `~/work/tony.sh/pnpm-workspace.yaml` declares
    `packages: - packages/*` (no `apps/*`; we add it).
33. **tony.sh content collection glob.**
    `~/work/tony.sh/packages/astro/src/content.config.ts:6-33`
    uses `**/*.{md,mdx}` patterns at lines 7, 15, 26, 38.
34. **tony.sh tailwind plugin patterns.**
    `~/work/tony.sh/packages/tailwind-plugin/src/tailwind-plugin.ts:50-72`
    OKLCH; `:87-99` color-mix opacity utilities;
    `~/work/tony.sh/packages/tailwind-plugin/src/schema.ts:31-87`
    token-input shape.
35. **tony.sh Playwright tests.**
    `~/work/tony.sh/packages/astro/tests/visual-parity.spec.ts`
    opens with `import { expect, test } from '@playwright/test'`.

### Python runtime

36. **`annotationlib.Format` membership on Python 3.14.**
    Verified by running `python3 -c "import annotationlib;
    print(list(annotationlib.Format.__members__))"`:
    `['VALUE', 'VALUE_WITH_FAKE_GLOBALS', 'FORWARDREF', 'STRING']`.

### Visual / convention precedents

37. **sphinx-design CSS namespace precedent.** `sd-` prefix per
    `~/study/python/sphinx-design/sphinx_design/`.
38. **Furo CSS variable scope.**
    `~/study/python/furo/src/furo/assets/styles/`.

---

**End of plan.** Ready for Phase-0 spike commit.
