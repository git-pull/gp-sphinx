import { describe, expect, test } from 'vitest'
import {
  parameterKindSchema,
  parameterSchema,
  symbolKindSchema,
  symbolSchema,
  symbolSourceSchema,
} from '../../src/schemas/symbol.ts'

describe('symbol zod schemas — leaves', () => {
  test('parameterKindSchema accepts each canonical kind', () => {
    for (const k of ['positional', 'keyword', 'var_positional', 'var_keyword'] as const) {
      expect(parameterKindSchema.parse(k)).toBe(k)
    }
  })

  test('parameterKindSchema rejects unknown kind', () => {
    expect(() => parameterKindSchema.parse('weird')).toThrow()
  })

  test('parameterSchema round-trips with non-null annotation and default', () => {
    const data = {
      name: 'count',
      annotation: 'int',
      default: '0',
      kind: 'positional' as const,
    }
    expect(parameterSchema.parse(data)).toEqual(data)
  })

  test('parameterSchema accepts null annotation and default', () => {
    const data = {
      name: 'x',
      annotation: null,
      default: null,
      kind: 'keyword' as const,
    }
    expect(parameterSchema.parse(data)).toEqual(data)
  })

  test('symbolSourceSchema carries repo, path, and line', () => {
    const data = { repo: 'x', path: 'y.py', line: 42 }
    expect(symbolSourceSchema.parse(data)).toEqual(data)
  })

  test('symbolKindSchema accepts each canonical kind', () => {
    const kinds = [
      'function',
      'class',
      'method',
      'attribute',
      'property',
      'enum',
      'dataclass',
      'module',
    ] as const
    for (const k of kinds) {
      expect(symbolKindSchema.parse(k)).toBe(k)
    }
  })

  test('symbolKindSchema rejects unknown kind', () => {
    expect(() => symbolKindSchema.parse('namespace')).toThrow()
  })
})

describe('symbol zod schemas — Symbol', () => {
  test('symbolSchema accepts the canonical hello-symbol payload', () => {
    const data = {
      id: 'demo_api.merge_demo',
      kind: 'function' as const,
      name: 'merge_demo',
      qualname: 'merge_demo',
      module: 'demo_api',
      signature: '(project: str, version: str = "0.0.0") -> dict[str, str]',
      parameters: [
        {
          name: 'project',
          annotation: 'str',
          default: null,
          kind: 'positional' as const,
        },
        {
          name: 'version',
          annotation: 'str',
          default: '"0.0.0"',
          kind: 'positional' as const,
        },
      ],
      returns: 'dict[str, str]',
      docstring_summary: 'Merge a tiny pseudo-config payload.',
      docstring_body: [
        {
          type: 'paragraph' as const,
          children: [{ type: 'text' as const, value: 'Merge a tiny pseudo-config payload.' }],
        },
      ],
      source: {
        repo: 'https://github.com/git-pull/gp-sphinx',
        path: 'demo_api.py',
        line: 4,
      },
    }
    expect(symbolSchema.parse(data)).toEqual(data)
  })

  test('symbolSchema accepts a payload with empty docstring_body', () => {
    const data = {
      id: 'x.y.foo',
      kind: 'function' as const,
      name: 'foo',
      qualname: 'foo',
      module: 'x.y',
      signature: '() -> None',
      parameters: [],
      returns: null,
      docstring_summary: '',
      docstring_body: [],
      source: null,
    }
    expect(symbolSchema.parse(data)).toEqual(data)
  })

  test('symbolSchema rejects an inline node in docstring_body', () => {
    expect(() =>
      symbolSchema.parse({
        id: 'x',
        kind: 'function' as const,
        name: 'x',
        qualname: 'x',
        module: 'x',
        signature: '()',
        parameters: [],
        returns: null,
        docstring_summary: '',
        docstring_body: [{ type: 'text' as const, value: 'wrong' }],
        source: null,
      }),
    ).toThrow()
  })
})
