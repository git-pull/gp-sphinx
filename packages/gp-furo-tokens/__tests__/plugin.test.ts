import type { PluginAPI } from "tailwindcss/plugin";
import { describe, expect, it } from "vitest";

import { FURO_TOKEN_NAMES, GP_SPHINX_ROLE_NAMES } from "../src/contract.js";
import { FURO_DARK_TOKENS } from "../src/dark.js";
import { FURO_LIGHT_TOKENS } from "../src/light.js";
import furoTokensPlugin from "../src/plugin.js";
import { GP_SPHINX_ROLE_TOKENS } from "../src/roles.js";

// Tailwind 4.3 exports PluginAPI from tailwindcss/plugin; CssInJs itself
// stays internal, so derive it from addBase's parameter. At-rule keys
// (`@media (...)`) hold nested selector→declaration maps; selector keys
// hold flat declaration maps.
type CssInJs = Parameters<PluginAPI["addBase"]>[0];
type Declarations = Record<string, string>;

// Partial<PluginAPI> keeps the capture cast-free at the call sites while
// staying assertable to the full PluginAPI below — we only exercise the
// addBase path here.
interface CapturingApi extends Partial<PluginAPI> {
  addBase: PluginAPI["addBase"];
  rules: CssInJs[];
}

function makeCapturingApi(): CapturingApi {
  const rules: CssInJs[] = [];
  return {
    rules,
    addBase(this: CapturingApi, rule) {
      rules.push(rule);
    },
  };
}

function runPlugin(): CssInJs[] {
  const api = makeCapturingApi();
  furoTokensPlugin.handler(api as PluginAPI);
  return api.rules;
}

function expectedDarkKeys(): string[] {
  return Object.keys(FURO_DARK_TOKENS)
    .filter((name) => (FURO_DARK_TOKENS as Record<string, string | undefined>)[name] !== "")
    .sort();
}

describe("plugin", () => {
  it("emits a body rule covering every contract token with a non-empty value", () => {
    const rules = runPlugin();
    expect(rules).toHaveLength(1);
    const root = rules[0]?.["body"] as Declarations | undefined;
    expect(root, "body rule missing").toBeDefined();
    if (!root) return;

    const expected = [
      ...FURO_TOKEN_NAMES.filter((name) => FURO_LIGHT_TOKENS[name] !== ""),
      ...GP_SPHINX_ROLE_NAMES.filter((name) => GP_SPHINX_ROLE_TOKENS[name] !== ""),
    ].sort();
    const got = Object.keys(root).sort();
    expect(got).toEqual(expected);
  });

  it("emits gp-sphinx role tokens on body alongside Furo's tokens", () => {
    const rules = runPlugin();
    const root = rules[0]?.["body"] as Declarations | undefined;
    expect(root?.["--gp-sphinx-type-body"]).toBe("var(--font-size--normal)");
    expect(root?.["--gp-sphinx-type-metadata"]).toBe("var(--font-size--small)");
    expect(root?.["--gp-sphinx-type-code-inline"]).toBe("var(--font-size--small--2)");
    expect(root?.["--gp-sphinx-type-icon-glyph"]).toBe("0.625rem");
  });

  it("emits a body[data-theme='dark'] rule for every dark delta", () => {
    const rules = runPlugin();
    const dark = rules[0]?.['body[data-theme="dark"]'] as Declarations | undefined;
    expect(dark, "body[data-theme='dark'] rule missing").toBeDefined();
    if (!dark) return;

    expect(Object.keys(dark).sort()).toEqual(expectedDarkKeys());
  });

  it("emits an OS-preference dark fallback respecting explicit `light` opt-out", () => {
    const rules = runPlugin();
    const media = rules[0]?.["@media (prefers-color-scheme: dark)"] as
      | Record<string, Declarations>
      | undefined;
    expect(media, "@media (prefers-color-scheme: dark) rule missing").toBeDefined();
    if (!media) return;

    const fallback = media['body:not([data-theme="light"])'];
    expect(fallback, "body:not([data-theme='light']) rule missing inside @media").toBeDefined();
    if (!fallback) return;

    expect(Object.keys(fallback).sort()).toEqual(expectedDarkKeys());
  });

  it("preserves Furo's value verbatim — no normalization", () => {
    const rules = runPlugin();
    const root = rules[0]?.["body"] as Declarations | undefined;
    expect(root?.["--color-brand-primary"]).toBe("#0a4bff");
    expect(root?.["--color-foreground-primary"]).toBe("black");
    expect(root?.["--color-link"]).toBe("var(--color-brand-content)");
    expect(root?.["--color-sidebar-item-background--hover"]).toContain("linear-gradient(");
  });

  it("skips the --color-background-muted slot (Furo uses but never declares)", () => {
    const rules = runPlugin();
    const root = rules[0]?.["body"] as Declarations | undefined;
    expect(root?.["--color-background-muted"]).toBeUndefined();
  });
});
