import { describe, expect, it } from "vitest";

import { FURO_TOKEN_NAMES } from "../src/contract.js";
import { FURO_DARK_TOKENS } from "../src/dark.js";
import { FURO_LIGHT_TOKENS } from "../src/light.js";
import furoTokensPlugin from "../src/plugin.js";

// addBase accepts nested CssInJs — at-rule keys (`@media (...)`) hold
// nested selector→declaration maps; selector keys hold flat
// declaration maps.  This mirrors what tailwindcss/plugin's runtime
// shape will hand to the compiler.
type Declarations = Record<string, string>;
type AddBaseArg = Record<string, Declarations | Record<string, Declarations>>;

interface CapturingApi {
  addBase: (rules: AddBaseArg) => void;
  rules: AddBaseArg[];
}

function makeCapturingApi(): CapturingApi {
  const rules: AddBaseArg[] = [];
  return {
    rules,
    addBase(this: CapturingApi, rule) {
      rules.push(rule);
    },
  };
}

function runPlugin(): AddBaseArg[] {
  const api = makeCapturingApi();
  // tailwindcss/plugin's return shape exposes a `handler` callback that
  // receives the PluginAPI. We're only exercising the addBase path here, so
  // a lightweight stand-in is enough to assert what would land in :root.
  // biome-ignore lint/suspicious/noExplicitAny: standing in for PluginAPI in unit tests
  furoTokensPlugin.handler(api as any);
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

    const expected = FURO_TOKEN_NAMES.filter((name) => FURO_LIGHT_TOKENS[name] !== "").sort();
    const got = Object.keys(root).sort();
    expect(got).toEqual(expected);
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
