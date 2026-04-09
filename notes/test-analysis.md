# Test And Autodoc Analysis

This note records the current post-consolidation state of the autodoc rendering
pipeline and the runtime profile of the test suite.

The two non-negotiable baselines remain unchanged:

- no test was deselected to make the suite "look" faster
- timing claims below are based on the full suite or on an explicitly named
  slice, not on a reduced-signal fast lane

Current suite status on 2026-04-09:

- `818` tests collected
- `815` passed
- `3` skipped

## Test categories and harnesses

The suite is still mostly surgical. The honest runtime remains concentrated in a
small number of cached builder-backed scenarios.

| Category | Main locations | Harness | Current verdict |
| --- | --- | --- | --- |
| Pure helper and parser tests | `tests/ext/api_style`, most of `tests/ext/autodoc_sphinx`, most of `tests/ext/autodoc_docutils`, `tests/ext/fastmcp`, workspace-root tests | Direct unit tests, parser helpers, badge builders, store helpers | Already light-weight |
| Doctree and transform tests | `tests/ext/layout/test_transforms.py`, `tests/ext/layout/test_render.py`, `tests/ext/fastmcp/test_transforms.py`, fixture doctree tests | Synthetic nodes, transform calls, targeted dummy-builder scenarios | Good balance; keep as default for structure coverage |
| Translator and render-node tests | `tests/ext/layout/test_visitors.py` | Direct visitor assertions with tiny translator stubs | Light and precise |
| Doctree snapshot tests | `tests/ext/layout/test_snapshots.py`, fixture doctree snapshots | Synthetic `desc` trees plus `on_doctree_resolved()` and snapshot normalization | Expanded in this pass; preferred over duplicate HTML snapshots |
| Cached emitted-HTML integration tests | `tests/ext/layout/test_integration.py`, `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py`, `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py`, `tests/ext/fastmcp/test_fastmcp_integration.py` | Shared `build_shared_sphinx_result()` scenarios | Required for emitted HTML contracts |
| Cross-document, inventory, and text-builder tests | `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` | Real HTML and text builds plus `objects.inv` checks | Honest expensive coverage; keep |
| Doctests | `docs/_ext/*.py`, selected package modules | `--doctest-modules` | Already light-weight |

## Current autodoc rendering pipeline

The repo now has two shared layers:

- `sphinx_autodoc_badges` is the only badge primitive package
- `sphinx_autodoc_layout` is the shared structural compositor for managed object
  descriptions

### Upstream hook points

1. Sphinx directive-time parsing creates semantic `desc`, `desc_signature`, and
   `desc_content` nodes.
2. Producer packages can still shape body content before final layout.
3. `viewcode`, `linkcode`, and Sphinx permalink injection still happen late
   enough that final header composition belongs in `doctree-resolved`, not only
   in directive code.

### Shared layout owner

`sphinx_autodoc_layout` is now profile-driven instead of Python-only. Its late
  pass owns final composition for:

- Python API entries already managed before this refactor
- `py:fixture`
- `std:confval`
- `rst:directive`
- `rst:role`
- `rst:directive:option`

Its responsibilities are:

- nested Python member ownership for class/exception trees
- wrapping `desc_content` into explicit body regions
- consuming `api_slot(slot="badges")` and `api_slot(slot="source-link")`
- rebuilding signatures into explicit `api-*` header regions
- inserting the managed permalink node
- optionally folding large Python signatures and parameter sections

### Producer packages

- `sphinx_autodoc_api_style` remains a Python metadata producer only. It emits
  badge and source-link slots and leaves all final HTML composition to layout.
- `sphinx_autodoc_pytest_fixtures` remains a fixture metadata producer only. It
  emits slot markers, strips redundant `Rtype` fields, and injects fixture
  fields such as `Used by` and `Parametrized`.
- `sphinx_autodoc_sphinx` now parses semantic `confval` markup through the new
  shared `parse_generated_markup()` helper, then injects a type badge
  (`config`) plus a rebuild-mode badge before layout runs.
- `sphinx_autodoc_docutils` now uses the same shared parse helper, then injects
  type badges for `directive`, `role`, and `option` entries before layout runs.
- `sphinx_autodoc_fastmcp` stays on the shipping section-card path for v1. It
  now uses shared badge primitives plus shared `api-entry` / `api-header` /
  `api-content` component builders inside the existing `nodes.section` wrapper.

## Chosen shared architecture

### Profile-driven `desc` composition

The structural contract now flows through a typed internal
`DescLayoutProfile` registry keyed by `(domain, objtype)`.

Stable profile classes now include:

- `api-profile--py-function`
- `api-profile--py-method`
- `api-profile--py-fixture`
- `api-profile--confval`
- `api-profile--rst-directive`
- `api-profile--rst-role`
- `api-profile--rst-directive-option`

### Stable slot contract

The cross-package handoff stays intentionally small:

- `api_slot(slot="badges")`
- `api_slot(slot="source-link")`

That contract is now shared by:

- `sphinx_autodoc_api_style`
- `sphinx_autodoc_pytest_fixtures`
- `sphinx_autodoc_sphinx`
- `sphinx_autodoc_docutils`

### Generic DOM contract

Managed `desc` entries now share one generic layout shell:

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

The corresponding CSS selectors were generalized from `dl.py.api-container` to
`dl.api-container`, so non-Python `desc` entries now reuse the same layout
primitives without HTML-string post-processing.

### FastMCP split-path evaluation

Two consolidation paths were considered for FastMCP:

- shipping path: keep the section-card model and rebuild the visible card using
  shared `api-*` components
- deferred path: migrate tools to a true `desc` / domain-backed representation

The shipping path won for now because it preserves the current section ids, ToC
labels, `{ref}` targets, and role resolution with minimal risk. The desc-based
prototype is still a valid future follow-up, but it is not necessary to share
layout and badge primitives today.

## Harness reductions completed

This pass widened structural coverage while keeping full builds to the places
that actually need builder output.

### Moved to lighter harnesses

- layout snapshots already covered the large-signature Python path
- new doctree snapshots now also cover `confval` and `rst:directive` /
  `rst:directive:option` decomposition directly
- the duplicated `_render_blocks()` logic from `autodoc-sphinx` and
  `autodoc-docutils` is gone; the shared parse helper is covered by unit tests
- FastMCP now has a direct transform test proving that later sibling content is
  re-parented into the shared `api-content` wrapper

### Full builds intentionally retained

These still need real builders:

- `tests/ext/layout/test_integration.py`
  for the final emitted Python API HTML contract
- `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py`
  for real emitted `confval` HTML
- `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py`
  for emitted `rst:*` HTML including nested directive options
- `tests/ext/fastmcp/test_fastmcp_integration.py`
  for shared-card HTML and same-page tool references
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py`
  for inventory output, genindex output, text builder output, and cross-document
  fixture links

## Benchmark matrix

These measurements were taken after the profile-registry/layout consolidation
and the new integration tests landed.

### Full suite

| Command | Result | What it shows |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s --durations=100 --durations-min=0.02` | `815 passed, 3 skipped in 37.91s`, wall `37.29s` | Current conservative baseline with slow-test evidence |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-consolidated` | `815 passed, 3 skipped in 3.49s`, wall `4.63s` | Same coverage with runner tempdir overhead mostly removed |

### Expanded autodoc slice

This slice is:

- `tests/ext/layout`
- `tests/ext/api_style`
- `tests/ext/autodoc_sphinx`
- `tests/ext/autodoc_docutils`
- `tests/ext/pytest_fixtures`
- `tests/ext/fastmcp`

| Command | Result | What it shows |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s --durations=80 --durations-min=0.02 tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp` | `257 passed, 3 skipped in 33.74s`, wall `33.87s` | Honest cost of the expanded autodoc surface in raw mode |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-autodoc-consolidated tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp` | `257 passed, 3 skipped in 2.11s`, wall `3.22s` | Same slice with runner overhead mostly removed |
| `uv run python -m cProfile -o /tmp/gp_sphinx_autodoc_consolidated.prof -m pytest -s tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp` | `257 passed, 3 skipped in 35.80s` | Profile source for the expanded autodoc slice |

## Long-running tests and causes

The slow tail is still mostly honest builder or scenario work.

| Test | Measured runtime | Cause | Verdict |
| --- | --- | --- | --- |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `5.43s setup` | Real multi-page HTML build with cross-document links | Keep |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `5.36s setup` | Real HTML build for final Python emitted layout contract | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `4.78s setup` | Real HTML build for badge markup, genindex, and inventory output | Keep |
| `tests/ext/fastmcp/test_fastmcp_integration.py::test_fastmcp_tool_cards_use_shared_layout` | `3.22s setup` | Real FastMCP HTML build with section refs and shared card wrappers | Keep |
| `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py::test_autodoc_sphinx_confvals_use_shared_layout` | `2.89s setup` | Real `confval` HTML build | Keep |
| `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py::test_autodoc_docutils_entries_use_shared_layout` | `2.84s setup` | Real `rst:*` HTML build with nested directive options | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `1.25s setup` | Shared MyST dummy-builder scenario | Already cached; acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_smoke` | `0.91s setup` | Distinct dummy-builder scenario | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_warning_and_manual_option_snapshot` | `0.80s call` | Dense fixture metadata scenario | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_text_builder_does_not_crash` | `0.77s call` | Real text-builder smoke | Keep |

No currently slow test looks like a hidden infinite loop or a falsely passing
timeout.

## Profiling findings

### Expanded autodoc slice cProfile

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `33.89s` |
| `pathlib.Path.resolve` | `14.93s` |
| `posixpath.realpath` | `14.92s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.29s` |
| `_pytest.tmpdir.mktemp` | `0.26s` |
| `sphinx_autodoc_layout._transforms.on_doctree_resolved` | `0.01s` |
| `sphinx_autodoc_api_style._transforms.on_doctree_resolved` | `0.00s` |
| `sphinx_autodoc_layout._visitors.visit_api_component` | `0.00s` |

### What that means

- the dominant repo-owned runtime is still the small set of cached synthetic
  Sphinx builds
- the dominant raw-runner overhead is still path resolution and tempdir churn
- the new profile registry, shared parse helper, and shared card wrappers are
  not hotspots
- the new integration tests are honest builder costs, not accidental harness
  inflation caused by redundant assertions

## Where execution appears to stall

There is no evidence of a true hang in the current suite.

The apparent "stall" points are:

- front-loaded setup for the remaining shared HTML scenarios
- raw pytest tempdir/path resolution before test logic starts

The profile does not show a hot loop in:

- layout profile resolution
- layout visitors
- FastMCP shared-card composition
- the new parse helper

## Real bugs, caching failures, and missing caching

### Real bugs fixed during this pass

- `rst:directive:option` entries were initially inheriting the parent
  `directive` badge because the new badge injector walked descendant
  signatures. The fix was to scope badge injection to direct signature
  children only.
- the new `setup_extension()` calls in `autodoc-sphinx` and
  `autodoc-docutils` exposed stale doctest fakes that did not implement
  `setup_extension()`. The doctests were updated so the examples remain
  executable.

### Test-scenario pitfall uncovered

- the first FastMCP integration scenario used a locally defined function in a
  `register(mcp)` closure, which made `app.env.fastmcp_tools` unpicklable in the
  cached scenario helper. The test now uses `introspect` mode with a top-level
  function and explicit `__fastmcp__` metadata, which preserves the real
  coverage and keeps the build cache compatible with Sphinx environment
  pickling.

### Fixture caching status

The current caching strategy is still effective:

- shared build results still flow through `tests/_sphinx_scenarios.py`
- the new autodoc-sphinx, autodoc-docutils, and FastMCP integration tests each
  build exactly one cached scenario
- the expensive scenarios are still mostly distinct scenario graphs, not missed
  cache hits

### Missing caching

No repo-owned missing cache stands out as the next big runtime win.

The biggest unresolved overhead remains outside the scenario helpers:

- pytest path resolution
- `realpath()`
- tempdir bookkeeping

## Doctree or snapshot fixtures versus full builds

This audit did another explicit pass over the suite looking for places where a
doctree or snapshot harness could replace a full build.

### Good candidates that were moved

- large-signature layout snapshots already run at the doctree level
- `confval` and `rst:*` structural decomposition now snapshot at the doctree
  level instead of requiring extra emitted-HTML assertions
- shared parse-helper behavior and FastMCP content-wrapping behavior now have
  direct unit coverage

### Remaining cases that should stay builder-backed

- final emitted Python API layout HTML
- emitted `confval` and `rst:*` HTML
- FastMCP section refs plus emitted shared-card HTML
- fixture inventory, genindex, and cross-document HTML links
- text-builder smoke
- any contract that depends on `viewcode`, `linkcode`, inventory generation, or
  real app lifecycle hooks

## Additional upstream API study

This pass re-checked the local study trees under:

- `~/study/python/sphinx`
- `~/study/python/docutils`
- `~/study/python/myst-parser`
- `~/study/python/sphinx-design`
- `~/study/python/pytest`
- `~/study/python/pytest-asyncio`
- `~/study/python/syrupy`

The useful confirmations were:

- `ObjectDescription.run()` and `DocFieldTransformer` still make directive time
  too early for final source-link and permalink placement
- `viewcode` and `linkcode` still reinforce the need for a late structural pass
  for managed `desc` entries
- `rst` and `std` description entries are good candidates for shared layout
  composition because their semantics already live in real Sphinx nodes
- the current FastMCP section-card path is the least risky shipping path while
  `:tool:` / `:toolref:` behavior depends on section labels

## Syrupy custom-extension audit

No custom Syrupy extension is warranted in the first pass.

Reasons:

- snapshot serialization is not a measurable hotspot in the profile
- `tests/_snapshots.py` already normalizes the unstable bits that matter:
  filesystem roots, warning text, and doctree metadata
- the new `confval` / `rst:*` snapshots fit cleanly into the existing
  `snapshot.with_defaults()` flow

If snapshot content ever becomes noisy enough to justify a serializer or
matcher, that should be revisited later. It is not the current runtime lever.

## Recommendations and follow-up

### Keep

- `api_slot` as the only cross-package handoff for desc-header metadata
- `sphinx_autodoc_layout` as the sole compositor for managed `desc` entries
- the FastMCP shared-card shipping path for now
- shared scenario caching in `tests/_sphinx_scenarios.py`

### Defer

- any attempt to infer body sections from signature parsing
- Jinja template overrides for base API entries
- a custom Syrupy serializer
- a FastMCP desc/domain migration until a bounded prototype proves it preserves
  labels, refs, and runtime behavior

### Good future follow-up

- add a tiny shared helper for "render one managed subtree to HTML" if more
  packages need translator-level tests without a full builder
- continue auditing builder-backed tests with the same rule used here:
  keep the build only when the contract truly depends on builder output
- evaluate a bounded FastMCP desc prototype later against the explicit criteria
  from the implementation plan rather than migrating piecemeal

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
