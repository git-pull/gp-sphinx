import type { PluginWithConfig } from "tailwindcss/plugin";
import { describe, expectTypeOf, it } from "vitest";
import type { z } from "zod";

import type { FuroTokenName, GpSphinxRoleName } from "../src/contract.js";
import {
  FURO_TOKEN_NAMES,
  FuroTokenNameSchema,
  GP_SPHINX_ROLE_NAMES,
  GpSphinxRoleNameSchema,
} from "../src/contract.js";
import { FURO_DARK_TOKENS } from "../src/dark.js";
import { FURO_LIGHT_TOKENS } from "../src/light.js";
import furoTokensPlugin from "../src/plugin.js";
import { GP_SPHINX_ROLE_TOKENS } from "../src/roles.js";

// The package's deliverable is a literal-union type. These assertions lock
// the three places that union lives — the `as const` tuple, the zod schema,
// and the token-map annotations — so they cannot drift apart silently. A
// runtime test cannot see any of these failures.

describe("contract types", () => {
  it("zod schema inference round-trips the tuple-derived union", () => {
    expectTypeOf<z.infer<typeof FuroTokenNameSchema>>().toEqualTypeOf<FuroTokenName>();
    expectTypeOf<z.infer<typeof GpSphinxRoleNameSchema>>().toEqualTypeOf<GpSphinxRoleName>();
  });

  it("exported unions stay literal, not widened to string", () => {
    expectTypeOf<FuroTokenName>().not.toEqualTypeOf<string>();
    expectTypeOf<GpSphinxRoleName>().not.toEqualTypeOf<string>();
    expectTypeOf<(typeof FURO_TOKEN_NAMES)[number]>().toEqualTypeOf<FuroTokenName>();
    expectTypeOf<(typeof GP_SPHINX_ROLE_NAMES)[number]>().toEqualTypeOf<GpSphinxRoleName>();
  });
});

describe("token map types", () => {
  it("light map is exhaustive over the contract", () => {
    expectTypeOf(FURO_LIGHT_TOKENS).toEqualTypeOf<Readonly<Record<FuroTokenName, string>>>();
  });

  it("dark map is a partial delta, never widened to full coverage", () => {
    expectTypeOf(FURO_DARK_TOKENS).toEqualTypeOf<
      Readonly<Partial<Record<FuroTokenName, string>>>
    >();
  });

  it("role map is exhaustive over the role contract", () => {
    expectTypeOf(GP_SPHINX_ROLE_TOKENS).toEqualTypeOf<
      Readonly<Record<GpSphinxRoleName, string>>
    >();
  });
});

describe("plugin types", () => {
  it("default export conforms to Tailwind's plugin contract", () => {
    expectTypeOf(furoTokensPlugin).toEqualTypeOf<PluginWithConfig>();
  });
});
