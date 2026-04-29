/**
 * Theme toggle module.
 *
 * The site exposes three colour-scheme choices: explicit ``light``,
 * explicit ``dark``, and ``system`` (follow the OS preference). The
 * scheme is stored in ``localStorage`` and reflected onto
 * ``<html>`` via two attributes that the @theme block in
 * ``global.css`` consumes:
 *
 * - ``data-theme-mode`` — the *resolved* mode (always ``light`` or
 *   ``dark``); this is what the CSS @custom-variant matches.
 * - ``data-color-scheme`` — the *user choice* (``light`` / ``dark`` /
 *   ``system``); useful for the toggle button to know what icon to
 *   render and what to cycle to next.
 *
 * The split-mode design lets us re-resolve when the OS preference
 * changes mid-session while the user is still on ``system``.
 *
 * The pure helpers (``cycleScheme``, ``resolveEffectiveMode``,
 * ``readSavedScheme``) carry the logic; ``applyScheme`` and
 * ``initThemeToggle`` are the DOM-touching seams.
 */

const STORAGE_KEY = 'gp-sphinx:color-scheme'

export type ThemeScheme = 'light' | 'dark' | 'system'
export type EffectiveThemeMode = 'light' | 'dark'

const SCHEMES: readonly ThemeScheme[] = ['light', 'dark', 'system']

const NEXT: Record<ThemeScheme, ThemeScheme> = {
  light: 'dark',
  dark: 'system',
  system: 'light',
}

export function cycleScheme(current: ThemeScheme): ThemeScheme {
  return NEXT[current]
}

export function resolveEffectiveMode(
  scheme: ThemeScheme,
  prefersDark: boolean,
): EffectiveThemeMode {
  if (scheme === 'system') {
    return prefersDark ? 'dark' : 'light'
  }
  return scheme
}

function isThemeScheme(value: unknown): value is ThemeScheme {
  return typeof value === 'string' && (SCHEMES as readonly string[]).includes(value)
}

export function readSavedScheme(): ThemeScheme {
  const raw = localStorage.getItem(STORAGE_KEY)
  return isThemeScheme(raw) ? raw : 'system'
}

function persistScheme(scheme: ThemeScheme): void {
  localStorage.setItem(STORAGE_KEY, scheme)
}

function detectSystemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function applyScheme(scheme: ThemeScheme): void {
  const root = document.documentElement
  const mode = resolveEffectiveMode(scheme, detectSystemPrefersDark())
  root.setAttribute('data-theme-mode', mode)
  root.setAttribute('data-color-scheme', scheme)
}

export interface InitThemeToggleOptions {
  button: HTMLElement
  initial: ThemeScheme
}

export function initThemeToggle(options: InitThemeToggleOptions): void {
  const { button } = options
  let current = options.initial
  const reflect = (): void => {
    button.setAttribute('data-color-scheme', current)
  }
  reflect()
  button.addEventListener('click', () => {
    current = cycleScheme(current)
    applyScheme(current)
    persistScheme(current)
    reflect()
  })
}
