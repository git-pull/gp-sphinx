import type { GpSphinxRoleName } from "./contract.js";

/**
 * gp-sphinx semantic type-role tokens.
 *
 * Defined as aliases of Furo's existing scale — no new pixel values, no
 * parallel scale — so the workspace gets a small named vocabulary
 * (`--gp-sphinx-type-body`, `--gp-sphinx-type-metadata`, ...) without
 * fighting Furo upstream. Future workspace CSS picks a role name; the
 * value stays traceable to one place.
 *
 * Emitted onto `body` alongside `FURO_LIGHT_TOKENS` so a downstream
 * consumer can override either Furo's tokens or these role aliases via
 * `html_theme_options["light_css_variables"]` and the override actually
 * shadows (descendants of body inherit body's value, not :root's).
 */
export const GP_SPHINX_ROLE_TOKENS: Readonly<Record<GpSphinxRoleName, string>> = {
  "--gp-sphinx-type-body": "var(--font-size--normal)",
  "--gp-sphinx-type-metadata": "var(--font-size--small)",
  "--gp-sphinx-type-code-inline": "var(--font-size--small--2)",
  "--gp-sphinx-type-icon-glyph": "0.625rem",
};
