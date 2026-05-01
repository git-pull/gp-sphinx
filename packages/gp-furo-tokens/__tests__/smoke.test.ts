import { describe, expect, it } from "vitest";

import { FURO_TOKENS_VERSION } from "../src/index.js";

describe("smoke", () => {
  it("exports a version string", () => {
    expect(FURO_TOKENS_VERSION).toBeTypeOf("string");
    expect(FURO_TOKENS_VERSION.length).toBeGreaterThan(0);
  });
});
