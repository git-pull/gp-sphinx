# The Doctrine Graph: A Practical Path to Sphinx-Compiled, Astro-Rendered Python Docs

> Research notes from a multi-model brainstorm-and-refine session (2026-03-28).
> 9 originals (Claude, Gemini, GPT x 3 variants), 3 refinement passes.
>
> Phase docs: [Furo Analysis](01-furo-analysis.md) | [Phase 0](02-phase-0-shared-platform.md) | [Phase 1](03-phase-1-astro-bridge.md) | [Phase 2](04-phase-2-multi-project.md) | [Phase 3](05-phase-3-semantic-export.md) | [Phase 4](06-phase-4-expansion.md) | [Operations](07-operational-concerns.md)

## The Actual Problem

The core problem is not Furo.

The core problem is that the docs platform is duplicated across 14+ repositories. The same extension stack, the same `conf.py` patterns, the same theme settings, the same JS workarounds (`tabs.js` removal, `spa-nav.js` injection), and the same maintenance burden are repeated everywhere.

**Affected repositories**: vcspull, libtmux, libvcs, tmuxp, gp-libs, g, django-admin-vibe, django-docutils, django-slugify-processor, cihai, cihai-cli, unihan-etl, unihan-db (and more).

That duplication is the first thing to fix. If a new rendering pipeline does not materially reduce platform duplication and maintenance cost, it is not a win.

## Working Thesis

Sphinx is already strong at the hard parts that are expensive to replace:

- Parsing reStructuredText and MyST
- Resolving Python cross-references across projects with intersphinx
- Extracting API docs from live Python objects with autodoc
- Building navigation and document relationships through `toctree`
- Managing inventories through `objects.inv`

Astro is better suited for the parts that are painful in Sphinx themes:

- Modern layout and component composition
- Shared design systems across multiple sites
- Client-side interactions and view transitions
- Faster frontend iteration with Tailwind CSS v4
- Better alignment with existing TypeScript projects (`tony.nl`, `tony.sh`, `cv`)

The practical goal is:

**Keep Sphinx as the documentation compiler. Move rendering to Astro only where the payoff is clear.**

This implies an incremental architecture, not a rewrite.

## Decision Principle

Use this rule before building new infrastructure:

**Prefer the simplest bridge that produces a shippable result. Only introduce a custom semantic format if existing Sphinx output is the proven bottleneck.**

---

## Architecture Options

### Option A: Standardize on Shared Sphinx + Furo

The fastest and lowest-risk option. See [Phase 0](02-phase-0-shared-platform.md).

**Deliverables**: Shared docs package (`gp_sphinx` on PyPI as `gp-sphinx`) with a `merge_sphinx_config()` API for per-project overrides, shared CI defaults, shared theme config, per-project `conf.py` reduced to minimal project metadata.

**Benefits**: Immediate maintenance reduction. No content migration. No custom builder. Low operational risk.

**Limits**: Still constrained by Sphinx theme architecture. Harder to share frontend patterns with TypeScript projects.

**Do this first regardless of any Astro decision.**

### Option B: Astro Renders Existing Sphinx Output

The best first experiment. See [Phase 1](03-phase-1-astro-bridge.md).

**Approach**: Build docs with Sphinx using an existing serializing builder, then load the output into Astro. The `JSONHTMLBuilder` from `sphinxcontrib-serializinghtml` (extracted from core Sphinx in 2.0) provides page-level JSON containing pre-rendered HTML fragments.

**Benefits**: Far lower complexity than a custom builder. Fastest way to validate whether Astro improves the frontend enough to matter. Keeps migration reversible.

**Limits**: Semantic structure flattened into HTML. Sphinx HTML fights with Tailwind (needs `rehype` sanitization). Rich API rendering harder.

**This is the recommended prototype path.** Cost: ~2-3 weeks.

### Option C: Custom Semantic Export (`.doctrine/`)

The most powerful option and the highest-maintenance one. See [Phase 3](05-phase-3-semantic-export.md).

**Approach**: A custom Sphinx builder (`sphinx-doctrine`) emits structured page data into a `.doctrine/` directory. Astro renders structured node types as components.

**Benefits**: Maximum rendering flexibility. Better API-specific components. Better structured search. No HTML/Tailwind collision.

**Costs**: Builder and schema must be maintained. Extension compatibility is your responsibility. Large regression surface.

**Only pursue this if Option B fails on real, recurring requirements.**

---

## Recommended Architecture: Three Packages

### Package 1: `gp_sphinx` (Python, PyPI: `gp-sphinx`)

Shared Sphinx platform for all repos. Exposes `merge_sphinx_config()` API so projects can override specific settings without abandoning the shared base. This is mandatory and ships first.

### Package 2: `@tony/docs-runtime` (TypeScript)

Astro integration layer. Content loaders for Sphinx output, shared layout and routing logic, search integration, cross-project URL rewriting. Supports both Option B and Option C so the migration remains reversible.

### Package 3: `@tony/docs-design` (CSS/TypeScript)

Pure presentation layer. Design tokens, typography, prose styling, navigation patterns. Tailwind CSS v4. Shared across docs and non-docs sites. Reuses existing Tailwind plugins from tony.nl and tony.sh.

---

## Decision Table

| Phase | Effort | Risk | Value | Gate |
|---|---:|---|---|---|
| Phase 0: `gp_sphinx` shared platform | 1-2 weeks | Very low | Immediate | Remove duplication |
| Phase 1: Astro bridge prototype | 2-3 weeks | Low-medium | High signal | Prove Astro value |
| Phase 2: Multi-project aggregation | 2-3 weeks | Medium | High | Prove operational model |
| Phase 3: Semantic export prototype | 5-7 weeks | High | Conditional | Prove real blocker |
| Phase 4: Targeted expansion | Ongoing | Medium | Selective | Add only where justified |

## Stop Conditions

Stop after Phase 0 if shared Sphinx eliminates enough pain.

Stop after Phase 1 if Astro does not provide a clearly better frontend and workflow.

Stop after Phase 2 if the HTML bridge is good enough.

Only continue to Phase 3 if there is a concrete, repeated limitation that semantic export resolves.

---

## What You Already Have

- Sphinx builder and translator infrastructure (stable API)
- Astro content loaders and Zod validation (Astro 6, requires Node 22+)
- Tailwind CSS v4 in existing TypeScript projects
- Existing Tailwind plugins in tony.nl and tony.sh
- 14 projects with near-identical Furo configs (perfect test corpus)
- IBM Plex fonts via Fontsource (trivially portable)

## What Success Looks Like

Success is not inventing a new docs architecture.

Success is:

- Shared docs infrastructure across repositories
- Less duplicated config and fewer repeated theme hacks
- One modern frontend surface across multiple Python projects
- Preserved Sphinx strengths: autodoc, intersphinx, domains
- Incremental migration with clear escape hatches
- No custom builder unless it proves necessary

## Core Recommendation

1. **Standardize the shared Sphinx platform.** (Phase 0 -- do this now)
2. **Prove Astro using existing Sphinx output.** (Phase 1 -- validate the frontend)
3. **Add semantic export only if simpler bridges fail on real requirements.** (Phase 3 -- earn the complexity)

That sequence ships value early, reduces maintenance immediately, and avoids committing to a custom docs compiler before it has earned its cost.

---

## Session Provenance

- **Method**: Multi-model brainstorm-and-refine (Claude Opus, Gemini 3.1 Pro, GPT 5.4)
- **Brainstorm**: 9 originals (3 models x 3 variants: Conventional, Creative, Contrarian)
- **Refinement**: 3 passes with role preambles (Maintainer, Skeptic, Builder)
- **Artifacts**: `/home/d/.local/state/ai-aip/repos/vcspull--6575d7c34abc/sessions/brainstorm-and-refine/20260328-161710Z-46812-ba6f/`
