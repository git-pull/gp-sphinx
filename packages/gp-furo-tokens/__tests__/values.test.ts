import { describe, expect, it } from "vitest";

import { FURO_TOKEN_NAMES } from "../src/contract.js";
import { FURO_DARK_TOKENS } from "../src/dark.js";
import { FURO_LIGHT_TOKENS } from "../src/light.js";

const contractNames = new Set<string>(FURO_TOKEN_NAMES);

describe("light values", () => {
  it("declares a string for every contract token", () => {
    const missing = FURO_TOKEN_NAMES.filter((name) => !(name in FURO_LIGHT_TOKENS)).sort();
    expect(missing, `${missing.length} contract tokens are missing light values`).toEqual([]);
  });

  it("does not declare values for tokens not in the contract", () => {
    const extra = Object.keys(FURO_LIGHT_TOKENS)
      .filter((name) => !contractNames.has(name))
      .sort();
    expect(extra, `${extra.length} light keys not in FURO_TOKEN_NAMES`).toEqual([]);
  });
});

describe("dark deltas", () => {
  it("only overrides tokens that exist in the contract", () => {
    const extra = Object.keys(FURO_DARK_TOKENS)
      .filter((name) => !contractNames.has(name))
      .sort();
    expect(extra, `${extra.length} dark keys not in FURO_TOKEN_NAMES`).toEqual([]);
  });

  it("scopes to the colors that Furo's @mixin colors-dark actually re-declares", () => {
    // Sanity: dark deltas should be a small subset of the contract; if this
    // explodes someone has accidentally widened the cascade.
    const declared = Object.keys(FURO_DARK_TOKENS).length;
    expect(declared).toBeGreaterThan(20);
    expect(declared).toBeLessThan(40);
  });
});
