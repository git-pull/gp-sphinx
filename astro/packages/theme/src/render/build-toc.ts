/**
 * Pure-function in-page table-of-contents builder.
 *
 * Walks a Document's section tree and produces a flat list of
 * ``{id, text, depth}`` entries the right-rail TOC component
 * renders. The page's top-level heading (the document title) is
 * the ``<h1>`` and gets skipped — the TOC starts at the children of
 * the root section, which render as ``<h2>``.
 *
 * Title text is flattened across inline children: ``[text, strong,
 * text]`` becomes a single concatenated string. Sections with an
 * empty id are skipped (they cannot be linked).
 */

import type { BlockNode, InlineNode } from '../schemas/doctree.ts'

export interface TocEntry {
  id: string
  text: string
  depth: number
}

export interface BuildTocOptions {
  /**
   * Maximum heading depth to include, where ``1`` is the children of
   * the root section (rendered as ``<h2>``) and ``2`` is the
   * grandchildren (rendered as ``<h3>``). Defaults to ``2``, which
   * matches the ``tocMinLevel: 2`` / ``tocMaxLevel: 3`` shape that
   * tony.sh uses.
   */
  maxDepth?: number
}

type SectionNode = Extract<BlockNode, { type: 'section' }>

function flattenTitle(title: readonly InlineNode[]): string {
  const parts: string[] = []
  for (const node of title) {
    if (node.type === 'text' || node.type === 'literal') {
      parts.push(node.value)
    } else if (node.type === 'emphasis' || node.type === 'strong' || node.type === 'reference') {
      parts.push(flattenTitle(node.children))
    } else if (node.type === 'badge') {
      parts.push(node.text)
    }
    // 'image' has no text content — skip.
  }
  return parts.join('')
}

function walk(section: SectionNode, currentDepth: number, maxDepth: number, out: TocEntry[]): void {
  if (currentDepth > maxDepth) {
    return
  }
  for (const child of section.children) {
    if (child.type !== 'section') {
      continue
    }
    if (child.id !== '') {
      out.push({
        id: child.id,
        text: flattenTitle(child.title),
        depth: currentDepth,
      })
    }
    walk(child, currentDepth + 1, maxDepth, out)
  }
}

export function buildToc(tree: SectionNode, options: BuildTocOptions = {}): TocEntry[] {
  const maxDepth = options.maxDepth ?? 2
  const out: TocEntry[] = []
  walk(tree, 1, maxDepth, out)
  return out
}
