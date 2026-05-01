import { describe, expect, it } from "vitest";

import { FURO_TOKEN_NAMES } from "../src/contract.js";
import { FURO_DARK_TOKENS } from "../src/dark.js";
import { FURO_LIGHT_TOKENS } from "../src/light.js";
import furoTokensPlugin from "../src/plugin.js";

type AddBaseArg = Record<string, Record<string, string>>;

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

describe("plugin", () => {
  it("emits a :root rule covering every contract token with a non-empty value", () => {
    const rules = runPlugin();
    expect(rules).toHaveLength(1);
    const root = rules[0]?.[":root"];
    expect(root, ":root rule missing").toBeDefined();
    if (!root) return;

    const expected = FURO_TOKEN_NAMES.filter((name) => FURO_LIGHT_TOKENS[name] !== "").sort();
    const got = Object.keys(root).sort();
    expect(got).toEqual(expected);
  });

  it("emits an html[data-theme='dark'] rule for every dark delta", () => {
    const rules = runPlugin();
    const dark = rules[0]?.['html[data-theme="dark"]'];
    expect(dark, "dark rule missing").toBeDefined();
    if (!dark) return;

    const expected = Object.keys(FURO_DARK_TOKENS)
      .filter((name) => (FURO_DARK_TOKENS as Record<string, string | undefined>)[name] !== "")
      .sort();
    expect(Object.keys(dark).sort()).toEqual(expected);
  });

  it("preserves Furo's value verbatim — no normalization", () => {
    const rules = runPlugin();
    const root = rules[0]?.[":root"];
    expect(root?.["--color-brand-primary"]).toBe("#0a4bff");
    expect(root?.["--color-foreground-primary"]).toBe("black");
    expect(root?.["--color-link"]).toBe("var(--color-brand-content)");
    expect(root?.["--color-sidebar-item-background--hover"]).toContain("linear-gradient(");
  });

  it("skips the --color-background-muted slot (Furo uses but never declares)", () => {
    const rules = runPlugin();
    const root = rules[0]?.[":root"];
    expect(root?.["--color-background-muted"]).toBeUndefined();
  });
});
