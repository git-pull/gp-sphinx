import { describe, expect, test } from 'vitest'
import { z } from 'zod/v4'
import { VERSION } from '../src/index.ts'

describe('@gp-sphinx-astro/theme toolchain smoke', () => {
  test('package exports VERSION constant', () => {
    expect(VERSION).toBe('0.0.1a12')
  })

  test('zod v4 is importable and validates a basic schema', () => {
    const schema = z.object({ id: z.string(), count: z.number() })
    expect(schema.parse({ id: 'x', count: 1 })).toEqual({ id: 'x', count: 1 })
  })

  test('zod v4 emits a JSON Schema via the built-in toJSONSchema helper', () => {
    const schema = z.object({ id: z.string() })
    const jsonSchema = z.toJSONSchema(schema)
    expect(jsonSchema).toMatchObject({
      type: 'object',
      properties: { id: { type: 'string' } },
    })
  })
})
