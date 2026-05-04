/**
 * Tests for the in-page TOC builder.
 *
 * ``buildToc`` walks a Document's section tree and produces a flat
 * list of ``{id, text, depth}`` entries the right-rail TOC component
 * renders. The function is pure: no DOM, no network, no Astro
 * runtime; we feed it doctree fixtures and assert the output.
 */

import { describe, expect, test } from 'vitest'
import { buildToc, type TocEntry } from '../../src/render/build-toc.ts'
import type { BlockNode, Document } from '../../src/schemas/doctree.ts'

function section(
  id: string,
  title: string,
  children: BlockNode[] = [],
): Extract<BlockNode, { type: 'section' }> {
  return {
    type: 'section',
    id,
    title: [{ type: 'text', value: title }],
    children,
  }
}

function makeDocument(tree: Extract<BlockNode, { type: 'section' }>): Document {
  return {
    id: 'doc',
    title: tree.title
      .map((c) => (c.type === 'text' || c.type === 'literal' ? c.value : ''))
      .join(''),
    tree,
  }
}

describe('buildToc — flat document', () => {
  test('returns an empty array when the page has no sub-sections', () => {
    const doc = makeDocument(
      section('intro', 'Intro', [{ type: 'paragraph', children: [{ type: 'text', value: 'hi' }] }]),
    )
    expect(buildToc(doc.tree)).toEqual([])
  })

  test('top-level child sections become depth-1 entries', () => {
    const doc = makeDocument(
      section('intro', 'Intro', [section('overview', 'Overview'), section('details', 'Details')]),
    )
    expect(buildToc(doc.tree)).toEqual<TocEntry[]>([
      { id: 'overview', text: 'Overview', depth: 1 },
      { id: 'details', text: 'Details', depth: 1 },
    ])
  })
})

describe('buildToc — nested sections', () => {
  test('grandchild sections become depth-2 entries', () => {
    const doc = makeDocument(
      section('intro', 'Intro', [
        section('overview', 'Overview', [
          section('motivation', 'Motivation'),
          section('goals', 'Goals'),
        ]),
        section('details', 'Details'),
      ]),
    )
    expect(buildToc(doc.tree)).toEqual<TocEntry[]>([
      { id: 'overview', text: 'Overview', depth: 1 },
      { id: 'motivation', text: 'Motivation', depth: 2 },
      { id: 'goals', text: 'Goals', depth: 2 },
      { id: 'details', text: 'Details', depth: 1 },
    ])
  })

  test('respects the maxDepth option (default 2)', () => {
    const doc = makeDocument(
      section('intro', 'Intro', [section('a', 'A', [section('b', 'B', [section('c', 'C')])])]),
    )
    expect(buildToc(doc.tree)).toEqual<TocEntry[]>([
      { id: 'a', text: 'A', depth: 1 },
      { id: 'b', text: 'B', depth: 2 },
    ])
    expect(buildToc(doc.tree, { maxDepth: 3 })).toEqual<TocEntry[]>([
      { id: 'a', text: 'A', depth: 1 },
      { id: 'b', text: 'B', depth: 2 },
      { id: 'c', text: 'C', depth: 3 },
    ])
  })
})

describe('buildToc — title extraction', () => {
  test('concatenates text and inline-formatted titles into a single string', () => {
    const tree: Extract<BlockNode, { type: 'section' }> = {
      type: 'section',
      id: 'root',
      title: [{ type: 'text', value: 'Root' }],
      children: [
        {
          type: 'section',
          id: 'mixed',
          title: [
            { type: 'text', value: 'Hello ' },
            {
              type: 'strong',
              children: [{ type: 'text', value: 'world' }],
            },
            { type: 'text', value: '!' },
          ],
          children: [],
        },
      ],
    }
    expect(buildToc(tree)).toEqual<TocEntry[]>([{ id: 'mixed', text: 'Hello world!', depth: 1 }])
  })
})

describe('buildToc — robustness', () => {
  test('skips sections whose id is the empty string', () => {
    const doc = makeDocument(
      section('root', 'Root', [section('', 'No id'), section('with-id', 'With id')]),
    )
    expect(buildToc(doc.tree)).toEqual<TocEntry[]>([{ id: 'with-id', text: 'With id', depth: 1 }])
  })

  test('ignores non-section block children', () => {
    const doc = makeDocument(
      section('root', 'Root', [
        { type: 'paragraph', children: [{ type: 'text', value: 'hi' }] },
        section('only', 'Only'),
        { type: 'transition' },
      ]),
    )
    expect(buildToc(doc.tree)).toEqual<TocEntry[]>([{ id: 'only', text: 'Only', depth: 1 }])
  })
})
