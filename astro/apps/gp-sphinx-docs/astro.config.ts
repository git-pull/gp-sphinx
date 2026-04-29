import tailwindcss from '@tailwindcss/vite'
import { defineConfig, fontProviders } from 'astro/config'

// Astro 6 config for the gp-sphinx-docs dogfood site. The Sphinx pipeline
// (run by the `prebuild` script) writes content into ./src/content, schemas
// into ./schemas, and the canonical Astro collection wiring into
// ./src/content.config.ts before this config is loaded.
//
// Layout chrome (TopNav / Sidebar / Footer / TOC) is built on top of:
// - Tailwind v4 via @tailwindcss/vite (the legacy @astrojs/tailwind
//   integration is deprecated as of Astro 6).
// - The built-in Astro Fonts API serving IBM Plex Sans/Mono via Google,
//   exposed as CSS variables that the @theme block in global.css consumes.
export default defineConfig({
  site: 'https://gp-sphinx.git-pull.com',
  trailingSlash: 'always',
  vite: {
    plugins: [tailwindcss()],
  },
  fonts: [
    {
      provider: fontProviders.google(),
      name: 'IBM Plex Sans',
      cssVariable: '--font-sans',
      weights: [400, 500, 600, 700],
      styles: ['normal'],
      fallbacks: ['system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
    },
    {
      provider: fontProviders.google(),
      name: 'IBM Plex Mono',
      cssVariable: '--font-mono',
      weights: [400, 500, 600],
      styles: ['normal'],
      fallbacks: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
    },
  ],
})
