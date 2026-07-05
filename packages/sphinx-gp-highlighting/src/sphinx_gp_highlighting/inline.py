"""Inline literal roles and transforms for Sphinx highlighting."""

from __future__ import annotations

import re
import typing as t

from docutils import nodes
from docutils.transforms import Transform

if t.TYPE_CHECKING:
    from docutils.parsers.rst.states import Inliner

InlineLiteralKind: t.TypeAlias = t.Literal["command", "shell-session", "path", "dir"]

_BASE_CLASS = "gp-sphinx-highlighting-inline"
_COMMAND_LANGUAGE = "bash"
_SHELL_SESSION_LANGUAGE = "console"
_SHELL_SESSION_RE = re.compile(r"^\$ \S")
_HOME_OR_DOT_PATH_RE = re.compile(r"^(?:~|\.{1,2}/)[^\s`]*$")
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/][^\s`]+$")
_RELATIVE_DIR_RE = re.compile(r"^(?:[\w.-]+/)+$")
_RELATIVE_FILE_RE = re.compile(r"^(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9][\w.-]*$")
_ABSOLUTE_PATH_ROOTS = frozenset(
    {
        "Applications",
        "Library",
        "Users",
        "bin",
        "dev",
        "etc",
        "home",
        "lib",
        "lib64",
        "mnt",
        "opt",
        "proc",
        "root",
        "run",
        "sbin",
        "srv",
        "sys",
        "tmp",
        "usr",
        "var",
        "Volumes",
    }
)


def classify_inline_literal(
    text: str,
    *,
    commands: t.Iterable[str] = (),
) -> InlineLiteralKind | None:
    """Classify a literal that is safe to highlight automatically.

    Parameters
    ----------
    text : str
        Literal text.
    commands : iterable of str
        Command names eligible for bare command highlighting.

    Returns
    -------
    InlineLiteralKind | None
        The safe literal kind, or ``None`` when the text should remain
        an ordinary inline literal.

    Examples
    --------
    >>> classify_inline_literal("tmuxp freeze my-session", commands=["tmuxp"])
    'command'
    >>> classify_inline_literal("~/.config/tmuxp/")
    'dir'
    >>> classify_inline_literal("module_name") is None
    True
    """
    candidate = text.strip()
    if not candidate or "\n" in candidate:
        return None
    if _SHELL_SESSION_RE.match(candidate):
        return "shell-session"
    first_word = candidate.split(maxsplit=1)[0]
    if first_word in set(commands) and " " in candidate:
        return "command"
    if _is_path_like(candidate):
        return "dir" if candidate.endswith("/") else "path"
    return None


def build_highlighted_literal(text: str, kind: InlineLiteralKind) -> nodes.literal:
    """Build a literal node with package highlighting classes.

    Parameters
    ----------
    text : str
        Literal text.
    kind : InlineLiteralKind
        Highlighting kind.

    Returns
    -------
    nodes.literal
        Literal node ready for the Sphinx HTML writer.

    Examples
    --------
    >>> node = build_highlighted_literal("tmuxp freeze my-session", "command")
    >>> node["language"]
    'bash'
    >>> "gp-sphinx-highlighting-inline--kind-command" in node["classes"]
    True
    >>> "language" in build_highlighted_literal("~/.config/tmuxp/", "dir")
    False
    """
    node = nodes.literal(
        text,
        text,
        classes=[_BASE_CLASS, f"{_BASE_CLASS}--kind-{kind}"],
    )
    if kind in {"command", "shell-session"}:
        node["classes"].extend(["code", "highlight"])
        node["language"] = (
            _SHELL_SESSION_LANGUAGE if kind == "shell-session" else _COMMAND_LANGUAGE
        )
    return node


def cmd_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner | None,
    options: dict[str, t.Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Role for inline shell commands.

    Parameters
    ----------
    name : str
        Role name.
    rawtext : str
        Full role markup.
    text : str
        Role content.
    lineno : int
        Source line number.
    inliner : Inliner | None
        Docutils inliner.
    options : dict | None
        Role options.
    content : list | None
        Role content lines.

    Returns
    -------
    tuple[list[nodes.Node], list[nodes.system_message]]
        Role output nodes and messages.

    Examples
    --------
    >>> nodes_, messages = cmd_role(
    ...     "cmd", "{cmd}`tmuxp freeze x`", "tmuxp freeze x", 1, None
    ... )
    >>> messages
    []
    >>> nodes_[0]["language"]
    'bash'
    """
    return [build_highlighted_literal(text, "command")], []


def path_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner | None,
    options: dict[str, t.Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Role for inline filesystem paths.

    Parameters
    ----------
    name : str
        Role name.
    rawtext : str
        Full role markup.
    text : str
        Role content.
    lineno : int
        Source line number.
    inliner : Inliner | None
        Docutils inliner.
    options : dict | None
        Role options.
    content : list | None
        Role content lines.

    Returns
    -------
    tuple[list[nodes.Node], list[nodes.system_message]]
        Role output nodes and messages.

    Examples
    --------
    >>> nodes_, messages = path_role("path", "{path}`~/x.py`", "~/x.py", 1, None)
    >>> messages
    []
    >>> "gp-sphinx-highlighting-inline--kind-path" in nodes_[0]["classes"]
    True
    """
    return [build_highlighted_literal(text, "path")], []


def dir_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner | None,
    options: dict[str, t.Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Role for inline filesystem directories.

    Parameters
    ----------
    name : str
        Role name.
    rawtext : str
        Full role markup.
    text : str
        Role content.
    lineno : int
        Source line number.
    inliner : Inliner | None
        Docutils inliner.
    options : dict | None
        Role options.
    content : list | None
        Role content lines.

    Returns
    -------
    tuple[list[nodes.Node], list[nodes.system_message]]
        Role output nodes and messages.

    Examples
    --------
    >>> nodes_, messages = dir_role("dir", "{dir}`~/x/`", "~/x/", 1, None)
    >>> messages
    []
    >>> "gp-sphinx-highlighting-inline--kind-dir" in nodes_[0]["classes"]
    True
    """
    return [build_highlighted_literal(text, "dir")], []


class HighlightingInlineTransform(Transform):
    """Highlight safe inline literals when configured."""

    default_priority = 120

    def apply(self) -> None:
        """Rewrite safe inline literals to highlighted literal nodes."""
        env = getattr(self.document.settings, "env", None)
        if env is None:
            return
        config = env.app.config
        if getattr(config, "gp_highlighting_inline_literals", "off") != "safe":
            return
        commands = tuple(getattr(config, "gp_highlighting_inline_commands", ()))
        for literal in list(self.document.findall(nodes.literal)):
            if _should_skip_literal(literal):
                continue
            kind = classify_inline_literal(literal.astext(), commands=commands)
            if kind is None:
                continue
            replacement = build_highlighted_literal(literal.astext(), kind)
            replacement.source = literal.source
            replacement.line = literal.line
            literal.replace_self(replacement)


def _is_path_like(text: str) -> bool:
    """Return whether ``text`` looks like a filesystem path.

    Examples
    --------
    >>> _is_path_like("~/.config/tmuxp/")
    True
    >>> _is_path_like("/mnt/c/Users/example")
    True
    >>> _is_path_like("application/json")
    False
    """
    return bool(
        _HOME_OR_DOT_PATH_RE.match(text)
        or _WINDOWS_PATH_RE.match(text)
        or _is_absolute_filesystem_path(text)
        or _is_relative_filesystem_path(text)
    )


def _is_absolute_filesystem_path(text: str) -> bool:
    """Return whether ``text`` starts with a common absolute path root.

    Examples
    --------
    >>> _is_absolute_filesystem_path("/proc/version")
    True
    >>> _is_absolute_filesystem_path("/api/pull")
    False
    """
    if not text.startswith("/"):
        return False
    first_component = text.removeprefix("/").split("/", maxsplit=1)[0]
    return first_component in _ABSOLUTE_PATH_ROOTS


def _is_relative_filesystem_path(text: str) -> bool:
    """Return whether ``text`` is a conservative bare relative path.

    Examples
    --------
    >>> _is_relative_filesystem_path("docs/conf.py")
    True
    >>> _is_relative_filesystem_path("resources/read")
    False
    """
    if text.startswith(("/", "~", "./", "../")):
        return False
    first_component = text.split("/", maxsplit=1)[0]
    if "." in first_component and not first_component.startswith("."):
        return False
    return bool(_RELATIVE_DIR_RE.match(text) or _RELATIVE_FILE_RE.match(text))


def _should_skip_literal(node: nodes.literal) -> bool:
    """Return whether a literal should not be rewritten."""
    classes: set[str] = set(node.get("classes", ()))
    if _BASE_CLASS in classes:
        return True
    return bool("language" in node or "code" in classes)
