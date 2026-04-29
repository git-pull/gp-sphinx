/**
 * Global keyboard shortcuts for the dogfood site.
 *
 * Vim-flavoured navigation:
 *   - ``g g``  → scroll to top
 *   - ``G``    → scroll to bottom
 *   - ``?``    → focus search
 *
 * The ``/`` shortcut already lives in ``search-shortcut.ts``; this
 * module is for the rest of the keystroke vocabulary. Splitting them
 * keeps each module's tests focused (and lets the search module ship
 * standalone if a future page reuses it without the global set).
 *
 * The pure ``ShortcutMatcher`` carries the sequence state (the "did
 * we just see g?" prefix) so unit tests can drive sequences without a
 * timer; the binder is the seam that converts the matcher's actions
 * into actual side-effects on the host page.
 */

const SEQUENCE_WINDOW_MS_DEFAULT = 1500

export type ShortcutAction =
  | 'scroll-to-top'
  | 'scroll-to-bottom'
  | 'focus-search'

export interface ShortcutEvent {
  key: string
  shiftKey?: boolean
}

export interface ShortcutMatcherOptions {
  /** How long the ``g`` prefix stays armed before resetting. */
  sequenceWindowMs?: number
  /** Wall-clock source — overridable so tests don't need timers. */
  now?: () => number
}

const EDITABLE_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

function isEditableActive(): boolean {
  const active = document.activeElement
  if (active === null || !(active instanceof HTMLElement)) {
    return false
  }
  if (active.isContentEditable) {
    return true
  }
  return EDITABLE_TAGS.has(active.tagName)
}

export class ShortcutMatcher {
  private gArmedAt: number | null = null
  private readonly sequenceWindowMs: number
  private readonly now: () => number

  constructor(options: ShortcutMatcherOptions = {}) {
    this.sequenceWindowMs =
      options.sequenceWindowMs ?? SEQUENCE_WINDOW_MS_DEFAULT
    this.now = options.now ?? (() => Date.now())
  }

  observe(event: ShortcutEvent): ShortcutAction | null {
    if (event.key === '?') {
      this.gArmedAt = null
      return 'focus-search'
    }
    if (event.key === 'G' || (event.key === 'g' && event.shiftKey === true)) {
      this.gArmedAt = null
      return 'scroll-to-bottom'
    }
    if (event.key === 'g') {
      const t = this.now()
      const armed =
        this.gArmedAt !== null && t - this.gArmedAt <= this.sequenceWindowMs
      if (armed) {
        this.gArmedAt = null
        return 'scroll-to-top'
      }
      this.gArmedAt = t
      return null
    }
    // Any other key cancels the prefix.
    this.gArmedAt = null
    return null
  }
}

export interface ShortcutHandlers {
  scrollToTop: () => void
  scrollToBottom: () => void
  focusSearch: () => void
}

export function initKeyboardShortcuts(handlers: ShortcutHandlers): void {
  const matcher = new ShortcutMatcher()
  document.addEventListener('keydown', (event) => {
    if (isEditableActive()) {
      return
    }
    const action = matcher.observe({
      key: event.key,
      shiftKey: event.shiftKey,
    })
    if (action === null) {
      return
    }
    if (action === 'focus-search') {
      event.preventDefault()
      handlers.focusSearch()
      return
    }
    if (action === 'scroll-to-top') {
      handlers.scrollToTop()
      return
    }
    if (action === 'scroll-to-bottom') {
      handlers.scrollToBottom()
    }
  })
}
