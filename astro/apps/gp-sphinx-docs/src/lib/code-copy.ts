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
 * The function is idempotent — re-running it on the same root after
 * an SPA navigation or a re-render leaves already-decorated blocks
 * untouched. Pages without ``<pre><code>`` pairs are no-ops.
 */

const COPIED_RESET_MS = 1500

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
    const button = document.createElement('button')
    button.type = 'button'
    button.setAttribute('data-test-id', 'code-copy')
    button.setAttribute('data-state', 'idle')
    button.setAttribute('aria-label', 'Copy code to clipboard')
    button.className =
      'absolute right-2 top-2 rounded border border-[color:var(--color-border)] bg-[color:var(--color-bg)] px-2 py-0.5 text-[0.65rem] font-medium uppercase tracking-wider text-[color:var(--color-muted)] hover:text-[color:var(--color-fg)] data-[state=copied]:text-[color:var(--color-accent)]'
    button.textContent = 'Copy'
    button.addEventListener('click', () => {
      void copyAndFlash(button, code.textContent ?? '')
    })
    pre.appendChild(button)
  }
}

async function copyAndFlash(
  button: HTMLButtonElement,
  text: string,
): Promise<void> {
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
