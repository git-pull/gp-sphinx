import plugin from "tailwindcss/plugin";

import { FURO_DARK_TOKENS } from "./dark.js";
import { FURO_LIGHT_TOKENS } from "./light.js";

/**
 * Convert a token map to a CSS rule body, skipping empty values.
 *
 * Furo references `--color-background-muted` but never declares it, so the
 * light table carries an empty string for that slot. Emitting
 * `--name: ;` is invalid CSS, and emitting a fallback value would diverge
 * from upstream byte-for-byte. Skip the slot and let the cascade fall back
 * to inherit/initial, exactly as Furo does.
 */
function declarations(
  tokens: Readonly<Record<string, string>> | Readonly<Partial<Record<string, string>>>,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [name, value] of Object.entries(tokens)) {
    if (typeof value === "string" && value !== "") {
      out[name] = value;
    }
  }
  return out;
}

/**
 * Tailwind v4 plugin emitting Furo's light + dark CSS custom-property
 * contract under three matched selectors:
 *
 * - `:root` for the light defaults
 * - `body[data-theme="dark"]` for explicit dark mode (set by furo.ts's
 *   theme-toggle button)
 * - `@media (prefers-color-scheme: dark) body:not([data-theme="light"])`
 *   for OS-preference dark mode that respects an explicit `light` opt-out
 *
 * The selectors mirror upstream Furo's `_theme.sass`
 * (`/home/d/study/python/furo/src/furo/assets/styles/base/_theme.sass`)
 * so behavioral parity holds across the toggle's three states (auto /
 * light / dark) and the cascade rules Furo's docstring contracts depend on.
 *
 * Apply via:
 *
 * ```css
 * @import "tailwindcss";
 * @plugin "@gp-sphinx/furo-tokens/plugin";
 * ```
 *
 * User overrides via Sphinx `html_theme_options["light_css_variables"]` /
 * `["dark_css_variables"]` are emitted by Furo's
 * `partials/_head_css_variables.html` template into a layer-less `:root` /
 * `body[data-theme="dark"]` block in `<head>`, which always wins over
 * Tailwind's `@layer theme` ordering.
 */
export default plugin((api) => {
  const darkDeclarations = declarations(FURO_DARK_TOKENS);
  api.addBase({
    ":root": declarations(FURO_LIGHT_TOKENS),
    'body[data-theme="dark"]': darkDeclarations,
    "@media (prefers-color-scheme: dark)": {
      'body:not([data-theme="light"])': darkDeclarations,
    },
  });
});
