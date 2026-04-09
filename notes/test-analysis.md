# Test And Autodoc Analysis

This note records the post-refactor state of the autodoc rendering pipeline and
the current runtime profile of the test suite.

The two non-negotiable baselines remain unchanged:

- no test was deselected to make the suite "look" faster
- timing claims below are based on the full suite or on an explicitly named
  slice, not on a reduced-signal fast lane

Current suite status on 2026-04-09:

- `805` tests collected
- `802` passed
- `3` skipped

## Test categories and harnesses

The suite is already mostly surgical. The remaining expensive work is
concentrated in a small number of builder-facing scenarios.

| Category | Main locations | Harness | Current verdict |
| --- | --- | --- | --- |
| Pure helper and parser tests | `tests/ext/api_style`, most of `tests/ext/pytest_fixtures`, `tests/ext/autodoc_sphinx`, `tests/ext/autodoc_docutils`, `tests/ext/argparse_neo`, workspace-root tests | Direct unit tests, parser helpers, store helpers, pure transforms | Already light-weight |
| Doctree and dummy-builder tests | `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py`, parts of `tests/ext/layout/test_transforms.py` | Synthetic Sphinx scenarios with `buildername="dummy"` plus doctree snapshots | Good balance; keep as the default for structure and metadata coverage |
| Translator and render-node tests | `tests/ext/layout/test_visitors.py`, `tests/ext/layout/test_snapshots.py` | Direct node construction plus layout transform / visitor assertions | Expanded in this pass to replace slower HTML snapshots |
| Cached full-build HTML and text tests | `tests/ext/layout/test_integration.py`, `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py`, selected scenario-cache tests | Shared `build_shared_sphinx_result()` scenarios with session cache roots | Still required for emitted HTML, inventory, and cross-document behavior |
| Cross-document and inventory tests | `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` | Real HTML builds with multiple source pages and `objects.inv` checks | Honest expensive coverage; keep |
| Doctests | `docs/_ext/*.py`, selected package modules | `--doctest-modules` | Already light-weight |

## Autodoc rendering path and hook points

The current Python-domain rendering path is now intentionally split into
producer extensions and one structural owner.

### Upstream hook points

1. Sphinx directive-time parsing creates `desc`, `desc_signature`, and
   `desc_content` nodes inside `ObjectDescription.run()`.
2. Package-specific directive code can still shape body content before the late
   layout pass. The main example is
   `sphinx_autodoc_pytest_fixtures.PyFixtureDirective.transform_content()`,
   which injects authored fixture metadata fields early.
3. `sphinx.ext.linkcode` and `sphinx.ext.viewcode` attach source-link material
   later than directive time, which is why final header composition cannot live
   only in the directive layer.

### Producer extensions

- `sphinx_autodoc_api_style` now computes badges and extracts `[source]`, then
  emits explicit `api_slot` markers instead of a raw `.gas-toolbar` inline.
- `sphinx_autodoc_pytest_fixtures` now does the same for fixture badges and
  `[source]`, then separately strips redundant `Rtype` fields and injects
  fixture-only metadata such as `Used by` and `Parametrized`.

### Structural owner

`sphinx_autodoc_layout` is now the sole owner of final Python `desc` header and
body composition in HTML builds.

Its `doctree-resolved` pass is responsible for:

- nesting Python members under their owning class or exception
- wrapping `desc_content` runs into explicit body regions
- consuming `api_slot(slot="badges")` and
  `api_slot(slot="source-link")`
- rebuilding each managed signature into stable `api-*` regions
- inserting the managed permalink node
- optionally folding large signatures and large parameter field lists when
  `gal_enabled` is on

Its HTML visitors then render those nodes without any Jinja template override.

## Chosen autodoc component architecture

The HTML contract is now deliberately componentized.

### Header and body structure

- `api-container`
- `api-header`
- `api-layout`
- `api-layout-left`
- `api-signature`
- `api-link`
- `api-layout-right`
- `api-badge-container`
- `api-source-link`
- `api-content`
- `api-description`
- `api-parameters`
- `api-footer`

### New shared slot contract

The cross-extension handoff is now:

- `api_slot(slot="badges")`
- `api_slot(slot="source-link")`

That contract lives in `sphinx_autodoc_layout` so producer extensions can stay
typed and explicit without coupling themselves to layout-specific HTML strings.

### Large-signature policy

Large signatures are still semantically represented by the canonical
`desc_parameterlist` and related Sphinx signature nodes.

This pass did not split parameters out of the signature text and did not try to
infer body sections from signature parsing. Instead it:

- keeps the real signature nodes intact
- folds only the rendered presentation when the configured threshold is crossed
- uses parameter field lists only to enrich the expanded multiline rendering
  with annotations when those annotations are already authored in the docs

The new synthetic stress snapshot in `tests/ext/layout/test_snapshots.py`
models the libtmux-style "large kwargs-heavy constructor" problem directly
without depending on libtmux as a build-time fixture.

## Why this architecture won

Three alternatives were considered and rejected for the first pass:

### Raw inline toolbar mutation

This was the old `gas-toolbar` approach. It was easy to inject but too implicit:

- badge and source ownership was mixed with layout ownership
- the right side of the header was effectively a flattened blob
- fixture and non-fixture pipelines could not share a clear contract

### Template-only overrides

Rejected because the problem is not just HTML string formatting. The renderer
needs access to real docutils and Sphinx nodes after `linkcode` and `viewcode`
have finished their own work.

### Parsing signatures into synthetic body sections

Rejected for v1 because it would risk changing semantics and duplicating
information already present in doc fields. The body remains driven by authored
content, not inferred signature structure.

## Harness reductions completed in this pass

The most important test-runtime change was to narrow the layout snapshot layer
without weakening coverage.

### Moved from slower builds to lighter harnesses

- `tests/ext/layout/test_snapshots.py` no longer snapshots full HTML fragments
  from shared HTML builds
- those snapshot assertions now build a synthetic large-signature `desc`
  directly, run `sphinx_autodoc_layout.on_doctree_resolved()`, and snapshot the
  transformed doctree
- this keeps the structural contract under snapshot coverage while removing one
  extra HTML-build scenario from the session

### Full builds intentionally retained

These tests still need real builders:

- `tests/ext/layout/test_integration.py`
  because it validates the emitted HTML contract end to end
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py`
  because it validates `objects.inv`, genindex output, text-builder output, and
  cross-document HTML links

### Current demotion guidance

The remaining builder-backed tests do not look over-harnessed:

- layout integration is down to one real emitted-HTML contract
- fixture integration keeps only the inventory, cross-document, and text
  builder contracts that really need a builder
- doctree snapshots already cover most fixture metadata and structure

## Benchmark matrix

These measurements were taken after the slot-node refactor and the snapshot
demotion described above.

### Full suite

| Command | Result | What it shows |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s --durations=100 --durations-min=0.02` | `802 passed, 3 skipped in 26.08s`, wall `27.00s` | Current conservative baseline with slow-test evidence |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-post` | `802 passed, 3 skipped in 2.82s`, wall `3.91s` | Same coverage with runner-path overhead mostly removed |
| `uv run py.test --reruns 0 -vvv out` | see validation section below | Required validator path still runs the real suite |

### Autodoc-heavy slice

This slice is:

- `tests/ext/layout`
- `tests/ext/api_style`
- `tests/ext/autodoc_sphinx`
- `tests/ext/autodoc_docutils`
- `tests/ext/pytest_fixtures`

| Command | Result | What it shows |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s --durations=80 --durations-min=0.02 tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures` | `234 passed, 3 skipped in 19.48s`, wall `20.45s` | Honest cost of the autodoc-focused surface in raw mode |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-autodoc-post tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures` | `234 passed, 3 skipped in 1.58s`, wall `1.51s` | Same slice with runner overhead mostly removed |
| `uv run python -m cProfile -o /tmp/gp_sphinx_autodoc_post.prof -m pytest -s tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures` | `234 passed, 3 skipped in 22.12s` | Profile source for the slice |

## Long-running tests and causes

The current slow tests are still mostly honest builder or scenario costs.

### Slowest autodoc-heavy tests in the raw slice

| Test | Measured runtime | Cause | Verdict |
| --- | --- | --- | --- |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `4.28s setup` | Real multi-page HTML build with cross-document links | Keep |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `4.13s setup` | Real HTML build for final emitted layout contract | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `3.56s setup` | Real HTML build for badge markup, genindex, and inventory output | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `1.14s setup` | Shared MyST dummy-builder scenario | Already cached; acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixture_index_resolution_smoke` | `0.68s call` | Distinct synthetic scenario and final table resolution | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_warning_and_manual_option_snapshot` | `0.67s call` | Dense fixture metadata scenario, still dummy-builder only | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_rst_snapshot` | `0.65s call` | Distinct generated-page scenario | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_text_builder_does_not_crash` | `0.63s call` | Real text-builder smoke | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_lint_level_error_sets_nonzero_status` | `0.61s call` | Real failing-lint scenario | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_dependency_rendering_snapshot` | `0.61s call` | Distinct dependency-link scenario | Keep |

### Full-suite top tail

The full suite shows the same pattern. The slow tail is dominated by:

- the two real fixture HTML scenarios
- the one real layout HTML scenario
- a handful of distinct dummy-builder fixture scenarios
- two `tests/test_sphinx_scenarios.py` cache semantics tests at about `0.43s`

No currently slow test looks like a hidden infinite loop or a falsely passing
timeout.

## Profiling findings

### Full-suite cProfile

The full-suite profile was taken with:

```console
$ uv run python -m cProfile \
    -o /tmp/gp_sphinx_full_post.prof \
    -m pytest \
    -s
```

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `20.12s` |
| `pathlib.Path.resolve` | `8.95s` |
| `posixpath.realpath` | `8.94s` |
| `posix.lstat` | `8.93s` |
| `_pytest.tmpdir.mktemp` | `0.22s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.15s` |

### Autodoc-heavy slice cProfile

The autodoc-heavy slice profile was taken with:

```console
$ uv run python -m cProfile \
    -o /tmp/gp_sphinx_autodoc_post.prof \
    -m pytest \
    -s \
    tests/ext/layout \
    tests/ext/api_style \
    tests/ext/autodoc_sphinx \
    tests/ext/autodoc_docutils \
    tests/ext/pytest_fixtures
```

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `20.69s` |
| `pathlib.Path.resolve` | `9.07s` |
| `posixpath.realpath` | `9.06s` |
| `posix.lstat` | `9.04s` |
| `_pytest.tmpdir.mktemp` | `0.13s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.15s` |
| `sphinx_autodoc_layout._transforms.on_doctree_resolved` | `0.01s` |
| `sphinx_autodoc_api_style._transforms.on_doctree_resolved` | `0.00s` to `0.01s` |
| `sphinx_autodoc_layout._visitors.visit_api_component` | `0.001s` |

### What that means

- the dominant repo-owned runtime is still the small set of cached synthetic
  Sphinx builds
- the dominant raw-runner overhead is still path resolution and filesystem
  probing
- the new slot-node layout machinery is not a hotspot
- the refactor improved maintainability and enabled lighter tests without
  introducing a meaningful new runtime cost

## Where execution appears to stall

There is no evidence of a true hang in the current suite.

The apparent "stall" points are:

- front-loaded setup for the remaining shared HTML Sphinx scenarios
- raw-runner path resolution during temporary-path and package-path handling

The profile does not show a hot loop in the new layout visitors or slot-node
logic.

## Suspected bugs, caching failures, and missing caching

### Real bugs

No new functional bug was uncovered by the runtime work itself. The refactor
did briefly surface a stale layout CSS selector test during implementation, and
that was fixed as part of the change.

### Runner-side bugs and oddities

- The earlier zero-collection capture-teardown problem is still an upstream
  pytest behavior worth remembering, but the repo-local validator path is
  already configured so `uv run py.test --reruns 0 -vvv out` runs the real
  suite instead of falling into that crash.

### Fixture caching status

The current synthetic Sphinx caching strategy is effective:

- shared build results still come through `tests/_sphinx_scenarios.py`
- session-scoped roots in `tests/ext/layout/conftest.py` and
  `tests/ext/pytest_fixtures/conftest.py` are still doing useful work
- the remaining slow scenarios are mostly distinct scenario graphs, not missed
  cache hits

### Missing caching

No repo-owned missing cache stands out as the next big win.

The biggest unresolved overhead is still outside the scenario helpers:

- pytest path resolution
- `realpath()`
- `lstat()`

## Doctree or snapshot fixtures versus full builds

This audit did another explicit pass over the suite looking for places where a
doctree or snapshot harness could replace a full build.

### Good candidates that were moved

- layout header snapshots moved from shared HTML builds to transform-level
  doctree snapshots

### Remaining cases that should stay builder-backed

- final emitted layout HTML
- fixture HTML inventory and genindex output
- cross-document fixture links
- text-builder smoke
- any contract that depends on `viewcode`, `linkcode`, inventory generation, or
  real app lifecycle hooks

### Remaining cases that are already narrow enough

- fixture metadata rendering snapshots
- fixture dependency-link doctree assertions
- `doc-pytest-plugin` generated-page snapshots
- `autofixtures` MyST smoke and source-order checks

## Additional upstream API study

This pass re-checked the local study trees under:

- `~/study/python/sphinx`
- `~/study/python/docutils`
- `~/study/python/myst-parser`
- `~/study/python/sphinx-design`
- `~/study/python/pytest`
- `~/study/python/pytest-asyncio`
- `~/study/python/syrupy`

The useful upstream confirmations were:

- `ObjectDescription.run()` and `DocFieldTransformer` make directive time too
  early for final source-link and permalink placement
- `viewcode` and `linkcode` both reinforce the need for a late structural pass
- the current layout approach belongs in node transforms and visitors, not in a
  template-only override

## Syrupy custom-extension audit

No custom Syrupy extension is warranted in the first pass.

Reasons:

- snapshot serialization is not a measurable hotspot in the profile
- the existing helpers in `tests/_snapshots.py` already normalize the unstable
  parts we care about: roots, warning text, and doctree metadata
- the new slot-node snapshots fit cleanly into the existing
  `snapshot.with_defaults()` flow

If snapshot content ever becomes too noisy, a serializer or matcher can be
revisited later. It is not the current performance lever.

## Recommendations and follow-up

### Keep

- `api_slot` as the only cross-extension handoff for header-side content
- `sphinx_autodoc_layout` as the sole HTML compositor for Python `desc` entries
- shared scenario caching in `tests/_sphinx_scenarios.py`

### Defer

- any attempt to infer parameter body sections from signature parsing
- template-only API entry overrides
- custom Syrupy serializers

### Good future follow-up

- add a tiny shared helper for "render one managed signature subtree to HTML" if
  future packages need more translator-level tests without a full builder
- continue auditing builder-backed tests with the same rule used here:
  keep the build only when the contract truly depends on builder output
- investigate whether any remaining distinct fixture scenarios can be merged
  without blurring their contracts, but do not collapse them just to shave a
  few tenths of a second

## Validation checklist

The required validation commands for this change are:

```console
$ uv run ruff check . --fix --show-fixes
```

```console
$ uv run ruff format .
```

```console
$ uv run mypy
```

```console
$ uv run py.test --reruns 0 -vvv out
```
