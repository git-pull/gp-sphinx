/**
 * Search keyboard-shortcut handler.
 *
 * Pagefind's default UI provides the search rendering; this module
 * adds two ergonomics:
 *   - Press ``/`` anywhere on the page (outside an editable element)
 *     to focus the search input. The keydown is cancelled so the
 *     slash doesn't get typed into the input itself.
 *   - Press ``Escape`` while the search input has focus to blur it
 *     and return the user to the page content.
 *
 * The function takes the input element directly so tests can use any
 * fixture node. In production the Pagefind UI script renders an
 * ``<input>`` inside its host element; the SearchBox component
 * resolves it via ``querySelector`` once the UI initialises.
 */

export interface SearchShortcutOptions {
  input: HTMLInputElement
}

const EDITABLE_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

function isEditableActive(): boolean {
  // ``event.target`` from a programmatic ``document.dispatchEvent`` is
  // the document itself, not the focused element. Querying
  // ``document.activeElement`` is the reliable way to know whether the
  // user is currently typing into a text field.
  const active = document.activeElement
  if (active === null || !(active instanceof HTMLElement)) {
    return false
  }
  if (active.isContentEditable) {
    return true
  }
  return EDITABLE_TAGS.has(active.tagName)
}

export function initSearchShortcut(options: SearchShortcutOptions): void {
  const { input } = options
  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !isEditableActive()) {
      event.preventDefault()
      input.focus()
      return
    }
    if (event.key === 'Escape' && document.activeElement === input) {
      input.blur()
    }
  })
}
