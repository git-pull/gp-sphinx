/**
 * @vitest-environment happy-dom
 *
 * Tests for the search keyboard-shortcut module.
 *
 * Pagefind ships its own default-UI Web Component; we wrap it with a
 * tiny shortcut handler so users can press ``/`` to jump to the
 * search input and ``Escape`` to dismiss focus. The pure function is
 * the testable seam — installing the listener and the focus dispatch
 * happens against any element (the Pagefind UI's hidden input in
 * production; a fixture ``<input>`` in tests).
 */

import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { initSearchShortcut } from '../../src/lib/search-shortcut.ts'

let input: HTMLInputElement
let other: HTMLDivElement

beforeEach(() => {
  while (document.body.firstChild !== null) {
    document.body.removeChild(document.body.firstChild)
  }
  input = document.createElement('input')
  input.setAttribute('data-test-id', 'search-input')
  other = document.createElement('div')
  other.tabIndex = 0
  document.body.appendChild(input)
  document.body.appendChild(other)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('initSearchShortcut', () => {
  test('focuses the input when "/" is pressed outside an editable target', () => {
    initSearchShortcut({ input })
    other.focus()
    const focusSpy = vi.spyOn(input, 'focus')
    const event = new KeyboardEvent('keydown', {
      key: '/',
      cancelable: true,
    })
    document.dispatchEvent(event)
    expect(focusSpy).toHaveBeenCalledOnce()
    expect(event.defaultPrevented).toBe(true)
  })

  test('ignores "/" when the user is already typing in the search input', () => {
    initSearchShortcut({ input })
    input.focus()
    const focusSpy = vi.spyOn(input, 'focus')
    const event = new KeyboardEvent('keydown', { key: '/', cancelable: true })
    document.dispatchEvent(event)
    expect(focusSpy).not.toHaveBeenCalled()
    expect(event.defaultPrevented).toBe(false)
  })

  test('ignores "/" when typing in any other text input', () => {
    initSearchShortcut({ input })
    const otherInput = document.createElement('textarea')
    document.body.appendChild(otherInput)
    otherInput.focus()
    const focusSpy = vi.spyOn(input, 'focus')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: '/' }))
    expect(focusSpy).not.toHaveBeenCalled()
  })

  test('Escape blurs the input when it currently holds focus', () => {
    initSearchShortcut({ input })
    input.focus()
    const blurSpy = vi.spyOn(input, 'blur')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(blurSpy).toHaveBeenCalledOnce()
  })

  test('Escape is a no-op when the search input is not focused', () => {
    initSearchShortcut({ input })
    other.focus()
    const blurSpy = vi.spyOn(input, 'blur')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(blurSpy).not.toHaveBeenCalled()
  })
})
