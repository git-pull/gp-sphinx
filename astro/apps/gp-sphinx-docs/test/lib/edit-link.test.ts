/**
 * Tests for the edit-on-GitHub URL helper.
 *
 * The dogfood docs live at ``docs/<slug>.md`` in the repo. The
 * Sphinx pipeline writes each rendered JSON entry's ``data.id`` as
 * the original Sphinx docname (e.g. ``packages/index`` before
 * Astro's glob loader strips ``/index``), so the helper takes that
 * raw docname and derives the GitHub edit URL.
 */

import { describe, expect, test } from 'vitest'
import { editOnGithubUrl } from '../../src/lib/edit-link.ts'

describe('editOnGithubUrl', () => {
  test('derives a top-level doc URL', () => {
    expect(
      editOnGithubUrl({
        repo: 'https://github.com/git-pull/gp-sphinx',
        branch: 'main',
        docname: 'architecture',
      }),
    ).toBe(
      'https://github.com/git-pull/gp-sphinx/edit/main/docs/architecture.md',
    )
  })

  test('preserves nested docnames untouched', () => {
    expect(
      editOnGithubUrl({
        repo: 'https://github.com/git-pull/gp-sphinx',
        branch: 'main',
        docname: 'packages/gp-sphinx',
      }),
    ).toBe(
      'https://github.com/git-pull/gp-sphinx/edit/main/docs/packages/gp-sphinx.md',
    )
  })

  test('keeps the explicit ``index`` suffix when the source is the section landing page', () => {
    expect(
      editOnGithubUrl({
        repo: 'https://github.com/git-pull/gp-sphinx',
        branch: 'main',
        docname: 'packages/index',
      }),
    ).toBe(
      'https://github.com/git-pull/gp-sphinx/edit/main/docs/packages/index.md',
    )
  })

  test('strips a trailing slash from the repo URL so we never double-slash', () => {
    expect(
      editOnGithubUrl({
        repo: 'https://github.com/git-pull/gp-sphinx/',
        branch: 'main',
        docname: 'architecture',
      }),
    ).toBe(
      'https://github.com/git-pull/gp-sphinx/edit/main/docs/architecture.md',
    )
  })

  test('honours an alternate branch (e.g. while drafting on a feature branch)', () => {
    expect(
      editOnGithubUrl({
        repo: 'https://github.com/git-pull/gp-sphinx',
        branch: 'astro-2026-04-26',
        docname: 'quickstart',
      }),
    ).toBe(
      'https://github.com/git-pull/gp-sphinx/edit/astro-2026-04-26/docs/quickstart.md',
    )
  })
})
