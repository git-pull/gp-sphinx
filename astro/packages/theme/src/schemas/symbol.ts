/**
 * Zod schemas for the Symbol wire format.
 *
 * Mirrors the Pydantic models in
 * `packages/gp-sphinx-astro-builder/src/gp_sphinx_astro_builder/models.py`
 * (Parameter, SymbolSource, Symbol). Symbol carries a `docstring_body`
 * field typed as `BlockNode[]`, so this module imports `blockNodeSchema`
 * from `./doctree.ts` and the schema for one Symbol entry transitively
 * covers every doctree node type as well.
 *
 * The Pydantic-emitted schema is the canonical contract; a parity test
 * in `test/schemas/symbol-parity.test.ts` asserts that fixture payloads
 * validate through both this hand-written schema and a Zod schema
 * reconstructed from the Pydantic JSON Schema via `z.fromJSONSchema`.
 */

import { z } from 'zod/v4'
import { blockNodeSchema } from './doctree.ts'

export const parameterKindSchema = z.enum([
  'positional',
  'keyword',
  'var_positional',
  'var_keyword',
])

export const parameterSchema = z.object({
  name: z.string(),
  annotation: z.string().nullable(),
  default: z.string().nullable(),
  kind: parameterKindSchema,
})

export const symbolSourceSchema = z.object({
  repo: z.string(),
  path: z.string(),
  line: z.number(),
})

export const symbolKindSchema = z.enum([
  'function',
  'class',
  'method',
  'attribute',
  'property',
  'enum',
  'dataclass',
  'module',
])

export const symbolSchema = z.object({
  id: z.string(),
  kind: symbolKindSchema,
  name: z.string(),
  qualname: z.string(),
  module: z.string(),
  signature: z.string(),
  parameters: z.array(parameterSchema),
  returns: z.string().nullable(),
  docstring_summary: z.string(),
  docstring_body: z.array(blockNodeSchema),
  source: symbolSourceSchema.nullable(),
})

// ─── Inferred TypeScript types

export type ParameterKind = z.infer<typeof parameterKindSchema>
export type Parameter = z.infer<typeof parameterSchema>
export type SymbolSource = z.infer<typeof symbolSourceSchema>
export type SymbolKind = z.infer<typeof symbolKindSchema>
export type Symbol = z.infer<typeof symbolSchema>
