/**
 * Tests for the pure-function Symbol HTML renderer.
 *
 * ``renderSymbol`` consumes one entry from ``src/content/api/symbols.json``
 * (a Pydantic-validated ``Symbol`` payload) and produces the structural
 * HTML one would render on an API page or embed inline in a doc. The
 * docstring body uses the same ``renderBlockNode`` dispatch as ordinary
 * docs so NumPy ``definitionList`` rubrics, code blocks, and
 * cross-references work uniformly.
 */

import { describe, expect, test } from 'vitest'
import { renderSymbol } from '../../src/render/render-symbol.ts'
import type { Symbol as ApiSymbol } from '../../src/schemas/symbol.ts'

function makeFunctionSymbol(overrides: Partial<ApiSymbol> = {}): ApiSymbol {
  return {
    id: 'gp_sphinx.config.merge_sphinx_config',
    kind: 'function',
    name: 'merge_sphinx_config',
    qualname: 'merge_sphinx_config',
    module: 'gp_sphinx.config',
    signature: '(*, project: str, version: str) -> dict[str, t.Any]',
    parameters: [
      { name: 'project', annotation: 'str', default: null, kind: 'keyword' },
      { name: 'version', annotation: 'str', default: '"0.0.0"', kind: 'keyword' },
    ],
    returns: 'dict[str, t.Any]',
    docstring_summary: 'Merge per-project Sphinx config onto shared defaults.',
    docstring_body: [],
    source: null,
    ...overrides,
  }
}

describe('renderSymbol — header and identity', () => {
  test('emits an <article> with id, kind class, and stable hooks', () => {
    const html = renderSymbol(makeFunctionSymbol())
    expect(html).toContain('<article ')
    expect(html).toContain('class="gp-sphinx-symbol gp-sphinx-symbol--function"')
    expect(html).toContain('id="gp_sphinx.config.merge_sphinx_config"')
    expect(html).toContain('data-symbol-id="gp_sphinx.config.merge_sphinx_config"')
  })

  test('renders the signature inside a code element with the symbol name', () => {
    const html = renderSymbol(makeFunctionSymbol())
    expect(html).toContain('<code class="gp-sphinx-symbol__signature">')
    // The signature line shows fully-qualified path + raw signature text.
    expect(html).toContain('merge_sphinx_config')
    expect(html).toContain('(*, project: str, version: str) -&gt; dict[str, t.Any]')
  })

  test('escapes special characters in module / qualname', () => {
    const html = renderSymbol(
      makeFunctionSymbol({
        id: '<weird>',
        name: '<weird>',
        qualname: '<weird>',
        module: 'a&b',
      }),
    )
    expect(html).toContain('&lt;weird&gt;')
    expect(html).toContain('a&amp;b')
    expect(html).not.toContain('<weird>')
  })

  test('uses the kind modifier class for class symbols', () => {
    const html = renderSymbol(makeFunctionSymbol({ kind: 'class' }))
    expect(html).toContain('gp-sphinx-symbol--class')
    expect(html).not.toContain('gp-sphinx-symbol--function')
  })
})

describe('renderSymbol — summary', () => {
  test('renders the docstring summary as a paragraph with a stable hook', () => {
    const html = renderSymbol(makeFunctionSymbol())
    expect(html).toContain('<p class="gp-sphinx-symbol__summary">')
    expect(html).toContain('Merge per-project Sphinx config onto shared defaults.')
  })

  test('omits the summary paragraph when docstring_summary is empty', () => {
    const html = renderSymbol(makeFunctionSymbol({ docstring_summary: '' }))
    expect(html).not.toContain('gp-sphinx-symbol__summary')
  })
})

describe('renderSymbol — parameters and returns', () => {
  test('renders parameters as a definition list of names + annotations', () => {
    const html = renderSymbol(makeFunctionSymbol())
    expect(html).toContain('<dl class="gp-sphinx-symbol__params">')
    expect(html).toContain('<dt>project</dt>')
    expect(html).toContain('<dd>str</dd>')
    expect(html).toContain('<dt>version</dt>')
    // The default value is rendered inline alongside the annotation.
    // Quotes are HTML-escaped because defaults can contain user-supplied
    // string literals that must not break out of attribute context.
    expect(html).toContain('&quot;0.0.0&quot;')
  })

  test('omits the parameters block when the function has no parameters', () => {
    const html = renderSymbol(makeFunctionSymbol({ parameters: [] }))
    expect(html).not.toContain('gp-sphinx-symbol__params')
  })

  test('renders a non-null returns annotation in its own block', () => {
    const html = renderSymbol(makeFunctionSymbol())
    expect(html).toContain('class="gp-sphinx-symbol__returns"')
    expect(html).toContain('dict[str, t.Any]')
  })

  test('omits the returns block when returns is null', () => {
    const html = renderSymbol(makeFunctionSymbol({ returns: null }))
    expect(html).not.toContain('gp-sphinx-symbol__returns')
  })
})

describe('renderSymbol — docstring body', () => {
  test('recursively renders block content via the doctree renderer', () => {
    const html = renderSymbol(
      makeFunctionSymbol({
        docstring_body: [
          {
            type: 'paragraph',
            children: [{ type: 'text', value: 'Detailed description.' }],
          },
          {
            type: 'literalBlock',
            language: 'python',
            code: 'merge_sphinx_config(project="x", version="1")',
          },
        ],
      }),
    )
    expect(html).toContain('<p>Detailed description.</p>')
    expect(html).toContain('<pre><code class="language-python">')
    expect(html).toContain('merge_sphinx_config(project=&quot;x&quot;, version=&quot;1&quot;)')
  })

  test('omits the body container when docstring_body is empty', () => {
    const html = renderSymbol(makeFunctionSymbol())
    expect(html).not.toContain('gp-sphinx-symbol__body')
  })
})

describe('renderSymbol — source attribution', () => {
  test('renders a deep blob link to the source line on GitHub', () => {
    const html = renderSymbol(
      makeFunctionSymbol({
        source: {
          repo: 'https://github.com/git-pull/gp-sphinx',
          path: 'packages/gp-sphinx/src/gp_sphinx/config.py',
          line: 42,
        },
      }),
    )
    expect(html).toContain('class="gp-sphinx-symbol__source"')
    // The link must land at the exact line on GitHub, not the repo
    // home; otherwise the user has to manually navigate the path.
    expect(html).toContain(
      'href="https://github.com/git-pull/gp-sphinx/blob/main/packages/gp-sphinx/src/gp_sphinx/config.py#L42"',
    )
    expect(html).toContain('packages/gp-sphinx/src/gp_sphinx/config.py')
    expect(html).toContain('42')
  })

  test('strips trailing slashes from the repo URL when composing the blob link', () => {
    const html = renderSymbol(
      makeFunctionSymbol({
        source: {
          repo: 'https://github.com/git-pull/gp-sphinx/',
          path: 'pkg/file.py',
          line: 7,
        },
      }),
    )
    expect(html).toContain('href="https://github.com/git-pull/gp-sphinx/blob/main/pkg/file.py#L7"')
  })

  test('omits the source attribution when source is null', () => {
    const html = renderSymbol(makeFunctionSymbol({ source: null }))
    expect(html).not.toContain('gp-sphinx-symbol__source')
  })
})
