/**
 * Tests for the OG / Twitter / canonical meta builder.
 *
 * Each doc page renders a list of ``<meta>`` tag descriptors derived
 * from its title + description + canonical URL + optional preview
 * image. The builder is pure so the layout can stamp the descriptors
 * deterministically and the test suite can assert their attribute
 * combinations directly.
 */

import { describe, expect, test } from 'vitest'
import { buildOgMeta, type MetaTag } from '../../src/lib/og-meta.ts'

const BASE_INPUT = {
  title: 'Architecture',
  description: 'Twelve workspace packages in three tiers.',
  canonicalUrl: 'https://gp-sphinx.git-pull.com/architecture/',
  siteName: 'gp-sphinx',
  imageUrl: undefined,
}

function pick(tags: MetaTag[], match: Partial<MetaTag>): MetaTag | undefined {
  return tags.find((tag) =>
    Object.entries(match).every(([k, v]) => tag[k as keyof MetaTag] === v),
  )
}

describe('buildOgMeta', () => {
  test('emits a description meta tag from the input description', () => {
    const tags = buildOgMeta(BASE_INPUT)
    expect(pick(tags, { name: 'description' })?.content).toBe(
      'Twelve workspace packages in three tiers.',
    )
  })

  test('emits the canonical Open Graph trio (title, description, url)', () => {
    const tags = buildOgMeta(BASE_INPUT)
    expect(pick(tags, { property: 'og:title' })?.content).toBe('Architecture')
    expect(pick(tags, { property: 'og:description' })?.content).toBe(
      'Twelve workspace packages in three tiers.',
    )
    expect(pick(tags, { property: 'og:url' })?.content).toBe(
      'https://gp-sphinx.git-pull.com/architecture/',
    )
  })

  test('emits og:type=website and og:site_name from siteName', () => {
    const tags = buildOgMeta(BASE_INPUT)
    expect(pick(tags, { property: 'og:type' })?.content).toBe('website')
    expect(pick(tags, { property: 'og:site_name' })?.content).toBe('gp-sphinx')
  })

  test('emits twitter:card=summary by default and summary_large_image with image', () => {
    expect(
      pick(buildOgMeta(BASE_INPUT), { name: 'twitter:card' })?.content,
    ).toBe('summary')
    expect(
      pick(
        buildOgMeta({
          ...BASE_INPUT,
          imageUrl: 'https://gp-sphinx.git-pull.com/og.png',
        }),
        { name: 'twitter:card' },
      )?.content,
    ).toBe('summary_large_image')
  })

  test('includes og:image when imageUrl is provided, otherwise omits it', () => {
    expect(pick(buildOgMeta(BASE_INPUT), { property: 'og:image' })).toBeUndefined()
    expect(
      pick(
        buildOgMeta({
          ...BASE_INPUT,
          imageUrl: 'https://gp-sphinx.git-pull.com/og.png',
        }),
        { property: 'og:image' },
      )?.content,
    ).toBe('https://gp-sphinx.git-pull.com/og.png')
  })
})
