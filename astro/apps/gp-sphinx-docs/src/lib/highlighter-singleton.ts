/**
 * Module-cached Shiki highlighter shared across all 242 build pages.
 *
 * Building a Shiki ``Highlighter`` loads the WASM regex engine and a
 * grammar bundle for every requested language; doing it once per
 * route would cost seconds across the corpus. This module memoises
 * the awaited highlighter so each Astro page just consumes the
 * promise.
 *
 * The bundled language list intentionally stays narrow — only
 * languages that actually appear in the gp-sphinx docs corpus
 * (``python``, ``typescript``, ``console`` for shell prompts,
 * ``json`` / ``yaml`` / ``toml`` for configs, ``rst`` and ``md``
 * for the docs themselves). Unknown languages fall back to plain
 * ``<pre><code>`` cleanly via the helper.
 */

import {
  type CodeHighlighter,
  createCodeHighlighter,
} from '@gp-sphinx-astro/theme/render/highlight-code'

let cached: Promise<CodeHighlighter> | null = null

export function getCodeHighlighter(): Promise<CodeHighlighter> {
  if (cached === null) {
    cached = createCodeHighlighter({
      themes: { light: 'github-light', dark: 'github-dark' },
      langs: [
        'python',
        'typescript',
        'tsx',
        'javascript',
        'jsx',
        'console',
        'bash',
        'shell',
        'json',
        'yaml',
        'toml',
        'ini',
        'rst',
        'md',
        'markdown',
        'mdx',
        'css',
        'html',
        'xml',
        'diff',
      ],
      // ``myst`` (MyST-Markdown), ``rest`` and ``restructuredtext``
      // aren't first-class Shiki bundles but are aliases over the
      // markdown / rst grammars; the helper rewrites them to a
      // bundled grammar before lookup.
      aliases: {
        myst: 'markdown',
        rest: 'rst',
        restructuredtext: 'rst',
        text: null,
        plaintext: null,
      },
    })
  }
  return cached
}
