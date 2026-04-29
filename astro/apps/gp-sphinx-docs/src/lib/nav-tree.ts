/**
 * Pure-function navigation-tree builder for the docs sidebar.
 *
 * Slugs in the ``docs`` content collection use ``/`` separators —
 * ``packages/gp-sphinx``, ``project/contributing``, etc. — so the
 * grouping is implicit in the slug itself. This module collapses that
 * into a two-level tree (top-level leaves + single-segment groups
 * containing leaves) which the Sidebar component renders.
 *
 * The builder accepts the minimal slice of ``CollectionEntry<'docs'>``
 * it needs (``NavEntryInput``) so the test suite doesn't depend on
 * Astro runtime types. The Sidebar component is the seam where the
 * full ``CollectionEntry`` is narrowed to that shape.
 */

export interface NavEntryInput {
  /** The slug, e.g. ``packages/gp-sphinx``. Mirrors ``entry.id``. */
  id: string
  data: {
    /** Display label, mirrors ``entry.data.title`` from the doctree. */
    title: string
  }
}

export interface NavLeaf {
  type: 'leaf'
  slug: string
  title: string
  href: string
}

export interface NavGroup {
  type: 'group'
  name: string
  children: NavLeaf[]
}

export type NavNode = NavLeaf | NavGroup

function makeLeaf(entry: NavEntryInput): NavLeaf {
  return {
    type: 'leaf',
    slug: entry.id,
    title: entry.data.title,
    href: `/${entry.id}/`,
  }
}

export function buildNavTree(entries: readonly NavEntryInput[]): NavNode[] {
  const topLeaves: NavLeaf[] = []
  const groupBuckets = new Map<string, NavLeaf[]>()

  for (const entry of entries) {
    if (entry.id === 'index') {
      // The index entry is the home page; the wordmark in TopNav is
      // its only navigation surface.
      continue
    }
    const slashIndex = entry.id.indexOf('/')
    if (slashIndex === -1) {
      topLeaves.push(makeLeaf(entry))
      continue
    }
    const groupName = entry.id.slice(0, slashIndex)
    const bucket = groupBuckets.get(groupName) ?? []
    bucket.push(makeLeaf(entry))
    groupBuckets.set(groupName, bucket)
  }

  topLeaves.sort((a, b) => a.title.localeCompare(b.title))

  const groups: NavGroup[] = Array.from(groupBuckets.entries())
    .map(([name, children]) => ({
      type: 'group' as const,
      name,
      children: children.toSorted((a, b) => a.title.localeCompare(b.title)),
    }))
    .sort((a, b) => a.name.localeCompare(b.name))

  return [...topLeaves, ...groups]
}
