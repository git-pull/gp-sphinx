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
  | 'versionadded'
  | 'versionchanged'
  | 'deprecated'

export type FootnoteKind = 'footnote' | 'citation'

export type BadgeSize = 'xxs' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'

export type BadgeStyle = 'full' | 'icon-only' | 'inline-icon' | 'filled' | 'outline'

export type InlineNode =
  | { type: 'text'; value: string }
  | { type: 'literal'; value: string }
  | { type: 'image'; uri: string; alt: string | null }
  | { type: 'emphasis'; children: InlineNode[] }
  | { type: 'strong'; children: InlineNode[] }
  | { type: 'reference'; href: string; classes: string[]; children: InlineNode[] }
  | {
      type: 'footnoteReference'
      kind: FootnoteKind
      href: string
      label: string
    }
  | {
      type: 'badge'
      text: string
      tooltip: string | null
      icon: string | null
      size: BadgeSize | null
      style: BadgeStyle
    }

export type ListItemNode = { type: 'listItem'; children: BlockNode[] }

export type DefinitionListItemNode = {
  type: 'definitionListItem'
  term: InlineNode[]
  definition: BlockNode[]
}

export type ApiLayoutComponent =
  | 'region'
  | 'fold'
  | 'sig_fold'
  | 'component'
  | 'inline_component'
  | 'slot'
  | 'permalink'

export type CliCommandComponent =
  | 'program'
  | 'usage'
  | 'group'
  | 'argument'
  | 'subcommands'
  | 'subcommand'

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
  | {
      type: 'footnote'
      kind: FootnoteKind
      id: string
      label: string
      children: BlockNode[]
    }
  | { type: 'definitionList'; children: DefinitionListItemNode[] }
  | { type: 'symbolRef'; symbolId: string }
  | {
      type: 'apiLayout'
      component: ApiLayoutComponent
      name: string | null
      tag: string | null
      kind: string | null
      summary: string | null
      href: string | null
      title: string | null
      slot: string | null
      open: boolean
      classes: string[]
      children: BlockNode[]
    }
  | {
      type: 'cliCommand'
      component: CliCommandComponent
      prog: string | null
      usage: string | null
      title: string | null
      description: string | null
      names: string[]
      help: string | null
      default: string | null
      choices: string[]
      required: boolean
      metavar: string | null
      name: string | null
      aliases: string[]
      classes: string[]
      children: BlockNode[]
    }

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

export const badgeSizeSchema = z.enum(['xxs', 'xs', 'sm', 'md', 'lg', 'xl'])

export const badgeStyleSchema = z.enum(['full', 'icon-only', 'inline-icon', 'filled', 'outline'])

export const badgeNodeSchema = z.object({
  type: z.literal('badge'),
  text: z.string(),
  tooltip: z.string().nullable().default(null),
  icon: z.string().nullable().default(null),
  size: badgeSizeSchema.nullable().default(null),
  style: badgeStyleSchema.default('full'),
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
  classes: z.array(z.string()).default([]),
  children: z.lazy(() => z.array(inlineNodeSchema)),
})

export const footnoteKindSchema = z.enum(['footnote', 'citation'])

export const footnoteReferenceNodeSchema = z.object({
  type: z.literal('footnoteReference'),
  kind: footnoteKindSchema,
  href: z.string(),
  label: z.string(),
})

// ─── Inline discriminated union (z.ZodType<InlineNode> on the union breaks the cycle)

export const inlineNodeSchema: z.ZodType<InlineNode> = z.discriminatedUnion('type', [
  textNodeSchema,
  literalNodeSchema,
  imageNodeSchema,
  emphasisNodeSchema,
  strongNodeSchema,
  referenceNodeSchema,
  footnoteReferenceNodeSchema,
  badgeNodeSchema,
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
  'versionadded',
  'versionchanged',
  'deprecated',
])

export const admonitionNodeSchema = z.object({
  type: z.literal('admonition'),
  variant: admonitionVariantSchema,
  children: z.lazy(() => z.array(blockNodeSchema)),
})

export const footnoteNodeSchema = z.object({
  type: z.literal('footnote'),
  kind: footnoteKindSchema,
  id: z.string(),
  label: z.string(),
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

export const symbolRefNodeSchema = z.object({
  type: z.literal('symbolRef'),
  symbolId: z.string(),
})

export const apiLayoutComponentSchema = z.enum([
  'region',
  'fold',
  'sig_fold',
  'component',
  'inline_component',
  'slot',
  'permalink',
])

export const apiLayoutNodeSchema = z.object({
  type: z.literal('apiLayout'),
  component: apiLayoutComponentSchema,
  name: z.string().nullable().default(null),
  tag: z.string().nullable().default(null),
  kind: z.string().nullable().default(null),
  summary: z.string().nullable().default(null),
  href: z.string().nullable().default(null),
  title: z.string().nullable().default(null),
  slot: z.string().nullable().default(null),
  open: z.boolean().default(false),
  classes: z.array(z.string()).default([]),
  get children() {
    return z.array(blockNodeSchema).default([])
  },
})

export const cliCommandComponentSchema = z.enum([
  'program',
  'usage',
  'group',
  'argument',
  'subcommands',
  'subcommand',
])

export const cliCommandNodeSchema = z.object({
  type: z.literal('cliCommand'),
  component: cliCommandComponentSchema,
  prog: z.string().nullable().default(null),
  usage: z.string().nullable().default(null),
  title: z.string().nullable().default(null),
  description: z.string().nullable().default(null),
  names: z.array(z.string()).default([]),
  help: z.string().nullable().default(null),
  default: z.string().nullable().default(null),
  choices: z.array(z.string()).default([]),
  required: z.boolean().default(false),
  metavar: z.string().nullable().default(null),
  name: z.string().nullable().default(null),
  aliases: z.array(z.string()).default([]),
  classes: z.array(z.string()).default([]),
  get children() {
    return z.array(blockNodeSchema).default([])
  },
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
  footnoteNodeSchema,
  definitionListNodeSchema,
  symbolRefNodeSchema,
  apiLayoutNodeSchema,
  cliCommandNodeSchema,
])

// ─── Top-level document

export const documentSchema: z.ZodType<Document> = z.object({
  id: z.string(),
  title: z.string(),
  tree: sectionNodeSchema,
})
