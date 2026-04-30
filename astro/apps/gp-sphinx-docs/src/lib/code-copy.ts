/**
 * Copy-to-clipboard buttons for fenced code blocks.
 *
 * The Pydantic→Zod renderer emits each fenced block as
 * ``<pre><code class="language-foo">…</code></pre>``. This module
 * walks the rendered DOM and decorates each ``<pre>`` with a small
 * copy button positioned in the top-right corner. Clicking the
 * button writes the inner ``<code>`` text to the clipboard and
 * flips the button into a "copied" state for a moment so the user
 * gets visible confirmation.
 *
 * Before writing, the captured text is run through :func:`formatCopyText`
 * which strips REPL / shell prompts (``>>> ``, ``... ``, ``$ ``,
 * ``# ``) so pasting a doctest or shell session yields runnable
 * code without the prompt prefixes — mirroring the contract of
 * sphinx-copybutton (``~/study/python/sphinx-copybutton/sphinx_copybutton/_static/copybutton_funcs.js``).
 *
 * The function is idempotent — re-running it on the same root after
 * an SPA navigation or a re-render leaves already-decorated blocks
 * untouched. Pages without ``<pre><code>`` pairs are no-ops.
 */

const COPIED_RESET_MS = 1500

/**
 * Regex anchored to the start of a line that captures one of the
 * supported prompt prefixes plus the trailing space. Each entry is
 * of the shape ``[(prompt regex with capture group), …]``; the
 * matching group ``[1]`` covers the prompt and is stripped.
 *
 * Order matters: ``... `` (Python continuation) must be tested
 * before ``$ `` and ``# `` so a stray ``... # comment`` line still
 * matches the continuation prefix rather than the root-shell one.
 */
const PROMPT_PATTERNS: readonly RegExp[] = [
  /^(>>> ?)(.*)$/,
  /^(\.\.\. ?)(.*)$/,
  /^(\$ )(.*)$/,
  /^(# )(.*)$/,
]

function matchPrompt(line: string): { prompt: string; rest: string } | null {
  for (const re of PROMPT_PATTERNS) {
    const m = line.match(re)
    if (m !== null) {
      return { prompt: m[1] ?? '', rest: m[2] ?? '' }
    }
  }
  return null
}

/**
 * Strip REPL / shell prompts from copied code text.
 *
 * If any line in ``text`` starts with a recognised prompt
 * (``>>> ``, ``... ``, ``$ ``, ``# ``), the function returns only
 * the prompted lines — with their prompts removed — preserving
 * blank lines between them. Non-prompted lines (typical doctest
 * output, e.g. ``'config'`` after ``>>> spec.text``) are skipped.
 *
 * If no line carries a prompt, the original text is returned
 * unchanged so plain code blocks (``def f(): ...``) are copied
 * verbatim.
 *
 * A trailing newline is always trimmed so that pasting into a
 * shell does not auto-execute the last command.
 */
export function formatCopyText(text: string): string {
  const lines = text.split('\n')
  const stripped: string[] = []
  let sawPrompt = false
  for (const line of lines) {
    const m = matchPrompt(line)
    if (m !== null) {
      sawPrompt = true
      stripped.push(m.rest)
      continue
    }
    if (line.trim() === '' && sawPrompt) {
      // Preserve blank lines that punctuate a multi-step session
      // (e.g. ``>>> a = 1\n\n>>> b = 2``).
      stripped.push(line)
    }
    // Otherwise it's an output line under a prompted session — skip.
  }
  const result = sawPrompt ? stripped.join('\n') : text
  return result.endsWith('\n') ? result.slice(0, -1) : result
}

/**
 * Token strings that, when they appear as the EXACT textContent of
 * a Shiki span, mark that span as a REPL / shell prompt. Tagging
 * these spans with ``select-none`` (Tailwind ``user-select: none``)
 * means triple-clicking a prompted line picks the command body —
 * the user can paste it back into a shell or REPL without manually
 * stripping the ``>>> `` / ``$ `` prefix. Mirrors the contract of
 * sphinx-copybutton's prompt detection.
 */
const PROMPT_TOKENS: ReadonlySet<string> = new Set(['>>>', '...', '$', '#'])

/**
 * Regex matching a recognised prompt at the START of a string,
 * INCLUDING the trailing whitespace separator. The full match is
 * what gets moved into a non-selectable prefix span so triple-
 * click selection starts cleanly at the command body rather than
 * at a leading space.
 */
const PROMPT_PREFIX = /^(>>>|\.\.\.|\$|#)(\s+)/

function splitPromptIfBundled(span: HTMLElement): void {
  // Shiki's ``console`` (and some Python shell renderings)
  // tokenize the entire line as a single coloured span. Detect a
  // leading prompt + whitespace, hoist BOTH into a non-selectable
  // prefix so the selection cursor stops at the command body.
  if (span.children.length > 0) {
    return
  }
  const text = span.textContent ?? ''
  const match = text.match(PROMPT_PREFIX)
  if (match === null) {
    return
  }
  const prefix = match[0]
  const rest = text.slice(prefix.length)
  const promptSpan = document.createElement('span')
  promptSpan.classList.add('select-none')
  if (span.getAttribute('style') !== null) {
    promptSpan.setAttribute('style', span.getAttribute('style') ?? '')
  }
  promptSpan.textContent = prefix
  span.textContent = rest
  span.parentNode?.insertBefore(promptSpan, span)
}

/**
 * After a span has been tagged exact-match as a prompt token
 * (cycle 74's first pass), check its NEXT-sibling span. If that
 * sibling starts with whitespace, hoist the leading whitespace
 * into a select-none sibling between them so the selection cursor
 * stops at the command body, not before the leading space. Mirrors
 * the bundled-prompt split for the non-bundled case.
 */
function hoistTrailingWhitespace(promptSpan: HTMLElement): void {
  const next = promptSpan.nextElementSibling
  if (!(next instanceof HTMLElement)) {
    return
  }
  if (next.children.length > 0) {
    return
  }
  const text = next.textContent ?? ''
  const wsMatch = text.match(/^(\s+)(.*)$/s)
  if (wsMatch === null) {
    return
  }
  const ws = wsMatch[1] ?? ''
  const rest = wsMatch[2] ?? ''
  const wsSpan = document.createElement('span')
  wsSpan.classList.add('select-none')
  if (next.getAttribute('style') !== null) {
    wsSpan.setAttribute('style', next.getAttribute('style') ?? '')
  }
  wsSpan.textContent = ws
  next.textContent = rest
  next.parentNode?.insertBefore(wsSpan, next)
}

function markPromptSpans(code: Element): void {
  // First pass: tag spans whose text is exactly a prompt token
  // (Shiki's Python tokenization, where ``>>>`` is its own span).
  // Then hoist the leading whitespace from the next sibling so the
  // separator after the prompt is also non-selectable.
  for (const span of code.querySelectorAll<HTMLElement>('span')) {
    if (PROMPT_TOKENS.has(span.textContent ?? '')) {
      span.classList.add('select-none')
      hoistTrailingWhitespace(span)
    }
  }
  // Second pass: split bundled-prompt spans (Shiki's ``console``
  // tokenization, where the entire line is one span). We only
  // consider the FIRST text-bearing span inside each
  // ``<span class="line">`` — a ``$`` mid-line is not a prompt.
  const lines = code.querySelectorAll<HTMLElement>('span.line')
  if (lines.length === 0) {
    for (const span of Array.from(code.children).filter(
      (c) => c instanceof HTMLElement,
    ) as HTMLElement[]) {
      splitPromptIfBundled(span)
    }
    return
  }
  for (const line of lines) {
    const firstSpan = line.querySelector<HTMLElement>(':scope > span')
    if (firstSpan === null) {
      continue
    }
    splitPromptIfBundled(firstSpan)
  }
}

export function enhanceCodeBlocks(root: ParentNode): void {
  const pres = root.querySelectorAll<HTMLPreElement>('pre')
  for (const pre of pres) {
    if (pre.getAttribute('data-code-copy-enhanced') === 'true') {
      continue
    }
    const code = pre.querySelector('code')
    if (code === null) {
      continue
    }
    pre.setAttribute('data-code-copy-enhanced', 'true')
    pre.style.position = pre.style.position === '' ? 'relative' : pre.style.position
    markPromptSpans(code)
    const button = document.createElement('button')
    button.type = 'button'
    button.setAttribute('data-test-id', 'code-copy')
    button.setAttribute('data-state', 'idle')
    button.setAttribute('aria-label', 'Copy code to clipboard')
    // Hover-reveal: hidden by default, fades in when the parent
    // ``<pre>`` (or any ancestor with the ``group`` semantics) is
    // hovered or the button itself is focused. Plain Tailwind
    // ``group-hover:`` would need ``.group`` on the pre; we use
    // ``[pre:hover_&]`` arbitrary variant so the rule attaches
    // without modifying the rendered ``<pre>`` markup.
    button.className =
      'absolute right-2 top-2 rounded border border-[color:var(--color-border)] bg-[color:var(--color-bg)] px-2 py-0.5 text-[0.65rem] font-medium uppercase tracking-wider text-[color:var(--color-muted)] opacity-0 transition-opacity hover:text-[color:var(--color-fg)] focus:opacity-100 focus-visible:opacity-100 [pre:hover_&]:opacity-100 data-[state=copied]:opacity-100 data-[state=copied]:text-[color:var(--color-accent)] data-[state=failed]:opacity-100'
    button.textContent = 'Copy'
    button.addEventListener('click', () => {
      void copyAndFlash(button, formatCopyText(code.textContent ?? ''))
    })
    pre.appendChild(button)
  }
}

async function copyAndFlash(button: HTMLButtonElement, text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    button.setAttribute('data-state', 'failed')
    button.textContent = 'Failed'
    return
  }
  button.setAttribute('data-state', 'copied')
  button.textContent = 'Copied'
  globalThis.setTimeout(() => {
    button.setAttribute('data-state', 'idle')
    button.textContent = 'Copy'
  }, COPIED_RESET_MS)
}
