/**
 * Open Graph / Twitter / description meta builder.
 *
 * Each page renders a small bundle of ``<meta>`` tags so social
 * unfurls and search snippets show useful information. The builder
 * is pure: feed it title + description + canonical URL + optional
 * preview image, get back a list of descriptors the layout stamps
 * into ``<head>``.
 */

export interface OgMetaInput {
  title: string
  description: string
  canonicalUrl: string
  siteName: string
  /** Optional preview image — when set, switches to ``summary_large_image``. */
  imageUrl: string | undefined
}

export interface MetaTag {
  name?: string
  property?: string
  content: string
}

export function buildOgMeta(input: OgMetaInput): MetaTag[] {
  const tags: MetaTag[] = [
    { name: 'description', content: input.description },
    { property: 'og:title', content: input.title },
    { property: 'og:description', content: input.description },
    { property: 'og:url', content: input.canonicalUrl },
    { property: 'og:type', content: 'website' },
    { property: 'og:site_name', content: input.siteName },
    {
      name: 'twitter:card',
      content:
        input.imageUrl === undefined ? 'summary' : 'summary_large_image',
    },
    { name: 'twitter:title', content: input.title },
    { name: 'twitter:description', content: input.description },
  ]
  if (input.imageUrl !== undefined) {
    tags.push({ property: 'og:image', content: input.imageUrl })
    tags.push({ name: 'twitter:image', content: input.imageUrl })
  }
  return tags
}
