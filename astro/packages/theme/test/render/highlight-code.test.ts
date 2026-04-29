/**
 * Tests for the Shiki-backed code highlighter.
 *
 * The factory is async (Shiki loads its WASM grammars + themes
 * lazily); the returned ``highlight`` is sync so it composes with
 * the existing pure ``renderBlockNode`` via a thin variant.
 */

import { beforeAll, describe, expect, test } from 'vitest'
import { type CodeHighlighter, createCodeHighlighter } from '../../src/render/highlight-code.ts'

let highlight: CodeHighlighter

beforeAll(async () => {
  highlight = await createCodeHighlighter({
    themes: { light: 'github-light', dark: 'github-dark' },
    langs: ['python', 'typescript', 'console'],
  })
})

describe('createCodeHighlighter', () => {
  test('resolves to a callable', () => {
    expect(typeof highlight).toBe('function')
  })

  test('produces Shiki markup for a known language', () => {
    const html = highlight('def foo():\n    return 1\n', 'python')
    expect(html).toContain('class="shiki')
    // Shiki tokens carry inline style="color:#…".
    expect(html).toMatch(/<span[^>]+style=["'][^"']*color:/)
  })

  test('falls back to plain <pre><code class="language-XXX"> for unknown language', () => {
    const html = highlight('# random ini\nfoo = bar', 'inifile')
    expect(html).toContain('<pre><code class="language-inifile">')
    expect(html).toContain('foo = bar')
    expect(html).not.toContain('class="shiki')
  })

  test('falls back to plain <pre><code> when language is null', () => {
    const html = highlight('plain text', null)
    expect(html.trim()).toBe('<pre><code>plain text</code></pre>')
  })

  test('escapes HTML special characters in the fallback paths', () => {
    const html = highlight('a < b && c > d', null)
    expect(html).toContain('a &lt; b &amp;&amp; c &gt; d')
    expect(html).not.toContain('<b>')
  })

  test('escapes HTML special characters in unknown-language fallback', () => {
    const html = highlight('a < b', 'whatever')
    expect(html).toContain('a &lt; b')
  })

  test('the returned function is callable many times without races', () => {
    expect(() => {
      for (let i = 0; i < 5; i += 1) {
        highlight(`x = ${i}\n`, 'python')
      }
    }).not.toThrow()
  })
})
