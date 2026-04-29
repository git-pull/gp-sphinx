/**
 * Footer metadata helpers.
 *
 * The footer's content is largely static, but the copyright string
 * needs to render either a single year (``© 2026 …``) or a range
 * (``© 2024–2026 …``) depending on when the project was started and
 * when the page was built. ``formatCopyright`` is the only piece of
 * dynamic logic; making it pure (no module-level ``new Date()``)
 * keeps the rendered output deterministic across build hosts.
 */

export interface FormatCopyrightInput {
  /** Name shown after the year, e.g. ``Tony Narlock``. */
  holder: string
  /** Project label appended after an em-dash. */
  project: string
  /** First year the project carried a copyright. */
  sinceYear: number
  /** A ``Date`` instance — typically ``new Date()`` from the call site. */
  now: Date
}

export function formatCopyright(input: FormatCopyrightInput): string {
  const currentYear = input.now.getUTCFullYear()
  const yearText =
    currentYear > input.sinceYear
      ? `${input.sinceYear}–${currentYear}`
      : String(currentYear)
  return `© ${yearText} ${input.holder} — ${input.project}`
}
