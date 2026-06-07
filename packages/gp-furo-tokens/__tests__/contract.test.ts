import { describe, expect, it } from "vitest";
import { z } from "zod";

import furoVars from "../upstream/furo-vars.json" with { type: "json" };
import { FuroVarsSchema } from "../scripts/harvest-schema.ts";
import { FURO_TOKEN_NAMES, FuroTokenNameSchema } from "../src/contract.js";

const upstream = new Set<string>(furoVars.names);
const ours = new Set<string>(FURO_TOKEN_NAMES);

describe("contract", () => {
  it("ships a structurally valid harvest fixture", () => {
    const result = FuroVarsSchema.safeParse(furoVars);
    expect(result.success, result.success ? "" : z.prettifyError(result.error)).toBe(true);
  });

  it("exports every CSS custom property Furo declares", () => {
    const missing = [...upstream].filter((name) => !ours.has(name)).sort();
    expect(missing, `missing ${missing.length} tokens from FURO_TOKEN_NAMES`).toEqual([]);
  });

  it("does not invent CSS custom properties Furo does not declare", () => {
    const extra = [...ours].filter((name) => !upstream.has(name)).sort();
    expect(extra, `${extra.length} contract tokens not present in upstream Furo`).toEqual([]);
  });

  it("emits names that match the public custom-property naming pattern", () => {
    for (const name of FURO_TOKEN_NAMES) {
      expect(FuroTokenNameSchema.safeParse(name).success, `invalid name: ${name}`).toBe(true);
    }
  });
});
