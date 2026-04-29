/**
 * sitemap.xml endpoint.
 *
 * Walks both content collections (docs + api/symbols) and emits one
 * canonical URL per slug. ``Astro.site`` carries the configured
 * deployment root; ``buildSitemap`` is the pure formatter (TDD'd via
 * vitest in ``test/lib/sitemap.test.ts``).
 */
import type { APIRoute } from 'astro'
import { getCollection } from 'astro:content'
import { buildSitemap, type SitemapEntry } from '../lib/sitemap.ts'

export const GET: APIRoute = async ({ site }) => {
  if (site === undefined) {
    throw new Error('astro.config.ts must define a `site` URL')
  }
  const docs = await getCollection('docs')
  const symbols = await getCollection('api')
  const entries: SitemapEntry[] = []
  for (const doc of docs) {
    // The catch-all doc route serves ``index`` at ``/`` and the rest
    // at ``/<slug>/`` (``trailingSlash: 'always'`` in astro.config).
    const path = doc.id === 'index' ? '' : `${doc.id}/`
    entries.push({ url: new URL(path, site).toString() })
  }
  for (const symbol of symbols) {
    entries.push({ url: new URL(`api/${symbol.id}/`, site).toString() })
  }
  const xml = buildSitemap(entries, {
    lastmod: new Date().toISOString().slice(0, 10),
  })
  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  })
}
