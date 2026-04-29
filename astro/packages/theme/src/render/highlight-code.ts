/**
 * Shiki-backed code highlighter for the doctree's literal blocks.
 *
 * Shiki's ``createHighlighter`` loads the WASM regex engine and the
 * requested grammars lazily; once awaited, ``codeToHtml`` is sync
 * and composes cleanly with the existing pure ``renderBlockNode``.
 * The returned ``highlight`` carries two themes — ``light`` and
 * ``dark`` — and emits Shiki's dual-theme markup so the site's
 * ``data-theme-mode`` attribute on ``<html>`` swaps the colours
 * without re-rendering.
 *
 * Unknown languages and a null language fall back to plain
 * ``<pre><code>`` markup matching the legacy ``renderBlockNode``
 * output. We never throw — a typo in a doc's ``language`` attribute
 * shouldn't fail the build.
 */

import { type BundledLanguage, createHighlighter } from 'shiki'

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

function fallback(code: string, language: string | null): string {
  const escaped = escapeHtml(code)
  if (language === null || language === '') {
    return `<pre><code>${escaped}</code></pre>`
  }
  return `<pre><code class="language-${escapeHtml(language)}">${escaped}</code></pre>`
}

export type CodeHighlighter = (code: string, language: string | null) => string

export interface CreateCodeHighlighterOptions {
  themes: { light: string; dark: string }
  langs: readonly string[]
  /**
   * Optional alias map. Keys are the language identifiers Sphinx
   * may emit on a fenced code block (``myst``, ``restructuredtext``,
   * ``plaintext``, …); values are either the canonical Shiki
   * grammar name to substitute (``"markdown"``) or ``null`` to
   * force the plain fallback path.
   */
  aliases?: Record<string, string | null>
}

export async function createCodeHighlighter(
  options: CreateCodeHighlighterOptions,
): Promise<CodeHighlighter> {
  const requestedLangs = options.langs as readonly BundledLanguage[]
  const highlighter = await createHighlighter({
    themes: [options.themes.light, options.themes.dark],
    langs: requestedLangs,
  })
  const knownLangs = new Set<string>(highlighter.getLoadedLanguages())
  const aliases = options.aliases ?? {}
  return (code, language) => {
    if (language === null || language === '') {
      return fallback(code, language)
    }
    // Aliases first: the source code's literal language string maps
    // to a canonical Shiki grammar (or null to force the fallback).
    let resolved: string = language
    if (Object.hasOwn(aliases, language)) {
      const aliased = aliases[language]
      if (aliased === null) {
        return fallback(code, language)
      }
      if (aliased !== undefined) {
        resolved = aliased
      }
    }
    if (!knownLangs.has(resolved)) {
      return fallback(code, language)
    }
    try {
      return highlighter.codeToHtml(code, {
        lang: resolved as BundledLanguage,
        themes: {
          light: options.themes.light,
          dark: options.themes.dark,
        },
        defaultColor: 'light',
      })
    } catch {
      return fallback(code, language)
    }
  }
}
