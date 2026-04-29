/**
 * Tests for the footer metadata helpers.
 *
 * The footer's only piece of dynamic content is the copyright string,
 * which depends on the build year. Keeping the formatter pure means
 * the build is deterministic — pass an explicit ``Date`` and assert
 * the rendered text — and a stale-by-default site doesn't accidentally
 * show last-year's copyright when the user's clock ticks past
 * midnight on Jan 1.
 */

import { describe, expect, test } from 'vitest'
import { formatCopyright } from '../../src/lib/footer-meta.ts'

describe('formatCopyright', () => {
  test('renders a single-year copyright when the project starts the same year', () => {
    const result = formatCopyright({
      holder: 'Tony Narlock',
      project: 'gp-sphinx',
      sinceYear: 2026,
      now: new Date('2026-04-29T00:00:00Z'),
    })
    expect(result).toBe('© 2026 Tony Narlock — gp-sphinx')
  })

  test('renders a year range when the build year is later than sinceYear', () => {
    const result = formatCopyright({
      holder: 'Tony Narlock',
      project: 'gp-sphinx',
      sinceYear: 2024,
      now: new Date('2026-04-29T00:00:00Z'),
    })
    expect(result).toBe('© 2024–2026 Tony Narlock — gp-sphinx')
  })

  test('uses the UTC year so the build is deterministic across timezones', () => {
    // 2025-12-31T23:30 UTC is still 2026 in Sydney; the helper must
    // anchor on UTC so a parallel build on two machines emits the
    // same copyright.
    const result = formatCopyright({
      holder: 'Tony Narlock',
      project: 'gp-sphinx',
      sinceYear: 2024,
      now: new Date('2025-12-31T23:30:00Z'),
    })
    expect(result).toBe('© 2024–2025 Tony Narlock — gp-sphinx')
  })
})
