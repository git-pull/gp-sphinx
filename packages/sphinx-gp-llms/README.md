# sphinx-gp-llms

LLM-friendly documentation outputs for Sphinx. Generates `llms.txt`,
`llms-full.txt`, `docs.json`, and per-page `.md` twin files during the
standard HTML build, giving LLM agents machine-readable entry points to
your documentation.

Part of the [gp-sphinx](https://github.com/git-pull/gp-sphinx)
documentation platform.

## Install

```console
$ pip install sphinx-gp-llms
```

When you depend on gp-sphinx, this extension is already loaded — see
the [package docs page](https://gp-sphinx.git-pull.com/packages/sphinx-gp-llms/)
for the integration story. The full config-key reference is
auto-generated from the live `app.add_config_value()` registrations.

## Credits

The output formats follow conventions established by their respective
communities:

- **`llms.txt`** — proposed by Jeremy Howard
  ([Answer.AI](https://www.answer.ai/)), September 2024.
  Specification at [llmstxt.org](https://llmstxt.org/).
- **`llms-full.txt`** — community convention adopted by Anthropic,
  Cloudflare, GitBook, Hugging Face, and others.
- **`docs.json`** — agent-manifest convention inspired by
  [Lakebed](https://docs.lakebed.dev/) (Ping,
  `github.com/pingdotgg/span`). See [A note on `docs.json`](#a-note-on-docsjson)
  below.
- **Per-page `.md` twins** — convention popularized by Cloudflare
  ("[Markdown for Agents](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/)"),
  Stripe, Anthropic, and Vercel.
- **Footer layout** (`Source: docs/page.md · Machine-readable:
  Markdown, raw source, docs.json, llms.txt, llms-full.txt`) —
  inspired by [docs.lakebed.dev](https://docs.lakebed.dev/).

## A note on `docs.json`

Sphinx already ships an inter-project linking mechanism:
[`objects.inv`](https://github.com/sphinx-doc/sphinx/blob/v9.1.0/sphinx/util/inventory.py#L43),
the inventory file that powers
[intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html).
It maps qualified names (classes, functions, config values) to URLs
across Sphinx sites. It is not, however, designed for LLM consumption
— the format is a compressed binary with a domain-specific schema
oriented toward cross-reference resolution, not content discovery.

`docs.json` fills a different role: a site-level beacon that tells
agents where the documentation lives, what pages exist, and how to
fetch them in Markdown. It carries `agentEntrypoints` (pointers to
`llms.txt`, `llms-full.txt`, and itself), a flat `pages[]` array with
per-page `markdownUrl` and `headings[]`, and the project's
`sourceRepository`.

There is no published specification for this format. We first noticed
the convention at [Lakebed](https://docs.lakebed.dev/)
(`github.com/pingdotgg/span`). Other documentation platforms also
emit a file named `docs.json`, but those are typically site-builder
configuration files (theme colors, navigation structure) closer to a
`manifest.json` than an agent-oriented content manifest.

## See also

- [sphinx-gp-sitemap](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-sitemap)
  — companion package for `sitemap.xml` emission
- [sphinx-gp-opengraph](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-gp-opengraph)
  — companion package for OpenGraph meta-tag emission
- [gp-sphinx](https://github.com/git-pull/gp-sphinx) — the umbrella
  docs platform; auto-derives `site_url` from a single `docs_url`
  argument
- [sphinx-gp-llms package page](https://gp-sphinx.git-pull.com/packages/sphinx-gp-llms/)
  — integration story, event hooks, and config reference
