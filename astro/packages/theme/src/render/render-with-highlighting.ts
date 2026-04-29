/**
 * Highlighting-aware document renderer.
 *
 * A thin variant of the pure ``renderDocument``: every node type
 * renders identically to ``renderBlockNode`` *except* ``literalBlock``,
 * which goes through an injected highlighter (Shiki in production,
 * a stub in tests). Block-bearing nodes (sections, blockquotes,
 * admonitions, list items, API/CLI layout containers) recurse so
 * nested literalBlocks also pick up the highlighter.
 *
 * Inline nodes never carry a literalBlock (only block contexts do)
 * so we delegate inline rendering straight to ``renderInlineNode``.
 */

import type {
  BlockNode,
  DefinitionListItemNode,
  Document,
  ListItemNode,
} from '../schemas/doctree.ts'
import { renderBlockNode, renderInlineNode } from './render-node.ts'

export type CodeHighlight = (code: string, language: string | null) => string

type SectionNode = Extract<BlockNode, { type: 'section' }>

const HTML_ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (c) => HTML_ESCAPES[c] ?? c)
}

function renderListItem(item: ListItemNode, highlight: CodeHighlight): string {
  return `<li>${item.children.map((c) => renderBlock(c, highlight)).join('')}</li>`
}

function renderDefinitionListItem(item: DefinitionListItemNode, highlight: CodeHighlight): string {
  const term = `<dt>${item.term.map(renderInlineNode).join('')}</dt>`
  const definition = `<dd>${item.definition.map((c) => renderBlock(c, highlight)).join('')}</dd>`
  return `${term}${definition}`
}

function renderSection(node: SectionNode, depth: number, highlight: CodeHighlight): string {
  const tag = `h${Math.min(depth, 6)}`
  const titleHtml = node.title.map(renderInlineNode).join('')
  const childrenHtml = node.children
    .map((child) =>
      child.type === 'section'
        ? renderSection(child, depth + 1, highlight)
        : renderBlock(child, highlight),
    )
    .join('')
  return `<section id="${escapeHtml(node.id)}"><${tag}>${titleHtml}</${tag}>${childrenHtml}</section>`
}

function renderBlock(node: BlockNode, highlight: CodeHighlight): string {
  switch (node.type) {
    case 'literalBlock':
      return highlight(node.code, node.language)
    case 'section':
      return renderSection(node, 1, highlight)
    case 'blockQuote':
      return `<blockquote>${node.children.map((c) => renderBlock(c, highlight)).join('')}</blockquote>`
    case 'bulletList':
      return `<ul>${node.children.map((c) => renderListItem(c, highlight)).join('')}</ul>`
    case 'enumeratedList': {
      const startAttr = node.start === null ? '' : ` start="${node.start}"`
      return `<ol${startAttr}>${node.children.map((c) => renderListItem(c, highlight)).join('')}</ol>`
    }
    case 'admonition':
      return `<aside class="admonition admonition--${escapeHtml(node.variant)}">${node.children.map((c) => renderBlock(c, highlight)).join('')}</aside>`
    case 'definitionList':
      return `<dl>${node.children.map((c) => renderDefinitionListItem(c, highlight)).join('')}</dl>`
    default:
      // ``apiLayout`` and ``cliCommand`` carry block children too, but
      // their rendering chrome (open/close tags) is private to
      // ``render-node.ts``; rather than duplicate that markup, we
      // delegate the entire branch — nested literalBlocks inside an
      // ``apiLayout`` keep the legacy ``<pre><code>`` rendering, which
      // is acceptable since those layouts mostly carry inline content
      // (signatures, badges) rather than fenced code.
      return renderBlockNode(node)
  }
}

export function renderDocumentWithHighlighting(doc: Document, highlight: CodeHighlight): string {
  return renderSection(doc.tree, 1, highlight)
}

/**
 * Render a list of block nodes (e.g. a Symbol's ``docstring_body``)
 * with the same dispatch the document renderer uses. Exposed so
 * ``renderSymbol`` can thread the highlighter through autodoc body
 * literalBlocks (NumPy ``Examples`` doctests).
 */
export function renderBlocksWithHighlighting(
  blocks: readonly BlockNode[],
  highlight: CodeHighlight,
): string {
  return blocks.map((b) => renderBlock(b, highlight)).join('')
}
