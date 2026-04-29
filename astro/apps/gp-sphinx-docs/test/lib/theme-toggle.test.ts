/**
 * @vitest-environment happy-dom
 *
 * Tests for the theme-toggle module.
 *
 * The module is split into pure helpers + a small DOM-touching driver
 * so the bulk of the logic is unit-testable without a real browser.
 * happy-dom gives us ``document``, ``window.matchMedia``, and
 * ``localStorage`` for the DOM-touching parts.
 */

import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import {
  type ThemeScheme,
  applyScheme,
  cycleScheme,
  initThemeToggle,
  readSavedScheme,
  resolveEffectiveMode,
} from '../../src/lib/theme-toggle.ts'

const STORAGE_KEY = 'gp-sphinx:color-scheme'

// Node 24 ships its own ``localStorage`` that shadows happy-dom's
// implementation and exposes only get/setItem; ``clear`` is missing.
// We swap in a deterministic Map-backed mock for these tests.
function installLocalStorageMock(): void {
  const store = new Map<string, string>()
  const mock = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, String(value))
    },
    removeItem: (key: string) => {
      store.delete(key)
    },
    clear: () => {
      store.clear()
    },
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size
    },
  }
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: mock,
  })
}

beforeEach(() => {
  installLocalStorageMock()
  document.documentElement.removeAttribute('data-theme-mode')
  document.documentElement.removeAttribute('data-color-scheme')
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('cycleScheme', () => {
  test('cycles light → dark → system → light', () => {
    expect(cycleScheme('light')).toBe('dark')
    expect(cycleScheme('dark')).toBe('system')
    expect(cycleScheme('system')).toBe('light')
  })
})

describe('resolveEffectiveMode', () => {
  test('returns the literal mode for explicit light or dark', () => {
    expect(resolveEffectiveMode('light', false)).toBe('light')
    expect(resolveEffectiveMode('dark', true)).toBe('dark')
  })

  test('falls back to OS preference when scheme is system', () => {
    expect(resolveEffectiveMode('system', true)).toBe('dark')
    expect(resolveEffectiveMode('system', false)).toBe('light')
  })
})

describe('applyScheme', () => {
  test('writes the resolved theme-mode and stores the scheme attribute', () => {
    applyScheme('dark')
    expect(document.documentElement.getAttribute('data-theme-mode')).toBe('dark')
    expect(document.documentElement.getAttribute('data-color-scheme')).toBe('dark')
  })

  test('uses the OS preference when the scheme is system', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation((query) =>
      ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
      }) as unknown as MediaQueryList,
    )
    applyScheme('system')
    expect(document.documentElement.getAttribute('data-theme-mode')).toBe('dark')
    expect(document.documentElement.getAttribute('data-color-scheme')).toBe('system')
  })
})

describe('readSavedScheme', () => {
  test('returns the persisted scheme when present and valid', () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    expect(readSavedScheme()).toBe('dark')
  })

  test('returns "system" when nothing is stored', () => {
    expect(readSavedScheme()).toBe('system')
  })

  test('returns "system" when the stored value is invalid', () => {
    localStorage.setItem(STORAGE_KEY, 'rainbow')
    expect(readSavedScheme()).toBe('system')
  })
})

describe('initThemeToggle', () => {
  test('attaches a click handler that cycles + persists + reflects', () => {
    const button = document.createElement('button')
    button.setAttribute('data-test-id', 'theme-toggle')
    document.body.appendChild(button)
    const initial: ThemeScheme = 'light'
    applyScheme(initial)
    initThemeToggle({ button, initial })
    button.click()
    expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
    expect(document.documentElement.getAttribute('data-color-scheme')).toBe('dark')
    button.click()
    expect(localStorage.getItem(STORAGE_KEY)).toBe('system')
    expect(document.documentElement.getAttribute('data-color-scheme')).toBe('system')
  })

  test('updates the button label to reflect the active scheme', () => {
    const button = document.createElement('button')
    document.body.appendChild(button)
    initThemeToggle({ button, initial: 'light' })
    expect(button.getAttribute('data-color-scheme')).toBe('light')
    button.click()
    expect(button.getAttribute('data-color-scheme')).toBe('dark')
  })
})
