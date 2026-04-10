# Test And Autodoc Analysis

This note records the current post-shared-stack state of the autodoc
extensions, the test harnesses in use, and the measured runtime profile of the
suite.

Two baselines remain non-negotiable:

- no test was deselected to make the suite appear faster
- timing claims below are based on the full suite or on an explicitly named
  slice, not on a reduced-signal shortcut

Current measured suite status on 2026-04-10:

- raw full suite: `916 passed, 3 skipped in 40.22s`
- optimized full suite: `916 passed, 3 skipped in 4.24s`, wall `5.44s`

The dominant conclusions did not change in this wave:

- honest repo-owned cost is still concentrated in a small set of cached Sphinx
  scenario builds
- the largest avoidable raw-runner cost is still pytest tempdir and path
  resolution churn
- the new shared layout, shared badge builders, and shared typehint renderers
  are not runtime hotspots

## Final shared-stack architecture

The shipped `sphinx-autodoc-*` packages now converge on three shared layers for
the responsibilities they actually share:

- `sphinx_autodoc_badges` is the only badge primitive and badge-group renderer
- `sphinx_autodoc_layout` is the only shared presenter for `api-*` entry
  structure and shared body sections
- `sphinx_typehints_gp` is the only owner of canonical annotation
  normalization, type text generation, and cross-reference node rendering

The deliberately preserved low-risk parts of the pipeline are:

- `confval` and `rst:*` entries still originate as semantic markup and still
  flow through `parse_text_to_nodes()` / `parse_generated_markup()`
- final source-link, permalink, and header composition still happens in
  `doctree-resolved`
- FastMCP still ships on the section-card outer wrapper path so its table of
  contents labels and `:tool:` / `:toolref:` behavior stay stable

### Shared contracts

The stable producer handoff remains intentionally small:

- `api_slot(slot="badges")`
- `api_slot(slot="source-link")`

The stable visible structure is:

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
- `api-facts`
- `api-parameters`
- `api-options`
- `api-footer`

`.gas-toolbar` remains only as a compatibility shim. The ownership point is
still `api-layout-right`.

### Shared gaps closed in this wave

This migration closed the remaining foundation gaps that were still forcing
package-local duplication:

- `sphinx_autodoc_layout` now exposes a public shared non-`desc`
  card-shell builder for section-card consumers
- shared section builders now cover description, facts, parameters, options,
  footer, and summary/index table wrappers
- generic card-shell CSS now lives in `sphinx_autodoc_layout` instead of being
  repeated in FastMCP
- `sphinx_autodoc_badges.BadgeSpec` and the shared badge-group builder are now
  the canonical badge pipeline
- `sphinx_typehints_gp` now provides reusable annotation helpers instead of
  requiring package-local stringification and xref rendering
- `sphinx_typehints_gp.AnnotationDisplay` and
  `classify_annotation_display()` now cover literal-only enum displays so
  FastMCP and other consumers no longer need local enum heuristics

## Rendering hook points and extension ownership

The current rendering path is:

1. Sphinx or a package directive creates semantic nodes such as `desc`,
   `desc_signature`, `desc_content`, tables, field lists, and literal blocks.
2. Producer packages discover package-specific metadata.
3. Producer packages attach shared slots and shared body sections.
4. `sphinx_autodoc_layout` performs final structural composition in
   `doctree-resolved`.
5. HTML visitors and shared CSS provide the final visual layout.

### What each shared layer owns

`sphinx_autodoc_badges`

- `BadgeSpec`
- badge node construction
- badge-group rendering
- badge CSS primitives

`sphinx_autodoc_layout`

- profile-driven desc layout policy
- shared body section wrappers
- shared summary/index presentation wrapper
- desc header composition
- non-`desc` shared card-entry builder
- generic layout CSS for `api-*` regions

`sphinx_typehints_gp`

- canonical annotation normalization
- structured annotation display classification
- type collection normalization
- annotation-to-node rendering
- paragraph helpers for embedding typed content in facts and tables
- private Sphinx annotation parsing isolation

### What each producer still owns

`sphinx_autodoc_api_style`

- Python metadata discovery
- badge spec production
- source-link metadata production

`sphinx_autodoc_pytest_fixtures`

- fixture discovery and store/index ownership
- fixture reference repair
- fixture-specific metadata

`sphinx_autodoc_sphinx`

- config value discovery
- semantic `confval` markup generation

`sphinx_autodoc_docutils`

- semantic `rst:directive`, `rst:role`, and `rst:directive:option` markup
  generation

`sphinx_autodoc_fastmcp`

- tool discovery and section wrapper ownership
- tool-specific parameter and return semantics
- current `:tool:` / `:toolref:` behavior

## Package-by-package migration status

### `sphinx_autodoc_api_style`

Now fully moved onto the shared badge and type stack for the parts it owns:

- badge creation uses `BadgeSpec`
- `setup()` auto-loads `sphinx_typehints_gp`
- layout composition remains entirely in `sphinx_autodoc_layout`

### `sphinx_autodoc_pytest_fixtures`

Now uses the shared stack for badge, layout, and type rendering:

- `setup()` auto-loads `sphinx_typehints_gp`
- fixture return metadata stores one canonical annotation form
- fixture index type cells use shared annotation paragraph rendering
- top-level metadata wraps into shared `api-facts`, `api-parameters`, and
  shared summary/index presentation

Removed package-local type duplication:

- removed `return_xref_target`
- removed dead local `_format_type_short`

### `sphinx_autodoc_sphinx`

Now uses the shared stack for layout and type text:

- `setup()` auto-loads `sphinx_typehints_gp`
- config type text now comes from shared type normalization
- config indexes now use the shared summary/index wrapper
- config facts now use shared fact sections
- complex defaults still render as real literal blocks

Removed package-local type duplication:

- package-local `_render_types`
- package-local `_type_text`

### `sphinx_autodoc_docutils`

Still keeps the semantic markup path, but its visible structure is now shared:

- `setup()` auto-loads `sphinx_typehints_gp`
- directives, roles, and options normalize into shared section wrappers
- index tables now use the shared summary/index wrapper

### `sphinx_autodoc_fastmcp`

FastMCP remains on the shipped section-card path, but its inner rendering is now
shared:

- `setup()` auto-loads `sphinx_typehints_gp`
- inner card shell uses the shared non-`desc` card-entry builder
- return and parameter type rendering use shared type helpers
- summary tables use the shared summary/index wrapper

Removed package-local type duplication:

- local `format_annotation`
- local `make_type_xref`

The desc-backed prototype remains test-only.

## Test categories and harnesses in use

The suite remains mostly surgical. Honest runtime is concentrated in cached
builder-backed scenarios plus raw pytest path handling.

| Category | Main locations | Harness | Current verdict |
| --- | --- | --- | --- |
| Pure helper and parser tests | `tests/ext/api_style`, `tests/ext/autodoc_sphinx`, `tests/ext/autodoc_docutils`, `tests/ext/fastmcp`, `tests/ext/typehints_gp`, root tests | Direct unit tests for strings, dataclasses, parsers, stores, builders | Already light-weight |
| Shared stack unit tests | `tests/ext/layout/test_render.py`, `tests/ext/test_shared_stack_setup.py`, `tests/ext/typehints_gp/test_unit.py` | Tiny synthetic nodes and direct helper assertions | New wave coverage; fast and precise |
| Doctree and transform tests | `tests/ext/layout/test_transforms.py`, `tests/ext/fastmcp/test_transforms.py`, fixture doctree tests | Synthetic trees, targeted transform calls, tiny dummy builders | Preferred structure harness |
| Visitor/render-node tests | `tests/ext/layout/test_visitors.py` | Direct visitor assertions with translator stubs | Light and precise |
| Snapshot unit tests | `tests/ext/layout/test_snapshots.py`, fixture doctree snapshots | Normalized doctree and HTML-fragment snapshots | Expanded in this wave; preferred over duplicate HTML builds |
| Cached emitted-HTML integration tests | `tests/ext/layout/test_integration.py`, `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py`, `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py`, `tests/ext/fastmcp/test_fastmcp_integration.py` | Shared cached Sphinx scenarios | Required for emitted HTML contracts |
| Cross-document, inventory, and text-builder tests | `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` | Real HTML and text builds plus `objects.inv` checks | Honest expensive coverage; keep |
| Docs page smoke | `tests/test_docs_package_pages.py` | Focused docs build smoke only where live demo output matters | Narrow and acceptable |
| Doctests | selected package modules and docs helpers | `--doctest-modules` capable helpers | Required by repo rules |

## Which tests moved from full builds to lighter harnesses

This wave continued the policy of moving structure assertions off full builds
when builder output is not the contract.

### Moved to lighter harnesses

- reusable type rendering now has direct unit coverage in
  `tests/ext/typehints_gp/test_unit.py`
- shared non-`desc` card-shell composition now has direct unit coverage in
  `tests/ext/layout/test_render.py`
- shared stack auto-loading now has direct unit coverage in
  `tests/ext/test_shared_stack_setup.py`
- `api-style` badge-spec adoption has direct unit coverage instead of relying
  on HTML inspection
- fixture index type-cell rendering now has unit coverage for shared type node
  usage instead of depending on full emitted HTML
- FastMCP shared parsing and shared card structure continue to be checked
  primarily by doctree and visitor-level tests

### Intentionally builder-backed

These remain on real builders because the builder is the contract:

- final emitted Python API HTML
- emitted `confval` HTML and config index output
- emitted `rst:*` HTML
- fixture inventory output, genindex output, cross-document HTML links, and
  text-builder behavior
- FastMCP section-card HTML plus `:tool:` / `:toolref:` behavior
- docs live-demo smoke where the page itself is the product

## Benchmark matrix

### Full suite

| Command | Result | What it shows |
| --- | --- | --- |
| `uv run py.test --reruns 0 -vvv` | `916 passed, 3 skipped in 40.22s` | Current conservative baseline with full signal and the required validation command |
| `/usr/bin/time -p uv run pytest -q -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-wave6` | `916 passed, 3 skipped in 4.24s`, wall `5.44s` | Same coverage with most raw tempdir/path overhead removed |

### Expanded autodoc slice

This slice is:

- `tests/ext/layout`
- `tests/ext/api_style`
- `tests/ext/autodoc_sphinx`
- `tests/ext/autodoc_docutils`
- `tests/ext/pytest_fixtures`
- `tests/ext/fastmcp`
- `tests/ext/typehints_gp`

| Command | Result | What it shows |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -q tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp tests/ext/typehints_gp` | `339 passed, 3 skipped in 36.74s`, wall `37.06s` | Honest cost of the shared autodoc surface in raw mode |
| `/usr/bin/time -p uv run pytest -q -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-autodoc-wave6 tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp tests/ext/typehints_gp` | `339 passed, 3 skipped in 2.40s`, wall `2.30s` | Same slice with runner overhead mostly removed |
| `uv run python -m cProfile -o /tmp/gp_sphinx_wave6_autodoc.prof -m pytest -q tests/ext/layout tests/ext/api_style tests/ext/autodoc_sphinx tests/ext/autodoc_docutils tests/ext/pytest_fixtures tests/ext/fastmcp tests/ext/typehints_gp` | `339 passed, 3 skipped in 38.93s` | Profile source for the shared-stack slice |

## Long-running tests and causes

The slow tail is still dominated by honest builder-backed scenarios.

| Test | Measured runtime | Cause | Verdict |
| --- | --- | --- | --- |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `3.9s`-class setup | Real multi-page HTML build with cross-document links and inventory data | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `3.4s`-class setup | Real HTML build for badge markup, genindex, and inventory output | Keep |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `3.2s`-class setup | Real HTML build for final emitted Python layout contract | Keep |
| `tests/test_docs_package_pages.py::test_fastmcp_docs_page_renders_live_demo_output` | `2.9s`-class setup | Focused docs build smoke for live rendered output | Keep |
| `tests/ext/autodoc_docutils/test_autodoc_docutils_integration.py::test_autodoc_docutils_entries_use_shared_layout` | `2.5s`-class setup | Real `rst:*` HTML build with nested directive options | Keep |
| `tests/ext/fastmcp/test_fastmcp_integration.py::test_fastmcp_tool_cards_use_shared_layout` | `2.0s`-class setup | Real FastMCP HTML build with section refs and shared-card wrappers | Keep |
| `tests/ext/autodoc_sphinx/test_autodoc_sphinx_integration.py::test_autodoc_sphinx_confvals_use_shared_layout` | `1.9s`-class setup | Real `confval` HTML build | Keep |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `0.7s`-class setup | Shared MyST dummy-builder scenario | Already cached; acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixture_index_resolution_smoke` | `0.6s`-class call | Dense fixture index scenario with real reference resolution | Acceptable |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_text_builder_does_not_crash` | `0.5s`-class call | Real text-builder smoke | Keep |

No currently slow test looks like a hidden hang or a synthetic timeout.

## Profiling findings

### Expanded autodoc slice cProfile

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `36.611s` |
| `posixpath.realpath` | `16.561s` |
| `_pytest.tmpdir.mktemp` | `0.313s` |
| `_pytest.pathlib.make_numbered_dir` | `0.155s` |
| `sphinx_autodoc_layout._transforms.on_doctree_resolved` | negligible compared with builder setup |
| `sphinx_typehints_gp.rendering.render_annotation_nodes` | negligible compared with builder setup |

Profile total:

- `8813847` function calls (`8224448` primitive calls) in `39.724s`

### What that means

- the dominant repo-owned cost is still cached Sphinx scenario setup
- the dominant raw-runner overhead is still path resolution and `realpath()`
- the new shared typehint helpers are not hotspots
- the new annotation-display classifier is not a hotspot
- the shared layout transform and shared card builder are not hotspots

## Where time is spent and where execution appears to stall

There is no evidence of a true hang in the current suite.

The apparent stall points are:

- front-loaded setup for the remaining shared HTML scenarios
- raw pytest tempdir and path resolution before test logic starts

The profile does not show hot loops in:

- shared badge-group rendering
- shared typehint normalization
- shared annotation node rendering
- shared slot injection
- shared layout composition
- shared FastMCP card-shell composition

## Suspected bugs, fixed bugs, and remaining risks

### Fixed during this migration

- duplicated badge-group and slot-injection logic across producer packages
- duplicated type normalization and xref rendering across fixtures, Sphinx
  config docs, and FastMCP
- package-specific inner card-shell assembly in FastMCP
- package-specific summary/index table presentation drift

### Remaining risks to watch

- FastMCP still uses the shipped section-card outer wrapper, so it is aligned
  structurally inside the card but not yet a real shipped `desc` object
- non-autodoc consumers now auto-load `sphinx_typehints_gp`, so the extension
  must continue to tolerate missing autodoc hooks and missing autodoc config
  without raising

### Real bug versus overhead

No current long-running test looks like a correctness bug disguised as a slow
test. The dominant slow cases are honest integration coverage plus raw pytest
path handling.

## Caching failures and missing caching

### Working caching

The current caching strategy is still effective:

- shared build results still flow through `tests/_sphinx_scenarios.py`
- expensive layout, `confval`, `rst:*`, FastMCP, and fixture integration tests
  still build exactly one cached scenario each
- the new shared-stack coverage did not add a new builder-backed scenario

### Missing or ineffective caching

No repo-owned missing cache stands out as the next major runtime win.

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
- `~/study/python/furo`

Useful confirmations:

- `SphinxDirective.parse_text_to_nodes()` remains the right low-cost parsing
  abstraction for markup-producing directives
- `doctree-resolved` remains the correct late hook for source-link and header
  composition
- custom nodes plus visitors remain the right layer for `api-*` wrappers; HTML
  template overrides are still unnecessary
- the current Amber snapshot workflow already covers these doctrees well enough
- Furo compatibility is best preserved by staying node and CSS based instead of
  patching theme templates

## Syrupy customization audit

No custom Syrupy extension is warranted in this wave.

Reasons:

- snapshot serialization is not a measurable hotspot
- `tests/_snapshots.py` already normalizes the unstable bits that matter
- the new shared-stack doctree and HTML-fragment snapshots fit cleanly into the
  existing Amber workflow

## Tradeoffs considered

- keeping `.gas-toolbar` for one compatibility wave adds minor markup clutter
  but avoids downstream CSS breakage while `api-*` remains the real contract
- keeping FastMCP on section cards preserves labels and `:tool:` / `:toolref:`
  behavior with low migration risk
- keeping `confval` and `rst:*` on the semantic-markup path avoids a
  high-risk domain rewrite while still allowing shared visual structure

## Recommendations and follow-up

### Keep

- `api_slot` as the only cross-package header handoff
- `sphinx_autodoc_layout` as the sole shared presenter
- `sphinx_autodoc_badges` as the sole badge DOM owner
- `sphinx_typehints_gp` as the sole annotation rendering layer
- shared scenario caching in `tests/_sphinx_scenarios.py`

### Defer

- a shipped FastMCP desc/domain migration
- Jinja template overrides for API entries
- a custom Syrupy serializer
- any attempt to infer body sections from signature parsing

### Good next follow-up

- add one small shared helper for rendering a managed subtree to an HTML
  fragment if more packages need translator-level assertions
- continue auditing builder-backed tests with the same rule used here: keep the
  build only when the builder output is the contract
- if FastMCP ever moves onto a shipped desc path, add a dedicated tool domain
  instead of overloading current section-label behavior

## Validation commands

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
$ uv run py.test --reruns 0 -vvv
```

```console
$ just build-docs
```
