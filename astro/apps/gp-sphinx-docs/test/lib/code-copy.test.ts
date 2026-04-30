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
import { enhanceCodeBlocks, formatCopyText } from '../../src/lib/code-copy.ts'

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

  test('strips Python REPL prompts when copying a doctest block', async () => {
    const root = document.createElement('div')
    root.appendChild(
      makePre(
        'python',
        '>>> spec = BadgeSpec("config")\n>>> spec.text\n\'config\'',
      ),
    )
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    const button = root.querySelector<HTMLButtonElement>(
      '[data-test-id="code-copy"]',
    )
    button?.click()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalledWith(
      'spec = BadgeSpec("config")\nspec.text',
    )
  })

  test('strips shell ``$ `` prompts and skips output lines', async () => {
    const root = document.createElement('div')
    root.appendChild(
      makePre('console', '$ pip install gp-sphinx\nSuccessfully installed'),
    )
    document.body.appendChild(root)
    enhanceCodeBlocks(root)
    const button = root.querySelector<HTMLButtonElement>(
      '[data-test-id="code-copy"]',
    )
    button?.click()
    await Promise.resolve()
    expect(writeText).toHaveBeenCalledWith('pip install gp-sphinx')
  })
})

describe('formatCopyText — prompt stripping', () => {
  test('returns text unchanged when no prompt is present', () => {
    const out = formatCopyText('const x = 1\nconsole.log(x)')
    expect(out).toBe('const x = 1\nconsole.log(x)')
  })

  test('strips Python REPL ``>>> `` prompt and skips output lines', () => {
    const out = formatCopyText('>>> a = 1\n>>> a\n1\n>>> a + 1\n2')
    expect(out).toBe('a = 1\na\na + 1')
  })

  test('strips Python REPL continuation ``... `` prompt', () => {
    const out = formatCopyText('>>> def f():\n...     return 1\n...\n>>> f()\n1')
    expect(out).toBe('def f():\n    return 1\n\nf()')
  })

  test('strips shell ``$ `` prompt and skips output lines', () => {
    const out = formatCopyText('$ pip install foo\nCollecting foo\n$ pip list\nfoo 1.0')
    expect(out).toBe('pip install foo\npip list')
  })

  test('strips root-shell ``# `` prompt', () => {
    const out = formatCopyText('# apt-get update\nReading package lists...\n# apt-get install foo')
    expect(out).toBe('apt-get update\napt-get install foo')
  })

  test('preserves blank lines between prompted lines', () => {
    const out = formatCopyText('>>> a = 1\n\n>>> b = 2')
    expect(out).toBe('a = 1\n\nb = 2')
  })

  test('trims a single trailing newline so paste does not auto-execute', () => {
    const out = formatCopyText('>>> a = 1\n')
    expect(out).toBe('a = 1')
  })
})
