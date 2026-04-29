/**
 * robots.txt endpoint.
 *
 * Serves a permissive policy with a Sitemap pointer to the dynamic
 * ``/sitemap.xml`` endpoint. ``buildRobots`` is the pure formatter
 * (TDD'd via vitest in ``test/lib/sitemap.test.ts``).
 */
import type { APIRoute } from 'astro'
import { buildRobots } from '../lib/sitemap.ts'

export const GET: APIRoute = ({ site }) => {
  if (site === undefined) {
    throw new Error('astro.config.ts must define a `site` URL')
  }
  const txt = buildRobots({ siteUrl: site.toString() })
  return new Response(txt, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
