/**
 * Zod schemas for the doctree wire format.
 *
 * Mirrors the Pydantic models in
 * `packages/gp-sphinx-astro-builder/src/gp_sphinx_astro_builder/models.py`
 * one-to-one. The Pydantic-emitted JSON Schema is the canonical contract;
 * a parity test in `test/schemas/parity.test.ts` asserts these Zod schemas
 * produce the same JSON Schema (after normalising the Pydantic
 * OpenAPI-discriminator quirk).
 *
 * Recursive types use `z.lazy(() => ...)` for the runtime self-reference,
 * with `z.ZodType<T>` annotations on the discriminated unions (not on
 * individual members). The annotation on the union breaks TypeScript's
 * eager type-inference cycle while leaving the member schemas unannotated
 * so `z.discriminatedUnion` can still introspect their discriminator
 * literals.
 */

import { z } from 'zod/v4'

// ─── TypeScript types (manual, used to annotate the unions only)

export type AdmonitionVariant =
  | 'note'
  | 'warning'
  | 'attention'
  | 'caution'
  | 'important'
  | 'tip'
  | 'hint'
  | 'danger'
  | 'error'

export type InlineNode =
  | { type: 'text'; value: string }
  | { type: 'literal'; value: string }
  | { type: 'image'; uri: string; alt: string | null }
  | { type: 'emphasis'; children: InlineNode[] }
  | { type: 'strong'; children: InlineNode[] }
  | { type: 'reference'; href: string; children: InlineNode[] }

export type ListItemNode = { type: 'listItem'; children: BlockNode[] }

export type DefinitionListItemNode = {
  type: 'definitionListItem'
  term: InlineNode[]
  definition: BlockNode[]
}

export type BlockNode =
  | { type: 'paragraph'; children: InlineNode[] }
  | { type: 'section'; id: string; title: InlineNode[]; children: BlockNode[] }
  | { type: 'literalBlock'; language: string | null; code: string }
  | { type: 'comment'; value: string }
  | { type: 'transition' }
  | { type: 'blockQuote'; children: BlockNode[] }
  | { type: 'bulletList'; children: ListItemNode[] }
  | { type: 'enumeratedList'; start: number | null; children: ListItemNode[] }
  | { type: 'admonition'; variant: AdmonitionVariant; children: BlockNode[] }
  | { type: 'definitionList'; children: DefinitionListItemNode[] }

export type Document = {
  id: string
  title: string
  tree: Extract<BlockNode, { type: 'section' }>
}

// ─── Leaf inline shapes (no recursion)

export const textNodeSchema = z.object({
  type: z.literal('text'),
  value: z.string(),
})

export const literalNodeSchema = z.object({
  type: z.literal('literal'),
  value: z.string(),
})

export const imageNodeSchema = z.object({
  type: z.literal('image'),
  uri: z.string(),
  alt: z.string().nullable(),
})

// ─── Inline shapes that recurse via z.lazy
//
// Members are NOT annotated with z.ZodType<...> so z.discriminatedUnion
// below can still introspect the discriminator literal. The recursion is
// safe because z.lazy defers the inlineNodeSchema reference to parse time,
// by which point inlineNodeSchema is defined.

export const emphasisNodeSchema = z.object({
  type: z.literal('emphasis'),
  children: z.lazy(() => z.array(inlineNodeSchema)),
})

export const strongNodeSchema = z.object({
  type: z.literal('strong'),
  children: z.lazy(() => z.array(inlineNodeSchema)),
})

export const referenceNodeSchema = z.object({
  type: z.literal('reference'),
  href: z.string(),
  children: z.lazy(() => z.array(inlineNodeSchema)),
})

// ─── Inline discriminated union (z.ZodType<InlineNode> on the union breaks the cycle)

export const inlineNodeSchema: z.ZodType<InlineNode> = z.discriminatedUnion('type', [
  textNodeSchema,
  literalNodeSchema,
  imageNodeSchema,
  emphasisNodeSchema,
  strongNodeSchema,
  referenceNodeSchema,
])

// ─── Leaf block shapes (no recursion)

export const literalBlockNodeSchema = z.object({
  type: z.literal('literalBlock'),
  language: z.string().nullable(),
  code: z.string(),
})

export const commentNodeSchema = z.object({
  type: z.literal('comment'),
  value: z.string(),
})

export const transitionNodeSchema = z.object({
  type: z.literal('transition'),
})

// ─── Block shapes with non-recursive inline children

export const paragraphNodeSchema = z.object({
  type: z.literal('paragraph'),
  children: z.array(inlineNodeSchema),
})

// ─── Block shapes that recurse via z.lazy

export const blockQuoteNodeSchema = z.object({
  type: z.literal('blockQuote'),
  children: z.lazy(() => z.array(blockNodeSchema)),
})

export const listItemNodeSchema = z.object({
  type: z.literal('listItem'),
  children: z.lazy(() => z.array(blockNodeSchema)),
})

export const bulletListNodeSchema = z.object({
  type: z.literal('bulletList'),
  children: z.array(listItemNodeSchema),
})

export const enumeratedListNodeSchema = z.object({
  type: z.literal('enumeratedList'),
  start: z.number().nullable(),
  children: z.array(listItemNodeSchema),
})

export const admonitionVariantSchema = z.enum([
  'note',
  'warning',
  'attention',
  'caution',
  'important',
  'tip',
  'hint',
  'danger',
  'error',
])

export const admonitionNodeSchema = z.object({
  type: z.literal('admonition'),
  variant: admonitionVariantSchema,
  children: z.lazy(() => z.array(blockNodeSchema)),
})

export const definitionListItemNodeSchema = z.object({
  type: z.literal('definitionListItem'),
  term: z.array(inlineNodeSchema),
  definition: z.lazy(() => z.array(blockNodeSchema)),
})

export const definitionListNodeSchema = z.object({
  type: z.literal('definitionList'),
  children: z.array(definitionListItemNodeSchema),
})

export const sectionNodeSchema = z.object({
  type: z.literal('section'),
  id: z.string(),
  title: z.array(inlineNodeSchema),
  children: z.lazy(() => z.array(blockNodeSchema)),
})

// ─── Block discriminated union (z.ZodType<BlockNode> on the union breaks the cycle)

export const blockNodeSchema: z.ZodType<BlockNode> = z.discriminatedUnion('type', [
  paragraphNodeSchema,
  sectionNodeSchema,
  literalBlockNodeSchema,
  commentNodeSchema,
  transitionNodeSchema,
  blockQuoteNodeSchema,
  bulletListNodeSchema,
  enumeratedListNodeSchema,
  admonitionNodeSchema,
  definitionListNodeSchema,
])

// ─── Top-level document

export const documentSchema: z.ZodType<Document> = z.object({
  id: z.string(),
  title: z.string(),
  tree: sectionNodeSchema,
})
