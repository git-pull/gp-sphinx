import type { FuroTokenName } from "./contract.js";

/**
 * Verbatim Furo dark-mode token *deltas* — only the entries `@mixin
 * colors-dark` in `_colors.scss` actually re-declares. Everything else
 * inherits the light value through CSS-variable cascade, just as in
 * upstream Furo.
 *
 * Emitted under `html[data-theme="dark"]` (and a `prefers-color-scheme`
 * fallback in `partials/_head_css_variables.html` when the user hasn't
 * chosen) — see `plugin.ts`.
 */
export const FURO_DARK_TOKENS: Readonly<Partial<Record<FuroTokenName, string>>> = {
  "--color-problematic": "#ee5151",

  "--color-foreground-primary": "#cfd0d0",
  "--color-foreground-secondary": "#9ca0a5",
  "--color-foreground-muted": "#81868d",
  "--color-foreground-border": "#666666",

  "--color-background-primary": "#131416",
  "--color-background-secondary": "#1a1c1e",
  "--color-background-hover": "#1e2124ff",
  "--color-background-hover--transparent": "#1e212400",
  "--color-background-border": "#303335",
  "--color-background-item": "#444",

  "--color-announcement-background": "#000000dd",
  "--color-announcement-text": "#eeebee",

  "--color-brand-primary": "#3d94ff",
  "--color-brand-content": "#5ca5ff",
  "--color-brand-visited": "#b27aeb",

  "--color-highlighted-background": "#083563",

  "--color-guilabel-background": "#08356380",
  "--color-guilabel-border": "#13395f80",

  "--color-api-keyword": "var(--color-foreground-secondary)",
  "--color-highlight-on-target": "#333300",

  "--color-api-added": "#3db854",
  "--color-api-added-border": "#267334",
  "--color-api-changed": "#09b0ce",
  "--color-api-changed-border": "#056d80",
  "--color-api-deprecated": "#b1a10b",
  "--color-api-deprecated-border": "#6e6407",
  "--color-api-removed": "#ff7575",
  "--color-api-removed-border": "#b03b3b",

  "--color-admonition-background": "#18181a",

  "--color-card-border": "var(--color-background-secondary)",
  "--color-card-background": "#18181a",
  "--color-card-marginals-background": "var(--color-background-hover)",
};
