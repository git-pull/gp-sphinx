/**
 * @vitest-environment happy-dom
 *
 * Tests for the global keyboard-shortcut module.
 *
 * The module recognises a small Vim-flavoured shortcut set:
 *   - ``g g`` → scroll the page to top
 *   - ``G`` (Shift+g) → scroll the page to bottom
 *   - ``?`` → focus the search input (if found)
 *
 * The pure ``ShortcutMatcher`` keeps the recent keystroke history so
 * we can test sequence detection without timers; the binder hooks
 * the matcher up to ``document.keydown`` and dispatches actions to
 * the host (scrollToTop, scrollToBottom, focusSearch).
 */

import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import {
  type ShortcutAction,
  ShortcutMatcher,
  initKeyboardShortcuts,
} from '../../src/lib/keyboard-shortcuts.ts'

describe('ShortcutMatcher', () => {
  test('returns "scroll-to-top" only after two consecutive "g" presses', () => {
    const matcher = new ShortcutMatcher({ sequenceWindowMs: 1_000_000 })
    expect(matcher.observe({ key: 'g' })).toBeNull()
    expect(matcher.observe({ key: 'g' })).toBe<ShortcutAction>('scroll-to-top')
  })

  test('resets the "g" prefix after a non-"g" keystroke', () => {
    const matcher = new ShortcutMatcher({ sequenceWindowMs: 1_000_000 })
    matcher.observe({ key: 'g' })
    matcher.observe({ key: 'a' })
    expect(matcher.observe({ key: 'g' })).toBeNull()
    expect(matcher.observe({ key: 'g' })).toBe<ShortcutAction>('scroll-to-top')
  })

  test('returns "scroll-to-bottom" on Shift+g', () => {
    const matcher = new ShortcutMatcher()
    expect(matcher.observe({ key: 'G', shiftKey: true })).toBe<ShortcutAction>(
      'scroll-to-bottom',
    )
  })

  test('returns "focus-search" on "?"', () => {
    const matcher = new ShortcutMatcher()
    expect(matcher.observe({ key: '?' })).toBe<ShortcutAction>('focus-search')
  })

  test('the "g g" prefix expires after sequenceWindowMs elapses', () => {
    let now = 0
    const matcher = new ShortcutMatcher({
      sequenceWindowMs: 100,
      now: () => now,
    })
    matcher.observe({ key: 'g' })
    now = 1000
    expect(matcher.observe({ key: 'g' })).toBeNull()
  })
})

describe('initKeyboardShortcuts', () => {
  let scrollToTop: ReturnType<typeof vi.fn>
  let scrollToBottom: ReturnType<typeof vi.fn>
  let focusSearch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    while (document.body.firstChild !== null) {
      document.body.removeChild(document.body.firstChild)
    }
    scrollToTop = vi.fn()
    scrollToBottom = vi.fn()
    focusSearch = vi.fn()
    initKeyboardShortcuts({ scrollToTop, scrollToBottom, focusSearch })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('``g g`` invokes scrollToTop once', () => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    expect(scrollToTop).toHaveBeenCalledOnce()
  })

  test('``G`` (Shift+g) invokes scrollToBottom once', () => {
    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'G', shiftKey: true }),
    )
    expect(scrollToBottom).toHaveBeenCalledOnce()
  })

  test('``?`` invokes focusSearch and cancels the keystroke', () => {
    const event = new KeyboardEvent('keydown', { key: '?', cancelable: true })
    document.dispatchEvent(event)
    expect(focusSearch).toHaveBeenCalledOnce()
    expect(event.defaultPrevented).toBe(true)
  })

  test('shortcuts are ignored when the user is typing in a text input', () => {
    const input = document.createElement('input')
    input.type = 'text'
    document.body.appendChild(input)
    input.focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'g' }))
    expect(scrollToTop).not.toHaveBeenCalled()
  })
})
