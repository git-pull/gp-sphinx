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
import {
  renderApiLayoutChrome,
  renderBlockNode,
  renderCliCommandChrome,
  renderInlineNode,
  renderTable,
} from './render-node.ts'

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
  const headerlink =
    node.id === ''
      ? ''
      : `<a class="headerlink" href="#${escapeHtml(node.id)}" aria-label="Permalink to this section">#</a>`
  return `<section id="${escapeHtml(node.id)}"><${tag}>${titleHtml}${headerlink}</${tag}>${childrenHtml}</section>`
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
    case 'admonition': {
      const variant = escapeHtml(node.variant)
      const titleHtml =
        node.title === null
          ? ''
          : `<p class="admonition-title">${node.title.map(renderInlineNode).join('')}</p>`
      const bodyHtml = node.children.map((c) => renderBlock(c, highlight)).join('')
      return `<aside class="admonition admonition--${variant}">${titleHtml}${bodyHtml}</aside>`
    }
    case 'footnote': {
      const baseClass = `gp-sphinx-${node.kind}`
      const idAttr = node.id === '' ? '' : ` id="${escapeHtml(node.id)}"`
      const labelHtml = `<span class="${baseClass}__label">[${escapeHtml(node.label)}]</span>`
      const bodyHtml = `<div class="${baseClass}__body">${node.children.map((c) => renderBlock(c, highlight)).join('')}</div>`
      return `<aside class="${baseClass}" role="doc-${node.kind === 'footnote' ? 'footnote' : 'biblioentry'}"${idAttr}>${labelHtml}${bodyHtml}</aside>`
    }
    case 'definitionList':
      return `<dl>${node.children.map((c) => renderDefinitionListItem(c, highlight)).join('')}</dl>`
    case 'apiLayout':
      // Recurse through apiLayout children with the highlighter so any
      // nested ``literalBlock`` (NumPy ``Examples`` doctests, fenced
      // code inside autodoc-style regions, confval/role example
      // blocks…) reaches the highlighter rather than falling back to
      // plain ``<pre><code>``. The chrome itself is composed by the
      // shared ``renderApiLayoutChrome`` helper to avoid duplicating
      // the per-component markup.
      return renderApiLayoutChrome(
        node,
        node.children.map((c) => renderBlock(c, highlight)).join(''),
      )
    case 'cliCommand':
      return renderCliCommandChrome(
        node,
        node.children.map((c) => renderBlock(c, highlight)).join(''),
      )
    case 'table':
      // Recurse cell children through the highlighting block
      // renderer so a ``literalBlock`` (e.g. a code example
      // inside a cell) reaches Shiki rather than falling back
      // to plain ``<pre>``.
      return renderTable(node, (c) => renderBlock(c, highlight))
    default:
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
