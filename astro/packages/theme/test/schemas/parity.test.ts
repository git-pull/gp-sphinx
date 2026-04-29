/**
 * Pydantic ↔ Zod parity tests.
 *
 * Pydantic and Zod emit JSON Schema in structurally different forms (Zod
 * inlines anonymous `__schemaN` definitions and uses bare `oneOf`+`const`,
 * while Pydantic emits per-class `$defs` with the OpenAPI `discriminator`
 * extension). A direct equality check is impractical without aggressive
 * normalisation that would erase information from both sides.
 *
 * Instead this file enforces **behavioural parity**: identical fixture
 * payloads validate through both the hand-written Zod schemas and a
 * Zod schema reconstructed from the Pydantic-emitted JSON Schema via
 * `z.fromJSONSchema`. If either side drifts, the same fixture stops
 * validating through one of the two paths and the test fails.
 */

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, test } from 'vitest'
import { z } from 'zod/v4'
import { documentSchema } from '../../src/schemas/doctree.ts'

const _here = dirname(fileURLToPath(import.meta.url))
const fixturesDir = join(_here, '..', '..', '..', '..', 'fixtures')

const pydanticSchemaJson = JSON.parse(
  readFileSync(join(fixturesDir, 'doctree.schema.json'), 'utf-8'),
) as { $defs?: Record<string, unknown> } & Record<string, unknown>

const helloWorldFixture = JSON.parse(
  readFileSync(join(fixturesDir, 'hello-world.json'), 'utf-8'),
) as unknown

describe('Pydantic ↔ Zod parity — fixture loading', () => {
  test('Pydantic schema fixture has the expected shape', () => {
    expect(pydanticSchemaJson).toMatchObject({
      $defs: expect.objectContaining({
        TextNode: expect.any(Object),
        AdmonitionNode: expect.any(Object),
        DefinitionListItemNode: expect.any(Object),
      }),
    })
  })

  test('hello-world fixture parses as JSON', () => {
    expect(helloWorldFixture).toMatchObject({
      id: 'index',
      title: 'Hello world',
    })
  })
})

describe('Pydantic ↔ Zod parity — behavioural', () => {
  test('hello-world fixture validates through hand-written documentSchema', () => {
    expect(() => documentSchema.parse(helloWorldFixture)).not.toThrow()
  })

  test('hello-world fixture validates through z.fromJSONSchema(pydanticSchema)', () => {
    const reconstructed = z.fromJSONSchema(
      pydanticSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(helloWorldFixture)).not.toThrow()
  })

  test('a malformed payload (wrong discriminator) fails both schemas', () => {
    const malformed = {
      id: 'index',
      title: 'X',
      tree: {
        // Wrong: top-level tree must be a section, not a paragraph.
        type: 'paragraph',
        children: [{ type: 'text', value: 'x' }],
      },
    }
    expect(() => documentSchema.parse(malformed)).toThrow()

    const reconstructed = z.fromJSONSchema(
      pydanticSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(malformed)).toThrow()
  })

  test('a malformed payload (missing required field) fails both schemas', () => {
    const malformed = {
      id: 'index',
      // Missing: title field is required by Document.
      tree: {
        type: 'section',
        id: 'x',
        title: [],
        children: [],
      },
    }
    expect(() => documentSchema.parse(malformed)).toThrow()

    const reconstructed = z.fromJSONSchema(
      pydanticSchemaJson as Parameters<typeof z.fromJSONSchema>[0],
    )
    expect(() => reconstructed.parse(malformed)).toThrow()
  })
})

describe('Pydantic ↔ Zod parity — definition coverage', () => {
  const expectedDefs = [
    'TextNode',
    'EmphasisNode',
    'StrongNode',
    'LiteralNode',
    'ReferenceNode',
    'ImageNode',
    'BadgeNode',
    'ParagraphNode',
    'SectionNode',
    'LiteralBlockNode',
    'CommentNode',
    'TransitionNode',
    'BlockQuoteNode',
    'BulletListNode',
    'EnumeratedListNode',
    'ListItemNode',
    'AdmonitionNode',
    'DefinitionListNode',
    'DefinitionListItemNode',
    'SymbolRefNode',
    'ApiLayoutNode',
    'CliCommandNode',
  ] as const

  test.each(expectedDefs)('Pydantic fixture defines %s', (defName) => {
    const defs = pydanticSchemaJson.$defs ?? {}
    expect(defs).toHaveProperty(defName)
  })
})
