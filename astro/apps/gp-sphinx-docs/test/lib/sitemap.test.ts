/**
 * Tests for the sitemap.xml + robots.txt builders.
 *
 * Both are pure functions: ``buildSitemap`` takes a list of slugs +
 * the site root and emits the canonical ``urlset`` XML; ``buildRobots``
 * emits the ``User-agent``/``Allow``/``Sitemap`` triple. Keeping them
 * pure means the dynamic Astro endpoints stay one-line wrappers.
 */

import { describe, expect, test } from 'vitest'
import {
  buildRobots,
  buildSitemap,
  type SitemapEntry,
} from '../../src/lib/sitemap.ts'

describe('buildSitemap', () => {
  test('emits a urlset with one <url> per entry', () => {
    const xml = buildSitemap(
      [
        { url: 'https://gp-sphinx.git-pull.com/' },
        { url: 'https://gp-sphinx.git-pull.com/architecture/' },
      ],
      { lastmod: '2026-04-29' },
    )
    expect(xml).toContain('<?xml version="1.0" encoding="UTF-8"?>')
    expect(xml).toContain(
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    )
    expect(
      (xml.match(/<url>/g) ?? []).length,
    ).toBe(2)
    expect(xml).toContain('<loc>https://gp-sphinx.git-pull.com/</loc>')
    expect(xml).toContain(
      '<loc>https://gp-sphinx.git-pull.com/architecture/</loc>',
    )
    expect(xml).toContain('<lastmod>2026-04-29</lastmod>')
  })

  test('escapes URL ampersands so the XML stays valid', () => {
    const xml = buildSitemap(
      [{ url: 'https://example.com/?a=1&b=2' } as SitemapEntry],
      { lastmod: '2026-04-29' },
    )
    expect(xml).toContain('https://example.com/?a=1&amp;b=2')
    expect(xml).not.toContain('?a=1&b=2')
  })

  test('emits an empty urlset when given no entries', () => {
    const xml = buildSitemap([], { lastmod: '2026-04-29' })
    expect(xml).toContain('<urlset')
    expect(xml).toContain('</urlset>')
    expect(xml).not.toContain('<url>')
  })
})

describe('buildRobots', () => {
  test('emits a permissive policy that points at the sitemap', () => {
    const txt = buildRobots({
      siteUrl: 'https://gp-sphinx.git-pull.com',
    })
    expect(txt).toContain('User-agent: *')
    expect(txt).toContain('Allow: /')
    expect(txt).toContain('Sitemap: https://gp-sphinx.git-pull.com/sitemap.xml')
  })

  test('strips a trailing slash from the site URL when composing the sitemap line', () => {
    const txt = buildRobots({
      siteUrl: 'https://gp-sphinx.git-pull.com/',
    })
    expect(txt).toContain('Sitemap: https://gp-sphinx.git-pull.com/sitemap.xml')
    expect(txt).not.toContain('//sitemap.xml')
  })
})
