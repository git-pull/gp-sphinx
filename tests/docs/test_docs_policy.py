"""Policy tests for hand-authored documentation pages."""

from __future__ import annotations

import ast
import inspect
import pathlib
import re
import sys
import typing as t

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference

from gp_sphinx.config import merge_sphinx_config

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
GP_SPHINX_CONFIG = (
    REPO_ROOT / "packages" / "gp-sphinx" / "src" / "gp_sphinx" / "config.py"
)


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
_GENERIC_PY_ROLE_RE = re.compile(r"\{(func|class|meth|attr|data|mod|exc)\}`")


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


def _setup_function() -> ast.FunctionDef:
    """Return the coordinator ``setup`` function AST."""
    tree = ast.parse(GP_SPHINX_CONFIG.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "setup":
            return node
    msg = f"setup() not found in {GP_SPHINX_CONFIG}"
    raise AssertionError(msg)


def _literal_arg(call: ast.Call, index: int) -> str | None:
    """Return a literal string argument from an AST call."""
    try:
        node = call.args[index]
    except IndexError:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_handler_name(call: ast.Call, index: int) -> str | None:
    """Return a simple handler name from an AST call."""
    try:
        node = call.args[index]
    except IndexError:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


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


def test_docs_use_explicit_py_domain_roles() -> None:
    """Python-domain roles are spelled explicitly in authored docs."""
    offenders: list[str] = []
    for path in _markdown_files():
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if _GENERIC_PY_ROLE_RE.search(line):
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}:{line_number}: {line.strip()}"
                )

    assert offenders == []


def test_packages_with_config_values_document_reference_surfaces() -> None:
    """Packages that register config values expose them from reference pages."""
    offenders: list[str] = []
    for package in package_reference.workspace_packages():
        package_name = package["name"]
        if package_name == "gp-sphinx":
            continue
        modules = package_reference.extension_modules(package["module_name"])
        modules_with_config = [
            block["module"]
            for module in modules
            if (block := package_reference.collect_extension_surface(module))[
                "config_values"
            ]
        ]
        if not modules_with_config:
            continue

        reference = DOCS_ROOT / "packages" / package_name / "reference.md"
        if not reference.is_file():
            offenders.append(
                f"{package_name}: missing reference.md for {modules_with_config}",
            )
            continue

        text = reference.read_text(encoding="utf-8")
        missing = [
            module
            for module in modules_with_config
            if f".. autoconfigvalues:: {module}" not in text
        ]
        if missing:
            offenders.append(f"{package_name}: missing autoconfigvalues for {missing}")

    assert offenders == []


def test_coordinator_setup_docs_match_registered_surface() -> None:
    """The coordinator setup reference lists registered hooks and lexers."""
    setup = _setup_function()
    connect_calls: list[tuple[str, str]] = []
    lexers: list[str] = []

    for node in ast.walk(setup):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "connect":
            event = _literal_arg(node, 0)
            handler = _call_handler_name(node, 1)
            if event is not None and handler is not None:
                connect_calls.append((event, handler))
        if node.func.attr == "add_lexer":
            lexer = _literal_arg(node, 0)
            if lexer is not None:
                lexers.append(lexer)

    text = (DOCS_ROOT / "configuration.md").read_text(encoding="utf-8")
    missing = [
        f"{event}:{handler}"
        for event, handler in connect_calls
        if event not in text or handler not in text
    ]
    missing.extend(f"lexer:{lexer}" for lexer in lexers if lexer not in text)

    assert missing == []


def test_tutorial_pages_start_as_learning_paths() -> None:
    """Tutorial pages do not open as generated-example inventories."""
    offenders: list[str] = []
    for path in sorted((DOCS_ROOT / "packages").glob("*/tutorial.md")):
        text = path.read_text(encoding="utf-8")
        first_section = next(
            (line.strip() for line in text.splitlines() if line.startswith("## ")),
            "",
        )
        if first_section == "## Working usage examples":
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_whats_new_avoids_branch_internal_names() -> None:
    """Published docs avoid branch-internal narrative."""
    text = (DOCS_ROOT / "whats-new.md").read_text(encoding="utf-8")

    assert "autodoc-improvements" not in text


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
