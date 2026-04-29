/**
 * @vitest-environment happy-dom
 *
 * Tests for the mobile-drawer toggle module.
 *
 * The drawer is a slide-in overlay shown only on viewports below the
 * ``lg`` Tailwind breakpoint. The pure helpers manage:
 *   - the open/closed state on a panel + trigger pair
 *   - body scroll-lock (``overflow: hidden`` on ``<html>``) while open
 *   - keyboard dismiss (Escape closes)
 *   - SPA-route-change dismiss (Astro's ``astro:after-swap``) so a
 *     sidebar link tap doesn't leave the drawer hanging open
 */

import { afterEach, beforeEach, describe, expect, test } from 'vitest'
import {
  closeDrawer,
  initMobileDrawer,
  isDrawerOpen,
  openDrawer,
  toggleDrawer,
} from '../../src/lib/mobile-drawer.ts'

function makeDrawerDom(): {
  trigger: HTMLButtonElement
  panel: HTMLElement
  closeButton: HTMLButtonElement
} {
  while (document.body.firstChild !== null) {
    document.body.removeChild(document.body.firstChild)
  }
  const trigger = document.createElement('button')
  trigger.setAttribute('data-test-id', 'mobile-drawer-trigger')
  trigger.setAttribute('aria-expanded', 'false')
  const panel = document.createElement('div')
  panel.setAttribute('data-test-id', 'mobile-drawer-panel')
  panel.setAttribute('data-state', 'closed')
  panel.setAttribute('hidden', '')
  const closeButton = document.createElement('button')
  closeButton.setAttribute('data-test-id', 'mobile-drawer-close')
  document.body.appendChild(trigger)
  document.body.appendChild(panel)
  document.body.appendChild(closeButton)
  return { trigger, panel, closeButton }
}

beforeEach(() => {
  document.documentElement.removeAttribute('style')
  while (document.body.firstChild !== null) {
    document.body.removeChild(document.body.firstChild)
  }
})

afterEach(() => {
  document.documentElement.removeAttribute('style')
})

describe('openDrawer / closeDrawer / toggleDrawer', () => {
  test('openDrawer flips panel state and scroll-locks the document', () => {
    const dom = makeDrawerDom()
    openDrawer(dom)
    expect(dom.panel.getAttribute('data-state')).toBe('open')
    expect(dom.panel.hasAttribute('hidden')).toBe(false)
    expect(dom.trigger.getAttribute('aria-expanded')).toBe('true')
    expect(document.documentElement.style.overflow).toBe('hidden')
  })

  test('closeDrawer reverses everything openDrawer set', () => {
    const dom = makeDrawerDom()
    openDrawer(dom)
    closeDrawer(dom)
    expect(dom.panel.getAttribute('data-state')).toBe('closed')
    expect(dom.panel.hasAttribute('hidden')).toBe(true)
    expect(dom.trigger.getAttribute('aria-expanded')).toBe('false')
    expect(document.documentElement.style.overflow).toBe('')
  })

  test('toggleDrawer flips between open and closed', () => {
    const dom = makeDrawerDom()
    expect(isDrawerOpen(dom)).toBe(false)
    toggleDrawer(dom)
    expect(isDrawerOpen(dom)).toBe(true)
    toggleDrawer(dom)
    expect(isDrawerOpen(dom)).toBe(false)
  })
})

describe('initMobileDrawer', () => {
  test('clicking the trigger opens the drawer', () => {
    const dom = makeDrawerDom()
    initMobileDrawer(dom)
    dom.trigger.click()
    expect(isDrawerOpen(dom)).toBe(true)
  })

  test('clicking the close button closes the drawer', () => {
    const dom = makeDrawerDom()
    initMobileDrawer(dom)
    openDrawer(dom)
    dom.closeButton.click()
    expect(isDrawerOpen(dom)).toBe(false)
  })

  test('Escape closes the drawer when it is open', () => {
    const dom = makeDrawerDom()
    initMobileDrawer(dom)
    openDrawer(dom)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(isDrawerOpen(dom)).toBe(false)
  })

  test('Escape is a no-op when the drawer is closed', () => {
    const dom = makeDrawerDom()
    initMobileDrawer(dom)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(isDrawerOpen(dom)).toBe(false)
    expect(document.documentElement.style.overflow).toBe('')
  })

  test('astro:after-swap closes any open drawer', () => {
    const dom = makeDrawerDom()
    initMobileDrawer(dom)
    openDrawer(dom)
    document.dispatchEvent(new Event('astro:after-swap'))
    expect(isDrawerOpen(dom)).toBe(false)
  })
})
