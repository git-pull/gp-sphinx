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
})
