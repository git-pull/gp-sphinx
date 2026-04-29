import { describe, expect, test } from 'vitest'
import { xrefEntrySchema, xrefIndexSchema } from '../../src/schemas/xref.ts'

describe('xref zod schemas — XrefEntry', () => {
  test('xrefEntrySchema round-trips a complete payload', () => {
    const data = {
      id: 'py:func:gp_sphinx.config.merge_sphinx_config',
      domain: 'py',
      role: 'func',
      target: 'gp_sphinx.config.merge_sphinx_config',
      href: '/api/gp_sphinx.config.merge_sphinx_config/',
      display: 'merge_sphinx_config',
      priority: 0,
    }
    expect(xrefEntrySchema.parse(data)).toEqual(data)
  })

  test('xrefEntrySchema applies defaults for display and priority', () => {
    const result = xrefEntrySchema.parse({
      id: 'py:class:Foo',
      domain: 'py',
      role: 'class',
      target: 'Foo',
      href: '/api/Foo/',
    })
    expect(result.display).toBeNull()
    expect(result.priority).toBe(0)
  })

  test('xrefEntrySchema rejects a payload missing required href', () => {
    expect(() =>
      xrefEntrySchema.parse({
        id: 'py:func:foo',
        domain: 'py',
        role: 'func',
        target: 'foo',
      }),
    ).toThrow()
  })

  test('xrefEntrySchema accepts explicit null display', () => {
    const result = xrefEntrySchema.parse({
      id: 'py:func:foo',
      domain: 'py',
      role: 'func',
      target: 'foo',
      href: '/api/foo/',
      display: null,
      priority: 1,
    })
    expect(result.display).toBeNull()
    expect(result.priority).toBe(1)
  })
})

describe('xref zod schemas — XrefIndex (array)', () => {
  test('xrefIndexSchema accepts an empty array', () => {
    expect(xrefIndexSchema.parse([])).toEqual([])
  })

  test('xrefIndexSchema accepts an array of two entries', () => {
    const data = [
      {
        id: 'py:func:foo',
        domain: 'py',
        role: 'func',
        target: 'foo',
        href: '/api/foo/',
        display: null,
        priority: 0,
      },
      {
        id: 'py:class:Bar',
        domain: 'py',
        role: 'class',
        target: 'Bar',
        href: '/api/Bar/',
        display: null,
        priority: 0,
      },
    ]
    expect(xrefIndexSchema.parse(data)).toEqual(data)
  })

  test('xrefIndexSchema rejects a non-array', () => {
    expect(() =>
      xrefIndexSchema.parse({
        id: 'py:func:foo',
        domain: 'py',
        role: 'func',
        target: 'foo',
        href: '/api/foo/',
      }),
    ).toThrow()
  })
})
