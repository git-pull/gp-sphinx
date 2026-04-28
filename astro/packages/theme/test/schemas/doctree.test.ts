import { describe, expect, test } from 'vitest'
import {
  admonitionNodeSchema,
  blockNodeSchema,
  blockQuoteNodeSchema,
  bulletListNodeSchema,
  commentNodeSchema,
  definitionListItemNodeSchema,
  definitionListNodeSchema,
  documentSchema,
  emphasisNodeSchema,
  enumeratedListNodeSchema,
  imageNodeSchema,
  inlineNodeSchema,
  listItemNodeSchema,
  literalBlockNodeSchema,
  literalNodeSchema,
  paragraphNodeSchema,
  referenceNodeSchema,
  sectionNodeSchema,
  strongNodeSchema,
  textNodeSchema,
  transitionNodeSchema,
} from '../../src/schemas/doctree.ts'

describe('doctree zod schemas — leaf inline shapes', () => {
  test('textNodeSchema round-trips a canonical text node', () => {
    const data = { type: 'text', value: 'hi' } as const
    expect(textNodeSchema.parse(data)).toEqual(data)
  })

  test('textNodeSchema rejects wrong discriminator', () => {
    expect(() => textNodeSchema.parse({ type: 'paragraph', value: 'x' })).toThrow()
  })

  test('literalNodeSchema round-trips with a value field', () => {
    expect(literalNodeSchema.parse({ type: 'literal', value: 'x' })).toEqual({
      type: 'literal',
      value: 'x',
    })
  })

  test('imageNodeSchema accepts uri with explicit alt', () => {
    expect(imageNodeSchema.parse({ type: 'image', uri: '/x.svg', alt: 'X' })).toEqual({
      type: 'image',
      uri: '/x.svg',
      alt: 'X',
    })
  })

  test('imageNodeSchema accepts uri with null alt', () => {
    expect(imageNodeSchema.parse({ type: 'image', uri: '/x.svg', alt: null })).toEqual({
      type: 'image',
      uri: '/x.svg',
      alt: null,
    })
  })
})

describe('doctree zod schemas — recursive inline shapes', () => {
  test('emphasisNodeSchema validates nested emphasis', () => {
    const data = {
      type: 'emphasis',
      children: [{ type: 'emphasis', children: [{ type: 'text', value: 'x' }] }],
    }
    expect(emphasisNodeSchema.parse(data)).toEqual(data)
  })

  test('strongNodeSchema accepts a strong run wrapping inline children', () => {
    const data = {
      type: 'strong',
      children: [{ type: 'text', value: 'loud' }],
    }
    expect(strongNodeSchema.parse(data)).toEqual(data)
  })

  test('referenceNodeSchema carries href and inline children', () => {
    const data = {
      type: 'reference',
      href: 'https://example.com',
      children: [{ type: 'text', value: 'Example' }],
    }
    expect(referenceNodeSchema.parse(data)).toEqual(data)
  })
})

describe('doctree zod schemas — block shapes', () => {
  test('paragraphNodeSchema accepts mixed inline children', () => {
    const data = {
      type: 'paragraph',
      children: [
        { type: 'text', value: 'a' },
        { type: 'strong', children: [{ type: 'text', value: 'b' }] },
        { type: 'literal', value: 'c' },
      ],
    }
    expect(paragraphNodeSchema.parse(data)).toEqual(data)
  })

  test('paragraphNodeSchema rejects a block child in inline position', () => {
    expect(() =>
      paragraphNodeSchema.parse({
        type: 'paragraph',
        children: [{ type: 'section', id: 'x', title: [], children: [] }],
      }),
    ).toThrow()
  })

  test('sectionNodeSchema carries id, inline title, and block children', () => {
    const data = {
      type: 'section',
      id: 'x',
      title: [{ type: 'text', value: 'X' }],
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'y' }],
        },
      ],
    }
    expect(sectionNodeSchema.parse(data)).toEqual(data)
  })

  test('literalBlockNodeSchema accepts language and code', () => {
    expect(
      literalBlockNodeSchema.parse({
        type: 'literalBlock',
        language: 'python',
        code: 'x = 1',
      }),
    ).toEqual({ type: 'literalBlock', language: 'python', code: 'x = 1' })
  })

  test('literalBlockNodeSchema accepts null language', () => {
    expect(
      literalBlockNodeSchema.parse({
        type: 'literalBlock',
        language: null,
        code: 'x = 1',
      }),
    ).toEqual({ type: 'literalBlock', language: null, code: 'x = 1' })
  })

  test('commentNodeSchema carries a value', () => {
    expect(commentNodeSchema.parse({ type: 'comment', value: 'TODO' })).toEqual({
      type: 'comment',
      value: 'TODO',
    })
  })

  test('transitionNodeSchema is payload-less', () => {
    expect(transitionNodeSchema.parse({ type: 'transition' })).toEqual({
      type: 'transition',
    })
  })

  test('blockQuoteNodeSchema wraps block children', () => {
    const data = {
      type: 'blockQuote',
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'q' }],
        },
      ],
    }
    expect(blockQuoteNodeSchema.parse(data)).toEqual(data)
  })

  test('listItemNodeSchema wraps block children', () => {
    const data = {
      type: 'listItem',
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'a' }],
        },
      ],
    }
    expect(listItemNodeSchema.parse(data)).toEqual(data)
  })

  test('bulletListNodeSchema accepts list_item children only', () => {
    const data = {
      type: 'bulletList',
      children: [
        {
          type: 'listItem',
          children: [
            {
              type: 'paragraph',
              children: [{ type: 'text', value: 'a' }],
            },
          ],
        },
      ],
    }
    expect(bulletListNodeSchema.parse(data)).toEqual(data)
  })

  test('enumeratedListNodeSchema accepts an explicit start', () => {
    const data = {
      type: 'enumeratedList',
      start: 3,
      children: [
        {
          type: 'listItem',
          children: [
            {
              type: 'paragraph',
              children: [{ type: 'text', value: 'c' }],
            },
          ],
        },
      ],
    }
    expect(enumeratedListNodeSchema.parse(data)).toEqual(data)
  })
})

describe('doctree zod schemas — admonitions', () => {
  const variants = [
    'note',
    'warning',
    'attention',
    'caution',
    'important',
    'tip',
    'hint',
    'danger',
    'error',
  ] as const

  test.each(variants)('admonitionNodeSchema accepts variant=%s', (variant) => {
    const data = {
      type: 'admonition',
      variant,
      children: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'x' }],
        },
      ],
    }
    expect(admonitionNodeSchema.parse(data)).toEqual(data)
  })

  test('admonitionNodeSchema rejects unknown variant', () => {
    expect(() =>
      admonitionNodeSchema.parse({
        type: 'admonition',
        variant: 'celebration',
        children: [],
      }),
    ).toThrow()
  })
})

describe('doctree zod schemas — definition lists', () => {
  test('definitionListItemNodeSchema carries term + definition slots', () => {
    const data = {
      type: 'definitionListItem',
      term: [{ type: 'text', value: 'foo' }],
      definition: [
        {
          type: 'paragraph',
          children: [{ type: 'text', value: 'describes foo' }],
        },
      ],
    }
    expect(definitionListItemNodeSchema.parse(data)).toEqual(data)
  })

  test('definitionListNodeSchema wraps definition_list_item children', () => {
    const data = {
      type: 'definitionList',
      children: [
        {
          type: 'definitionListItem',
          term: [{ type: 'text', value: 'x' }],
          definition: [
            {
              type: 'paragraph',
              children: [{ type: 'text', value: 'y' }],
            },
          ],
        },
      ],
    }
    expect(definitionListNodeSchema.parse(data)).toEqual(data)
  })
})

describe('doctree zod schemas — discriminated unions', () => {
  const inlineFixtures = [
    { type: 'text', value: 'x' },
    { type: 'literal', value: 'x' },
    { type: 'emphasis', children: [{ type: 'text', value: 'x' }] },
    { type: 'strong', children: [{ type: 'text', value: 'x' }] },
    {
      type: 'reference',
      href: 'https://example.com',
      children: [{ type: 'text', value: 'x' }],
    },
    { type: 'image', uri: '/x.svg', alt: null },
  ] as const

  test.each(inlineFixtures)('inlineNodeSchema validates type=$type', (fixture) => {
    const parsed = inlineNodeSchema.parse(fixture)
    expect(parsed.type).toBe(fixture.type)
  })

  test('inlineNodeSchema rejects a block-level node', () => {
    expect(() =>
      inlineNodeSchema.parse({
        type: 'paragraph',
        children: [{ type: 'text', value: 'x' }],
      }),
    ).toThrow()
  })

  test('blockNodeSchema validates each block variant', () => {
    expect(blockNodeSchema.parse({ type: 'transition' }).type).toBe('transition')
    expect(blockNodeSchema.parse({ type: 'comment', value: 'TODO' }).type).toBe('comment')
  })

  test('blockNodeSchema rejects an inline node', () => {
    expect(() => blockNodeSchema.parse({ type: 'text', value: 'x' })).toThrow()
  })
})

describe('doctree zod schemas — Document', () => {
  test('documentSchema accepts the canonical hello-world payload', () => {
    const data = {
      id: 'index',
      title: 'Hello world',
      tree: {
        type: 'section',
        id: 'hello-world',
        title: [{ type: 'text', value: 'Hello world' }],
        children: [
          {
            type: 'paragraph',
            children: [
              { type: 'text', value: 'Hello ' },
              {
                type: 'emphasis',
                children: [{ type: 'text', value: 'world' }],
              },
              { type: 'text', value: '.' },
            ],
          },
        ],
      },
    }
    expect(documentSchema.parse(data)).toEqual(data)
  })

  test('documentSchema rejects a tree that is not a section', () => {
    expect(() =>
      documentSchema.parse({
        id: 'x',
        title: 'X',
        tree: { type: 'paragraph', children: [] },
      }),
    ).toThrow()
  })
})
