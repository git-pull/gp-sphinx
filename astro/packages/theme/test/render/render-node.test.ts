/**
 * Tests for the pure-function HTML renderer.
 *
 * The renderer maps each :doc:`gp_sphinx_astro_builder` Pydantic node type
 * onto its HTML emission. Step 8 will wrap these functions in Astro
 * components, but the rendering logic itself is pure so it tests in
 * microseconds and stays readable.
 */

import { describe, expect, test } from 'vitest'
import { renderBlockNode, renderDocument, renderInlineNode } from '../../src/render/render-node.ts'
import type { BlockNode, Document, InlineNode } from '../../src/schemas/doctree.ts'

describe('renderInlineNode — leaves', () => {
  test('text escapes HTML special characters', () => {
    const node: InlineNode = { type: 'text', value: '<x> & "y"' }
    expect(renderInlineNode(node)).toBe('&lt;x&gt; &amp; &quot;y&quot;')
  })

  test('literal wraps text in a <code> element', () => {
    expect(renderInlineNode({ type: 'literal', value: 'x = 1' })).toBe('<code>x = 1</code>')
  })

  test('image emits a self-closing <img> with src and alt', () => {
    expect(renderInlineNode({ type: 'image', uri: '/img/logo.svg', alt: 'Logo' })).toBe(
      '<img src="/img/logo.svg" alt="Logo" />',
    )
  })

  test('image with null alt omits the alt attribute', () => {
    expect(renderInlineNode({ type: 'image', uri: '/img/x.png', alt: null })).toBe(
      '<img src="/img/x.png" />',
    )
  })
})

describe('renderInlineNode — recursive shapes', () => {
  test('emphasis wraps children in <em>', () => {
    expect(
      renderInlineNode({
        type: 'emphasis',
        children: [{ type: 'text', value: 'stressed' }],
      }),
    ).toBe('<em>stressed</em>')
  })

  test('strong wraps children in <strong>', () => {
    expect(
      renderInlineNode({
        type: 'strong',
        children: [{ type: 'text', value: 'loud' }],
      }),
    ).toBe('<strong>loud</strong>')
  })

  test('reference emits an <a> with href and rendered children', () => {
    expect(
      renderInlineNode({
        type: 'reference',
        href: 'https://example.com',
        children: [{ type: 'text', value: 'Example' }],
      }),
    ).toBe('<a href="https://example.com">Example</a>')
  })

  test('nested emphasis renders recursively', () => {
    expect(
      renderInlineNode({
        type: 'emphasis',
        children: [
          {
            type: 'emphasis',
            children: [{ type: 'text', value: 'very' }],
          },
        ],
      }),
    ).toBe('<em><em>very</em></em>')
  })
})

describe('renderBlockNode — leaves', () => {
  test('paragraph renders inline children inside <p>', () => {
    expect(
      renderBlockNode({
        type: 'paragraph',
        children: [
          { type: 'text', value: 'Hello ' },
          { type: 'strong', children: [{ type: 'text', value: 'world' }] },
        ],
      }),
    ).toBe('<p>Hello <strong>world</strong></p>')
  })

  test('literalBlock wraps language-tagged code in <pre><code>', () => {
    expect(
      renderBlockNode({
        type: 'literalBlock',
        language: 'python',
        code: "print('hi')",
      }),
    ).toBe('<pre><code class="language-python">print(&#39;hi&#39;)</code></pre>')
  })

  test('literalBlock without language omits the class', () => {
    expect(
      renderBlockNode({
        type: 'literalBlock',
        language: null,
        code: 'raw',
      }),
    ).toBe('<pre><code>raw</code></pre>')
  })

  test('comment renders as an HTML comment', () => {
    expect(renderBlockNode({ type: 'comment', value: 'TODO write more' })).toBe(
      '<!-- TODO write more -->',
    )
  })

  test('transition renders as <hr />', () => {
    expect(renderBlockNode({ type: 'transition' })).toBe('<hr />')
  })
})

describe('renderBlockNode — containers', () => {
  test('blockQuote wraps block children in <blockquote>', () => {
    expect(
      renderBlockNode({
        type: 'blockQuote',
        children: [
          {
            type: 'paragraph',
            children: [{ type: 'text', value: 'q' }],
          },
        ],
      }),
    ).toBe('<blockquote><p>q</p></blockquote>')
  })

  test('bulletList wraps list_item children in <ul><li>', () => {
    expect(
      renderBlockNode({
        type: 'bulletList',
        children: [
          {
            type: 'listItem',
            children: [
              {
                type: 'paragraph',
                children: [{ type: 'text', value: 'a' }],
              },
            ],
          },
          {
            type: 'listItem',
            children: [
              {
                type: 'paragraph',
                children: [{ type: 'text', value: 'b' }],
              },
            ],
          },
        ],
      }),
    ).toBe('<ul><li><p>a</p></li><li><p>b</p></li></ul>')
  })

  test('enumeratedList with explicit start emits start attribute', () => {
    expect(
      renderBlockNode({
        type: 'enumeratedList',
        start: 3,
        children: [
          {
            type: 'listItem',
            children: [
              {
                type: 'paragraph',
                children: [{ type: 'text', value: 'c' }],
              },
            ],
          },
        ],
      }),
    ).toBe('<ol start="3"><li><p>c</p></li></ol>')
  })

  test('enumeratedList without start omits the attribute', () => {
    expect(
      renderBlockNode({
        type: 'enumeratedList',
        start: null,
        children: [
          {
            type: 'listItem',
            children: [
              {
                type: 'paragraph',
                children: [{ type: 'text', value: 'a' }],
              },
            ],
          },
        ],
      }),
    ).toBe('<ol><li><p>a</p></li></ol>')
  })

  test('definitionList renders <dt>+<dd> per item', () => {
    expect(
      renderBlockNode({
        type: 'definitionList',
        children: [
          {
            type: 'definitionListItem',
            term: [{ type: 'text', value: 'foo' }],
            definition: [
              {
                type: 'paragraph',
                children: [{ type: 'text', value: 'describes foo' }],
              },
            ],
          },
        ],
      }),
    ).toBe('<dl><dt>foo</dt><dd><p>describes foo</p></dd></dl>')
  })
})

describe('renderBlockNode — admonitions', () => {
  const variants = [
    'note',
    'warning',
    'attention',
    'caution',
    'important',
    'tip',
    'hint',
    'danger',
    'error',
  ] as const

  test.each(variants)('admonition variant=%s emits the variant class', (variant) => {
    const html = renderBlockNode({
      type: 'admonition',
      variant,
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'note body' }],
        },
      ],
    })
    expect(html).toContain(`admonition admonition--${variant}`)
    expect(html).toContain('<p>note body</p>')
  })
})

describe('renderBlockNode — apiLayout', () => {
  test('region emits a <div> with kind class', () => {
    const html = renderBlockNode({
      type: 'apiLayout',
      component: 'region',
      name: null,
      tag: null,
      kind: 'narrative',
      summary: null,
      href: null,
      title: null,
      slot: null,
      open: false,
      classes: [],
      children: [{ type: 'paragraph', children: [{ type: 'text', value: 'x' }] }],
    })
    expect(html).toContain(
      'class="gp-sphinx-api gp-sphinx-api--region gp-sphinx-api--kind-narrative"',
    )
    expect(html).toContain('<p>x</p>')
  })

  test('fold renders <details> with summary and open flag', () => {
    const html = renderBlockNode({
      type: 'apiLayout',
      component: 'fold',
      name: null,
      tag: null,
      kind: 'parameters',
      summary: 'Parameters (3)',
      href: null,
      title: null,
      slot: null,
      open: true,
      classes: [],
      children: [],
    })
    expect(html).toContain('<details ')
    expect(html).toContain(' open>')
    expect(html).toContain('<summary>Parameters (3)</summary>')
  })

  test('permalink renders <a> with href and title', () => {
    const html = renderBlockNode({
      type: 'apiLayout',
      component: 'permalink',
      name: null,
      tag: null,
      kind: null,
      summary: null,
      href: '#mod.func',
      title: 'Link',
      slot: null,
      open: false,
      classes: [],
      children: [],
    })
    expect(html).toContain('<a ')
    expect(html).toContain('href="#mod.func"')
    expect(html).toContain('title="Link"')
  })

  test('slot renders empty <span> with data-slot', () => {
    const html = renderBlockNode({
      type: 'apiLayout',
      component: 'slot',
      name: null,
      tag: null,
      kind: null,
      summary: null,
      href: null,
      title: null,
      slot: 'badges',
      open: false,
      classes: [],
      children: [],
    })
    expect(html).toContain('data-slot="badges"')
  })

  test('inline_component uses tag from payload (default span)', () => {
    const html = renderBlockNode({
      type: 'apiLayout',
      component: 'inline_component',
      name: 'gp-sphinx-api-source-link',
      tag: 'span',
      kind: null,
      summary: null,
      href: null,
      title: null,
      slot: null,
      open: false,
      classes: [],
      children: [],
    })
    expect(html.startsWith('<span ')).toBe(true)
    expect(html).toContain('gp-sphinx-api-source-link')
  })
})

describe('renderBlockNode — cliCommand', () => {
  test('program emits a <section> with prog data attribute', () => {
    const html = renderBlockNode({
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
      children: [],
    })
    expect(html).toContain('<section ')
    expect(html).toContain('class="gp-sphinx-cli gp-sphinx-cli--program"')
    expect(html).toContain('data-prog="myapp"')
  })

  test('usage renders a <pre> with the usage text escaped', () => {
    const html = renderBlockNode({
      type: 'cliCommand',
      component: 'usage',
      prog: null,
      usage: 'myapp [-h] <cmd>',
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
      children: [],
    })
    expect(html).toContain('<pre class="gp-sphinx-cli__usage">')
    expect(html).toContain('myapp [-h] &lt;cmd&gt;')
  })

  test('argument renders a <dl> with names term and help description', () => {
    const html = renderBlockNode({
      type: 'cliCommand',
      component: 'argument',
      prog: null,
      usage: null,
      title: null,
      description: null,
      names: ['-v', '--verbose'],
      help: 'Increase output verbosity',
      default: 'False',
      choices: [],
      required: false,
      metavar: 'LEVEL',
      name: null,
      aliases: [],
      classes: [],
      children: [],
    })
    expect(html).toContain('<dl class="gp-sphinx-cli__arg">')
    expect(html).toContain('-v')
    expect(html).toContain('--verbose')
    expect(html).toContain('LEVEL')
    expect(html).toContain('Increase output verbosity')
  })

  test('subcommand renders a <details> with name + aliases', () => {
    const html = renderBlockNode({
      type: 'cliCommand',
      component: 'subcommand',
      prog: null,
      usage: null,
      title: null,
      description: null,
      names: [],
      help: 'Build the project',
      default: null,
      choices: [],
      required: false,
      metavar: null,
      name: 'build',
      aliases: ['b'],
      classes: [],
      children: [],
    })
    expect(html).toContain('<details ')
    expect(html).toContain('class="gp-sphinx-cli gp-sphinx-cli--subcommand"')
    expect(html).toContain('build')
    expect(html).toContain('Build the project')
  })

  test('subcommands wraps children inside a <section>', () => {
    const html = renderBlockNode({
      type: 'cliCommand',
      component: 'subcommands',
      prog: null,
      usage: null,
      title: 'Commands',
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
      children: [],
    })
    expect(html).toContain('<section ')
    expect(html).toContain('class="gp-sphinx-cli gp-sphinx-cli--subcommands"')
    expect(html).toContain('Commands')
  })

  test('group renders a <section> with title', () => {
    const html = renderBlockNode({
      type: 'cliCommand',
      component: 'group',
      prog: null,
      usage: null,
      title: 'Output Options',
      description: 'General options',
      names: [],
      help: null,
      default: null,
      choices: [],
      required: false,
      metavar: null,
      name: null,
      aliases: [],
      classes: [],
      children: [],
    })
    expect(html).toContain('<section ')
    expect(html).toContain('class="gp-sphinx-cli gp-sphinx-cli--group"')
    expect(html).toContain('Output Options')
  })
})

describe('renderBlockNode — symbolRef', () => {
  test('symbolRef emits a typed link with data-symbol-id', () => {
    const html = renderBlockNode({
      type: 'symbolRef',
      symbolId: 'gp_sphinx.config.merge_sphinx_config',
    })
    expect(html).toContain('data-symbol-id="gp_sphinx.config.merge_sphinx_config"')
    expect(html).toContain('href="#gp_sphinx.config.merge_sphinx_config"')
  })
})

describe('renderBlockNode — section', () => {
  test('top-level section emits <h1> with id', () => {
    const html = renderBlockNode({
      type: 'section',
      id: 'intro',
      title: [{ type: 'text', value: 'Intro' }],
      children: [],
    })
    expect(html).toBe('<section id="intro"><h1>Intro</h1></section>')
  })

  test('nested section emits a deeper heading', () => {
    const html = renderBlockNode({
      type: 'section',
      id: 'outer',
      title: [{ type: 'text', value: 'Outer' }],
      children: [
        {
          type: 'section',
          id: 'inner',
          title: [{ type: 'text', value: 'Inner' }],
          children: [],
        },
      ],
    })
    expect(html).toContain('<h1>Outer</h1>')
    expect(html).toContain('<h2>Inner</h2>')
  })
})

describe('renderDocument', () => {
  test('renders the canonical hello-world Document', () => {
    const doc: Document = {
      id: 'index',
      title: 'Hello world',
      tree: {
        type: 'section',
        id: 'hello-world',
        title: [{ type: 'text', value: 'Hello world' }],
        children: [
          {
            type: 'paragraph',
            children: [
              { type: 'text', value: 'Hello ' },
              {
                type: 'emphasis',
                children: [{ type: 'text', value: 'world' }],
              },
              { type: 'text', value: '.' },
            ],
          },
        ],
      },
    }
    expect(renderDocument(doc)).toMatchInlineSnapshot(
      `"<section id="hello-world"><h1>Hello world</h1><p>Hello <em>world</em>.</p></section>"`,
    )
  })
})

describe('renderInlineNode — badge', () => {
  test('badge with full payload emits a span with size + style classes', () => {
    const html = renderInlineNode({
      type: 'badge',
      text: 'readonly',
      tooltip: 'Read-only operation',
      icon: '🔒',
      size: 'sm',
      style: 'filled',
    })
    expect(html).toContain(
      'class="gp-sphinx-badge gp-sphinx-badge--style-filled gp-sphinx-badge--size-sm"',
    )
    expect(html).toContain('title="Read-only operation"')
    expect(html).toContain('aria-label="Read-only operation"')
    expect(html).toContain('data-icon="🔒"')
    expect(html).toContain('<span class="gp-sphinx-badge__label">readonly</span>')
  })

  test('badge with default style omits the size class when size is null', () => {
    const html = renderInlineNode({
      type: 'badge',
      text: 'ok',
      tooltip: null,
      icon: null,
      size: null,
      style: 'full',
    })
    expect(html).toContain('class="gp-sphinx-badge gp-sphinx-badge--style-full"')
    expect(html).not.toContain('gp-sphinx-badge--size-')
    expect(html).not.toContain('title=')
    expect(html).not.toContain('data-icon=')
  })
})

describe('renderInlineNode — type-coverage', () => {
  // Sanity check that every InlineNode variant is dispatched. If a new
  // variant is added to the schema without updating renderInlineNode,
  // TypeScript's exhaustiveness check would catch it at compile time;
  // this test catches it at runtime as well.
  const inlineFixtures: InlineNode[] = [
    { type: 'text', value: 'x' },
    { type: 'literal', value: 'x' },
    { type: 'image', uri: '/x.svg', alt: null },
    { type: 'emphasis', children: [{ type: 'text', value: 'x' }] },
    { type: 'strong', children: [{ type: 'text', value: 'x' }] },
    {
      type: 'reference',
      href: '/x',
      children: [{ type: 'text', value: 'x' }],
    },
    {
      type: 'badge',
      text: 'x',
      tooltip: null,
      icon: null,
      size: null,
      style: 'full',
    },
  ]

  test.each(inlineFixtures)('inline variant $type renders to non-empty HTML', (node) => {
    const html = renderInlineNode(node as InlineNode)
    expect(html).toBeTruthy()
  })
})

describe('renderBlockNode — type-coverage', () => {
  const blockFixtures: BlockNode[] = [
    { type: 'paragraph', children: [] },
    { type: 'literalBlock', language: null, code: '' },
    { type: 'comment', value: '' },
    { type: 'transition' },
    { type: 'blockQuote', children: [] },
    { type: 'bulletList', children: [] },
    { type: 'enumeratedList', start: null, children: [] },
    {
      type: 'admonition',
      variant: 'note',
      children: [],
    },
    { type: 'definitionList', children: [] },
    { type: 'symbolRef', symbolId: 'x.y' },
    {
      type: 'section',
      id: 'x',
      title: [],
      children: [],
    },
  ]

  test.each(blockFixtures)('block variant $type renders to non-empty HTML', (node) => {
    const html = renderBlockNode(node as BlockNode)
    expect(html).toBeTruthy()
  })
})
