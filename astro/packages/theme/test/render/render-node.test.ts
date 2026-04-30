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
        classes: [],
        children: [{ type: 'text', value: 'Example' }],
      }),
    ).toBe('<a href="https://example.com">Example</a>')
  })

  test('reference with xref classes emits a class attribute', () => {
    const html = renderInlineNode({
      type: 'reference',
      href: '/api/foo/',
      classes: ['xref', 'py', 'py-func'],
      children: [{ type: 'literal', value: 'foo()' }],
    })
    expect(html).toBe('<a href="/api/foo/" class="xref py py-func"><code>foo()</code></a>')
  })

  test('reference omits class attribute when classes are empty', () => {
    const html = renderInlineNode({
      type: 'reference',
      href: '/x',
      classes: [],
      children: [{ type: 'text', value: 'x' }],
    })
    expect(html).not.toContain('class=')
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
      title: null,
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

  test('admonition with custom title renders an admonition-title heading', () => {
    const html = renderBlockNode({
      type: 'admonition',
      variant: 'warning',
      title: [{ type: 'text', value: 'Alpha' }],
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'Pre-1.0 status.' }],
        },
      ],
    })
    expect(html).toContain('<p class="admonition-title">Alpha</p>')
    expect(html).toContain('<p>Pre-1.0 status.</p>')
  })

  test('admonition with title=null omits the admonition-title element', () => {
    const html = renderBlockNode({
      type: 'admonition',
      variant: 'note',
      title: null,
      children: [],
    })
    expect(html).not.toContain('admonition-title')
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
  test('symbolRef emits a typed link pointing at the symbol page', () => {
    const html = renderBlockNode({
      type: 'symbolRef',
      symbolId: 'gp_sphinx.config.merge_sphinx_config',
    })
    expect(html).toContain('data-symbol-id="gp_sphinx.config.merge_sphinx_config"')
    // Symbol pages live at /api/<id>/ in the dogfood Astro app; the
    // doctree's symbolRef anchors the cross-doc navigation.
    expect(html).toContain('href="/api/gp_sphinx.config.merge_sphinx_config/"')
  })

  test('symbolRef escapes path-unfriendly characters in the href', () => {
    const html = renderBlockNode({
      type: 'symbolRef',
      symbolId: 'mod.<weird>',
    })
    expect(html).toContain('data-symbol-id="mod.&lt;weird&gt;"')
    expect(html).toContain('href="/api/mod.&lt;weird&gt;/"')
  })
})

describe('renderBlockNode — section', () => {
  test('top-level section emits <h1> with id and a headerlink anchor', () => {
    const html = renderBlockNode({
      type: 'section',
      id: 'intro',
      title: [{ type: 'text', value: 'Intro' }],
      children: [],
    })
    // The heading carries an in-page jump anchor so visitors can
    // copy a link to a specific section. The ``headerlink`` class
    // is the chrome's hover-reveal hook (see global.css).
    expect(html).toContain('<section id="intro">')
    expect(html).toContain('<h1>Intro')
    expect(html).toContain(
      '<a class="headerlink" href="#intro" aria-label="Permalink to this section">#</a>',
    )
  })

  test('nested section emits a deeper heading with its own headerlink', () => {
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
    expect(html).toContain('<h1>Outer')
    expect(html).toContain('<h2>Inner')
    expect(html).toContain('href="#outer"')
    expect(html).toContain('href="#inner"')
  })

  test('omits the headerlink when the section has no id (cannot link to it)', () => {
    const html = renderBlockNode({
      type: 'section',
      id: '',
      title: [{ type: 'text', value: 'No id' }],
      children: [],
    })
    expect(html).not.toContain('headerlink')
    expect(html).toContain('<h1>No id</h1>')
  })

  test('escapes the section id when composing the headerlink href', () => {
    const html = renderBlockNode({
      type: 'section',
      id: 'a"b',
      title: [{ type: 'text', value: 'X' }],
      children: [],
    })
    expect(html).toContain('href="#a&quot;b"')
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
      `"<section id="hello-world"><h1>Hello world<a class="headerlink" href="#hello-world" aria-label="Permalink to this section">#</a></h1><p>Hello <em>world</em>.</p></section>"`,
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
      classes: [],
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
      classes: [],
    })
    expect(html).toContain('class="gp-sphinx-badge gp-sphinx-badge--style-full"')
    expect(html).not.toContain('gp-sphinx-badge--size-')
    expect(html).not.toContain('title=')
    expect(html).not.toContain('data-icon=')
  })

  test('badge appends modifier classes from the wire format', () => {
    const html = renderInlineNode({
      type: 'badge',
      text: 'function',
      tooltip: null,
      icon: null,
      size: null,
      style: 'full',
      classes: ['gp-sphinx-badge--type-function', 'gp-sphinx-badge--dense'],
    })
    expect(html).toContain(
      'class="gp-sphinx-badge gp-sphinx-badge--style-full gp-sphinx-badge--type-function gp-sphinx-badge--dense"',
    )
  })
})

describe('renderInlineNode — footnoteReference', () => {
  test('numeric footnote reference renders as a bracketed superscript link', () => {
    const html = renderInlineNode({
      type: 'footnoteReference',
      kind: 'footnote',
      href: '#footnote-1',
      label: '1',
    })
    expect(html).toBe(
      '<sup class="gp-sphinx-footnote-reference-wrap"><a class="gp-sphinx-footnote-reference" href="#footnote-1">[1]</a></sup>',
    )
  })

  test('citation reference uses the citation class instead of footnote', () => {
    const html = renderInlineNode({
      type: 'footnoteReference',
      kind: 'citation',
      href: '#smith2020',
      label: 'Smith2020',
    })
    expect(html).toContain('class="gp-sphinx-citation-reference-wrap"')
    expect(html).toContain('class="gp-sphinx-citation-reference"')
    expect(html).toContain('[Smith2020]')
    expect(html).toContain('href="#smith2020"')
  })

  test('escapes hostile content in label and href', () => {
    const html = renderInlineNode({
      type: 'footnoteReference',
      kind: 'footnote',
      href: '"</a>',
      label: '<x>',
    })
    // The legitimate closing sequence ends with ``</a></sup>``; the
    // hostile attempt would inject an additional ``</a>`` mid-tag.
    // Counting confirms only the legitimate closer survives.
    expect(html.match(/<\/a>/g)?.length ?? 0).toBe(1)
    expect(html).toContain('&quot;')
    expect(html).toContain('&lt;x&gt;')
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
      classes: [],
      children: [{ type: 'text', value: 'x' }],
    },
    {
      type: 'footnoteReference',
      kind: 'footnote',
      href: '#footnote-1',
      label: '1',
    },
    {
      type: 'badge',
      text: 'x',
      tooltip: null,
      icon: null,
      size: null,
      style: 'full',
      classes: [],
    },
  ]

  test.each(inlineFixtures)('inline variant $type renders to non-empty HTML', (node) => {
    const html = renderInlineNode(node as InlineNode)
    expect(html).toBeTruthy()
  })
})

describe('renderBlockNode — footnote', () => {
  test('footnote body renders with id, label, and aside chrome', () => {
    const html = renderBlockNode({
      type: 'footnote',
      kind: 'footnote',
      id: 'footnote-1',
      label: '1',
      children: [{ type: 'paragraph', children: [{ type: 'text', value: 'A note.' }] }],
    })
    expect(html).toContain('class="gp-sphinx-footnote"')
    expect(html).toContain('id="footnote-1"')
    expect(html).toContain('role="doc-footnote"')
    expect(html).toContain('<span class="gp-sphinx-footnote__label">[1]</span>')
    expect(html).toContain('<div class="gp-sphinx-footnote__body"><p>A note.</p></div>')
  })

  test('citation body uses the citation class and biblioentry role', () => {
    const html = renderBlockNode({
      type: 'footnote',
      kind: 'citation',
      id: 'smith2020',
      label: 'Smith2020',
      children: [{ type: 'paragraph', children: [{ type: 'text', value: 'Smith, J.' }] }],
    })
    expect(html).toContain('class="gp-sphinx-citation"')
    expect(html).toContain('role="doc-biblioentry"')
    expect(html).toContain('<span class="gp-sphinx-citation__label">[Smith2020]</span>')
  })
})

describe('renderBlockNode — table', () => {
  test('table with thead + tbody emits matching structural HTML', () => {
    const html = renderBlockNode({
      type: 'table',
      head: [
        {
          type: 'tableRow',
          cells: [
            {
              type: 'tableCell',
              header: true,
              children: [{ type: 'paragraph', children: [{ type: 'text', value: 'Object' }] }],
            },
            {
              type: 'tableCell',
              header: true,
              children: [{ type: 'paragraph', children: [{ type: 'text', value: 'CSS class' }] }],
            },
          ],
        },
      ],
      body: [
        {
          type: 'tableRow',
          cells: [
            {
              type: 'tableCell',
              header: false,
              children: [{ type: 'paragraph', children: [{ type: 'text', value: 'function' }] }],
            },
            {
              type: 'tableCell',
              header: false,
              children: [
                {
                  type: 'paragraph',
                  children: [{ type: 'literal', value: 'gp-sphinx-badge--type-function' }],
                },
              ],
            },
          ],
        },
      ],
    })
    expect(html).toBe(
      '<table class="docutils">' +
        '<thead><tr><th><p>Object</p></th><th><p>CSS class</p></th></tr></thead>' +
        '<tbody><tr><td><p>function</p></td><td><p><code>gp-sphinx-badge--type-function</code></p></td></tr></tbody>' +
        '</table>',
    )
  })

  test('table with empty head omits the thead element', () => {
    const html = renderBlockNode({
      type: 'table',
      head: [],
      body: [
        {
          type: 'tableRow',
          cells: [
            {
              type: 'tableCell',
              header: false,
              children: [{ type: 'paragraph', children: [{ type: 'text', value: 'x' }] }],
            },
          ],
        },
      ],
    })
    expect(html).not.toContain('<thead')
    expect(html).toContain('<tbody><tr><td>')
  })

  test('table with empty body omits the tbody element', () => {
    const html = renderBlockNode({
      type: 'table',
      head: [
        {
          type: 'tableRow',
          cells: [
            {
              type: 'tableCell',
              header: true,
              children: [{ type: 'paragraph', children: [{ type: 'text', value: 'h' }] }],
            },
          ],
        },
      ],
      body: [],
    })
    expect(html).not.toContain('<tbody')
    expect(html).toContain('<thead><tr><th>')
  })
})

describe('renderBlockNode — rubric', () => {
  test('rubric emits a styled paragraph with the gp-sphinx-rubric class', () => {
    const html = renderBlockNode({ type: 'rubric', text: 'Examples' })
    expect(html).toBe('<p class="gp-sphinx-rubric">Examples</p>')
  })

  test('rubric escapes HTML in its label text', () => {
    const html = renderBlockNode({ type: 'rubric', text: '<x> & "y"' })
    expect(html).toBe('<p class="gp-sphinx-rubric">&lt;x&gt; &amp; &quot;y&quot;</p>')
  })
})

describe('renderBlockNode — type-coverage', () => {
  const blockFixtures: BlockNode[] = [
    { type: 'paragraph', children: [] },
    { type: 'literalBlock', language: null, code: '' },
    { type: 'comment', value: '' },
    { type: 'transition' },
    { type: 'rubric', text: 'Examples' },
    { type: 'table', head: [], body: [] },
    { type: 'blockQuote', children: [] },
    { type: 'bulletList', children: [] },
    { type: 'enumeratedList', start: null, children: [] },
    {
      type: 'admonition',
      variant: 'note',
      title: null,
      children: [],
    },
    {
      type: 'footnote',
      kind: 'footnote',
      id: 'footnote-1',
      label: '1',
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
