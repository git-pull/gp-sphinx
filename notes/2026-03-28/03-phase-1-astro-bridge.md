# Phase 1: Astro Bridge Prototype

> [Back to Overview](00-overview.md) | Previous: [Phase 0 -- Shared Platform](02-phase-0-shared-platform.md) | Next: [Phase 2 -- Multi-Project](04-phase-2-multi-project.md)

**Duration**: 2-3 weeks | **Risk**: Low-medium | **Status**: Recommended next step (after Phase 0)

## Goal

Prove that Astro provides a clearly better frontend for documentation than Sphinx HTML theming, using **existing** Sphinx output -- no custom builder required.

This phase answers: **Is Astro worth it at all?**

## Architecture: Option B

```
RST/MyST sources
    -> Sphinx (parse, resolve, autodoc, intersphinx)
    -> JSONHTMLBuilder (sphinxcontrib-serializinghtml)
    -> JSON files with pre-rendered HTML body fragments
    -> Astro content loader
    -> Astro site with Tailwind v4 + shared components
```

### Why `sphinxcontrib-serializinghtml`?

The `JSONHTMLBuilder` (extracted from core Sphinx in 2.0, now in the `sphinxcontrib-serializinghtml` package) outputs one JSON file per page containing:

```json
{
  "body": "<div class=\"section\" id=\"sync\">\n<h1>Sync Command...</h1>\n...",
  "title": "Sync Command",
  "toc": "<ul>\n<li><a href=\"#sync\">Sync Command</a></li>\n...</ul>",
  "parents": [{"link": "../", "title": "CLI Reference"}],
  "prev": {"link": "../", "title": "CLI Reference"},
  "next": {"link": "add/", "title": "Adding Repositories"},
  "meta": {},
  "current_page_name": "cli/sync"
}
```

This is already structured metadata + pre-rendered HTML body. No custom builder needed.

**Ref**: `~/study/python/sphinx/sphinx/builders/html/__init__.py` (the `SerializingHTMLBuilder` base class and `JSONHTMLBuilder` subclass).

## The HTML/Tailwind Collision Problem

Sphinx HTML output carries its own structural classes (`class="section"`, `class="admonition note"`, `class="highlight"`), wrapper divs, and sometimes inline styles. Dropping this raw into a Tailwind-styled Astro page causes conflicts.

**Solution**: Use `rehype` plugins in the Astro pipeline to sanitize Sphinx HTML:

```typescript
// rehype-strip-sphinx.ts
import type { Plugin } from 'unified';
import { visit } from 'unist-util-visit';

/**
 * Strip Sphinx-specific classes and wrappers that conflict with Tailwind.
 * Preserve semantic structure (admonition types, code language, etc.).
 */
export const rehypeStripSphinx: Plugin = () => (tree) => {
  visit(tree, 'element', (node) => {
    // Strip Sphinx wrapper divs that add no semantic value
    if (node.tagName === 'div' && node.properties?.className?.includes('section')) {
      // Unwrap: replace div.section with its children
      // Preserve the id attribute for anchor linking
    }

    // Normalize Sphinx admonition classes to data attributes
    // class="admonition note" -> data-admonition="note"
    if (node.properties?.className?.includes('admonition')) {
      const type = node.properties.className.find(
        (c: string) => c !== 'admonition'
      );
      node.properties['data-admonition'] = type;
      node.properties.className = [];  // Let Tailwind handle styling
    }

    // Strip Sphinx's inline styles on tables
    if (node.tagName === 'table') {
      delete node.properties.style;
    }
  });
};
```

## Astro Content Loader

```typescript
// src/loaders/sphinx-json-loader.ts
import { z } from 'astro/zod';
import type { Loader } from 'astro/loaders';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';

const sphinxPageSchema = z.object({
  body: z.string(),
  title: z.string(),
  toc: z.string(),
  current_page_name: z.string(),
  parents: z.array(z.object({
    link: z.string(),
    title: z.string(),
  })).optional(),
  prev: z.object({ link: z.string(), title: z.string() }).nullable(),
  next: z.object({ link: z.string(), title: z.string() }).nullable(),
});

export function sphinxJsonLoader(options: {
  buildDir: string;
  project: string;
}): Loader {
  return {
    name: 'sphinx-json-loader',
    schema: sphinxPageSchema,
    async load(context) {
      const { store, parseData, logger } = context;
      const globalsPath = path.join(options.buildDir, 'globalcontext.json');

      // Read Sphinx global context for project metadata
      let globals: Record<string, unknown> = {};
      try {
        globals = JSON.parse(await fs.readFile(globalsPath, 'utf-8'));
      } catch {
        logger.warn(`No globalcontext.json found in ${options.buildDir}`);
      }

      // Discover all page JSON files
      const pagesDir = options.buildDir;
      const files = await discoverJsonPages(pagesDir);

      store.clear();
      for (const file of files) {
        const raw = await fs.readFile(file, 'utf-8');
        const page = JSON.parse(raw);
        const docname = path.relative(pagesDir, file).replace('.fjson', '');
        const data = await parseData({ id: docname, data: page });
        store.set({ id: docname, data });
      }

      logger.info(`Loaded ${files.length} pages from ${options.project}`);
    },
  };
}

async function discoverJsonPages(dir: string): Promise<string[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true, recursive: true });
  return entries
    .filter(e => e.isFile() && e.name.endsWith('.fjson'))
    .map(e => path.join(e.parentPath ?? dir, e.name));
}
```

### Content Collection Config

```typescript
// src/content.config.ts
import { defineCollection } from 'astro:content';
import { sphinxJsonLoader } from './loaders/sphinx-json-loader';

export const collections = {
  vcspull: defineCollection({
    loader: sphinxJsonLoader({
      buildDir: '../vcspull/docs/_build/json',
      project: 'vcspull',
    }),
  }),
};
```

## Page Template

```astro
---
// src/pages/vcspull/[...slug].astro
import { getCollection } from 'astro:content';
import DocsLayout from '../../layouts/DocsLayout.astro';

export async function getStaticPaths() {
  const pages = await getCollection('vcspull');
  return pages.map(page => ({
    params: { slug: page.id },
    props: { page },
  }));
}

const { page } = Astro.props;
---

<DocsLayout
  title={page.data.title}
  toc={page.data.toc}
  prev={page.data.prev}
  next={page.data.next}
>
  <!-- Sphinx pre-rendered HTML, styled with Tailwind prose -->
  <article class="prose prose-zinc dark:prose-invert max-w-none" set:html={page.data.body} />
</DocsLayout>
```

## Pagefind Search

```astro
---
// src/components/Search.astro
---
<div id="search" data-pagefind-ui></div>
<link href="/_pagefind/pagefind-ui.css" rel="stylesheet" />
<script src="/_pagefind/pagefind-ui.js" is:inline></script>
<script is:inline>
  new PagefindUI({ element: '#search', showSubResults: true });
</script>
```

Pagefind indexes the rendered HTML at build time. Zero config. Works across all content collections. Replaces Sphinx's `searchindex.js` entirely.

## Local Dev Workflow

The two-stage build adds latency. For fast local iteration:

```bash
# Terminal 1: Watch Sphinx docs (rebuilds on .rst/.md changes)
cd vcspull && uv run sphinx-build -b json docs/ docs/_build/json --watch

# Terminal 2: Astro dev server (hot-reloads on Sphinx output changes)
cd docs-site && npm run dev
```

Astro's dev server watches the content directory. When Sphinx rebuilds JSON output, Astro picks up the change and hot-reloads.

## Deliverables

- Astro site consuming vcspull Sphinx JSON output
- `rehype` sanitization of Sphinx HTML classes
- Shared page shell with Tailwind v4 (sidebar, header, TOC)
- Pagefind search
- Preserved routes (matching existing URL structure)
- Basic local dev workflow (Sphinx watch + Astro dev)

## Success Criteria

- Frontend iteration is meaningfully faster than editing Jinja2/SCSS
- No major content regressions compared to Furo-rendered site
- Local preview is acceptable (< 5 second rebuild)
- The resulting site is clearly better than Sphinx-only Furo

## Exit Gate

Proceed to Phase 2 only if Astro creates clear value without degrading authoring or operations. If the bridge proves too limiting (e.g., Sphinx HTML structure makes Tailwind styling impractical), that is evidence for Phase 3 -- but not a reason to skip Phase 1.
