/**
 * @vitest-environment happy-dom
 *
 * Tests for the code-copy module.
 *
 * The Pydantic→Zod renderer emits each fenced code block as
 * ``<pre><code class="language-foo">…</code></pre>``; this module
 * walks the rendered DOM and decorates each ``<pre>`` with a copy
 * button that writes the code to the clipboard. The pure function
 * lets us test the walking + idempotency + clipboard contract
 * without a real browser.
 */

import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { enhanceCodeBlocks } from '../../src/lib/code-copy.ts'

let writeText: ReturnType<typeof vi.fn>

function installClipboardMock(): void {
  writeText = vi.fn(() => Promise.resolve())
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText },
  })
}

function makePre(language: string, code: string): HTMLPreElement {
  const pre = document.createElement('pre')
  const codeEl = document.createElement('code')
  codeEl.className = `language-${language}`
  codeEl.textContent = code
  pre.appendChild(codeEl)
  return pre
}

beforeEach(() => {
  while (document.body.firstChild !== null) {
    document.body.removeChild(document.body.firstChild)
  }
  installClipboardMock()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('enhanceCodeBlocks — placement', () => {
  test('adds one copy button per <pre> in the root', () => {
    const root = document.createElement('div')
    root.appendChild(makePre('python', 'print("a")'))
    root.appendChild(makePre('typescript', 'const x = 1'))
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    const buttons = root.querySelectorAll('[data-test-id="code-copy"]')
    expect(buttons.length).toBe(2)
  })

  test('marks the host <pre> with data-code-copy-enhanced for idempotency', () => {
    const root = document.createElement('div')
    const pre = makePre('python', 'print("a")')
    root.appendChild(pre)
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    expect(pre.getAttribute('data-code-copy-enhanced')).toBe('true')
  })

  test('is idempotent when called twice on the same root', () => {
    const root = document.createElement('div')
    root.appendChild(makePre('python', 'print("a")'))
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    enhanceCodeBlocks(root)
    expect(root.querySelectorAll('[data-test-id="code-copy"]').length).toBe(1)
  })

  test('skips <pre> elements without a <code> child', () => {
    const root = document.createElement('div')
    const lone = document.createElement('pre')
    lone.textContent = 'plain text without a code element'
    root.appendChild(lone)
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    expect(root.querySelectorAll('[data-test-id="code-copy"]').length).toBe(0)
  })
})

describe('enhanceCodeBlocks — copy behaviour', () => {
  test('clicking the button writes the <code> textContent to the clipboard', async () => {
    const root = document.createElement('div')
    root.appendChild(makePre('python', 'print("hello, world")'))
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    const button = root.querySelector<HTMLButtonElement>(
      '[data-test-id="code-copy"]',
    )
    expect(button).not.toBeNull()
    button?.click()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalledOnce()
    expect(writeText).toHaveBeenCalledWith('print("hello, world")')
  })

  test('flips the button into a copied state after a successful write', async () => {
    const root = document.createElement('div')
    root.appendChild(makePre('python', 'a = 1'))
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    const button = root.querySelector<HTMLButtonElement>(
      '[data-test-id="code-copy"]',
    )
    expect(button?.getAttribute('data-state')).toBe('idle')
    button?.click()
    await Promise.resolve()
    await Promise.resolve()
    expect(button?.getAttribute('data-state')).toBe('copied')
  })
})
