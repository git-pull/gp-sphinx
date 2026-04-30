/**
 * Tests for the doctree description extractor.
 *
 * The extractor walks the top-level section's first paragraph (or
 * any nested first-paragraph if the section opens with a section)
 * and returns its inline-flattened text — a one-sentence-ish blurb
 * suitable for ``<meta name="description">``.
 */

import { describe, expect, test } from 'vitest'
import { extractDescription } from '../../src/render/extract-description.ts'
import type { BlockNode } from '../../src/schemas/doctree.ts'

function section(
  id: string,
  title: string,
  children: BlockNode[],
): Extract<BlockNode, { type: 'section' }> {
  return {
    type: 'section',
    id,
    title: [{ type: 'text', value: title }],
    children,
  }
}

describe('extractDescription', () => {
  test('returns the text of the first paragraph in the section', () => {
    const tree = section('intro', 'Intro', [
      {
        type: 'paragraph',
        children: [{ type: 'text', value: 'A short summary of the page.' }],
      },
      {
        type: 'paragraph',
        children: [{ type: 'text', value: 'A longer body that follows.' }],
      },
    ])
    expect(extractDescription(tree)).toBe('A short summary of the page.')
  })

  test('flattens inline emphasis and literals into the description text', () => {
    const tree = section('intro', 'Intro', [
      {
        type: 'paragraph',
        children: [
          { type: 'text', value: 'Defines the ' },
          { type: 'literal', value: 'merge_sphinx_config' },
          { type: 'text', value: ' helper.' },
        ],
      },
    ])
    expect(extractDescription(tree)).toBe('Defines the merge_sphinx_config helper.')
  })

  test('descends into the first sub-section if the page opens with one', () => {
    const tree = section('outer', 'Outer', [
      section('inner', 'Inner', [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'Inner page summary.' }],
        },
      ]),
    ])
    expect(extractDescription(tree)).toBe('Inner page summary.')
  })

  test('returns null when no paragraph exists anywhere in the tree', () => {
    const tree = section('empty', 'Empty', [{ type: 'transition' }])
    expect(extractDescription(tree)).toBeNull()
  })

  test('truncates with an ellipsis when the paragraph exceeds maxChars', () => {
    const tree = section('long', 'Long', [
      {
        type: 'paragraph',
        children: [{ type: 'text', value: 'a'.repeat(400) }],
      },
    ])
    const result = extractDescription(tree, { maxChars: 160 })
    expect(result).toHaveLength(160)
    expect(result?.endsWith('…')).toBe(true)
  })

  test('skips a leading badge-only paragraph and uses the first prose paragraph', () => {
    // Mirrors the gp-sphinx package overview shape: a header row of
    // status badges + GitHub/PyPI links, followed by the real
    // intro paragraph. The badge labels concatenated as
    // "Alpha GitHub PyPI" make a useless OG description; the
    // real summary lives in paragraph #2.
    const tree = section('pkg', 'Package', [
      {
        type: 'paragraph',
        children: [
          {
            type: 'badge',
            text: 'Alpha',
            tooltip: null,
            icon: null,
            size: null,
            style: 'full',
            classes: ['gp-sphinx-badge--meta-alpha'],
          },
          { type: 'text', value: ' ' },
          {
            type: 'reference',
            href: 'https://github.com/git-pull/gp-sphinx',
            classes: [],
            children: [{ type: 'text', value: 'GitHub' }],
          },
          { type: 'text', value: ' ' },
          {
            type: 'reference',
            href: 'https://pypi.org/project/sphinx-autodoc-fastmcp/',
            classes: [],
            children: [{ type: 'text', value: 'PyPI' }],
          },
        ],
      },
      {
        type: 'paragraph',
        children: [
          { type: 'text', value: 'Sphinx extension for documenting FastMCP tools.' },
        ],
      },
    ])
    expect(extractDescription(tree)).toBe(
      'Sphinx extension for documenting FastMCP tools.',
    )
  })
})
