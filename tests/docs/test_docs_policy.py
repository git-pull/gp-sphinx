"""Policy tests for hand-authored documentation pages."""

from __future__ import annotations

import ast
import inspect
import pathlib
import re
import typing as t

import pytest

from gp_sphinx.config import merge_sphinx_config

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"


class MarkdownFence(t.NamedTuple):
    """One fenced code block from a Markdown document."""

    test_id: str
    path: pathlib.Path
    line_number: int
    language: str
    body: str


_FENCE_START_RE = re.compile(r"^(?P<indent>\s*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_INLINE_DOC_COMMANDS = (
    "`just start-docs`",
    "`just start`",
    "`cd docs/` and `just html`",
    "`just serve`",
    "`just build-docs`, `just serve-docs`",
    "`just watch-docs`",
    "`just dev-docs`",
)
_DOCUMENTED_OVERRIDE_KWARGS = frozenset(
    {
        "api_collapsed_threshold",
        "api_layout_enabled",
        "linkcode_resolve",
    },
)


def _markdown_files() -> list[pathlib.Path]:
    """Return hand-authored Markdown files in ``docs/``."""
    return sorted(
        path
        for path in DOCS_ROOT.rglob("*.md")
        if "_build" not in path.parts and path.name not in {"AGENTS.md", "CLAUDE.md"}
    )


def _iter_markdown_fences(path: pathlib.Path) -> t.Iterator[MarkdownFence]:
    """Yield fenced code blocks with their source location."""
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        start = _FENCE_START_RE.match(lines[index])
        if start is None:
            index += 1
            continue

        fence_marker = start.group("fence")
        fence_char = fence_marker[0]
        fence_len = len(fence_marker)
        info = start.group("info").strip()
        language = info.split(maxsplit=1)[0] if info else ""
        body_start = index + 1
        index = body_start
        body_lines: list[str] = []
        while index < len(lines):
            stripped = lines[index].strip()
            if stripped.startswith(fence_char * fence_len):
                break
            body_lines.append(lines[index])
            index += 1

        yield MarkdownFence(
            test_id=f"{path.relative_to(REPO_ROOT)}:{body_start}",
            path=path,
            line_number=body_start,
            language=language,
            body="\n".join(body_lines),
        )
        index += 1


def _python_fences_with_merge_config() -> list[MarkdownFence]:
    """Return Python snippets that call ``merge_sphinx_config``."""
    return [
        fence
        for path in _markdown_files()
        for fence in _iter_markdown_fences(path)
        if fence.language == "python" and "merge_sphinx_config(" in fence.body
    ]


def test_release_docs_leave_tagging_to_maintainers() -> None:
    """Release docs do not teach agent-forbidden tag creation or tag pushes."""
    text = (DOCS_ROOT / "project" / "releasing.md").read_text(encoding="utf-8")

    assert "git commit -m 'Tag v" in text
    assert "git tag " not in text
    assert "git push --tags" not in text


def test_contributing_docs_use_copyable_documentation_commands() -> None:
    """Documentation workflow commands are shown as console blocks."""
    text = (DOCS_ROOT / "project" / "contributing.md").read_text(encoding="utf-8")
    docs_section = text.split("## Documentation", maxsplit=1)[1].split(
        "## Test hierarchy",
        maxsplit=1,
    )[0]

    offenders = [command for command in _INLINE_DOC_COMMANDS if command in docs_section]
    assert offenders == []


def test_console_blocks_contain_one_prompted_command() -> None:
    """Each console block has one copyable command prompt."""
    offenders: list[str] = []
    for path in _markdown_files():
        for fence in _iter_markdown_fences(path):
            if fence.language != "console":
                continue
            prompted = [
                line
                for line in fence.body.splitlines()
                if line.lstrip().startswith("$ ")
            ]
            if len(prompted) != 1:
                offenders.append(f"{fence.test_id}: {len(prompted)} prompted commands")

    assert offenders == []


def test_package_how_to_pages_open_with_concept_prose() -> None:
    """Package how-to pages introduce the concept before configuration blocks."""
    offenders: list[str] = []
    for path in sorted((DOCS_ROOT / "packages").glob("*/how-to.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("(") or stripped.startswith("#"):
                continue
            if stripped.startswith("```") or stripped.startswith("::::"):
                offenders.append(str(path.relative_to(REPO_ROOT)))
            break

    assert offenders == []


@pytest.mark.parametrize(
    "fence",
    _python_fences_with_merge_config(),
    ids=lambda fence: fence.test_id,
)
def test_merge_sphinx_config_snippets_use_known_kwargs(fence: MarkdownFence) -> None:
    """Coordinator snippets use real params or documented override keys."""
    signature = inspect.signature(merge_sphinx_config)
    allowed = {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
    } | _DOCUMENTED_OVERRIDE_KWARGS
    tree = ast.parse(fence.body)
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "merge_sphinx_config":
            continue
        offenders.extend(
            keyword.arg
            for keyword in node.keywords
            if keyword.arg is not None and keyword.arg not in allowed
        )

    assert offenders == []
