(sphinx-gp-llms-how-to)=

# How to

## Integration with gp-sphinx

`sphinx_gp_llms` ships in {py:data}`~gp_sphinx.defaults.DEFAULT_EXTENSIONS`,
so projects that build through {py:func}`~gp_sphinx.config.merge_sphinx_config`
load it automatically. Passing `docs_url=` to that function auto-derives
the URL input the extension needs:

| Auto-derived | Source |
| --- | --- |
| `site_url` | `docs_url`, normalized to end in `/` |

When {confval}`site_url` is unset, the extension logs at INFO and skips all
output — no broken builds.

## Output formats

### `llms.txt`

Structured Markdown index following the
[llmstxt.org](https://llmstxt.org/) specification (Jeremy Howard,
Answer.AI). The file gives LLM agents a curated entry point to
the site's content:

- **H1** — project name
- **Blockquote** — first paragraph of the root document
- **H2 sections** — one per {rst:dir}`sphinx:toctree` directive with a `:caption:`
  option; pages not in any captioned toctree fall into a
  "Documentation" section
- **Bulleted links** — `[Page Title](full URL): first-paragraph
  description` per page

### `llms-full.txt`

Concatenated full-content Markdown of every documentation page,
following the community convention adopted by Anthropic, Cloudflare,
and GitBook. Each page appears under a title header with
a source URL, separated by `---` dividers. Source files are included
as-is — MyST pages are already Markdown; RST pages are included
verbatim.

### `docs.json`

Agent-oriented manifest following the convention established by
Lakebed (Ping). The JSON file provides structured metadata for
machine consumption:

- `agentEntrypoints` — pointers to `/docs.json`, `/llms.txt`,
  `/llms-full.txt`
- `pages[]` — flat array with `title`, `description`, `section`,
  `url`, `markdownUrl`, and `headings[]` per page
- `sourceRepository` — read from `html_theme_options["source_repository"]`

### Per-page `.md` twins

Source file copies alongside each HTML page, following the
"Markdown for Agents" convention (Cloudflare, Stripe, Anthropic,
Vercel). Every HTML page at `/path/page.html` gets a sibling at
`/path/page.md` containing the original source content.

## How the outputs are built

All output files are generated at `build-finished` in the main
process, iterating {py:attr}`~sphinx.environment.BuildEnvironment.found_docs`
(the env-merged set of all
documented files). This means:

- **Incremental builds** produce complete output — no pages are
  missed because Sphinx only re-wrote a subset.
- **Parallel builds** (`sphinx-build -j N`) work correctly —
  `found_docs` is merged across workers before `build-finished` fires.
- **Non-HTML builders** (text, json, manpage) are skipped
  automatically — the handler checks for `get_target_uri`.

Footer link injection runs via `html-page-context`, adding template
variables (`llms_md_url`, `llms_txt_url`, etc.) only when the
corresponding `llms_generate_*` flag is `True`.

## Event hooks

```text
build-finished    →  _write_llm_outputs    (llms.txt, llms-full.txt,
                                            docs.json, .md twins)
html-page-context →  _inject_llms_context  (footer link variables)
```

Both live in
[`sphinx_gp_llms/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-llms/src/sphinx_gp_llms/__init__.py).

## Footer integration

When the extension is loaded and `site_url` is configured, the
page footer's "Machine-readable" line includes links to Markdown
(per-page `.md` twin), raw source (GitHub), docs.json, llms.txt,
and llms-full.txt. Each link appears only when its corresponding
output is enabled — disabling {confval}`llms_generate_json` removes the
docs.json link from the footer.

The footer renders LLM links independently of `source_repository`,
so projects that configure `docs_url` but not `source_repository`
still get the LLM output links.
