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

/**
 * Return ``true`` if a paragraph carries no real prose — only badges,
 * cross-references with badge-like labels, and whitespace text.
 *
 * gp-sphinx package overview pages open with a row of status / source
 * / PyPI badges (e.g. ``Alpha GitHub PyPI``); flattening those into
 * meta description text produces a useless three-word string. Skip
 * such paragraphs so the first real prose sentence wins.
 */
function isBadgeOnlyParagraph(paragraph: ParagraphNode): boolean {
  let sawSubstantive = false
  for (const child of paragraph.children) {
    if (child.type === 'badge') {
      continue
    }
    if (child.type === 'text' && child.value.trim() === '') {
      continue
    }
    if (child.type === 'reference') {
      // A reference whose only inline content is a single short text
      // node (≤16 chars, no internal whitespace) is treated as a
      // badge-equivalent link — typical for "GitHub", "PyPI",
      // "Docs", "Issues" header chips. Anything longer is real prose.
      const refText = child.children
        .map((c) => (c.type === 'text' ? c.value : ''))
        .join('')
        .trim()
      if (refText.length > 0 && refText.length <= 16 && !/\s/.test(refText)) {
        continue
      }
    }
    sawSubstantive = true
    break
  }
  return !sawSubstantive
}

function findFirstParagraph(section: SectionNode): ParagraphNode | null {
  for (const child of section.children) {
    if (child.type === 'paragraph') {
      if (isBadgeOnlyParagraph(child)) {
        continue
      }
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
