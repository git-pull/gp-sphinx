"""Generate package reference sections from live workspace metadata.

Architecture
------------
This Sphinx extension auto-generates the "Registered Surface" and "Copyable
config snippet" sections that appear at the bottom of every
``docs/packages/<name>.md`` page.  It works in three layers:

1. **Workspace discovery** (``workspace_packages()``) — walks
   ``packages/*/pyproject.toml`` to find every publishable package and reads
   its name, version, description, classifiers, and GitHub URL.

2. **Surface extraction** (``collect_extension_surface()``) — imports the
   module and monkey-patches ``app.add_*`` methods on a lightweight mock
   ``Sphinx`` object to intercept calls that ``setup()`` makes.  Each
   registered item (config value, directive, role, lexer, theme) is captured
   into a ``SurfaceDict``.

3. **Rendering** (``package_reference_markdown()``) — converts the collected
   surface into a Markdown fragment (config snippet + tables), which the
   ``PackageReferenceDirective`` injects into the page via a raw docutils node.

Adding a new package
--------------------
No code changes are required.  Once a ``packages/<name>/pyproject.toml``
exists with a ``[project]`` table the package is picked up automatically on
the next docs build.

Extending the surface extractor
--------------------------------
To capture a new ``app.add_*`` call, add a handler to the mock
``_MockApp`` class inside ``collect_extension_surface()``.  Follow the pattern
of the existing ``add_directive`` / ``add_role`` handlers.

Examples
--------
>>> package = workspace_packages()[0]
>>> package["name"] in {
...     "gp-sphinx",
...     "sphinx-fonts",
...     "sphinx-gptheme",
...     "sphinx-argparse-neo",
...     "sphinx-autodoc-docutils",
...     "sphinx-autodoc-pytest-fixtures",
...     "sphinx-autodoc-sphinx",
... }
True

>>> surface = collect_extension_surface("sphinx_fonts")
>>> any(item["name"] == "sphinx_fonts" for item in surface["config_values"])
True
"""

from __future__ import annotations

import configparser
import importlib
import inspect
import logging
import os
import pathlib
import pkgutil
import sys
import typing as t

from docutils import nodes
from docutils.parsers.rst import roles
from sphinx.util.docutils import SphinxDirective

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class SurfaceDict(t.TypedDict):
    """Collected extension surface rows keyed by registration category."""

    module: str
    config_values: list[dict[str, str]]
    directives: list[dict[str, str]]
    roles: list[dict[str, str]]
    lexers: list[dict[str, str]]
    themes: list[dict[str, str]]


def ensure_workspace_imports() -> None:
    """Ensure each workspace package ``src`` directory is importable.

    Examples
    --------
    >>> ensure_workspace_imports()
    """
    for package in workspace_packages():
        src_path = os.fspath(pathlib.Path(package["package_dir"]) / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)


def workspace_root() -> pathlib.Path:
    """Return the repository root for the current docs build.

    Examples
    --------
    >>> workspace_root().name
    'gp-sphinx'
    """
    return pathlib.Path(__file__).resolve().parents[2]


def workspace_packages() -> list[dict[str, str]]:
    """Return publishable workspace packages and their module names.

    Examples
    --------
    >>> names = [package["name"] for package in workspace_packages()]
    >>> "gp-sphinx" in names
    True
    """
    packages_dir = workspace_root() / "packages"
    packages: list[dict[str, str]] = []
    for pyproject_path in sorted(packages_dir.glob("*/pyproject.toml")):
        with pyproject_path.open("rb") as handle:
            project = tomllib.load(handle)["project"]
        src_dir = pyproject_path.parent / "src"
        module_dir = next((path for path in src_dir.iterdir() if path.is_dir()), None)
        if module_dir is None:
            continue
        packages.append(
            {
                "name": str(project["name"]),
                "module_name": module_dir.name,
                "package_dir": str(pyproject_path.parent),
                "description": str(project.get("description", "")),
                "version": str(project["version"]),
                "repository": str(project.get("urls", {}).get("Repository", "")),
                "maturity": maturity_from_classifiers(
                    t.cast(list[str], project.get("classifiers", []))
                ),
            }
        )
    return packages


def maturity_from_classifiers(classifiers: list[str]) -> str:
    """Return the short maturity label derived from project classifiers.

    Examples
    --------
    >>> maturity_from_classifiers(["Development Status :: 4 - Beta"])
    'Beta'
    >>> maturity_from_classifiers([])
    'Unknown'
    """
    for classifier in classifiers:
        if classifier.startswith("Development Status :: 3"):
            return "Alpha"
        if classifier.startswith("Development Status :: 4"):
            return "Beta"
        if classifier.startswith("Development Status :: 5"):
            return "Production/Stable"
    return "Unknown"


def extension_modules(module_name: str) -> list[str]:
    """Return importable submodules that expose a Sphinx ``setup()`` function.

    Examples
    --------
    >>> "sphinx_argparse_neo" in extension_modules("sphinx_argparse_neo")
    True
    >>> "sphinx_argparse_neo.exemplar" in extension_modules("sphinx_argparse_neo")
    True
    """
    ensure_workspace_imports()
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        logger.warning("package-reference: could not import %r", module_name)
        return []
    modules = []
    if callable(getattr(module, "setup", None)):
        modules.append(module_name)

    package_paths = getattr(module, "__path__", None)
    if package_paths is None:
        return modules

    for module_info in pkgutil.walk_packages(package_paths, prefix=f"{module_name}."):
        try:
            submodule = importlib.import_module(module_info.name)
        except ImportError:
            logger.warning(
                "package-reference: could not import submodule %r", module_info.name
            )
            continue
        if callable(getattr(submodule, "setup", None)):
            modules.append(module_info.name)
    return modules


def summarize(text: str | None) -> str:
    """Return the first non-empty sentence-like summary from a docstring.

    Examples
    --------
    >>> summarize("One sentence.\\n    Two sentence.")
    'One sentence.'
    >>> summarize(None)
    ''
    """
    if not text:
        return ""
    stripped = inspect.cleandoc(text).strip()
    if not stripped:
        return ""
    first_line = stripped.splitlines()[0].strip()
    if first_line:
        return first_line
    return stripped


def render_value(value: object) -> str:
    """Render a compact literal representation for docs tables.

    Examples
    --------
    >>> render_value(True)
    '`True`'
    >>> render_value(["a", "b"])
    "`['a', 'b']`"
    """
    return f"`{value!r}`"


def render_types(types: object, default: object) -> str:
    """Render a readable type cell for a config-value table.

    Examples
    --------
    >>> render_types([dict], {})
    '`dict`'
    >>> render_types(None, "x")
    '`str`'
    """
    if isinstance(types, (list, tuple, set, frozenset)) and types:
        names = sorted(
            getattr(item, "__name__", str(item))
            for item in t.cast(t.Iterable[object], types)
        )
        return f"`{' | '.join(names)}`"
    if default is None:
        return "`None`"
    return f"`{type(default).__name__}`"


class RecorderApp:
    """Lightweight recorder for Sphinx setup calls.

    Examples
    --------
    >>> app = RecorderApp()
    >>> app.add_config_value("demo", 1, "env")
    >>> app.calls[0][0]
    'add_config_value'
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def __getattr__(self, name: str) -> t.Callable[..., None]:
        """Record arbitrary Sphinx app API calls used by extension setup code.

        Examples
        --------
        >>> app = RecorderApp()
        >>> app.add_role("demo", object())
        >>> app.calls[0][0]
        'add_role'
        """

        def _record(*args: object, **kwargs: object) -> None:
            self.calls.append((name, args, kwargs))

        return _record


def collect_extension_surface(module_name: str) -> SurfaceDict:
    """Collect config values, directives, roles, and lexers for an extension.

    Examples
    --------
    >>> surface = collect_extension_surface("sphinx_autodoc_pytest_fixtures")
    >>> any(item["name"] == "autofixtures" for item in surface["directives"])
    True
    """
    ensure_workspace_imports()
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        logger.warning("package-reference: could not import %r", module_name)
        return SurfaceDict(
            module=module_name,
            config_values=[],
            directives=[],
            roles=[],
            lexers=[],
            themes=[],
        )
    app = RecorderApp()
    registered_roles: list[tuple[str, object]] = []
    original_local = roles.register_local_role
    original_canonical = roles.register_canonical_role

    def _record_local(name: str, role: object) -> None:
        registered_roles.append((name, role))

    # Temporarily replace the two docutils global role-registration functions so
    # that any role registered by setup(app) is captured in registered_roles.
    # The try/finally guarantees restoration even if setup() raises.
    # Limitation: this mutates process-global state and is not safe for
    # parallel Sphinx builds (sphinx -j N); single-threaded builds only.
    try:
        roles.register_local_role = t.cast(t.Any, _record_local)
        roles.register_canonical_role = t.cast(t.Any, _record_local)
        setup = t.cast(t.Callable[[object], object], getattr(module, "setup"))
        setup(app)
    finally:
        roles.register_local_role = original_local
        roles.register_canonical_role = original_canonical

    config_values: list[dict[str, str]] = []
    directives: list[dict[str, str]] = []
    role_items: list[dict[str, str]] = []
    lexers: list[dict[str, str]] = []
    themes: list[dict[str, str]] = []

    for name, args, kwargs in app.calls:
        if name == "add_config_value":
            if len(args) < 1:
                continue
            option = str(args[0])
            default = kwargs.get("default", args[1] if len(args) > 1 else None)
            rebuild = str(kwargs.get("rebuild", args[2] if len(args) > 2 else ""))
            types = kwargs.get("types")
            config_values.append(
                {
                    "name": option,
                    "default": render_value(default),
                    "rebuild": f"`{rebuild}`" if rebuild else "",
                    "types": render_types(types, default),
                }
            )
        elif name == "add_directive":
            directive_name = str(args[0])
            directive_cls = args[1]
            directives.append(
                {
                    "name": directive_name,
                    "kind": "directive",
                    "callable": object_path(directive_cls),
                    "summary": summarize(getattr(directive_cls, "__doc__", None)),
                    "options": directive_options_markdown(directive_cls),
                }
            )
        elif name == "add_directive_to_domain":
            domain = str(args[0])
            directive_name = str(args[1])
            directive_cls = args[2]
            directives.append(
                {
                    "name": f"{domain}:{directive_name}",
                    "kind": "domain directive",
                    "callable": object_path(directive_cls),
                    "summary": summarize(getattr(directive_cls, "__doc__", None)),
                    "options": directive_options_markdown(directive_cls),
                }
            )
        elif name == "add_crossref_type":
            directive_name = str(args[0])
            role_name = str(args[1] if len(args) > 1 else args[0])
            directives.append(
                {
                    "name": f"std:{directive_name}",
                    "kind": "cross-reference directive",
                    "callable": "{py:meth}`~sphinx.application.Sphinx.add_crossref_type`",
                    "summary": "Registers a standard-domain cross-reference target.",
                    "options": "",
                }
            )
            role_items.append(
                {
                    "name": f"std:{role_name}",
                    "kind": "cross-reference role",
                    "callable": "{py:meth}`~sphinx.application.Sphinx.add_crossref_type`",
                    "summary": "Registers a standard-domain cross-reference role.",
                }
            )
        elif name == "add_role":
            role_name = str(args[0])
            role_fn = args[1]
            role_items.append(
                {
                    "name": role_name,
                    "kind": "role",
                    "callable": object_path(role_fn),
                    "summary": summarize(getattr(role_fn, "__doc__", None)),
                }
            )
        elif name == "add_role_to_domain":
            domain = str(args[0])
            role_name = str(args[1])
            role_fn = args[2]
            role_items.append(
                {
                    "name": f"{domain}:{role_name}",
                    "kind": "domain role",
                    "callable": object_path(role_fn),
                    "summary": summarize(getattr(role_fn, "__doc__", None)),
                }
            )
        elif name == "add_lexer":
            lexers.append(
                {
                    "name": str(args[0]),
                    "callable": object_path(args[1]),
                }
            )
        elif name == "add_html_theme":
            themes.append(
                {
                    "name": str(args[0]),
                    "path": f"`{args[1]}`",
                }
            )

    for role_name, role_fn in registered_roles:
        role_items.append(
            {
                "name": role_name,
                "kind": "docutils role",
                "callable": object_path(role_fn),
                "summary": summarize(getattr(role_fn, "__doc__", None)),
            }
        )

    return {
        "module": module_name,
        "config_values": unique_by_name(config_values),
        "directives": unique_by_name(directives),
        "roles": unique_by_name(role_items),
        "lexers": unique_by_name(lexers),
        "themes": unique_by_name(themes),
    }


def object_path(value: object) -> str:
    """Return a ``{py:obj}`` cross-reference for an arbitrary object.

    Uses the ``~`` prefix so Sphinx renders just the short name as link text.

    Examples
    --------
    >>> object_path(RecorderApp)
    '{py:obj}`~package_reference.RecorderApp`'
    """
    module_name = getattr(value, "__module__", type(value).__module__)
    object_name = getattr(value, "__name__", type(value).__name__)
    return f"{{py:obj}}`~{module_name}.{object_name}`"


def unique_by_name(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate rows while preserving their first-seen order.

    Examples
    --------
    >>> unique_by_name([{"name": "x"}, {"name": "x"}, {"name": "y"}])
    [{'name': 'x'}, {'name': 'y'}]
    """
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        name = item["name"]
        if name in seen:
            continue
        seen.add(name)
        result.append(item)
    return result


def directive_options_markdown(directive_cls: object) -> str:
    """Render a Markdown table of directive options, if any.

    Examples
    --------
    >>> from sphinx_argparse_neo.directive import ArgparseDirective
    >>> "module" in directive_options_markdown(ArgparseDirective)
    True
    """
    option_spec = getattr(directive_cls, "option_spec", None)
    if not isinstance(option_spec, dict) or not option_spec:
        return ""
    lines = [
        "",
        "| Option | |",
        "| --- | --- |",
    ]
    for option_name in sorted(str(key) for key in option_spec):
        lines.append(f"| `:{option_name}:` | Registered option |")
    return "\n".join(lines)


def theme_options(package_dir: pathlib.Path) -> list[str]:
    """Return theme option names declared in a package ``theme.conf`` file.

    Examples
    --------
    >>> "light_logo" in theme_options(workspace_root() / "packages" / "sphinx-gptheme")
    True
    """
    theme_conf = package_dir / "src" / "sphinx_gptheme" / "theme" / "theme.conf"
    if not theme_conf.exists():
        return []
    parser = configparser.ConfigParser()
    parser.read(theme_conf)
    if "options" not in parser:
        return []
    return sorted(parser["options"].keys())


def package_reference_markdown(package_name: str) -> str:
    """Render the generated Markdown fragment for a workspace package page.

    Returns an empty string and logs a warning when ``package_name`` is not
    found among the workspace packages.

    Examples
    --------
    >>> "Registered Surface" in package_reference_markdown("sphinx-fonts")
    True
    >>> package_reference_markdown("nonexistent-package")
    ''
    """
    package = next(
        (item for item in workspace_packages() if item["name"] == package_name),
        None,
    )
    if package is None:
        logger.warning("package-reference: unknown package %r", package_name)
        return ""
    package_dir = pathlib.Path(package["package_dir"])
    module_name = package["module_name"]
    extension_blocks = [
        collect_extension_surface(name) for name in extension_modules(module_name)
    ]

    lines = [
        "## Copyable config snippet",
        "",
        "```python",
        "extensions = [",
    ]

    if extension_blocks:
        for block in extension_blocks:
            lines.append(f'    "{block["module"]}",')
    elif package_name == "gp-sphinx":
        lines.append('    "gp_sphinx",')
    else:
        lines.append(f'    "{module_name}",')

    lines.extend(["]", "```", ""])

    if package["repository"]:
        lines.extend(
            [
                "## Package metadata",
                "",
                f"- Source on GitHub: [{package_name}]({package['repository']}/tree/main/packages/{package_name})",
                f"- Maturity: `{package['maturity']}`",
                "",
            ]
        )

    if package_name == "gp-sphinx":
        lines.extend(
            [
                "## Registered Surface",
                "",
                "This package is a coordinator rather than a Sphinx extension module.",
                "Its public runtime surface is documented in {doc}`/configuration` and {doc}`/api`.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## Registered Surface", ""])

    for block in extension_blocks:
        lines.extend([f"### {block['module']}", ""])
        config_rows = block["config_values"]
        if config_rows:
            lines.extend(
                [
                    "#### Config values",
                    "",
                    "| Name | Default | Rebuild | Types |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for row in config_rows:
                lines.append(
                    f"| `{row['name']}` | {row['default']} | {row['rebuild']} | {row['types']} |"
                )
            lines.append("")

        directive_rows = block["directives"]
        if directive_rows:
            lines.extend(
                [
                    "#### Directives",
                    "",
                    "| Name | Kind | Callable | Summary |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for row in directive_rows:
                lines.append(
                    f"| `{row['name']}` | {row['kind']} | {row['callable']} | {row['summary']} |"
                )
            lines.append("")
            for row in directive_rows:
                if row["options"]:
                    lines.extend(
                        [
                            f"##### {row['name']} options",
                            row["options"],
                            "",
                        ]
                    )

        role_rows = block["roles"]
        if role_rows:
            lines.extend(
                [
                    "#### Roles",
                    "",
                    "| Name | Kind | Callable | Summary |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for row in role_rows:
                lines.append(
                    f"| `{row['name']}` | {row['kind']} | {row['callable']} | {row['summary']} |"
                )
            lines.append("")

        lexer_rows = block["lexers"]
        if lexer_rows:
            lines.extend(
                [
                    "#### Lexers",
                    "",
                    "| Name | Callable |",
                    "| --- | --- |",
                ]
            )
            for row in lexer_rows:
                lines.append(f"| `{row['name']}` | {row['callable']} |")
            lines.append("")

        theme_rows = block["themes"]
        if theme_rows:
            lines.extend(
                [
                    "#### Theme registration",
                    "",
                    "| Theme | Path |",
                    "| --- | --- |",
                ]
            )
            for row in theme_rows:
                lines.append(f"| `{row['name']}` | {row['path']} |")
            lines.append("")

    if module_name == "sphinx_gptheme":
        options = theme_options(package_dir)
        lines.extend(
            [
                "### Theme options (theme.conf)",
                "",
                "| Option |",
                "| --- |",
            ]
        )
        for option in options:
            lines.append(f"| `{option}` |")
        lines.append("")

    return "\n".join(lines)


def maturity_badge(maturity: str) -> str:
    """Return a sphinx-design badge role matching a package maturity label.

    Examples
    --------
    >>> maturity_badge("Alpha")
    '{bdg-warning-line}`Alpha`'
    """
    if maturity == "Alpha":
        return "{bdg-warning-line}`Alpha`"
    if maturity == "Beta":
        return "{bdg-success-line}`Beta`"
    return f"{{bdg-secondary-line}}`{maturity}`"


def workspace_package_grid_markdown() -> str:
    """Render the package index grid from workspace metadata.

    Examples
    --------
    >>> "grid-item-card" in workspace_package_grid_markdown()
    True
    >>> "+++" in workspace_package_grid_markdown()
    True
    """
    lines = [
        "::::{grid} 1 1 2 2",
        ":gutter: 2 2 3 3",
        "",
    ]
    for package in workspace_packages():
        lines.extend(
            [
                f":::{{grid-item-card}} {package['name']}",
                f":link: {package['name']}",
                ":link-type: doc",
                "",
                str(package["description"]),
                "",
                "+++",
                maturity_badge(package["maturity"]),
                ":::",
                "",
            ]
        )
    lines.append("::::")
    return "\n".join(lines)


class PackageReferenceDirective(SphinxDirective):
    """Render a generated package reference block inside a page."""

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0]
        return self.parse_text_to_nodes(package_reference_markdown(package_name))


class WorkspacePackageGridDirective(SphinxDirective):
    """Render the packages index grid from workspace package metadata."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        return self.parse_text_to_nodes(workspace_package_grid_markdown())


def setup(app: t.Any) -> dict[str, object]:
    """Register the package-reference directive for documentation pages.

    Examples
    --------
    >>> fake = RecorderApp()
    >>> metadata = setup(fake)
    >>> metadata["parallel_read_safe"]
    True
    """
    ensure_workspace_imports()
    app.add_directive("package-reference", PackageReferenceDirective)
    app.add_directive("workspace-package-grid", WorkspacePackageGridDirective)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": "0.0.1",
    }
