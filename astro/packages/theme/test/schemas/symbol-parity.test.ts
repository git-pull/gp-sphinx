/**
 * Pydantic ↔ Zod parity for the Symbol wire format.
 *
 * Same shape as `parity.test.ts` (the doctree parity tests), but for the
 * Symbol schema: the canonical fixture must validate through both the
 * hand-written Zod ``symbolSchema`` and a Zod schema reconstructed from
 * the Pydantic-emitted ``symbol.schema.json`` via ``z.fromJSONSchema``.
 */

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, test } from 'vitest'
import { z } from 'zod/v4'
import { symbolSchema } from '../../src/schemas/symbol.ts'

const _here = dirname(fileURLToPath(import.meta.url))
const fixturesDir = join(_here, '..', '..', '..', '..', 'fixtures')

const pydanticSymbolSchemaJson = JSON.parse(
  readFileSync(join(fixturesDir, 'symbol.schema.json'), 'utf-8'),
) as { $defs?: Record<string, unknown> } & Record<string, unknown>

const helloSymbolFixture = JSON.parse(
  readFileSync(join(fixturesDir, 'hello-symbol.json'), 'utf-8'),
) as unknown

describe('Pydantic ↔ Zod symbol parity — fixture loading', () => {
  test('Pydantic symbol schema fixture has the expected shape', () => {
    expect(pydanticSymbolSchemaJson).toMatchObject({
      $defs: expect.objectContaining({
        Parameter: expect.any(Object),
        SymbolSource: expect.any(Object),
        TextNode: expect.any(Object),
      }),
    })
  })

  test('hello-symbol fixture has the expected top-level fields', () => {
    expect(helloSymbolFixture).toMatchObject({
      id: 'demo_api.merge_demo',
      kind: 'function',
      module: 'demo_api',
    })
  })
})

describe('Pydantic ↔ Zod symbol parity — behavioural', () => {
  test('hello-symbol validates through hand-written symbolSchema', () => {
    expect(() => symbolSchema.parse(helloSymbolFixture)).not.toThrow()
  })

  test('hello-symbol validates through z.fromJSONSchema(pydanticSymbolSchema)', () => {
    const reconstructed = z.fromJSONSchema(
      pydanticSymbolSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(helloSymbolFixture)).not.toThrow()
  })

  test('a malformed Symbol (unknown kind) fails both schemas', () => {
    const malformed = {
      ...(helloSymbolFixture as Record<string, unknown>),
      kind: 'totally_made_up',
    }
    expect(() => symbolSchema.parse(malformed)).toThrow()

    const reconstructed = z.fromJSONSchema(
      pydanticSymbolSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(malformed)).toThrow()
  })

  test('a malformed Symbol (missing required field) fails both schemas', () => {
    const malformed: { id?: unknown } & Record<string, unknown> = {
      ...(helloSymbolFixture as Record<string, unknown>),
    }
    delete malformed.id
    expect(() => symbolSchema.parse(malformed)).toThrow()

    const reconstructed = z.fromJSONSchema(
      pydanticSymbolSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(malformed)).toThrow()
  })
})

describe('Pydantic ↔ Zod symbol parity — definition coverage', () => {
  const expectedDefs = ['Parameter', 'SymbolSource'] as const

  test.each(expectedDefs)('Pydantic fixture defines symbol-specific %s', (defName) => {
    const defs = pydanticSymbolSchemaJson.$defs ?? {}
    expect(defs).toHaveProperty(defName)
  })
})
