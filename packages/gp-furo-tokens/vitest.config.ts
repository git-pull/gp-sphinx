import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["__tests__/**/*.test.ts"],
    environment: "node",
    typecheck: {
      enabled: true,
      include: ["__tests__/**/*.test-d.ts"],
    },
  },
});
