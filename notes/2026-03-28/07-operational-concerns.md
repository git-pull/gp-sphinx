# Operational Concerns

> [Back to Overview](00-overview.md) | Previous: [Phase 4 -- Expansion](06-phase-4-expansion.md)

Cross-cutting concerns that apply to all phases.

---

## CI/CD Model

### Production Builds

Each repository builds its docs artifact independently and publishes it. The Astro portal consumes those artifacts and rebuilds.

```
[libvcs merges PR]
    -> CI runs sphinx-build -b json (or -b doctrine)
    -> Zips output, uploads as release artifact
    -> Fires repository_dispatch webhook to docs-portal repo
    -> Docs portal fetches latest artifacts from all 14 projects
    -> Astro build produces static site
    -> Deploy to hosting (Cloudflare Pages, Vercel, Netlify)
```

### PR Preview Environments

A webhook portal build is useless for reviewing PRs. When a developer changes docs in `libvcs`, they need a preview of the **integrated** Astro site with their changes.

**Approach**: The project CI uploads the PR's docs artifact to a temporary location, then triggers a portal preview build that substitutes that project's artifact while keeping all other projects at their latest stable version.

If the PR preview experience degrades materially, developer adoption will fail. This is a hard requirement, not a nice-to-have.

### Build Times

The two-stage pipeline (Sphinx then Astro) adds latency:
- Sphinx build: typically 10-30 seconds per project
- Astro build: depends on total page count across all projects
- Total portal build: potentially 2-5 minutes with 14 projects

Optimize by:
- Caching Sphinx environments between builds
- Only rebuilding changed projects (stale artifacts are reused)
- Parallel artifact fetching

---

## Failure Isolation

One project's broken docs build must never block the entire portal.

**Rules**:
1. The portal always builds from the **latest valid artifact** for each project
2. If a project's latest artifact is missing or malformed, the portal uses the last-known-good version (cached in the portal repo)
3. Failed projects are flagged in a status dashboard, not in the portal build
4. Cross-project reference failures (broken intersphinx links) are warnings, not errors

**Implementation**: The artifact fetching script tries to download the latest artifact for each project. On failure, it falls through to the cached version:

```bash
#!/bin/bash
# scripts/fetch-docs-artifacts.sh
PROJECTS=(vcspull libtmux libvcs tmuxp gp-libs g cihai cihai-cli unihan-etl unihan-db django-docutils django-slugify-processor django-admin-vibe)

for project in "${PROJECTS[@]}"; do
  echo "Fetching $project..."
  if ! gh release download latest \
      --repo "tony/$project" \
      --pattern "docs-*.zip" \
      --dir ".artifacts/$project/" 2>/dev/null; then
    echo "  [WARN] Using cached artifact for $project"
  fi
done
```

---

## Local Authoring Workflow

Writers must still be able to:
- Edit docs locally and preview changes quickly
- Debug broken references
- Understand build failures without learning a new platform stack

### For Phase 0 (shared Sphinx only)

No change. `uv run sphinx-build -b html docs/ docs/_build/html` works as before.

### For Phase 1+ (Astro bridge)

Two-stage local dev:

```bash
# Terminal 1: Watch Sphinx docs (rebuilds on .rst/.md changes)
cd ~/work/python/vcspull
uv run sphinx-build -b json docs/ docs/_build/json

# Terminal 2: Astro dev server (hot-reloads on JSON changes)
cd ~/work/python/docs-portal
npm run dev
```

Astro's dev server watches content directories. When Sphinx rebuilds JSON output, Astro picks up the change.

**Key metric**: Local rebuild cycle should be < 5 seconds end-to-end. If it is materially slower than `sphinx-build -b html`, adoption will suffer.

---

## URL Compatibility

If routes change, redirects must be explicitly planned. This affects:

- **Existing inbound links** from external sites, blog posts, Stack Overflow answers
- **Intersphinx consumers** (other projects linking to your docs via `objects.inv`)
- **Search engine indexing** (Google, DuckDuckGo)
- **README and CHANGES file references** across all 14 repos

### Strategy

1. **Preserve routes where possible.** Map Sphinx's `docs/cli/sync.html` to Astro's `/vcspull/cli/sync/`.
2. **Generate `objects.inv`** from the Astro site so external intersphinx consumers still work. The DoctrineBuilder (Phase 3) can export `inventory.json`; a build step converts it to standard `objects.inv` format.
3. **Redirect rules** for any route changes, configured in `astro.config.mjs` or hosting platform.

---

## Ownership

A custom builder (Phase 3) is a **product**, not a script. It requires named ownership of:

| Responsibility | What It Means |
|---|---|
| **Schema versioning** | Breaking changes to `.doctrine/` format need migration plans |
| **Sphinx compatibility** | Test against Sphinx releases (major + minor) before upgrading across 14 projects |
| **Docutils compatibility** | Node types can change across docutils versions |
| **Extension coverage** | Each extension's custom nodes need explicit translator support |
| **Regression testing** | Golden-file test suite must be maintained and updated |
| **Upgrade policy** | Clear process for when/how to update the translator |

**If there is no appetite to own this, stop at Option B (Phase 1-2).**

---

## Astro 6 / Node 22+ Requirement

Astro 6 requires Node 22+. This affects CI/CD pipeline configuration:

```yaml
# All Astro-related CI jobs need:
- uses: actions/setup-node@v4
  with:
    node-version: 22
```

Ensure all contributors have Node 22+ available locally. Consider adding an `.nvmrc` or `package.json` `engines` field:

```json
{
  "engines": {
    "node": ">=22"
  }
}
```

---

## Cost Summary

| Concern | Phase 0 Impact | Phase 1-2 Impact | Phase 3+ Impact |
|---|---|---|---|
| CI/CD | None | Artifact pipeline + webhooks | + PR previews |
| Local dev | None | Two-stage build | Same |
| URL compat | None | Route mapping needed | + `objects.inv` generation |
| Failure isolation | N/A | Artifact caching | Same |
| Ownership | Low (shared config package) | Medium (Astro runtime) | High (builder + schema) |
| Node.js dependency | None | Astro requires Node 22+ | Same |
