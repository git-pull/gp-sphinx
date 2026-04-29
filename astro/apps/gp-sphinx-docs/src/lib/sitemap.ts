/**
 * sitemap.xml + robots.txt builders.
 *
 * Both helpers are pure: callers (the dynamic Astro endpoints) stay
 * one-line wrappers that pull the site URL from ``Astro.site`` and
 * the slug list from ``getCollection``.
 */

const XML_ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&apos;',
}

function escapeXml(value: string): string {
  return value.replace(/[&<>"']/g, (c) => XML_ESCAPES[c] ?? c)
}

export interface SitemapEntry {
  url: string
}

export interface BuildSitemapOptions {
  /** ISO-8601 date used for ``<lastmod>`` on every entry. */
  lastmod: string
}

export function buildSitemap(
  entries: readonly SitemapEntry[],
  options: BuildSitemapOptions,
): string {
  const urls = entries
    .map(
      (entry) =>
        `  <url><loc>${escapeXml(entry.url)}</loc><lastmod>${options.lastmod}</lastmod></url>`,
    )
    .join('\n')
  const body = entries.length === 0 ? '' : `\n${urls}\n`
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    body,
    '</urlset>',
    '',
  ].join('')
}

export interface BuildRobotsOptions {
  siteUrl: string
}

export function buildRobots(options: BuildRobotsOptions): string {
  const root = options.siteUrl.replace(/\/+$/, '')
  return [
    'User-agent: *',
    'Allow: /',
    '',
    `Sitemap: ${root}/sitemap.xml`,
    '',
  ].join('\n')
}
