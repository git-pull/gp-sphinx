import { resolve } from "node:path";

import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

/**
 * Vite configuration for the gp-furo-theme asset pipeline.
 *
 * Three entries map onto upstream Furo's filename contract; output keys
 * carry the destination subdirectory inside the theme so the final layout
 * is `static/{scripts,styles}/...`.
 *
 * Filenames are deliberately not hashed — gp-furo-theme keeps Furo's
 * Python-side `?digest=<sha1>` cache-busting in `_html_page_context`, and
 * the Sphinx build pipeline references `furo.css`, `furo-extensions.css`,
 * and `furo.js` by exact name.
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
        "styles/furo": resolve(import.meta.dirname, "src/styles/furo.css"),
        "styles/furo-extensions": resolve(
          import.meta.dirname,
          "src/styles/furo-extensions.css",
        ),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name][extname]",
      },
    },
  },
});
