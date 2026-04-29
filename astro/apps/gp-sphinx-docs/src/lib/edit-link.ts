/**
 * Edit-on-GitHub URL helper.
 *
 * Derives the canonical GitHub ``/edit/<branch>/docs/<docname>.md``
 * URL from a Sphinx docname. The doc page route passes
 * ``entry.data.id`` (the original Sphinx docname, before Astro's
 * glob loader normalises ``<dir>/index`` to ``<dir>``) so the edit
 * link always points at the on-disk source file even when the URL
 * slug differs.
 */

export interface EditOnGithubUrlOptions {
  /** Repository home URL, e.g. ``https://github.com/git-pull/gp-sphinx``. */
  repo: string
  /** Branch the docs source lives on. */
  branch: string
  /** Sphinx docname — ``architecture`` / ``packages/index``. */
  docname: string
}

export function editOnGithubUrl(options: EditOnGithubUrlOptions): string {
  const repo = options.repo.replace(/\/+$/, '')
  return `${repo}/edit/${options.branch}/docs/${options.docname}.md`
}
