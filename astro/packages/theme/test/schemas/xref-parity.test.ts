/**
 * Pydantic ↔ Zod parity for the cross-reference index wire format.
 *
 * Same shape as the doctree and symbol parity tests: the canonical fixture
 * must validate through both the hand-written Zod ``xrefIndexSchema`` and
 * a Zod schema reconstructed from the Pydantic-emitted
 * ``xref-index.schema.json`` via ``z.fromJSONSchema``.
 */

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, test } from 'vitest'
import { z } from 'zod/v4'
import { xrefIndexSchema } from '../../src/schemas/xref.ts'

const _here = dirname(fileURLToPath(import.meta.url))
const fixturesDir = join(_here, '..', '..', '..', '..', 'fixtures')

const pydanticXrefSchemaJson = JSON.parse(
  readFileSync(join(fixturesDir, 'xref-index.schema.json'), 'utf-8'),
) as Record<string, unknown>

const helloXrefFixture = JSON.parse(
  readFileSync(join(fixturesDir, 'hello-xref-index.json'), 'utf-8'),
) as unknown

describe('Pydantic ↔ Zod xref parity — fixture loading', () => {
  test('Pydantic xref schema fixture is an array schema', () => {
    expect(pydanticXrefSchemaJson).toMatchObject({
      type: 'array',
      $defs: expect.objectContaining({
        XrefEntry: expect.any(Object),
      }),
    })
  })

  test('hello-xref-index fixture has the expected shape', () => {
    expect(Array.isArray(helloXrefFixture)).toBe(true)
    expect((helloXrefFixture as unknown[]).length).toBeGreaterThan(0)
  })
})

describe('Pydantic ↔ Zod xref parity — behavioural', () => {
  test('hello-xref-index validates through hand-written xrefIndexSchema', () => {
    expect(() => xrefIndexSchema.parse(helloXrefFixture)).not.toThrow()
  })

  test('hello-xref-index validates through z.fromJSONSchema(pydantic)', () => {
    const reconstructed = z.fromJSONSchema(
      pydanticXrefSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(helloXrefFixture)).not.toThrow()
  })

  test('a malformed entry (missing href) fails both schemas', () => {
    const malformed = [
      {
        id: 'py:func:x',
        domain: 'py',
        role: 'func',
        target: 'x',
      },
    ]
    expect(() => xrefIndexSchema.parse(malformed)).toThrow()

    const reconstructed = z.fromJSONSchema(
      pydanticXrefSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(malformed)).toThrow()
  })

  test('a non-array payload fails both schemas', () => {
    const malformed = { id: 'py:func:x' }
    expect(() => xrefIndexSchema.parse(malformed)).toThrow()

    const reconstructed = z.fromJSONSchema(
      pydanticXrefSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(malformed)).toThrow()
  })
})
