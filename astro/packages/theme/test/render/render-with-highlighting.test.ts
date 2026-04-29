/**
 * Tests for the highlighting-aware document renderer.
 *
 * ``renderDocumentWithHighlighting`` is a thin variant of the pure
 * ``renderDocument``: every node type renders identically *except*
 * ``literalBlock``, which goes through an injected highlighter
 * (Shiki in production, a stub here).
 */

import { describe, expect, test } from 'vitest'
import { renderDocumentWithHighlighting } from '../../src/render/render-with-highlighting.ts'
import type { Document } from '../../src/schemas/doctree.ts'

function makeDoc(): Document {
  return {
    id: 'demo',
    title: 'Demo',
    tree: {
      type: 'section',
      id: 'demo',
      title: [{ type: 'text', value: 'Demo' }],
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'Hello world.' }],
        },
        {
          type: 'literalBlock',
          language: 'python',
          code: 'print("hi")',
        },
        {
          type: 'literalBlock',
          language: null,
          code: 'no language here',
        },
      ],
    },
  }
}

describe('renderDocumentWithHighlighting', () => {
  test('routes literalBlock nodes through the injected highlighter', () => {
    const calls: Array<{ code: string; language: string | null }> = []
    const highlight = (code: string, language: string | null): string => {
      calls.push({ code, language })
      return `<pre data-stub="${language ?? 'null'}">${code}</pre>`
    }
    const html = renderDocumentWithHighlighting(makeDoc(), highlight)
    expect(calls).toEqual([
      { code: 'print("hi")', language: 'python' },
      { code: 'no language here', language: null },
    ])
    expect(html).toContain('<pre data-stub="python">print("hi")</pre>')
    expect(html).toContain('<pre data-stub="null">no language here</pre>')
  })

  test('renders non-literalBlock nodes the same as the base renderer', () => {
    const html = renderDocumentWithHighlighting(makeDoc(), () => '<pre/>')
    // Section heading + paragraph come from the base ``renderBlockNode``.
    expect(html).toContain('<section id="demo">')
    expect(html).toContain('<h1>Demo<a class="headerlink"')
    expect(html).toContain('href="#demo"')
    expect(html).toContain('<p>Hello world.</p>')
  })
})
