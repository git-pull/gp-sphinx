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

describe('renderDocumentWithHighlighting — apiLayout / cliCommand recursion', () => {
  test('literalBlock inside an apiLayout region routes through the highlighter', () => {
    const doc: Document = {
      id: 'demo',
      title: 'Demo',
      tree: {
        type: 'section',
        id: 'demo',
        title: [{ type: 'text', value: 'Demo' }],
        children: [
          {
            type: 'apiLayout',
            component: 'region',
            name: 'gp-sphinx-api-region--narrative',
            tag: 'div',
            kind: null,
            summary: null,
            href: null,
            title: null,
            slot: null,
            open: false,
            classes: [],
            children: [
              {
                type: 'literalBlock',
                language: 'python',
                code: 'print("hi")',
              },
            ],
          },
        ],
      },
    }
    const calls: Array<{ code: string; language: string | null }> = []
    const highlight = (code: string, language: string | null): string => {
      calls.push({ code, language })
      return `<pre class="shiki" data-stub="${language ?? 'null'}">${code}</pre>`
    }
    const html = renderDocumentWithHighlighting(doc, highlight)
    expect(calls).toEqual([{ code: 'print("hi")', language: 'python' }])
    expect(html).toContain('<pre class="shiki" data-stub="python">print("hi")</pre>')
    expect(html).toContain('class="gp-sphinx-api gp-sphinx-api--region')
    expect(html).not.toContain('class="language-python"')
  })

  test('literalBlock inside a cliCommand program routes through the highlighter', () => {
    const doc: Document = {
      id: 'demo',
      title: 'Demo',
      tree: {
        type: 'section',
        id: 'demo',
        title: [{ type: 'text', value: 'Demo' }],
        children: [
          {
            type: 'cliCommand',
            component: 'program',
            prog: 'myapp',
            usage: null,
            title: null,
            description: null,
            names: [],
            help: null,
            default: null,
            choices: [],
            required: false,
            metavar: null,
            name: null,
            aliases: [],
            classes: [],
            children: [
              {
                type: 'literalBlock',
                language: 'bash',
                code: 'myapp --help',
              },
            ],
          },
        ],
      },
    }
    const calls: Array<{ code: string; language: string | null }> = []
    const highlight = (code: string, language: string | null): string => {
      calls.push({ code, language })
      return `<pre class="shiki" data-stub="${language ?? 'null'}">${code}</pre>`
    }
    const html = renderDocumentWithHighlighting(doc, highlight)
    expect(calls).toEqual([{ code: 'myapp --help', language: 'bash' }])
    expect(html).toContain('<pre class="shiki" data-stub="bash">myapp --help</pre>')
    expect(html).toContain('class="gp-sphinx-cli gp-sphinx-cli--program"')
  })

  test('literalBlock nested two layers deep in apiLayout still reaches the highlighter', () => {
    const doc: Document = {
      id: 'demo',
      title: 'Demo',
      tree: {
        type: 'section',
        id: 'demo',
        title: [{ type: 'text', value: 'Demo' }],
        children: [
          {
            type: 'apiLayout',
            component: 'region',
            name: null,
            tag: 'div',
            kind: null,
            summary: null,
            href: null,
            title: null,
            slot: null,
            open: false,
            classes: [],
            children: [
              {
                type: 'apiLayout',
                component: 'fold',
                name: null,
                tag: null,
                kind: null,
                summary: 'Examples',
                href: null,
                title: null,
                slot: null,
                open: false,
                classes: [],
                children: [
                  {
                    type: 'literalBlock',
                    language: 'python',
                    code: 'a = 1',
                  },
                ],
              },
            ],
          },
        ],
      },
    }
    const calls: Array<{ code: string; language: string | null }> = []
    const highlight = (code: string, language: string | null): string => {
      calls.push({ code, language })
      return `<pre class="shiki" data-stub="${language ?? 'null'}">${code}</pre>`
    }
    const html = renderDocumentWithHighlighting(doc, highlight)
    expect(calls).toEqual([{ code: 'a = 1', language: 'python' }])
    expect(html).toContain('<pre class="shiki" data-stub="python">a = 1</pre>')
  })

  test('non-literalBlock content inside apiLayout renders the same as base renderer', async () => {
    const { renderDocument } = await import('../../src/render/render-node.ts')
    const doc: Document = {
      id: 'demo',
      title: 'Demo',
      tree: {
        type: 'section',
        id: 'demo',
        title: [{ type: 'text', value: 'Demo' }],
        children: [
          {
            type: 'apiLayout',
            component: 'region',
            name: 'gp-sphinx-api-region--narrative',
            tag: 'div',
            kind: 'function',
            summary: null,
            href: null,
            title: null,
            slot: null,
            open: false,
            classes: ['extra'],
            children: [
              {
                type: 'paragraph',
                children: [{ type: 'text', value: 'Body text.' }],
              },
            ],
          },
        ],
      },
    }
    // Highlighter is a no-op stub — there are no literalBlocks in this fixture.
    const highlightStub = (): string => {
      throw new Error('highlight should not be called for non-literalBlock content')
    }
    const baseHtml = renderDocument(doc)
    const highlightedHtml = renderDocumentWithHighlighting(doc, highlightStub)
    expect(highlightedHtml).toBe(baseHtml)
  })
})
