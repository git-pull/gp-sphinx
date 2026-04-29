/**
 * Tests for the sidebar navigation-tree builder.
 *
 * `buildNavTree` is the pure function the Sidebar component uses to
 * group ``CollectionEntry<'docs'>`` objects into top-level leaves and
 * single-segment groups. We test against the minimal `NavEntryInput`
 * shape to keep the suite free of Astro runtime types.
 */

import { describe, expect, test } from 'vitest'
import {
  buildNavTree,
  type NavEntryInput,
  type NavGroup,
  type NavLeaf,
} from '../../src/lib/nav-tree.ts'

function entry(id: string, title: string): NavEntryInput {
  return { id, data: { title } }
}

describe('buildNavTree — flat layout', () => {
  test('returns an empty array for an empty input', () => {
    expect(buildNavTree([])).toEqual([])
  })

  test('flat slugs become top-level leaves with /<slug>/ hrefs', () => {
    const tree = buildNavTree([
      entry('architecture', 'Architecture'),
      entry('quickstart', 'Quickstart'),
    ])
    expect(tree).toEqual<NavLeaf[]>([
      {
        type: 'leaf',
        slug: 'architecture',
        title: 'Architecture',
        href: '/architecture/',
      },
      {
        type: 'leaf',
        slug: 'quickstart',
        title: 'Quickstart',
        href: '/quickstart/',
      },
    ])
  })

  test('the index entry is filtered out of the tree (it is the home)', () => {
    const tree = buildNavTree([
      entry('index', 'gp-sphinx'),
      entry('quickstart', 'Quickstart'),
    ])
    expect(tree).toHaveLength(1)
    expect((tree[0] as NavLeaf).slug).toBe('quickstart')
  })

  test('top-level entries sort alphabetically by title', () => {
    const tree = buildNavTree([
      entry('zeta', 'Zeta'),
      entry('alpha', 'Alpha'),
      entry('mu', 'Mu'),
    ])
    expect(tree.map((node) => (node as NavLeaf).title)).toEqual([
      'Alpha',
      'Mu',
      'Zeta',
    ])
  })
})

describe('buildNavTree — grouped layout', () => {
  test('slugs with one prefix segment group under that segment', () => {
    const tree = buildNavTree([
      entry('packages/gp-sphinx', 'gp-sphinx'),
      entry('packages/sphinx-fonts', 'sphinx-fonts'),
    ])
    expect(tree).toHaveLength(1)
    const group = tree[0] as NavGroup
    expect(group.type).toBe('group')
    expect(group.name).toBe('packages')
    expect(group.children).toEqual<NavLeaf[]>([
      {
        type: 'leaf',
        slug: 'packages/gp-sphinx',
        title: 'gp-sphinx',
        href: '/packages/gp-sphinx/',
      },
      {
        type: 'leaf',
        slug: 'packages/sphinx-fonts',
        title: 'sphinx-fonts',
        href: '/packages/sphinx-fonts/',
      },
    ])
  })

  test('group children sort alphabetically by title', () => {
    const tree = buildNavTree([
      entry('packages/zeta', 'zeta'),
      entry('packages/alpha', 'alpha'),
    ])
    const group = tree[0] as NavGroup
    expect(group.children.map((leaf) => leaf.title)).toEqual([
      'alpha',
      'zeta',
    ])
  })

  test('groups appear after top-level leaves', () => {
    const tree = buildNavTree([
      entry('packages/foo', 'foo'),
      entry('quickstart', 'Quickstart'),
      entry('project/bar', 'bar'),
      entry('architecture', 'Architecture'),
    ])
    const types = tree.map((node) => node.type)
    expect(types).toEqual(['leaf', 'leaf', 'group', 'group'])
    // Within each kind, alphabetical: leaves by title, groups by name.
    expect((tree[0] as NavLeaf).title).toBe('Architecture')
    expect((tree[1] as NavLeaf).title).toBe('Quickstart')
    expect((tree[2] as NavGroup).name).toBe('packages')
    expect((tree[3] as NavGroup).name).toBe('project')
  })

  test('multi-segment slugs flatten to the first segment for now', () => {
    const tree = buildNavTree([
      entry('a/b/c', 'Deep'),
      entry('a/b/d', 'Deeper'),
    ])
    expect(tree).toHaveLength(1)
    const group = tree[0] as NavGroup
    expect(group.name).toBe('a')
    expect(group.children).toHaveLength(2)
    // Slugs preserve the full path so the href remains unique.
    expect(group.children.map((leaf) => leaf.slug)).toEqual([
      'a/b/c',
      'a/b/d',
    ])
    expect(group.children[0].href).toBe('/a/b/c/')
  })
})
