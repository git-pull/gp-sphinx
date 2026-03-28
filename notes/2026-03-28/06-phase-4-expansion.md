# Phase 4: Targeted Expansion

> [Back to Overview](00-overview.md) | Previous: [Phase 3 -- Semantic Export](05-phase-3-semantic-export.md) | Next: [Operational Concerns](07-operational-concerns.md)

**Duration**: Ongoing | **Risk**: Medium | **Status**: Selective -- add only where justified

## Principle

Do not pursue full ~152-node semantic coverage as a goal in itself. Add node types only when there is a renderer for them and a demonstrated user need.

---

## Extension Strategy

Classify each current extension by where it should live:

### Keep as Compiler-Only (stay in Sphinx)

These extensions do their work during Sphinx's parse/resolve phase. Their output becomes doctree nodes that the DoctrineTranslator handles. They do not need replacement.

| Extension | Role | Why Keep |
|---|---|---|
| `myst_parser` | Parses Markdown into doctree | Output IS the doctree |
| `sphinx.ext.intersphinx` | Resolves cross-project refs | Runs before builder |
| `sphinx.ext.autodoc` | Extracts API docs from code | Runs before builder |
| `sphinx_autodoc_typehints` | Adds type annotations | Modifies doctree |
| `sphinx.ext.napoleon` | Google/NumPy docstring support | Modifies doctree |
| `sphinx.ext.todo` | Todo directives | Standard node |
| `sphinx.ext.linkcode` | Source code links | Modifies doctree |
| `linkify_issues` | Issue reference links | Modifies doctree |

### Replace at Render Time (Astro components)

These extensions primarily provide **presentation behavior** that is better handled by modern frontend components.

| Extension | Current Role | Astro Replacement |
|---|---|---|
| `sphinx_copybutton` | Adds copy button to code blocks | `<CodeBlock>` component with `navigator.clipboard.writeText()` |
| `sphinx_inline_tabs` | CSS/JS tabbed content | `<Tabs>` Astro component (Radix UI, Headless UI, or native) |
| `sphinx_fonts` (IBM Plex) | Self-hosted fonts via Fontsource CDN | Tailwind v4 `@theme` + `@font-face` declarations |
| `sphinxext.opengraph` | OG meta tags | Astro's built-in `<head>` management in layouts |
| `sphinxext.rediraffe` | Redirect management | `astro.config.mjs` `redirects` config |

### Reevaluate Per Need

These depend on whether the semantic export (Phase 3) exists and whether the HTML bridge is sufficient:

| Extension | Consideration |
|---|---|
| `sphinx_design` (cards, grids, badges) | If using Option B (HTML bridge), style with Tailwind. If using Option C, map to `<Card>`, `<Grid>` components. |
| `linkify_issues` | Simple link generation -- may work fine in HTML bridge. |

**Rule**: If Sphinx already solves it well at compile-time and Astro gains little, keep it in Sphinx.

---

## Python Domain Node Handling

The hardest translator work is Python domain nodes. These produce deeply nested structures:

```
desc
  desc_signature
    desc_annotation ("class", "def", "async")
    desc_addname ("vcspull.cli.")
    desc_name ("sync")
    desc_parameterlist
      desc_parameter
        desc_sig_name ("repo_terms")
        desc_sig_punctuation (":")
        desc_sig_name ("list[str]")
      desc_parameter
        desc_sig_name ("config")
        desc_sig_punctuation (":")
        ...
    desc_returns
      ...
  desc_content
    field_list (Parameters, Returns, etc.)
    paragraph (description text)
```

**Ref**: `~/study/python/sphinx/sphinx/writers/html5.py` -- the `visit_desc*` family of methods handles this hierarchy. Lines ~84-120 in the HTML5Translator.

The DoctrineTranslator needs to serialize this into structured data:

```json
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
    { "kind": "parameters", "entries": [
      { "name": "repo_terms", "type": "list[str]", "description": "Repository name patterns." }
    ]},
    { "kind": "returns", "type": "None", "description": "" }
  ]
}
```

**Estimated effort**: 1-2 weeks for the full Python domain translator. This is the single hardest component.

---

## Search Strategy

### Phase 1: Pagefind (ship immediately)

Pagefind indexes rendered HTML at build time. Zero configuration. Works across all Astro content collections.

```astro
---
// src/components/Search.astro
---
<div id="search" data-pagefind-ui></div>
<link href="/_pagefind/pagefind-ui.css" rel="stylesheet" />
<script src="/_pagefind/pagefind-ui.js" is:inline></script>
<script is:inline>
  new PagefindUI({
    element: '#search',
    showSubResults: true,
    showImages: false,
  });
</script>
```

This replaces Sphinx's `searchindex.js` entirely. Better relevance, faster, more features.

### Phase 2: Faceted Search with Orama (only with semantic export)

If `.doctrine/` output exists, build a structured search index at Astro build time:

```typescript
// src/search/build-index.ts
import { create, insertMultiple } from '@orama/orama';

const db = create({
  schema: {
    project: 'string',
    docname: 'string',
    title: 'string',
    objectType: 'string',    // 'function', 'class', 'module', 'page'
    domain: 'string',        // 'py', 'std', etc.
    fullname: 'string',      // 'vcspull.cli.sync.sync'
    summary: 'string',
    content: 'string',
  },
});
```

This enables:
```
Search: "sync"
Results:
  [function] vcspull.cli.sync.sync           (vcspull > CLI)
  [page]     Synchronization Guide            (vcspull > User Guide)
  [class]    libvcs.sync.git.GitSync          (libvcs > API)
  [method]   libtmux.Session.sync             (libtmux > API)
```

Filter by project, object type, domain. Impossible with Sphinx's stemmed-word `searchindex.js`.

**Do not build this before Pagefind proves insufficient.**

---

## Starlight Assessment

Astro's official docs framework, Starlight, is worth evaluating but is not a replacement for this architecture.

**What Starlight expects**: Markdown, MDX, or Markdoc input -- not Sphinx output.

**What Starlight does NOT handle**: Python domain semantics, intersphinx, autodoc, custom node types, multi-project aggregation.

**What is useful as reference**: Sidebar generation patterns, Pagefind integration, i18n architecture, responsive layout patterns, dark mode implementation.

Starlight's source can inform `@tony/docs-runtime` design without being a dependency.

---

## The 14-Project Monorepo Vision

Once Phase 3-4 mature, all 14 projects become content collections in a single Astro site:

```typescript
// src/content.config.ts
import { defineCollection } from 'astro:content';
import { sphinxDoctrineLoader } from '@tony/docs-runtime';

export const collections = {
  vcspull:                   defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/vcspull/.doctrine' }) }),
  libtmux:                   defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/libtmux/.doctrine' }) }),
  libvcs:                    defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/libvcs/.doctrine' }) }),
  tmuxp:                     defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/tmuxp/.doctrine' }) }),
  'gp-libs':                 defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/gp-libs/.doctrine' }) }),
  g:                         defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/g/.doctrine' }) }),
  cihai:                     defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/cihai/.doctrine' }) }),
  'cihai-cli':               defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/cihai-cli/.doctrine' }) }),
  'unihan-etl':              defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/unihan-etl/.doctrine' }) }),
  'unihan-db':               defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/unihan-db/.doctrine' }) }),
  'django-docutils':         defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/django-docutils/.doctrine' }) }),
  'django-slugify-processor': defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/django-slugify-processor/.doctrine' }) }),
  'django-admin-vibe':       defineCollection({ loader: sphinxDoctrineLoader({ doctrinePath: '.artifacts/django-admin-vibe/.doctrine' }) }),
};
```

Cross-project references become **intra-site navigation**. vcspull's reference to `libvcs.sync.git.GitSync` is a local route transition with prefetching and shared layout state, instead of an external HTTP link.

---

## What Makes This Genuinely Novel

1. **Sphinx becomes a headless CMS.** It does what it is uniquely good at (Python semantic analysis, cross-referencing, autodoc) and nothing more.

2. **The `.doctrine/` format is a versioned public API.** Other tools can consume it -- VS Code extensions, CLIs, alternative renderers. The format is useful beyond "generating a website."

3. **Cross-project references become intra-site navigation.** All 14 projects in one Astro site with View Transitions.

4. **Furo's design decisions become optional, not structural.** Furo's CSS-only checkbox navigation, its BeautifulSoup HTML surgery, its SCSS pipeline -- all replaced by component props and Tailwind utilities. Keep the visual taste, discard the implementation constraints.

5. **Extensions stop being CSS/JS hacks and become components.** No more patching JS file loading. Tabs are a `<Tabs>` component. Copy buttons are a `<CodeBlock>` feature.
