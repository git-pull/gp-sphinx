import { defineConfig } from 'astro/config'

// Minimal Astro 6 config for the gp-sphinx-docs dogfood site. The Sphinx
// pipeline (run by the `prebuild` script) writes content into ./src/content,
// schemas into ./schemas, and the canonical Astro collection wiring into
// ./src/content.config.ts before this config is loaded.
export default defineConfig({
  site: 'https://gp-sphinx.git-pull.com',
  trailingSlash: 'always',
})
