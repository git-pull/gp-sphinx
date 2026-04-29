/**
 * Pure-function HTML renderer for one Symbol payload.
 *
 * Each entry in `src/content/api/symbols.json` describes one autodoc
 * symbol (function, class, method, …). `renderSymbol` produces the
 * structural HTML for that symbol — header with signature, summary,
 * parameters, return annotation, source attribution, and the
 * recursively-rendered docstring body. The docstring body uses the
 * existing `renderBlockNode` dispatch, so NumPy-style `definitionList`
 * rubrics, code blocks, admonitions, and cross-references work
 * uniformly with what doc pages render.
 *
 * Output is intentionally minimal: structural elements with stable
 * `gp-sphinx-symbol*` hooks. Tailwind v4 / OKLCH styling lands in a
 * later cycle.
 */

// The schema's ``Symbol`` type shadows the JavaScript global; alias on
// import so static analysers don't flag the shadow at every use site.
import type { Symbol as ApiSymbol, Parameter, SymbolSource } from '../schemas/symbol.ts'
import { renderBlockNode } from './render-node.ts'
import { type CodeHighlight, renderBlocksWithHighlighting } from './render-with-highlighting.ts'

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

function renderSignature(symbol: ApiSymbol): string {
  const parts: string[] = []
  if (symbol.module !== '') {
    parts.push(`<span class="gp-sphinx-symbol__module">${escapeHtml(symbol.module)}.</span>`)
  }
  parts.push(`<span class="gp-sphinx-symbol__name">${escapeHtml(symbol.qualname)}</span>`)
  parts.push(escapeHtml(symbol.signature))
  return `<code class="gp-sphinx-symbol__signature">${parts.join('')}</code>`
}

function renderParameter(param: Parameter): string {
  const annotation = param.annotation === null ? '' : escapeHtml(param.annotation)
  const defaultPart =
    param.default === null
      ? ''
      : ` <span class="gp-sphinx-symbol__param-default">= ${escapeHtml(param.default)}</span>`
  return `<dt>${escapeHtml(param.name)}</dt><dd>${annotation}${defaultPart}</dd>`
}

function renderParameters(parameters: readonly Parameter[]): string {
  if (parameters.length === 0) {
    return ''
  }
  const items = parameters.map(renderParameter).join('')
  return `<dl class="gp-sphinx-symbol__params">${items}</dl>`
}

function renderReturns(returns: string | null): string {
  if (returns === null) {
    return ''
  }
  return `<div class="gp-sphinx-symbol__returns"><code>${escapeHtml(returns)}</code></div>`
}

function renderSource(source: SymbolSource | null): string {
  if (source === null) {
    return ''
  }
  // Build a deep blob link (file + ``#L<line>``) so clicking lands
  // the reader on the exact line they're reading about. The repo
  // URL may have a trailing slash from how it's authored in the
  // Sphinx config; strip it so we never produce ``...//blob/...``.
  const repo = source.repo.replace(/\/+$/, '')
  const href = `${repo}/blob/main/${source.path}#L${source.line}`
  return [
    `<a class="gp-sphinx-symbol__source" href="${escapeHtml(href)}">`,
    escapeHtml(source.path),
    `:${source.line}`,
    '</a>',
  ].join('')
}

function renderSummary(summary: string): string {
  if (summary === '') {
    return ''
  }
  return `<p class="gp-sphinx-symbol__summary">${escapeHtml(summary)}</p>`
}

function renderBody(
  body: ApiSymbol['docstring_body'],
  highlight: CodeHighlight | undefined,
): string {
  if (body.length === 0) {
    return ''
  }
  const blocks =
    highlight === undefined
      ? body.map(renderBlockNode).join('')
      : renderBlocksWithHighlighting(body, highlight)
  return `<div class="gp-sphinx-symbol__body">${blocks}</div>`
}

export function renderSymbol(symbol: ApiSymbol, highlight?: CodeHighlight): string {
  const classAttr = `class="gp-sphinx-symbol gp-sphinx-symbol--${symbol.kind}"`
  const idAttr = `id="${escapeHtml(symbol.id)}"`
  const dataAttr = `data-symbol-id="${escapeHtml(symbol.id)}"`
  const headerHtml = `<header class="gp-sphinx-symbol__header">${renderSignature(symbol)}</header>`
  const summaryHtml = renderSummary(symbol.docstring_summary)
  const paramsHtml = renderParameters(symbol.parameters)
  const returnsHtml = renderReturns(symbol.returns)
  const bodyHtml = renderBody(symbol.docstring_body, highlight)
  const sourceHtml = renderSource(symbol.source)
  return [
    `<article ${classAttr} ${idAttr} ${dataAttr}>`,
    headerHtml,
    summaryHtml,
    paramsHtml,
    returnsHtml,
    bodyHtml,
    sourceHtml,
    '</article>',
  ].join('')
}
