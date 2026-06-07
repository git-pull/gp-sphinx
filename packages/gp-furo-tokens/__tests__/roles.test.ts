import { describe, expect, it } from "vitest";
import { z } from "zod";

import {
  GP_SPHINX_ROLE_NAMES,
  GpSphinxRoleMapSchema,
  GpSphinxRoleNameSchema,
} from "../src/contract.js";
import { GP_SPHINX_ROLE_TOKENS } from "../src/roles.js";

const roleNames = new Set<string>(GP_SPHINX_ROLE_NAMES);

describe("gp-sphinx role contract", () => {
  it("declares a string for every role name", () => {
    const missing = GP_SPHINX_ROLE_NAMES.filter(
      (name) => !(name in GP_SPHINX_ROLE_TOKENS),
    ).sort();
    expect(missing, `${missing.length} role names missing values`).toEqual([]);
  });

  it("does not declare values for names not in the role contract", () => {
    const extra = Object.keys(GP_SPHINX_ROLE_TOKENS)
      .filter((name) => !roleNames.has(name))
      .sort();
    expect(extra, `${extra.length} role keys not in GP_SPHINX_ROLE_NAMES`).toEqual([]);
  });

  it("emits names that match the gp-sphinx-type-* convention", () => {
    for (const name of GP_SPHINX_ROLE_NAMES) {
      expect(name).toMatch(/^--gp-sphinx-type-[a-z][a-z0-9-]*$/);
      expect(GpSphinxRoleNameSchema.safeParse(name).success).toBe(true);
    }
  });

  it("role map parses through the exhaustive role-map schema", () => {
    const result = GpSphinxRoleMapSchema.safeParse(GP_SPHINX_ROLE_TOKENS);
    expect(result.success, result.success ? "" : z.prettifyError(result.error)).toBe(true);
  });
});
