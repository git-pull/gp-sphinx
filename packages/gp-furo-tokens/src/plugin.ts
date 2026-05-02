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
 * - `body` for the light defaults
 * - `body[data-theme="dark"]` for explicit dark mode (set by furo.ts's
 *   theme-toggle button)
 * - `@media (prefers-color-scheme: dark) body:not([data-theme="light"])`
 *   for OS-preference dark mode that respects an explicit `light` opt-out
 *
 * The selectors mirror upstream Furo's `_theme.sass`
 * (`/home/d/study/python/furo/src/furo/assets/styles/base/_theme.sass`)
 * which emits via `body { @include colors }` (NOT `:root { @include colors }`).
 * The `body` choice is load-bearing for any token whose value is an alias —
 * e.g. `--color-content-foreground: var(--color-foreground-primary)` — because
 * CSS `var()` substitution is computed at the element where the custom property
 * is declared.  If the alias is declared at `:root` and the underlying token
 * is overridden at `body[data-theme="dark"]`, the alias's computed value stays
 * frozen at the `:root`-scope substitution and never picks up the dark value.
 * Co-locating both declarations at `body` lets every alias re-substitute when
 * its dependency changes via a more-specific body selector.
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
 * `partials/_head_css_variables.html` template into a layer-less `body` /
 * `body[data-theme="dark"]` block in `<head>`, which always wins over
 * Tailwind's `@layer base` ordering.
 */
export default plugin((api) => {
  const darkDeclarations = declarations(FURO_DARK_TOKENS);
  api.addBase({
    body: declarations(FURO_LIGHT_TOKENS),
    'body[data-theme="dark"]': darkDeclarations,
    "@media (prefers-color-scheme: dark)": {
      'body:not([data-theme="light"])': darkDeclarations,
    },
  });
});
