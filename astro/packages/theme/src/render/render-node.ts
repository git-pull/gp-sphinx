/**
 * Pure-function HTML renderer for the doctree wire format.
 *
 * Each :doc:`gp_sphinx_astro_builder` Pydantic node type maps to a small
 * HTML pattern. The function shape — pure, returning a single string —
 * keeps the renderer easy to test and easy to wrap in an Astro component
 * later (Step 8 will use ``<Fragment set:html={renderDocument(...)} />``).
 *
 * The output is intentionally minimal: no Tailwind classes, no inline
 * styles, just structural HTML with stable hooks (section ids, admonition
 * variant classes, ``data-symbol-id``) so the theme's CSS can target it
 * without coupling the renderer to a styling system.
 */

import type {
  BlockNode,
  DefinitionListItemNode,
  Document,
  InlineNode,
  ListItemNode,
} from '../schemas/doctree.ts'

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

export function renderInlineNode(node: InlineNode): string {
  switch (node.type) {
    case 'text':
      return escapeHtml(node.value)
    case 'literal':
      return `<code>${escapeHtml(node.value)}</code>`
    case 'emphasis':
      return `<em>${node.children.map(renderInlineNode).join('')}</em>`
    case 'strong':
      return `<strong>${node.children.map(renderInlineNode).join('')}</strong>`
    case 'reference': {
      // Preserve Sphinx domain-role classes (``xref`` / ``py-func`` /
      // ``std-term`` / …) so CSS can style each role distinctly. The
      // attribute is omitted when the class list is empty so plain
      // external links don't gain a stray ``class=""``.
      const classAttr =
        node.classes.length === 0 ? '' : ` class="${escapeHtml(node.classes.join(' '))}"`
      return `<a href="${escapeHtml(node.href)}"${classAttr}>${node.children.map(renderInlineNode).join('')}</a>`
    }
    case 'footnoteReference': {
      // Footnote / citation jumps render as a bracketed superscript so
      // they read as inline references rather than body text. The
      // ``kind`` discriminator drives a single class so CSS can style
      // citations (``Smith2020``) differently from numeric footnotes.
      const refClass = `gp-sphinx-${node.kind}-reference`
      const escapedHref = escapeHtml(node.href)
      const escapedLabel = escapeHtml(node.label)
      return `<sup class="${refClass}-wrap"><a class="${refClass}" href="${escapedHref}">[${escapedLabel}]</a></sup>`
    }
    case 'image':
      return node.alt === null
        ? `<img src="${escapeHtml(node.uri)}" />`
        : `<img src="${escapeHtml(node.uri)}" alt="${escapeHtml(node.alt)}" />`
    case 'badge': {
      const classes = ['gp-sphinx-badge', `gp-sphinx-badge--style-${node.style}`]
      if (node.size !== null) {
        classes.push(`gp-sphinx-badge--size-${node.size}`)
      }
      const tooltipAttr =
        node.tooltip === null
          ? ''
          : ` title="${escapeHtml(node.tooltip)}" aria-label="${escapeHtml(node.tooltip)}"`
      const iconAttr = node.icon === null ? '' : ` data-icon="${escapeHtml(node.icon)}"`
      return `<span class="${classes.join(' ')}"${tooltipAttr}${iconAttr} role="note"><span class="gp-sphinx-badge__label">${escapeHtml(node.text)}</span></span>`
    }
  }
}

function renderListItem(item: ListItemNode): string {
  return `<li>${item.children.map(renderBlockNode).join('')}</li>`
}

function renderDefinitionListItem(item: DefinitionListItemNode): string {
  const term = `<dt>${item.term.map(renderInlineNode).join('')}</dt>`
  const definition = `<dd>${item.definition.map(renderBlockNode).join('')}</dd>`
  return `${term}${definition}`
}

function renderSection(node: Extract<BlockNode, { type: 'section' }>, depth: number): string {
  const tag = `h${Math.min(depth, 6)}`
  const titleHtml = node.title.map(renderInlineNode).join('')
  const childrenHtml = node.children
    .map((child) =>
      child.type === 'section' ? renderSection(child, depth + 1) : renderBlockNode(child),
    )
    .join('')
  // ``headerlink`` mirrors Sphinx/Furo: a small ``#`` icon that
  // appears on heading hover so readers can copy a deep link.
  // Skip it when the section carries no id (no anchor to link to).
  const headerlink =
    node.id === ''
      ? ''
      : `<a class="headerlink" href="#${escapeHtml(node.id)}" aria-label="Permalink to this section">#</a>`
  return `<section id="${escapeHtml(node.id)}"><${tag}>${titleHtml}${headerlink}</${tag}>${childrenHtml}</section>`
}

export function renderBlockNode(node: BlockNode): string {
  switch (node.type) {
    case 'paragraph':
      return `<p>${node.children.map(renderInlineNode).join('')}</p>`
    case 'literalBlock': {
      const className =
        node.language === null ? '' : ` class="language-${escapeHtml(node.language)}"`
      return `<pre><code${className}>${escapeHtml(node.code)}</code></pre>`
    }
    case 'comment':
      return `<!-- ${escapeHtml(node.value)} -->`
    case 'transition':
      return '<hr />'
    case 'blockQuote':
      return `<blockquote>${node.children.map(renderBlockNode).join('')}</blockquote>`
    case 'bulletList':
      return `<ul>${node.children.map(renderListItem).join('')}</ul>`
    case 'enumeratedList': {
      const startAttr = node.start === null ? '' : ` start="${node.start}"`
      return `<ol${startAttr}>${node.children.map(renderListItem).join('')}</ol>`
    }
    case 'admonition':
      return `<aside class="admonition admonition--${escapeHtml(node.variant)}">${node.children.map(renderBlockNode).join('')}</aside>`
    case 'footnote': {
      const baseClass = `gp-sphinx-${node.kind}`
      const idAttr = node.id === '' ? '' : ` id="${escapeHtml(node.id)}"`
      const labelHtml = `<span class="${baseClass}__label">[${escapeHtml(node.label)}]</span>`
      const bodyHtml = `<div class="${baseClass}__body">${node.children.map(renderBlockNode).join('')}</div>`
      return `<aside class="${baseClass}" role="doc-${node.kind === 'footnote' ? 'footnote' : 'biblioentry'}"${idAttr}>${labelHtml}${bodyHtml}</aside>`
    }
    case 'definitionList':
      return `<dl>${node.children.map(renderDefinitionListItem).join('')}</dl>`
    case 'symbolRef': {
      const escapedId = escapeHtml(node.symbolId)
      // Symbol pages live at ``/api/<id>/`` in the dogfood Astro app.
      // The doctree's ``symbolRef`` is the navigation anchor between
      // narrative pages and symbol pages; the renderer doesn't need
      // the full Symbol payload here, only its id.
      return `<a class="symbol-ref" data-symbol-id="${escapedId}" href="/api/${escapedId}/">${escapedId}</a>`
    }
    case 'section':
      return renderSection(node, 1)
    case 'apiLayout':
      return renderApiLayoutNode(node)
    case 'cliCommand':
      return renderCliCommandNode(node)
  }
}

/**
 * Compose the apiLayout chrome around a pre-rendered ``childrenHtml`` string.
 *
 * Split out from ``renderApiLayoutNode`` so the highlighting-aware
 * variant in ``render-with-highlighting.ts`` can recurse through the
 * tree (passing the highlighter to nested ``literalBlock`` nodes) and
 * still reuse the exact same chrome — no markup duplication, no risk
 * of the two renderers drifting apart.
 */
export function renderApiLayoutChrome(
  node: Extract<BlockNode, { type: 'apiLayout' }>,
  childrenHtml: string,
): string {
  const baseClasses = ['gp-sphinx-api', `gp-sphinx-api--${node.component}`]
  if (node.kind !== null) {
    baseClasses.push(`gp-sphinx-api--kind-${node.kind}`)
  }
  if (node.name !== null && node.name !== '') {
    baseClasses.push(node.name)
  }
  for (const c of node.classes) {
    baseClasses.push(c)
  }

  const classAttr = `class="${baseClasses.join(' ')}"`

  switch (node.component) {
    case 'fold':
    case 'sig_fold': {
      const openAttr = node.open ? ' open' : ''
      const summaryHtml = `<summary>${escapeHtml(node.summary ?? '')}</summary>`
      return `<details ${classAttr}${openAttr}>${summaryHtml}${childrenHtml}</details>`
    }
    case 'permalink': {
      const titleAttr = node.title === null ? '' : ` title="${escapeHtml(node.title)}"`
      return `<a ${classAttr} href="${escapeHtml(node.href ?? '#')}"${titleAttr}>${childrenHtml}</a>`
    }
    case 'slot':
      return `<span ${classAttr} data-slot="${escapeHtml(node.slot ?? '')}"></span>`
    case 'inline_component': {
      const tag = node.tag ?? 'span'
      return `<${tag} ${classAttr}>${childrenHtml}</${tag}>`
    }
    case 'region':
    case 'component': {
      const tag = node.tag ?? 'div'
      return `<${tag} ${classAttr}>${childrenHtml}</${tag}>`
    }
  }
}

function renderApiLayoutNode(node: Extract<BlockNode, { type: 'apiLayout' }>): string {
  return renderApiLayoutChrome(node, node.children.map(renderBlockNode).join(''))
}

/**
 * Compose the cliCommand chrome around a pre-rendered ``childrenHtml`` string.
 *
 * Mirror of :func:`renderApiLayoutChrome`. Same rationale.
 */
export function renderCliCommandChrome(
  node: Extract<BlockNode, { type: 'cliCommand' }>,
  childrenHtml: string,
): string {
  const baseClasses = ['gp-sphinx-cli', `gp-sphinx-cli--${node.component}`]
  for (const c of node.classes) {
    baseClasses.push(c)
  }
  const classAttr = `class="${baseClasses.join(' ')}"`

  switch (node.component) {
    case 'program': {
      const progAttr = node.prog === null ? '' : ` data-prog="${escapeHtml(node.prog)}"`
      return `<section ${classAttr}${progAttr}>${childrenHtml}</section>`
    }
    case 'usage':
      return `<pre class="gp-sphinx-cli__usage">${escapeHtml(node.usage ?? '')}</pre>`
    case 'group': {
      const titleHtml =
        node.title === null
          ? ''
          : `<h3 class="gp-sphinx-cli__group-title">${escapeHtml(node.title)}</h3>`
      const descHtml =
        node.description === null
          ? ''
          : `<p class="gp-sphinx-cli__group-description">${escapeHtml(node.description)}</p>`
      return `<section ${classAttr}>${titleHtml}${descHtml}${childrenHtml}</section>`
    }
    case 'argument': {
      const namesHtml = node.names.map((n) => `<code>${escapeHtml(n)}</code>`).join(' ')
      const metavarHtml =
        node.metavar === null
          ? ''
          : ` <var class="gp-sphinx-cli__metavar">${escapeHtml(node.metavar)}</var>`
      const helpHtml = node.help === null ? '' : escapeHtml(node.help)
      const defaultHtml =
        node.default === null
          ? ''
          : ` <span class="gp-sphinx-cli__default">(default: <code>${escapeHtml(node.default)}</code>)</span>`
      const choicesHtml =
        node.choices.length === 0
          ? ''
          : ` <span class="gp-sphinx-cli__choices">{${node.choices.map(escapeHtml).join(', ')}}</span>`
      return `<dl class="gp-sphinx-cli__arg"><dt>${namesHtml}${metavarHtml}</dt><dd>${helpHtml}${defaultHtml}${choicesHtml}</dd></dl>`
    }
    case 'subcommands': {
      const titleHtml =
        node.title === null
          ? ''
          : `<h2 class="gp-sphinx-cli__subcommands-title">${escapeHtml(node.title)}</h2>`
      return `<section ${classAttr}>${titleHtml}${childrenHtml}</section>`
    }
    case 'subcommand': {
      const aliasesHtml =
        node.aliases.length === 0
          ? ''
          : ` <span class="gp-sphinx-cli__aliases">(${node.aliases.map(escapeHtml).join(', ')})</span>`
      const summaryHtml = `<summary><code>${escapeHtml(node.name ?? '')}</code>${aliasesHtml}</summary>`
      const helpHtml =
        node.help === null
          ? ''
          : `<p class="gp-sphinx-cli__subcommand-help">${escapeHtml(node.help)}</p>`
      return `<details ${classAttr}>${summaryHtml}${helpHtml}${childrenHtml}</details>`
    }
  }
}

function renderCliCommandNode(node: Extract<BlockNode, { type: 'cliCommand' }>): string {
  return renderCliCommandChrome(node, node.children.map(renderBlockNode).join(''))
}

export function renderDocument(doc: Document): string {
  return renderSection(doc.tree, 1)
}
