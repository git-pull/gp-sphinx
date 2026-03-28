# Phase 3: Semantic Export -- The DoctrineBuilder

> [Back to Overview](00-overview.md) | Previous: [Phase 2 -- Multi-Project](04-phase-2-multi-project.md) | Next: [Phase 4 -- Expansion](06-phase-4-expansion.md)

**Duration**: 5-7 weeks | **Risk**: High | **Status**: Only if Phase 2 exposes real blockers

## When This Phase Is Justified

Do not build a custom builder because it is elegant. Build it only if Option B (HTML bridge from Phase 1-2) proves insufficient.

Concrete blockers that justify this phase:

- API pages need richer rendering than Sphinx HTML provides (e.g., interactive parameter tables, collapsible signatures)
- Search needs structured filtering by project, object type, or domain
- Cross-project links need first-class identity beyond URL rewriting
- Sphinx HTML structure makes Tailwind styling brittle despite `rehype` sanitization
- Extension output (sphinx_design cards, tabs) requires component-level rendering

If none of these materialize, **stop at Phase 2**.

---

## The Core Insight: The "Doctrine Graph"

> Origin: Claude-v2 (Creative) brainstorm variant, scored 38/40.

Sphinx is not a documentation builder. **Sphinx is a semantic compiler for Python knowledge graphs.** It parses reStructuredText and Markdown, resolves cross-references via intersphinx, extracts type information via autodoc, and builds a navigational topology via toctree.

The HTML translator **destroys** this semantic structure. A `:py:func:` reference becomes `<a href="...">` -- the domain, role, and target information are gone. An `api_object` becomes `<dl><dt>...</dt><dd>...</dd></dl>` -- the parameter types, defaults, and docstring sections are lost.

The DoctrineBuilder preserves all of it in a structured JSON intermediate representation.

## Key Technical Clarification

ALL Sphinx builders receive resolved doctrees. `Builder._write_serial()` calls `env.get_and_resolve_doctree()` for every builder, including the XML builder.

**Ref**: `~/study/python/sphinx/sphinx/builders/__init__.py` -- the `_write_serial()` method at the core of the builder lifecycle.

The DoctrineBuilder's advantage is not in receiving resolved data (all builders do). It is in **preserving semantic structure** instead of flattening it into HTML strings or raw XML.

## The `.doctrine/` Output Format

```text
.doctrine/
  manifest.json              # Project metadata, schema_version, page list
  pages/
    index.json               # Each page as a structured document
    cli/sync.json
  toctree.json               # Full navigation topology (maxdepth, hidden, glob)
  inventory.json             # Resolved intersphinx data (objects.inv as JSON)
  refs.json                  # Cross-reference targets
  assets/                    # Copied images and static files
```

### Schema Versioning

The `.doctrine/` format is a **public API** between Python and TypeScript. Changes must be versioned from day one.

- `manifest.json` includes `schema_version: 1`
- Breaking changes (renamed fields, changed nesting) increment the version
- Additive changes (new node types, new optional fields) do not
- The Astro loader validates compatibility at build time
- The translator and loader are tested against golden-file snapshots

## Semantic AST: Per-Page JSON

```json
{
  "docname": "cli/sync",
  "title": "Synchronization",
  "schema_version": 1,
  "toc": [
    { "id": "sync-command", "text": "Sync Command", "depth": 2 },
    { "id": "options", "text": "Options", "depth": 3 }
  ],
  "navigation": {
    "prev": { "docname": "cli/index", "title": "CLI Reference" },
    "next": { "docname": "cli/add", "title": "Adding Repositories" },
    "parents": [{ "docname": "cli/index", "title": "CLI Reference" }]
  },
  "body": [
    {
      "type": "section",
      "id": "sync-command",
      "children": [
        { "type": "heading", "depth": 2, "text": "Sync Command" },
        {
          "type": "paragraph",
          "children": [
            { "type": "text", "value": "The " },
            { "type": "code_inline", "value": "sync" },
            { "type": "text", "value": " command pulls updates for configured repositories." }
          ]
        },
        {
          "type": "directive",
          "name": "code-block",
          "language": "console",
          "content": "$ vcspull sync flask"
        },
        {
          "type": "cross_reference",
          "domain": "py",
          "role": "func",
          "target": "vcspull.cli.sync.create_sync_subparser",
          "resolved_uri": "cli/sync#vcspull.cli.sync.create_sync_subparser",
          "display_text": "create_sync_subparser()"
        },
        {
          "type": "api_object",
          "domain": "py",
          "objtype": "function",
          "fullname": "vcspull.cli.sync.sync",
          "signature": {
            "parameters": [
              { "name": "repo_terms", "type": "list[str]", "default": null },
              { "name": "config", "type": "pathlib.Path | None", "default": "None" }
            ],
            "returns": { "type": "None" }
          },
          "docstring_sections": [
            { "kind": "summary", "text": "Synchronize repositories matching the given terms." },
            {
              "kind": "parameters",
              "entries": [
                { "name": "repo_terms", "type": "list[str]", "description": "Repository name patterns to match." }
              ]
            },
            { "kind": "returns", "type": "None", "description": "" }
          ]
        }
      ]
    }
  ]
}
```

Compare this to what the HTML builder produces: `write_doc()` (at `~/study/python/sphinx/sphinx/builders/html/__init__.py` line ~650) walks the doctree with a translator that accumulates HTML strings, then injects them into Jinja2 templates. The semantic structure is destroyed in this process.

## The Harsh Reality of Docutils

Docutils is not a clean, semantic AST. It is a messy hybrid of semantics and formatting.

More critically, Sphinx extensions inject custom nodes and provide their own `visit_<node>_html` methods for the HTML builder -- but they will NOT provide `visit_<node>_doctrine` methods for your builder.

### Actual Node Counts (Sphinx 8.2.3 / docutils 0.21.2)

| Category | Count | Source |
|---|---|---|
| docutils Element subclasses | ~100 | `docutils.nodes` |
| Sphinx-specific addnodes | 52 | `sphinx.addnodes` |
| **Total** | **~152** | Verified via introspection |

### Translator Benchmarks

| Translator | visit methods | depart methods | Total methods | Lines |
|---|---|---|---|---|
| HTML5Translator | 68 | 55 | 123 | ~1,030 |
| TextTranslator | 105 | 86 | 191 | ~1,370 |

**Ref**: `~/study/python/sphinx/sphinx/writers/html5.py`, `~/study/python/sphinx/sphinx/writers/text.py`

The DoctrineTranslator will need ~120-150 visitor methods. Not all 152 node types need unique handlers (some share base class visitors), but the number is substantially larger than initial estimates might suggest.

## The DoctrineTranslator

Stack-based JSON builder (instead of string accumulator):

```python
from __future__ import annotations

import typing as t

from sphinx.util.docutils import SphinxTranslator

if t.TYPE_CHECKING:
    import docutils.nodes as nodes


class DoctrineTranslator(SphinxTranslator):
    """Translates resolved doctree nodes into structured JSON-serializable dicts.

    Instead of accumulating HTML strings, this translator pushes structured
    dicts onto a stack. The result is a JSON-serializable tree that preserves
    domain semantics, cross-reference identity, and API object structure.
    """

    def __init__(self, document: nodes.document, builder: t.Any) -> None:
        super().__init__(document, builder)
        self.output: list[dict[str, t.Any]] = []
        self._stack: list[list[dict[str, t.Any]]] = [self.output]

    def _push(self, node_dict: dict[str, t.Any]) -> None:
        if "children" not in node_dict:
            node_dict["children"] = []
        self._stack[-1].append(node_dict)
        self._stack.append(node_dict["children"])

    def _pop(self) -> None:
        self._stack.pop()

    # --- Standard docutils nodes ---

    def visit_section(self, node: nodes.section) -> None:
        self._push({"type": "section", "id": node.get("ids", [None])[0]})

    def depart_section(self, node: nodes.section) -> None:
        self._pop()

    def visit_title(self, node: nodes.title) -> None:
        self._push({"type": "heading", "depth": self._section_depth()})

    def depart_title(self, node: nodes.title) -> None:
        self._pop()

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        self._push({"type": "paragraph"})

    def depart_paragraph(self, node: nodes.paragraph) -> None:
        self._pop()

    def visit_Text(self, node: nodes.Text) -> None:
        self._stack[-1].append({"type": "text", "value": node.astext()})

    def depart_Text(self, node: nodes.Text) -> None:
        pass

    def visit_literal(self, node: nodes.literal) -> None:
        self._stack[-1].append({
            "type": "code_inline",
            "value": node.astext(),
        })
        raise nodes.SkipChildren

    def visit_literal_block(self, node: nodes.literal_block) -> None:
        self._stack[-1].append({
            "type": "code_block",
            "language": node.get("language", ""),
            "content": node.astext(),
        })
        raise nodes.SkipChildren

    def visit_reference(self, node: nodes.reference) -> None:
        ref: dict[str, t.Any] = {
            "type": "reference",
            "uri": node.get("refuri", ""),
            "internal": node.get("internal", False),
        }
        if "refdomain" in node:
            ref["domain"] = node["refdomain"]
            ref["reftype"] = node.get("reftype", "")
        self._push(ref)

    def depart_reference(self, node: nodes.reference) -> None:
        self._pop()

    # --- Sphinx domain nodes ---

    def visit_desc(self, node: nodes.Element) -> None:
        """API object description (function, class, method, etc.)."""
        self._push({
            "type": "api_object",
            "domain": node.get("domain", ""),
            "objtype": node.get("objtype", ""),
            "noindex": node.get("noindex", False),
        })

    def depart_desc(self, node: nodes.Element) -> None:
        self._pop()

    def visit_desc_signature(self, node: nodes.Element) -> None:
        self._push({
            "type": "api_signature",
            "fullname": node.get("fullname", ""),
            "module": node.get("module", ""),
        })

    def depart_desc_signature(self, node: nodes.Element) -> None:
        self._pop()

    # --- Admonitions ---

    def visit_admonition(self, node: nodes.Element) -> None:
        classes = node.get("classes", [])
        kind = classes[0] if classes else "note"
        self._push({"type": "admonition", "kind": kind})

    def depart_admonition(self, node: nodes.Element) -> None:
        self._pop()

    # Map specific admonition types to generic handler
    visit_note = visit_admonition
    depart_note = depart_admonition
    visit_warning = visit_admonition
    depart_warning = depart_admonition
    visit_tip = visit_admonition
    depart_tip = depart_admonition
    visit_important = visit_admonition
    depart_important = depart_admonition

    # --- Fallback for unknown nodes ---

    def unknown_visit(self, node: nodes.Node) -> None:
        """Emit a generic node preserving type name. Never crash."""
        self._push({
            "type": node.__class__.__name__,
            "_unhandled": True,
        })

    def unknown_departure(self, node: nodes.Node) -> None:
        self._pop()

    # --- Helpers ---

    def _section_depth(self) -> int:
        depth = 0
        for frame in self._stack:
            for item in frame:
                if isinstance(item, dict) and item.get("type") == "section":
                    depth += 1
        return depth
```

### Complexity Warning

The translator's complexity is in **visitor state management**, not string formatting:
- Tables require tracking column spans and header/body state
- Nested lists require depth tracking
- Parameter lists require `required_params_left` / `optional_param_level` state
- Footnotes require collection and back-reference tracking

The output format changes from strings to dicts, but the state machine is comparable to `HTML5Translator`.

## The Astro Loader (`.doctrine/` Consumer)

```typescript
// @tony/docs-runtime/src/loaders/sphinx-doctrine-loader.ts
import { z } from 'astro/zod';
import type { Loader } from 'astro/loaders';
import * as fs from 'node:fs/promises';

export function sphinxDoctrineLoader(options: {
  doctrinePath: string;
}): Loader {
  return {
    name: 'sphinx-doctrine-loader',
    schema: z.object({
      docname: z.string(),
      title: z.string(),
      schema_version: z.number(),
      navigation: z.object({
        prev: z.any().nullable(),
        next: z.any().nullable(),
        parents: z.array(z.any()).optional(),
      }),
      toc: z.array(z.object({
        id: z.string(),
        text: z.string(),
        depth: z.number(),
      })),
      body: z.array(z.any()),
    }),
    async load(context) {
      const { store, parseData, logger } = context;
      const manifestRaw = await fs.readFile(
        `${options.doctrinePath}/manifest.json`,
        'utf-8',
      );
      const manifest = JSON.parse(manifestRaw);

      // Schema version compatibility check
      if (manifest.schema_version > 1) {
        logger.warn(
          `Doctrine schema v${manifest.schema_version} is newer than supported. ` +
          `Update @tony/docs-runtime.`,
        );
      }

      store.clear();
      for (const docname of manifest.pages) {
        const pageRaw = await fs.readFile(
          `${options.doctrinePath}/pages/${docname}.json`,
          'utf-8',
        );
        const page = JSON.parse(pageRaw);
        const data = await parseData({ id: docname, data: page });
        store.set({ id: docname, data });
      }

      logger.info(
        `Loaded ${manifest.pages.length} pages from ${options.doctrinePath}`,
      );
    },
  };
}
```

## Component-Driven Rendering (PortableText-style)

```astro
---
// src/components/sphinx/SphinxRenderer.astro
import Section from './Section.astro';
import ApiObject from './ApiObject.astro';
import CodeBlock from './CodeBlock.astro';
import CrossRef from './CrossRef.astro';
import Admonition from './Admonition.astro';
import Tab from './Tab.astro';
import Card from './Card.astro';
import UnknownNode from './UnknownNode.astro';

const componentMap: Record<string, any> = {
  section: Section,
  api_object: ApiObject,
  code_block: CodeBlock,
  cross_reference: CrossRef,
  admonition: Admonition,
  inline_tab: Tab,
  design_card: Card,
};

const { node } = Astro.props;
const Component = componentMap[node.type] || UnknownNode;
---
<Component {node} />
```

### ApiObject Component (Tailwind v4)

```astro
---
// src/components/sphinx/ApiObject.astro
const { node } = Astro.props;
const params = node.signature?.parameters ?? [];
const summary = node.docstring_sections?.find(
  (s: { kind: string }) => s.kind === 'summary'
);
---
<div class="not-prose border border-zinc-200 dark:border-zinc-700 rounded-lg overflow-hidden my-6">
  <div class="bg-zinc-50 dark:bg-zinc-800/50 px-4 py-3 border-b border-zinc-200 dark:border-zinc-700">
    <div class="flex items-center gap-2">
      <span class="text-xs font-medium uppercase tracking-wide text-violet-600 dark:text-violet-400">
        {node.objtype}
      </span>
      <code class="text-sm font-mono font-semibold text-zinc-900 dark:text-zinc-100">
        {node.fullname}
      </code>
    </div>
    {params.length > 0 && (
      <div class="mt-2 font-mono text-sm text-zinc-600 dark:text-zinc-400">
        ({params.map((p: any, i: number) => (
          <span>
            <span class="text-amber-600 dark:text-amber-400">{p.name}</span>
            {p.type && <span class="text-zinc-500">: {p.type}</span>}
            {p.default !== null && <span class="text-zinc-400"> = {p.default}</span>}
            {i < params.length - 1 && ', '}
          </span>
        ))})
        {node.signature?.returns && (
          <span class="text-zinc-500"> -&gt; {node.signature.returns.type}</span>
        )}
      </div>
    )}
  </div>
  {summary && (
    <div class="px-4 py-3 text-sm text-zinc-700 dark:text-zinc-300">
      {summary.text}
    </div>
  )}
</div>
```

Compare this to Furo, where `visit_desc()` emits `<dl>`, `visit_desc_signature()` emits `<dt>`, and SCSS styles those generic elements. With the DoctrineBuilder, the component can be anything -- a card, an interactive playground, a collapsible panel with source links.

## Testing Strategy: Golden Files

```python
# tests/test_translator.py
import json
import pathlib

import pytest


FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "basic_paragraphs",
        "code_blocks",
        "admonitions",
        "api_function",
        "api_class_with_methods",
        "cross_references",
        "nested_lists",
        "tables",
        "intersphinx_links",
    ],
)
def test_translator_output(fixture_name: str, tmp_path: pathlib.Path) -> None:
    """Compare translator output against known-good golden file."""
    # Build the fixture with sphinx-build -b doctrine
    source_dir = FIXTURES_DIR / fixture_name
    out_dir = tmp_path / "output"
    # ... run sphinx-build ...

    # Compare output against golden file
    actual = json.loads((out_dir / "pages" / "index.json").read_text())
    golden = json.loads((GOLDEN_DIR / f"{fixture_name}.json").read_text())

    assert actual == golden, f"Output differs from golden file for {fixture_name}"
```

Update golden files with `--update-golden` flag when translator behavior changes intentionally.

## Effort Estimate

| Component | Effort |
|---|---|
| Builder skeleton (subclass `Builder`) | 2-3 days |
| Core docutils node visitors (~60 of 100) | 3-4 weeks |
| `unknown_visit`/`unknown_departure` fallback | 1 day |
| Navigation, TOC, metadata export | 3-4 days |
| Asset copying | 1-2 days |
| Golden-file test suite | 3-4 days |
| **Total Phase 3** | **5-7 weeks** |

Extension-specific nodes (sphinx_design, sphinx_inline_tabs, Python domain) add another 2-3 weeks in Phase 4.

## Deliverables

- `sphinx-doctrine` Python package on PyPI
- DoctrineTranslator with ~60 core node type handlers
- `unknown_visit` fallback for graceful degradation
- `.doctrine/` output with `manifest.json`, page JSONs, `toctree.json`, `inventory.json`
- Schema versioning (v1)
- Golden-file test suite
- Astro loader (`sphinxDoctrineLoader`) with Zod validation
- SphinxRenderer component tree (~10-15 node-type components)
- Working rendering of vcspull docs via `.doctrine/` output

## Exit Gate

Expand to Phase 4 only if the prototype proves both value (solves real Phase 2 blockers) and maintainability (builder updates do not block Sphinx upgrades across 14 projects).
