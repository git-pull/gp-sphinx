# Test And Autodoc Analysis

This note records the current post-second-wave state of the autodoc rendering
pipeline and the measured runtime profile of the suite.

Two baselines remain non-negotiable:

- no test was deselected to make the suite "look" faster
- timing claims below are based on the full suite or on an explicitly named
  slice, not on a reduced-signal fast lane

Current suite status on 2026-04-09:

- `828` tests collected
- `825` passed
- `3` skipped

## Test categories and harnesses

The suite is still mostly surgical. Honest runtime remains concentrated in a
small set of cached builder-backed scenarios plus raw pytest tempdir/path
resolution.

| Category | Main locations | Harness | Current verdict |
| --- | --- | --- | --- |
| Pure helper and parser tests | `tests/ext/api_style`, most of `tests/ext/autodoc_sphinx`, most of `tests/ext/autodoc_docutils`, most of `tests/ext/fastmcp`, workspace-root tests | Direct unit tests, badge builders, parser helpers, store helpers | Already light-weight |
| Shared slot/helper tests | `tests/ext/layout/test_slots.py`, `tests/ext/layout/test_render.py` | Synthetic `desc_signature` nodes and tiny dummy directives | New second-wave coverage; fast and precise |
| Doctree and transform tests | `tests/ext/layout/test_transforms.py`, `tests/ext/fastmcp/test_transforms.py`, fixture doctree tests | Synthetic nodes, transform calls, targeted dummy-builder scenarios | Good balance; keep as the default structure harness |
| Visitor/render-node tests | `tests/ext/layout/test_visitors.py` | Direct visitor assertions with tiny translator stubs | Light and precise |
| Doctree snapshot tests | `tests/ext/layout/test_snapshots.py`, fixture doctree snapshots | Synthetic `desc` trees plus `on_doctree_resolved()` and snapshot normalization | Expanded again in this wave; preferred over duplicate HTML snapshots |
| Cached emitted-HTML integration tests | `tests/ext/layout/test_integration.py`, `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py`, `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py`, `tests/ext/fastmcp/test_fastmcp_integration.py` | Shared `build_shared_sphinx_result()` scenarios | Required for emitted HTML contracts |
| Cross-document, inventory, and text-builder tests | `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` | Real HTML and text builds plus `objects.inv` checks | Honest expensive coverage; keep |
| Prototype-only feasibility tests | `tests/ext/fastmcp/test_prototype.py` | Test-only `mcp:tool` desc builder plus layout transform | New second-wave feasibility coverage with no shipping behavior change |
| Doctests | `docs/_ext/*.py`, selected package modules | `--doctest-modules` | Already light-weight |

## Current autodoc rendering pipeline

The repo now has two shared layers:

- `sphinx_autodoc_badges` is the only badge primitive package
- `sphinx_autodoc_layout` is the shared structural compositor for managed
  object-description output

### Upstream hook points

1. Sphinx directive-time parsing still creates semantic `desc`,
   `desc_signature`, and `desc_content` nodes.
2. Producer packages still own metadata discovery and package-specific body
   content.
3. `viewcode`, `linkcode`, and Sphinx permalink injection still happen late
   enough that final header composition belongs in `doctree-resolved`, not only
   in directive code.

### Shared layout owner

`sphinx_autodoc_layout` is profile-driven and owns final composition for:

- Python API entries
- `py:fixture`
- `std:confval`
- `rst:directive`
- `rst:role`
- `rst:directive:option`
- test-only `mcp:tool` prototype entries

Its responsibilities are:

- nested Python member ownership for class/exception trees
- wrapping `desc_content` into explicit body regions
- consuming `api_slot(slot="badges")` and `api_slot(slot="source-link")`
- rebuilding signatures into explicit `api-*` header regions
- inserting the managed permalink node
- optionally folding large signatures and parameter sections when the active
  profile allows it

### Producer packages

- `sphinx_autodoc_api_style` is still a Python metadata producer only. It now
  delegates slot injection to the shared helper and leaves all final HTML
  composition to layout.
- `sphinx_autodoc_pytest_fixtures` is still a fixture metadata producer only.
  It now uses the same shared slot helper for badge/source-link insertion and
  keeps fixture-only responsibilities such as metadata fields, store updates,
  and reference repair.
- `sphinx_autodoc_sphinx` still generates real `confval` markup, parses it via
  `parse_generated_markup()`, and injects only package-owned badge slots.
- `sphinx_autodoc_docutils` still generates real `rst:*` markup, parses it via
  `parse_generated_markup()`, and injects only package-owned badge slots.
- `sphinx_autodoc_fastmcp` still ships on the section-card path. Its runtime
  output is unchanged in principle: shared `api-*` regions inside `nodes.section`
  wrappers, same labels, same `:tool:` / `:toolref:` behavior.

## Chosen architecture and second-wave changes

### Stable shared contracts

The shared producer handoff remains intentionally small:

- `api_slot(slot="badges")`
- `api_slot(slot="source-link")`

The public structural DOM contract stays:

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

`.gas-toolbar` remains on `api-layout-right` as a compatibility shim only.
Layout ownership is still with the `api-*` regions.

### Shared slot-injection helper

The main second-wave consolidation change is the new internal helper in
`sphinx_autodoc_layout._slots`:

- shared viewcode/source-link extraction
- shared slot append order
- shared idempotence guard on `desc_signature`

This removed the remaining duplicated slot-injection logic from:

- `sphinx_autodoc_api_style`
- `sphinx_autodoc_pytest_fixtures`
- `sphinx_autodoc_sphinx`
- `sphinx_autodoc_docutils`

The layout transform itself is still the only compositor.

### Profile-driven desc composition

`DescLayoutProfile` remains internal, but it is now the canonical typed policy
registry for all managed `(domain, objtype)` pairs.

Stable profile classes now include:

- `api-profile--py-function`
- `api-profile--py-method`
- `api-profile--py-fixture`
- `api-profile--confval`
- `api-profile--rst-directive`
- `api-profile--rst-role`
- `api-profile--rst-directive-option`
- `api-profile--mcp-tool`

### FastMCP split-path result

The "both tracks" decision is now reflected in code:

- shipping path: keep FastMCP on shared section cards
- prototype path: add a non-shipping `mcp:tool` desc builder used only in tests

The prototype answers these questions positively enough to keep exploring later:

- tool ids can map cleanly to desc ids using the current slug style such as
  `list-sessions`
- parameter tables and return metadata fit inside `desc_content`
- the shared layout can render a tool-style large signature without special
  FastMCP-only compositor code

What it does **not** prove yet:

- that the runtime extension should switch from section labels to a real tool
  domain now
- that current `:tool:` / `:toolref:` behavior can be swapped without a more
  deliberate migration

That migration should stay deferred.

## Which tests moved off full builds

This pass widened structural coverage without paying for extra full builds.

### Moved to lighter harnesses

- shared slot-injection behavior now has direct unit coverage
- FastMCP desc-prototype feasibility now has doctree/transform coverage instead
  of a shipping integration scenario
- large non-Python header cases now snapshot at the doctree level:
  - `confval` with multiple badges and a long default block
  - nested `rst:directive` / `directive:option`
  - wide `mcp:tool` prototype with many parameters and badge cluster

### Cases intentionally left builder-backed

These still need real builders:

- final emitted Python API layout HTML
- emitted `confval` HTML
- emitted `rst:*` HTML
- FastMCP section refs plus emitted shared-card HTML
- fixture inventory, genindex, and cross-document HTML links
- text-builder smoke
- any contract that depends on `viewcode`, `linkcode`, inventory generation, or
  full app lifecycle behavior

## Benchmark matrix

These measurements were taken after the shared slot helper and the FastMCP
prototype coverage landed.

### Full suite

| Command | Result | What it shows |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s --durations=100 --durations-min=0.02` | `825 passed, 3 skipped in 24.06s`, wall `24.08s` | Current conservative baseline with slow-test evidence |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-wave2` | `825 passed, 3 skipped in 4.42s`, wall `5.63s` | Same coverage with runner tempdir overhead mostly removed |

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
| `/usr/bin/time -p uv run pytest -s --durations=80 --durations-min=0.02 tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp` | `266 passed, 3 skipped in 20.51s`, wall `21.63s` | Honest cost of the expanded autodoc surface in raw mode |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-autodoc-wave2 tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp` | `266 passed, 3 skipped in 2.73s`, wall `4.05s` | Same slice with runner overhead mostly removed |
| `uv run python -m cProfile -o /tmp/gp_sphinx_wave2_autodoc.prof -m pytest -s tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp` | `266 passed, 3 skipped in 34.97s` | Profile source for the expanded autodoc slice |

## Long-running tests and causes

The slow tail is still dominated by honest builder-backed scenarios.

| Test | Measured runtime | Cause | Verdict |
| --- | --- | --- | --- |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `3.66s setup` | Real HTML build for the final emitted Python layout contract | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `3.25s setup` | Real multi-page HTML build with cross-document links | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `2.74s setup` | Real HTML build for badge markup, genindex, and inventory output | Keep |
| `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py::test_autodoc_docutils_entries_use_shared_layout` | `2.15s setup` | Real `rst:*` HTML build with nested directive options | Keep |
| `tests/ext/fastmcp/test_fastmcp_integration.py::test_fastmcp_tool_cards_use_shared_layout` | `1.67s setup` | Real FastMCP HTML build with section refs and shared-card wrappers | Keep |
| `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py::test_autodoc_sphinx_confvals_use_shared_layout` | `1.58s setup` | Real `confval` HTML build | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `0.54s setup` | Shared MyST dummy-builder scenario | Already cached; acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_warning_and_manual_option_snapshot` | `0.53s call` | Dense fixture metadata scenario | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_default_fixture_store_and_domain_contract` | `0.49s setup` | Distinct dummy-builder scenario | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_text_builder_does_not_crash` | `0.47s call` | Real text-builder smoke | Keep |

No currently slow test looks like a hidden infinite loop or a falsely passing
timeout.

## Profiling findings

### Expanded autodoc slice cProfile

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `32.89s` |
| `pathlib.Path.resolve` | `14.41s` |
| `posixpath.realpath` | `14.40s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.32s` |
| `_pytest.tmpdir.mktemp` | `0.28s` |
| `sphinx_autodoc_layout._transforms.on_doctree_resolved` | `0.02s` |
| `sphinx_autodoc_layout._transforms._rebuild_signature_layout` | `0.01s` |
| `sphinx_autodoc_layout._slots.inject_signature_slots` | `0.00s` |
| `sphinx_autodoc_layout._visitors.visit_api_component` | `0.00s` |

### What that means

- the dominant repo-owned runtime is still the small set of cached synthetic
  Sphinx builds
- the dominant raw-runner overhead is still path resolution and tempdir churn
- the second-wave slot helper and the FastMCP prototype are not hotspots
- the shared layout transform remains cheap relative to builder setup

## Where execution appears to stall

There is no evidence of a true hang in the current suite.

The apparent "stall" points are:

- front-loaded setup for the remaining shared HTML scenarios
- raw pytest tempdir/path resolution before test logic starts

The profile does not show a hot loop in:

- layout profile resolution
- slot injection
- layout visitors
- FastMCP shared-card composition
- the new FastMCP desc prototype

## Real bugs, caching failures, and missing caching

### Real bugs fixed during this pass

- the remaining producer-side slot injection was duplicated four ways; that is
  now collapsed into one shared helper so future fixes land in one place
- the second-wave FastMCP prototype surfaced one design constraint clearly:
  tool ids can be represented cleanly as desc ids, but that alone is not enough
  to justify changing the shipping role/label strategy yet

### Fixture caching status

The current caching strategy is still effective:

- shared build results still flow through `tests/_sphinx_scenarios.py`
- the expensive layout, `confval`, `rst:*`, FastMCP, and fixture integration
  tests still build exactly one cached scenario each
- the new prototype coverage did not add a new builder-backed scenario

### Missing caching

No repo-owned missing cache stands out as the next big runtime win.

The biggest unresolved overhead remains outside the scenario helpers:

- pytest path resolution
- `realpath()`
- tempdir bookkeeping

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

- `SphinxDirective.parse_text_to_nodes()` is still the right shared parsing
  abstraction for markup-producing directives
- `doctree-resolved` is still the correct late hook for final header/source link
  composition
- `add_node()` and custom visitors remain the right layer for `api-*` wrappers;
  HTML template overrides are still unnecessary for this wave
- Syrupy makes custom extensions possible, but the current Amber serializer and
  repo-local normalization already fit these doctree snapshots well enough

## Syrupy custom-extension audit

No custom Syrupy extension is warranted in this wave.

Reasons:

- snapshot serialization is not a measurable hotspot in the profile
- `tests/_snapshots.py` already normalizes the unstable bits that matter:
  filesystem roots, warning text, and doctree metadata
- the new `confval`, `rst:*`, and FastMCP prototype snapshots fit cleanly into
  the existing Amber workflow

If snapshot content ever becomes noisy enough to justify a serializer or
matcher, that should be revisited later. It is not the current runtime lever.

## Tradeoffs considered

- keeping `.gas-toolbar` for one compatibility wave costs a little markup
  clutter, but avoids a downstream CSS break while the `api-*` regions settle
- keeping FastMCP on section cards preserves current refs and labels with low
  risk; the desc prototype provides evidence without forcing a migration
- using field-list wrappers around the prototype parameter table keeps layout's
  `api-parameters` decomposition intact while still testing that a table can sit
  naturally inside `desc_content`

## Recommendations and follow-up

### Keep

- `api_slot` as the only cross-package desc-header handoff
- `sphinx_autodoc_layout` as the sole compositor for managed `desc` entries
- the shared slot helper as the only place that moves viewcode/source links into
  slots
- the FastMCP shared-card shipping path for now
- shared scenario caching in `tests/_sphinx_scenarios.py`

### Defer

- any attempt to infer body sections from signature parsing
- Jinja template overrides for base API entries
- a custom Syrupy serializer
- a runtime FastMCP desc/domain migration until a bounded prototype proves it
  can preserve labels, refs, and runtime behavior together

### Good future follow-up

- add one tiny shared helper for "render one managed subtree to HTML" if more
  packages want translator-level assertions without a full builder
- continue auditing builder-backed tests with the same rule used here:
  keep the build only when the contract truly depends on builder output
- if the FastMCP desc path becomes a real migration candidate, add a dedicated
  tool domain rather than overloading the current section-label approach

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
