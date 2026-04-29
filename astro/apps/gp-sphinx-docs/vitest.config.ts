import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    // happy-dom gives DOM tests (theme-toggle, future client-side helpers)
    // ``document`` / ``window.matchMedia`` / ``localStorage`` without paying
    // the jsdom cost. Pure-logic tests like nav-tree.test.ts run cleanly
    // here too.
    environment: 'happy-dom',
    typecheck: { enabled: true },
  },
})
