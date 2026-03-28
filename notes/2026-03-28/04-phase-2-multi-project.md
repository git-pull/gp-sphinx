# Phase 2: Multi-Project Aggregation

> [Back to Overview](00-overview.md) | Previous: [Phase 1 -- Astro Bridge](03-phase-1-astro-bridge.md) | Next: [Phase 3 -- Semantic Export](05-phase-3-semantic-export.md)

**Duration**: 2-3 weeks | **Risk**: Medium | **Status**: Conditional on Phase 1 success

## Goal

Prove that an Astro-based docs portal can aggregate multiple Sphinx projects into a single site without coupling repositories too tightly.

Add 2-3 more projects (libvcs, libtmux, tmuxp) alongside vcspull from Phase 1.

## Multi-Project Content Collections

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
  libtmux: defineCollection({
    loader: sphinxJsonLoader({
      buildDir: '../libtmux/docs/_build/json',
      project: 'libtmux',
    }),
  }),
  libvcs: defineCollection({
    loader: sphinxJsonLoader({
      buildDir: '../libvcs/docs/_build/json',
      project: 'libvcs',
    }),
  }),
  tmuxp: defineCollection({
    loader: sphinxJsonLoader({
      buildDir: '../tmuxp/docs/_build/json',
      project: 'tmuxp',
    }),
  }),
};
```

For local development, these are relative paths. In CI/CD, they resolve to downloaded artifacts (see below).

## Cross-Project URL Rewriting

Intersphinx resolves cross-references to **external HTTP URLs** based on `objects.inv` files. When vcspull references `:py:class:\`libvcs.sync.git.GitSync\``, Sphinx resolves it to `https://libvcs.git-pull.com/sync/git.html#libvcs.sync.git.GitSync`.

To make these into intra-site navigation, we need URL rewriting. **This must be version-aware** -- intersphinx handles versions naturally; naive string replacement breaks if projects maintain multiple active versions.

```typescript
// src/utils/url-rewriter.ts

/**
 * Map of known external documentation domains to internal Astro route prefixes.
 * Version paths (e.g., /en/v1.2/) are preserved.
 */
const KNOWN_DOMAINS: Record<string, string> = {
  'vcspull.git-pull.com': '/vcspull',
  'libvcs.git-pull.com': '/libvcs',
  'libtmux.git-pull.com': '/libtmux',
  'tmuxp.git-pull.com': '/tmuxp',
  'gp-libs.git-pull.com': '/gp-libs',
  'cihai.git-pull.com': '/cihai',
  'cihai-cli.git-pull.com': '/cihai-cli',
  'unihan-etl.git-pull.com': '/unihan-etl',
  'unihan-db.git-pull.com': '/unihan-db',
  'g.git-pull.com': '/g',
  'django-docutils.git-pull.com': '/django-docutils',
  'django-slugify-processor.git-pull.com': '/django-slugify-processor',
  'django-admin-vibe.git-pull.com': '/django-admin-vibe',
};

export interface RewriteResult {
  href: string;
  isInternal: boolean;
  project?: string;
}

/**
 * Rewrite known external documentation URLs to internal Astro routes.
 *
 * Preserves version/locale path segments if present.
 * Falls through to external URL if domain is not recognized.
 */
export function rewriteSphinxUrl(url: string): RewriteResult {
  for (const [domain, prefix] of Object.entries(KNOWN_DOMAINS)) {
    const domainUrl = `https://${domain}/`;
    if (url.startsWith(domainUrl)) {
      const path = url.slice(domainUrl.length);
      // Preserve version paths like en/v1.2/...
      return {
        href: `${prefix}/${path}`,
        isInternal: true,
        project: domain.split('.')[0],
      };
    }
  }
  return { href: url, isInternal: false };
}
```

### Applying URL Rewriting to Sphinx HTML

Since Option B outputs pre-rendered HTML, URL rewriting happens as a `rehype` transform:

```typescript
// rehype-rewrite-sphinx-urls.ts
import type { Plugin } from 'unified';
import { visit } from 'unist-util-visit';
import { rewriteSphinxUrl } from '../utils/url-rewriter';

export const rehypeRewriteSphinxUrls: Plugin = () => (tree) => {
  visit(tree, 'element', (node) => {
    if (node.tagName === 'a' && node.properties?.href) {
      const result = rewriteSphinxUrl(String(node.properties.href));
      node.properties.href = result.href;
      if (result.isInternal) {
        // Mark for Astro View Transitions prefetching
        node.properties['data-astro-prefetch'] = '';
        node.properties['data-project'] = result.project;
      }
    }
  });
};
```

## CI/CD Orchestration

### Production Builds

Each repository builds its docs artifact independently:

```yaml
# .github/workflows/docs.yml (in each project repo)
name: Build Docs Artifact
on:
  push:
    branches: [master]
    paths: ['docs/**', 'src/**']

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync
      - run: uv run sphinx-build -b json docs/ docs/_build/json
      - uses: actions/upload-artifact@v4
        with:
          name: docs-json
          path: docs/_build/json/
      # Trigger portal rebuild
      - uses: peter-evans/repository-dispatch@v3
        with:
          repository: tony/docs-portal
          event-type: docs-updated
          client-payload: '{"project": "${{ github.repository }}"}'
```

### Portal Rebuild

The Astro docs portal fetches artifacts on rebuild:

```yaml
# .github/workflows/build.yml (in docs-portal repo)
name: Build Portal
on:
  repository_dispatch:
    types: [docs-updated]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22  # Required for Astro 6
      - run: npm ci
      # Download latest artifacts from each project
      - run: ./scripts/fetch-docs-artifacts.sh
      - run: npm run build
      - uses: actions/upload-pages-artifact@v4
        with:
          path: dist/
```

### PR Preview Environments

A webhook portal build is useless for reviewing PRs. When a developer changes docs in `libvcs`, they need a preview of the **integrated** Astro site with their specific changes.

**Approach**: Use Vercel/Netlify preview deploys. The project CI uploads the PR's docs artifact to a temporary location, then triggers a portal preview build that substitutes that project's artifact.

```yaml
# In each project repo
- name: Upload PR artifact
  if: github.event_name == 'pull_request'
  uses: actions/upload-artifact@v4
  with:
    name: docs-json-pr-${{ github.event.number }}
    path: docs/_build/json/

- name: Trigger preview
  if: github.event_name == 'pull_request'
  uses: peter-evans/repository-dispatch@v3
  with:
    repository: tony/docs-portal
    event-type: docs-preview
    client-payload: |
      {
        "project": "${{ github.repository }}",
        "pr": ${{ github.event.number }},
        "artifact": "docs-json-pr-${{ github.event.number }}"
      }
```

## Failure Isolation

One project's broken docs build should never block the entire portal.

**Rules**:
1. The portal always builds from the **latest valid artifact** for each project
2. If a project's artifact is missing or malformed, the portal uses the last-known-good version
3. Failed projects are flagged in a status dashboard, not in the portal build

```typescript
// scripts/fetch-docs-artifacts.ts
for (const project of PROJECTS) {
  try {
    await downloadLatestArtifact(project);
  } catch (error) {
    console.warn(`[${project}] Using cached artifact: ${error.message}`);
    // Fall through -- the cached version in the repo is used
  }
}
```

## Shared Design System

At this point, introduce `@tony/docs-design` as a shared design package:

- Tailwind v4 `@theme` with IBM Plex fonts, color system
- Shared page shell (sidebar, header, TOC, footer)
- Project switcher component
- Consistent responsive behavior
- Dark/light mode toggle

This package is shared across the portal and can be reused in tony.nl, tony.sh, and cv.

## Deliverables

- Aggregated Astro site with 3-4 projects
- Cross-project URL rewriting (version-aware)
- Artifact-based CI/CD flow with webhook triggers
- PR preview environments
- Failure isolation (last-known-good fallback)
- Shared design system (`@tony/docs-design`)
- Shared navigation across projects (project switcher)

## Success Criteria

- Repositories remain operationally decoupled
- Portal rebuilds are reliable (< 5 min)
- Cross-project navigation works without manual fixes
- PR previews are available within CI/CD flow
- Build and preview workflows remain understandable

## Exit Gate

Proceed to Phase 3 only if the aggregated model works but the flattened HTML bridge is **demonstrably** blocking important features. Common blockers that justify Phase 3:

- API pages need richer rendering than Sphinx HTML provides
- Search needs structured filtering by project, object type, or domain
- Sphinx HTML structure makes Tailwind styling impractical despite `rehype` sanitization
- Extension output (sphinx_design cards, tabs) cannot be meaningfully styled

If the HTML bridge is good enough, **stop here**.
