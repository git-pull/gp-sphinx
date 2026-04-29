/**
 * Pure-function description extractor for the doctree.
 *
 * Walks a Document's section tree and pulls the text of the first
 * paragraph it finds (descending into the first sub-section when
 * the section starts with one). Used by the dogfood layout to
 * derive ``<meta name="description">`` content automatically rather
 * than asking authors to write a frontmatter blurb.
 */

import type { BlockNode, InlineNode } from '../schemas/doctree.ts'

type SectionNode = Extract<BlockNode, { type: 'section' }>
type ParagraphNode = Extract<BlockNode, { type: 'paragraph' }>

export interface ExtractDescriptionOptions {
  /**
   * Truncate to this many characters; the result still ends with an
   * ellipsis so the cut isn't ambiguous. Defaults to no truncation.
   */
  maxChars?: number
}

function flattenInline(nodes: readonly InlineNode[]): string {
  const parts: string[] = []
  for (const node of nodes) {
    if (node.type === 'text' || node.type === 'literal') {
      parts.push(node.value)
    } else if (node.type === 'emphasis' || node.type === 'strong' || node.type === 'reference') {
      parts.push(flattenInline(node.children))
    } else if (node.type === 'badge') {
      parts.push(node.text)
    }
    // ``image`` carries no text — skip.
  }
  return parts.join('')
}

function findFirstParagraph(section: SectionNode): ParagraphNode | null {
  for (const child of section.children) {
    if (child.type === 'paragraph') {
      return child
    }
    if (child.type === 'section') {
      const inner = findFirstParagraph(child)
      if (inner !== null) {
        return inner
      }
    }
  }
  return null
}

function truncate(text: string, max: number): string {
  if (text.length <= max) {
    return text
  }
  return `${text.slice(0, max - 1)}…`
}

export function extractDescription(
  tree: SectionNode,
  options: ExtractDescriptionOptions = {},
): string | null {
  const paragraph = findFirstParagraph(tree)
  if (paragraph === null) {
    return null
  }
  const text = flattenInline(paragraph.children)
  if (options.maxChars === undefined) {
    return text
  }
  return truncate(text, options.maxChars)
}
