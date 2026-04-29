/**
 * Mobile drawer toggle.
 *
 * The dogfood site shows the docs sidebar inline on viewports at the
 * Tailwind ``lg`` breakpoint (1024px) and above; below that, a slide-in
 * panel exposes the same nav, opened from a hamburger trigger in the
 * top nav. This module centralises the open/close mechanics so we can
 * unit-test the behaviour without a real browser:
 *
 * - ``data-state="open"|"closed"`` on the panel drives the slide-in
 *   CSS transition.
 * - ``hidden`` is removed when open so the slide animation can run; it
 *   is reapplied when fully closed so screen readers and tab order
 *   skip the panel.
 * - ``aria-expanded`` on the trigger button stays in sync.
 * - The document element's ``style.overflow`` is locked while the
 *   drawer is open so background content doesn't scroll behind it.
 *
 * The pure helpers (``openDrawer`` / ``closeDrawer`` / ``toggleDrawer``
 * / ``isDrawerOpen``) are the testable seams; ``initMobileDrawer``
 * wires the click + keydown listeners on top.
 */

export interface MobileDrawerNodes {
  trigger: HTMLElement
  panel: HTMLElement
  closeButton?: HTMLElement
}

export function isDrawerOpen(nodes: MobileDrawerNodes): boolean {
  return nodes.panel.getAttribute('data-state') === 'open'
}

export function openDrawer(nodes: MobileDrawerNodes): void {
  nodes.panel.setAttribute('data-state', 'open')
  nodes.panel.removeAttribute('hidden')
  nodes.trigger.setAttribute('aria-expanded', 'true')
  document.documentElement.style.overflow = 'hidden'
}

export function closeDrawer(nodes: MobileDrawerNodes): void {
  nodes.panel.setAttribute('data-state', 'closed')
  nodes.panel.setAttribute('hidden', '')
  nodes.trigger.setAttribute('aria-expanded', 'false')
  document.documentElement.style.overflow = ''
}

export function toggleDrawer(nodes: MobileDrawerNodes): void {
  if (isDrawerOpen(nodes)) {
    closeDrawer(nodes)
  } else {
    openDrawer(nodes)
  }
}

export function initMobileDrawer(nodes: MobileDrawerNodes): void {
  nodes.trigger.addEventListener('click', () => {
    toggleDrawer(nodes)
  })
  nodes.closeButton?.addEventListener('click', () => {
    closeDrawer(nodes)
  })
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isDrawerOpen(nodes)) {
      closeDrawer(nodes)
    }
  })
  document.addEventListener('astro:after-swap', () => {
    if (isDrawerOpen(nodes)) {
      closeDrawer(nodes)
    }
  })
}
