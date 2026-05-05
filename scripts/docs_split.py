"""One-shot migration helper: split a flat package docs page into a Diátaxis tree.

The per-package documentation restructure (see the implementation plan
at ``/home/d/.claude/plans/create-a-plan-to-joyful-valley.md`` and the
woven plan it references) replaces single-file ``docs/packages/<name>.md``
pages with per-package directories carrying ``index.md`` (a 2-line
stub rendered by ``{package-landing}``) plus Diátaxis subpages.

This script handles three modes:

``split``
    Read ``docs/packages/<name>.md``, walk its H2 sections, classify
    each by heading text into a Diátaxis bucket, and write the
    matching ``packages/<name>/docs/<subpage>.md`` files plus a
    2-line ``docs/packages/<name>/index.md`` stub.

``new``
    Generate a fresh ``docs/packages/<name>/index.md`` stub for a
    newly-added package (no flat page to migrate from).

``report``
    Print a candidate-splits report for a flat page without writing.

The script is removed in commit G3 of the migration plan once every
package has shipped — the long-lived part is the
``PackageLandingDirective`` in ``docs/_ext/package_reference.py``.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import typing as t

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# Ordered classification rules. The first matching pattern wins.
# A target of ``None`` deletes the H2 section (it is duplicated by the
# synthesized landing). Unmatched H2 sections fall through to the
# default in :data:`_DEFAULT_BUCKET`.
_H2_RULES: list[tuple[re.Pattern[str], str | None]] = [
    (re.compile(r"^Package reference\s*$", re.IGNORECASE), None),
    (
        re.compile(
            r"^(?:Downstream\s+conf\.py|Working\s+usage\s+examples?)\s*$",
            re.IGNORECASE,
        ),
        "tutorial",
    ),
    (re.compile(r"^Live\s+demos?\b", re.IGNORECASE), "examples"),
    (re.compile(r"^Tool\s+cards?\b", re.IGNORECASE), "examples"),
    (re.compile(r"^Parameter\s+tables?\b", re.IGNORECASE), "examples"),
    (
        re.compile(
            r"^(?:Colou?r\s+palette|CSS\s+custom\s+properties"
            r"|Context-aware\s+sizing)\s*$",
            re.IGNORECASE,
        ),
        "reference",
    ),
    (re.compile(r"^Downstream\s+extensions?\b", re.IGNORECASE), "explanation"),
    (re.compile(r".*\bReference\b.*", re.IGNORECASE), "reference"),
    (re.compile(r"^Config(?:uration)?\s+values?\s*$", re.IGNORECASE), "reference"),
    (re.compile(r"^Directives?\s*$", re.IGNORECASE), "reference"),
    (re.compile(r"^Roles?\s*$", re.IGNORECASE), "reference"),
    (re.compile(r"^CSS\s+classes?\s*$", re.IGNORECASE), "reference"),
]
_DEFAULT_BUCKET: str = "how-to"

_VALID_BUCKETS: tuple[str, ...] = (
    "tutorial",
    "how-to",
    "reference",
    "explanation",
    "examples",
    "errors",
    "cli",
)


_BANNED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:TBD|XXX|FIXME|placeholder)\b", re.IGNORECASE),
    re.compile(r"\bComing soon\b", re.IGNORECASE),
    re.compile(r"\bintentionally blank\b", re.IGNORECASE),
    re.compile(r"\bLorem ipsum\b", re.IGNORECASE),
    re.compile(r"\(write me\)", re.IGNORECASE),
)


class H2Section(t.NamedTuple):
    """One ``## ...`` section captured from a flat package page."""

    heading_text: str
    body_lines: list[str]


def classify_heading(heading_text: str) -> str | None:
    """Return the target Diátaxis bucket for an H2 heading text.

    ``None`` means the section is deleted (e.g. the auto-generated
    ``## Package reference`` block, which the landing now emits).

    Examples
    --------
    >>> classify_heading("Live demos")
    'examples'
    >>> classify_heading("Configuration values")
    'reference'
    >>> classify_heading("Downstream extensions")
    'explanation'
    >>> classify_heading("Package reference") is None
    True
    >>> classify_heading("fastmcp_server_module")
    'how-to'
    """
    text = heading_text.strip()
    for pattern, target in _H2_RULES:
        if pattern.match(text):
            return target
    return _DEFAULT_BUCKET


def parse_h2_sections(markdown: str) -> list[H2Section]:
    r"""Extract every ``## ...`` section from a flat package markdown page.

    Returns a list in source order; the body of each section is every
    line up to but excluding the next ``## ...`` heading. Lines before
    the first ``## ...`` heading are discarded (they are the page
    title + meta directive + Alpha admonition that the landing
    replaces).

    Examples
    --------
    >>> sections = parse_h2_sections(
    ...     "# Title\n\nintro\n\n## First\n\nbody\n\n## Second\n\nmore\n"
    ... )
    >>> [s.heading_text for s in sections]
    ['First', 'Second']
    >>> sections[0].body_lines
    ['', 'body', '']
    """
    sections: list[H2Section] = []
    current_heading: str | None = None
    current_body: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            if current_heading is not None:
                sections.append(H2Section(current_heading, current_body))
            current_heading = line[len("## ") :].strip()
            current_body = []
            continue
        if current_heading is not None:
            current_body.append(line)
    if current_heading is not None:
        sections.append(H2Section(current_heading, current_body))
    return sections


def _trim_blank_edges(lines: list[str]) -> list[str]:
    """Drop leading and trailing blank lines from a list of body lines."""
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def assemble_subpage(
    package_name: str,
    bucket: str,
    sections: list[H2Section],
) -> str:
    """Stitch the sections classified into ``bucket`` into one markdown file.

    Emits an ``(package-name-bucket)=`` anchor + ``# Bucket Title``
    H1 followed by each section's heading and trimmed body.

    Examples
    --------
    >>> sections = [H2Section("Live demos", ["", "demo body", ""])]
    >>> rendered = assemble_subpage("foo", "examples", sections)
    >>> "(foo-examples)=" in rendered
    True
    >>> "# Examples" in rendered
    True
    >>> "## Live demos" in rendered
    True
    """
    bucket_titles = {
        "tutorial": "Tutorial",
        "how-to": "How-to",
        "reference": "Reference",
        "explanation": "Explanation",
        "examples": "Examples",
        "errors": "Errors",
        "cli": "CLI",
    }
    title = bucket_titles.get(bucket, bucket.replace("-", " ").title())
    anchor = f"({package_name}-{bucket})="
    out: list[str] = [anchor, "", f"# {title}", ""]
    for section in sections:
        out.append(f"## {section.heading_text}")
        out.append("")
        body = _trim_blank_edges(list(section.body_lines))
        out.extend(body)
        out.append("")
    while out and not out[-1].strip():
        out.pop()
    out.append("")
    return "\n".join(out)


def assert_no_filler(rendered: str, *, source_label: str) -> None:
    """Raise if the rendered subpage contains any banned-strings pattern."""
    for pattern in _BANNED_PATTERNS:
        match = pattern.search(rendered)
        if match is not None:
            msg = (
                f"banned filler {match.group()!r} in generated {source_label}; "
                "fix the source flat page or split rules before committing"
            )
            raise ValueError(msg)


def stub_markdown(package_name: str) -> str:
    r"""Return the 2-line ``index.md`` stub that calls ``{package-landing}``.

    Examples
    --------
    >>> stub_markdown("sphinx-fonts")
    '```{package-landing} sphinx-fonts\n```\n'
    """
    return f"```{{package-landing}} {package_name}\n```\n"


class _SplitOutcome(t.NamedTuple):
    """Result of classifying a flat page (without writing files)."""

    sections_by_bucket: dict[str, list[H2Section]]
    deleted_headings: list[str]
    package_name: str


def classify_flat_page(flat_path: pathlib.Path) -> _SplitOutcome:
    """Read a flat ``docs/packages/<name>.md`` and bucket its H2 sections.

    Examples
    --------
    >>> import textwrap, tempfile, pathlib as _p
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     flat = _p.Path(tmp) / "demo-pkg.md"
    ...     _ = flat.write_text(textwrap.dedent('''
    ...         # demo-pkg
    ...
    ...         ## Live demos
    ...
    ...         demo body
    ...
    ...         ## Reference
    ...
    ...         reference body
    ...     ''').lstrip())
    ...     outcome = classify_flat_page(flat)
    >>> sorted(outcome.sections_by_bucket.keys())
    ['examples', 'reference']
    >>> outcome.deleted_headings
    []
    """
    text = flat_path.read_text(encoding="utf-8")
    sections = parse_h2_sections(text)
    by_bucket: dict[str, list[H2Section]] = {}
    deleted: list[str] = []
    for section in sections:
        bucket = classify_heading(section.heading_text)
        if bucket is None:
            deleted.append(section.heading_text)
            continue
        by_bucket.setdefault(bucket, []).append(section)
    return _SplitOutcome(
        sections_by_bucket=by_bucket,
        deleted_headings=deleted,
        package_name=flat_path.stem,
    )


def render_report(outcome: _SplitOutcome) -> str:
    """Render a human-readable report of how a flat page would be split."""
    lines = [f"# Migration report for {outcome.package_name}", ""]
    for bucket in _VALID_BUCKETS:
        members = outcome.sections_by_bucket.get(bucket, [])
        if not members:
            continue
        lines.append(f"## -> {bucket}.md")
        lines.extend(f"  - ## {section.heading_text}" for section in members)
        lines.append("")
    if outcome.deleted_headings:
        lines.append("## Deleted (replaced by landing)")
        lines.extend(f"  - ## {heading}" for heading in outcome.deleted_headings)
        lines.append("")
    return "\n".join(lines)


def _run_split(args: argparse.Namespace) -> int:
    flat_path = pathlib.Path(args.flat_page).resolve()
    if not flat_path.is_file():
        sys.stderr.write(f"docs_split: not a file: {flat_path}\n")
        return 1
    outcome = classify_flat_page(flat_path)

    if args.report:
        sys.stdout.write(render_report(outcome))
        return 0

    package_name = outcome.package_name
    out_dir = REPO_ROOT / "docs" / "packages" / package_name
    out_dir.mkdir(parents=True, exist_ok=True)
    for bucket, members in outcome.sections_by_bucket.items():
        rendered = assemble_subpage(package_name, bucket, members)
        assert_no_filler(rendered, source_label=f"{package_name}/{bucket}.md")
        target = out_dir / f"{bucket}.md"
        target.write_text(rendered, encoding="utf-8")
    (out_dir / "index.md").write_text(stub_markdown(package_name), encoding="utf-8")
    if not args.keep_flat:
        flat_path.unlink()
    return 0


def _run_new(args: argparse.Namespace) -> int:
    package_name = args.name
    out_dir = REPO_ROOT / "docs" / "packages" / package_name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.md").write_text(stub_markdown(package_name), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    split = sub.add_parser("split", help="split a flat docs/packages/<name>.md")
    split.add_argument("flat_page", help="path to the flat package page")
    split.add_argument(
        "--report",
        action="store_true",
        help="print classification report only; write nothing",
    )
    split.add_argument(
        "--keep-flat",
        action="store_true",
        help="leave the flat page on disk after splitting (testing aid)",
    )
    split.set_defaults(func=_run_split)

    new = sub.add_parser("new", help="emit a fresh package landing stub")
    new.add_argument("name", help="package name (e.g. sphinx-foo)")
    new.set_defaults(func=_run_new)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
