import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

/**
 * Vite configuration for the gp-furo-theme asset pipeline.
 *
 * Two entries — the strict-typed TS bundle and the pure Tailwind v4
 * CSS — map onto the filenames Sphinx loads via `theme.conf` and the
 * Python `_html_page_context` hook in `gp_furo_theme.__init__`:
 *   - `scripts/furo.js` is added by `app.add_js_file()`
 *   - `styles/furo-tw.css` is set as `stylesheet = ...` in `theme.conf`
 *
 * Filenames are deliberately not hashed — gp-furo-theme keeps Furo's
 * Python-side `?digest=<sha1>` cache-busting in `_html_page_context`,
 * and the Sphinx build pipeline references those names exactly.
 *
 * The SCSS pipeline (vendored Furo styles + sass + normalize.css) was
 * dropped in step 9.14 of the 2026-04-30 pivot — see plan section
 * "Pivot — 2026-04-30 — pure Tailwind v4 (no SASS)".
 */
export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: resolve(import.meta.dirname, "../src/gp_furo_theme/theme/gp-furo/static"),
    emptyOutDir: true,
    cssCodeSplit: true,
    assetsInlineLimit: 0,
    sourcemap: false,
    rollupOptions: {
      input: {
        "scripts/furo": resolve(import.meta.dirname, "src/scripts/furo.ts"),
        "styles/furo-tw": resolve(import.meta.dirname, "src/styles/index.css"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name][extname]",
      },
    },
  },
});
