/**
 * Zod schemas for the cross-reference index wire format.
 *
 * Mirrors :class:`gp_sphinx_astro_builder.models.XrefEntry`. The xref index
 * is shipped as a flat array of entries, so consumers typically validate
 * through ``z.array(xrefEntrySchema)``.
 *
 * The Pydantic-emitted ``xref-index.schema.json`` is the canonical
 * contract; a parity test in ``test/schemas/xref-parity.test.ts`` asserts
 * the same fixture array passes through both this hand-written schema and
 * a Zod schema reconstructed from the Pydantic JSON Schema via
 * ``z.fromJSONSchema``.
 */

import { z } from 'zod/v4'

export const xrefEntrySchema = z.object({
  id: z.string(),
  domain: z.string(),
  role: z.string(),
  target: z.string(),
  href: z.string(),
  display: z.string().nullable().default(null),
  priority: z.number().default(0),
})

export const xrefIndexSchema = z.array(xrefEntrySchema)

// ─── Inferred TypeScript types

export type XrefEntry = z.infer<typeof xrefEntrySchema>
export type XrefIndex = z.infer<typeof xrefIndexSchema>
