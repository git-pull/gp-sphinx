"""Generate package reference sections from live workspace metadata.

Architecture
------------
This Sphinx extension auto-generates the "Copyable config snippet" and
"Package metadata" sections that appear on every ``docs/packages/<name>.md``
page.  Surface documentation (config values, directives, roles) is owned by
the autodoc directives in ``sphinx-autodoc-sphinx`` (``autoconfigvalues``)
and ``sphinx-autodoc-docutils`` (``autodirectives`` / ``autoroles``) —
invoke them on the page directly.

It works in three layers:

1. **Workspace discovery** (``workspace_packages()``) — walks
   ``packages/*/pyproject.toml`` to find every publishable package and reads
   its name, version, description, classifiers, and GitHub URL.

2. **Surface extraction** (``collect_extension_surface()``) — replays the
   extension's ``setup()`` against
   :func:`sphinx_autodoc_docutils.replay_setup`, the shared workspace
   recorder, and maps the captured ``app.add_*`` calls into a
   ``SurfaceDict``.  The collected surface is consumed by
   ``_register_extension_objects()`` to populate the py-domain so
   cross-references resolve.

3. **Rendering** (``package_reference_markdown()``) — emits the copyable
   conf snippet and metadata block, which the ``PackageReferenceDirective``
   injects into the page via a raw docutils node.

Adding a new package
--------------------
No code changes are required.  Once a ``packages/<name>/pyproject.toml``
exists with a ``[project]`` table the package is picked up automatically on
the next docs build.

Examples
--------
>>> package = workspace_packages()[0]
>>> package["name"] in {
...     "gp-furo-theme",
...     "sphinx-vite-builder",
...     "sphinx-gp-opengraph",
...     "sphinx-gp-sitemap",
...     "gp-sphinx",
...     "sphinx-fonts",
...     "sphinx-gp-theme",
...     "sphinx-autodoc-argparse",
...     "sphinx-autodoc-docutils",
...     "sphinx-autodoc-fastmcp",
...     "sphinx-autodoc-pytest-fixtures",
...     "sphinx-autodoc-sphinx",
... }
True

>>> surface = collect_extension_surface("sphinx_fonts")
>>> any(item["name"] == "sphinx_fonts" for item in surface["config_values"])
True
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import pathlib
import pkgutil
import sys
import typing as t
from dataclasses import dataclass, field

from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_docutils import SetupRecorder, replay_setup

if t.TYPE_CHECKING:
    from docutils import nodes

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


PackageState = t.Literal["shipped-py", "shipped-js", "emerging"]


@dataclass(frozen=True)
class DocsOpts:
    """Per-package overrides parsed from ``[tool.gp-sphinx.docs]``.

    Attributes
    ----------
    omit
        Subpages this package opts out of (e.g. tokens packages omit
        ``tutorial`` and ``examples``).
    extra
        Subpages beyond the Diátaxis defaults (e.g. ``errors``, ``cli``,
        ``tokens``).
    showcase
        Optional Sublimity subpages this package opts into (subset of
        ``signatures``, ``kitchen-sink``, ``surface-diff``, ``dependents``).
    reference_link
        When set, the Reference card on the landing redirects to this
        docname rather than rendering ``packages/<name>/reference``.

    Examples
    --------
    >>> DocsOpts().omit
    ()
    >>> DocsOpts(extra=("errors",)).extra
    ('errors',)
    """

    omit: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()
    showcase: tuple[str, ...] = ()
    reference_link: str | None = None


@dataclass(frozen=True)
class PackageDocsRecord:
    """Single source of truth for a workspace package's docs metadata.

    Populated once at workspace discovery; every directive downstream
    reads from this record rather than re-parsing manifest files.

    Attributes
    ----------
    name
        Distribution name (``"sphinx-autodoc-fastmcp"``,
        ``"@gp-sphinx/furo-tokens"``).
    state
        Manifest probe result: ``"shipped-py"`` (has ``pyproject.toml``),
        ``"shipped-js"`` (has ``package.json`` only), or ``"emerging"``
        (no manifest yet).
    cluster
        Sidebar cluster the package belongs to (e.g. ``"autodoc"``).
    package_dir
        Directory of the package under ``packages/``.
    manifest_path
        Path to the manifest file (``pyproject.toml`` or
        ``package.json``); ``None`` for emerging packages.
    src_dir
        Path to the package's ``src/`` directory; ``None`` if absent.
    module_name
        Importable Python module name (only meaningful for shipped-py).
    description
        One-line synopsis for the landing page.
    version
        Package version string from the manifest; empty for emerging.
    repository_url
        GitHub URL.
    pypi_url
        PyPI project URL; ``None`` for shipped-js and emerging.
    npm_url
        npm registry URL; ``None`` for shipped-py and emerging.
    maturity
        Short label (``"Alpha"``, ``"Beta"``, ``"Production/Stable"``,
        ``"Unknown"``).
    docs_opts
        Parsed ``[tool.gp-sphinx.docs]`` overrides (empty if section
        absent or manifest is ``package.json``).

    Examples
    --------
    >>> records = workspace_package_records()
    >>> shipped_py = [r for r in records if r.state == "shipped-py"]
    >>> "gp-sphinx" in {r.name for r in shipped_py}
    True
    """

    name: str
    state: PackageState
    cluster: str
    package_dir: pathlib.Path
    manifest_path: pathlib.Path | None
    src_dir: pathlib.Path | None
    module_name: str
    description: str
    version: str
    repository_url: str
    pypi_url: str | None
    npm_url: str | None
    maturity: str
    docs_opts: DocsOpts = field(default_factory=DocsOpts)


_CLUSTER_FOR_NAME: dict[str, str] = {
    "gp-sphinx": "theme-coordinator",
    "sphinx-gp-theme": "theme-coordinator",
    "gp-furo-theme": "theme-coordinator",
    "sphinx-serene-theme": "theme-coordinator",
    "gp-furo-tokens": "tokens",
    "gp-serene-tokens": "tokens",
    "@gp-sphinx/furo-tokens": "tokens",
    "@gp-sphinx/serene-tokens": "tokens",
    "sphinx-fonts": "tokens",
    "sphinx-ux-badges": "ux",
    "sphinx-ux-autodoc-layout": "ux",
    "sphinx-vite-builder": "build-seo",
    "sphinx-gp-opengraph": "build-seo",
    "sphinx-gp-sitemap": "build-seo",
}


def _cluster_for(name: str) -> str:
    """Return the sidebar cluster a package belongs to.

    Examples
    --------
    >>> _cluster_for("sphinx-autodoc-fastmcp")
    'autodoc'
    >>> _cluster_for("gp-sphinx")
    'theme-coordinator'
    >>> _cluster_for("sphinx-ux-badges")
    'ux'
    """
    if name in _CLUSTER_FOR_NAME:
        return _CLUSTER_FOR_NAME[name]
    if name.startswith("sphinx-autodoc-"):
        return "autodoc"
    return "unknown"


def _docs_opts_from_pyproject(table: dict[str, t.Any]) -> DocsOpts:
    """Parse ``[tool.gp-sphinx.docs]`` overrides from a pyproject TOML dict.

    Examples
    --------
    >>> _docs_opts_from_pyproject({}).extra
    ()
    >>> opts = _docs_opts_from_pyproject(
    ...     {"tool": {"gp-sphinx": {"docs": {"extra": ["errors"]}}}}
    ... )
    >>> opts.extra
    ('errors',)
    """
    section = table.get("tool", {}).get("gp-sphinx", {}).get("docs", {})
    return DocsOpts(
        omit=tuple(section.get("omit", [])),
        extra=tuple(section.get("extra", [])),
        showcase=tuple(section.get("showcase", [])),
        reference_link=section.get("reference_link"),
    )


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
    >>> workspace_root().is_dir()
    True
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
                    t.cast("list[str]", project.get("classifiers", [])),
                ),
            },
        )
    return packages


def workspace_package_records() -> list[PackageDocsRecord]:
    """Return every workspace package directory as a :class:`PackageDocsRecord`.

    Probes ``pyproject.toml`` first; falls back to ``package.json`` for
    JS-only packages; classifies as ``"emerging"`` when neither manifest
    is present. Records are returned sorted by directory name.

    Unlike :func:`workspace_packages` this includes JS-only and emerging
    packages and surfaces the parsed ``[tool.gp-sphinx.docs]`` overrides.

    Examples
    --------
    >>> records = workspace_package_records()
    >>> "gp-sphinx" in {r.name for r in records}
    True
    >>> states = {r.state for r in records}
    >>> states <= {"shipped-py", "shipped-js", "emerging"}
    True
    """
    packages_dir = workspace_root() / "packages"
    records: list[PackageDocsRecord] = []
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue
        record = _package_record_from_dir(pkg_dir)
        if record is not None:
            records.append(record)
    return records


def _package_record_from_dir(pkg_dir: pathlib.Path) -> PackageDocsRecord | None:
    """Build a :class:`PackageDocsRecord` for a single package directory.

    Returns ``None`` for directories that do not look like a workspace
    package at all (e.g. an ``__pycache__/`` slipped in).
    """
    pyproject_path = pkg_dir / "pyproject.toml"
    package_json_path = pkg_dir / "package.json"
    src_dir = pkg_dir / "src"
    src_module_dir: pathlib.Path | None = None
    if src_dir.is_dir():
        src_module_dir = next(
            (path for path in src_dir.iterdir() if path.is_dir()),
            None,
        )

    if pyproject_path.is_file():
        with pyproject_path.open("rb") as handle:
            table = tomllib.load(handle)
        project = table.get("project")
        if not isinstance(project, dict):
            return None
        if src_module_dir is None:
            return None
        name = str(project["name"])
        return PackageDocsRecord(
            name=name,
            state="shipped-py",
            cluster=_cluster_for(name),
            package_dir=pkg_dir,
            manifest_path=pyproject_path,
            src_dir=src_dir,
            module_name=src_module_dir.name,
            description=str(project.get("description", "")),
            version=str(project.get("version", "")),
            repository_url=str(project.get("urls", {}).get("Repository", "")),
            pypi_url=f"https://pypi.org/project/{name}/",
            npm_url=None,
            maturity=maturity_from_classifiers(
                t.cast("list[str]", project.get("classifiers", [])),
            ),
            docs_opts=_docs_opts_from_pyproject(table),
        )

    if package_json_path.is_file():
        manifest = json.loads(package_json_path.read_text(encoding="utf-8"))
        name = str(manifest.get("name", pkg_dir.name))
        npm_slug = name.lstrip("@").replace("/", "%2f") if name else pkg_dir.name
        return PackageDocsRecord(
            name=name,
            state="shipped-js",
            cluster=_cluster_for(name),
            package_dir=pkg_dir,
            manifest_path=package_json_path,
            src_dir=src_dir if src_dir.is_dir() else None,
            module_name="",
            description=str(manifest.get("description", "")),
            version=str(manifest.get("version", "")),
            repository_url=_repository_url_from_package_json(manifest),
            pypi_url=None,
            npm_url=f"https://www.npmjs.com/package/{npm_slug}",
            maturity="Unknown",
        )

    return PackageDocsRecord(
        name=pkg_dir.name,
        state="emerging",
        cluster=_cluster_for(pkg_dir.name),
        package_dir=pkg_dir,
        manifest_path=None,
        src_dir=src_dir if src_dir.is_dir() else None,
        module_name="",
        description="",
        version="",
        repository_url="",
        pypi_url=None,
        npm_url=None,
        maturity="Unknown",
    )


def _repository_url_from_package_json(manifest: dict[str, t.Any]) -> str:
    """Extract a GitHub URL from a ``package.json`` ``repository`` field.

    Accepts either the string form (``"github:owner/repo"``) or the
    object form (``{"type": "git", "url": "..."}``).

    Examples
    --------
    >>> _repository_url_from_package_json({})
    ''
    >>> _repository_url_from_package_json({"repository": "github:git-pull/x"})
    'https://github.com/git-pull/x'
    >>> _repository_url_from_package_json(
    ...     {"repository": {"url": "git+https://github.com/git-pull/x.git"}}
    ... )
    'https://github.com/git-pull/x'
    """
    repo = manifest.get("repository")
    if isinstance(repo, str):
        if repo.startswith("github:"):
            return f"https://github.com/{repo[len('github:') :]}"
        return repo
    if isinstance(repo, dict):
        url = str(repo.get("url", ""))
        if url.startswith("git+"):
            url = url[len("git+") :]
        if url.endswith(".git"):
            url = url[: -len(".git")]
        return url
    return ""


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
    >>> "sphinx_autodoc_argparse" in extension_modules("sphinx_autodoc_argparse")
    True
    >>> "sphinx_autodoc_argparse.exemplar" in extension_modules("sphinx_autodoc_argparse")
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
                "package-reference: could not import submodule %r",
                module_info.name,
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
            for item in t.cast("t.Iterable[object]", types)
        )
        return f"`{' | '.join(names)}`"
    if default is None:
        return "`None`"
    return f"`{type(default).__name__}`"


# Re-export the shared recorder so existing references and doctests in this
# module still work; new code should import SetupRecorder from
# sphinx_autodoc_docutils directly.
RecorderApp = SetupRecorder


def _extract_arg(
    index: int,
    key: str,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> object | None:
    """Pick a Sphinx app-method argument from positional or keyword form.

    Sphinx APIs accept both forms — e.g. ``app.add_directive("foo", Foo)``
    AND ``app.add_directive(name="foo", cls=Foo)`` — so a recorder consumer
    that only indexes ``args[N]`` raises ``IndexError`` (or silently misses
    the registration) on the keyword form. Mirror's the helper used in
    ``sphinx_autodoc_docutils._directives``.

    Examples
    --------
    >>> _extract_arg(0, "name", ("foo",), {})
    'foo'
    >>> _extract_arg(0, "name", (), {"name": "foo"})
    'foo'
    >>> _extract_arg(1, "cls", (), {}) is None
    True
    """
    if len(args) > index:
        return args[index]
    return kwargs.get(key)


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
        importlib.import_module(module_name)
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
    app = replay_setup(module_name)
    if app is None:
        return SurfaceDict(
            module=module_name,
            config_values=[],
            directives=[],
            roles=[],
            lexers=[],
            themes=[],
        )

    config_values: list[dict[str, str]] = []
    directives: list[dict[str, str]] = []
    role_items: list[dict[str, str]] = []
    lexers: list[dict[str, str]] = []
    themes: list[dict[str, str]] = []

    for name, args, kwargs in app.calls:
        if name == "add_config_value":
            option = _extract_arg(0, "name", args, kwargs)
            if option is None:
                continue
            default = _extract_arg(1, "default", args, kwargs)
            rebuild = _extract_arg(2, "rebuild", args, kwargs) or ""
            types = _extract_arg(3, "types", args, kwargs)
            config_values.append(
                {
                    "name": str(option),
                    "default": render_value(default),
                    "rebuild": f"`{rebuild}`" if rebuild else "",
                    "types": render_types(types, default),
                },
            )
        elif name == "add_directive":
            directive_name = _extract_arg(0, "name", args, kwargs)
            directive_cls = _extract_arg(1, "cls", args, kwargs)
            if directive_name is None or directive_cls is None:
                continue
            directives.append(
                {
                    "name": str(directive_name),
                    "kind": "directive",
                    "callable": object_path(directive_cls),
                    "summary": summarize(getattr(directive_cls, "__doc__", None)),
                    "options": directive_options_markdown(directive_cls),
                },
            )
        elif name == "add_directive_to_domain":
            domain = _extract_arg(0, "domain", args, kwargs)
            directive_name = _extract_arg(1, "name", args, kwargs)
            directive_cls = _extract_arg(2, "cls", args, kwargs)
            if domain is None or directive_name is None or directive_cls is None:
                continue
            directives.append(
                {
                    "name": f"{domain}:{directive_name}",
                    "kind": "domain directive",
                    "callable": object_path(directive_cls),
                    "summary": summarize(getattr(directive_cls, "__doc__", None)),
                    "options": directive_options_markdown(directive_cls),
                },
            )
        elif name == "add_crossref_type":
            directive_name = _extract_arg(0, "directivename", args, kwargs)
            if directive_name is None:
                continue
            role_name = _extract_arg(1, "rolename", args, kwargs) or directive_name
            directives.append(
                {
                    "name": f"std:{directive_name}",
                    "kind": "cross-reference directive",
                    "callable": "{py:meth}`~sphinx.application.Sphinx.add_crossref_type`",
                    "summary": "Registers a standard-domain cross-reference target.",
                    "options": "",
                },
            )
            role_items.append(
                {
                    "name": f"std:{role_name}",
                    "kind": "cross-reference role",
                    "callable": "{py:meth}`~sphinx.application.Sphinx.add_crossref_type`",
                    "summary": "Registers a standard-domain cross-reference role.",
                },
            )
        elif name == "add_role":
            role_name = _extract_arg(0, "name", args, kwargs)
            role_fn = _extract_arg(1, "role", args, kwargs)
            if role_name is None or role_fn is None:
                continue
            role_items.append(
                {
                    "name": str(role_name),
                    "kind": "role",
                    "callable": object_path(role_fn),
                    "summary": summarize(getattr(role_fn, "__doc__", None)),
                },
            )
        elif name == "add_role_to_domain":
            domain = _extract_arg(0, "domain", args, kwargs)
            role_name = _extract_arg(1, "name", args, kwargs)
            role_fn = _extract_arg(2, "role", args, kwargs)
            if domain is None or role_name is None or role_fn is None:
                continue
            role_items.append(
                {
                    "name": f"{domain}:{role_name}",
                    "kind": "domain role",
                    "callable": object_path(role_fn),
                    "summary": summarize(getattr(role_fn, "__doc__", None)),
                },
            )
        elif name == "add_lexer":
            alias = _extract_arg(0, "alias", args, kwargs)
            lexer = _extract_arg(1, "lexer", args, kwargs)
            if alias is None or lexer is None:
                continue
            lexers.append(
                {
                    "name": str(alias),
                    "callable": object_path(lexer),
                },
            )
        elif name == "add_html_theme":
            theme_name = _extract_arg(0, "name", args, kwargs)
            theme_path = _extract_arg(1, "theme_path", args, kwargs)
            if theme_name is None or theme_path is None:
                continue
            themes.append(
                {
                    "name": str(theme_name),
                    "path": f"`{theme_path}`",
                },
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
    >>> object_path(SurfaceDict)
    '{py:obj}`~package_reference.SurfaceDict`'
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
    >>> from sphinx_autodoc_argparse.directive import ArgparseDirective
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


def package_reference_markdown(package_name: str) -> str:
    """Render the copyable conf snippet and metadata block for a package page.

    Surface documentation (config values, directives, roles, lexers, themes)
    is owned by the autodoc directives in ``sphinx-autodoc-sphinx`` and
    ``sphinx-autodoc-docutils`` — invoke them directly on the page.

    Returns an empty string and logs a warning when ``package_name`` is not
    found among the workspace packages.

    Examples
    --------
    >>> "Copyable config snippet" in package_reference_markdown("sphinx-fonts")
    True
    >>> "## Package metadata" in package_reference_markdown("sphinx-fonts")
    False
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

    # NOTE: The "Package metadata" section (GitHub + PyPI + Maturity)
    # was dropped here in commit C2 of the per-package docs restructure.
    # The same surface is conveyed once per page by the
    # gp-sphinx-package-meta directive (docs/_ext/sab_meta.py); rendering
    # it again as a paragraph below the conf snippet was duplication.
    # The badge row remains the only metadata surface on the landing.

    if package_name == "gp-sphinx":
        lines.extend(
            [
                "## Public surface",
                "",
                "This package is a coordinator rather than a Sphinx extension module.",
                "Its public runtime surface is documented in {doc}`/configuration` and {doc}`/api`.",
                "",
            ],
        )

    return "\n".join(lines)


def maturity_badge(maturity: str) -> str:
    """Return a sphinx-design badge role for use in grid markdown output.

    Used only in :func:`workspace_package_grid_markdown` which produces raw
    MyST markdown strings.  Per-page package headers use the ``gp-sphinx-package-meta``
    directive (see ``docs/_ext/sab_meta.py``) which emits SAB-native badges.

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


_CLUSTER_HEADINGS: tuple[tuple[str, str, str], ...] = (
    (
        "theme-coordinator",
        "Theme & coordinator",
        "Shared Sphinx configuration and presentation surface.",
    ),
    (
        "tokens",
        "Tokens",
        "Design tokens, fonts, and shared CSS custom properties.",
    ),
    (
        "autodoc",
        "Autodoc extensions",
        "Domain-specific autodoc extensions: each adds directives that "
        "generate documentation from a particular source-construct family.",
    ),
    (
        "ux",
        "UX components",
        "Badge primitives, layout presenters, and other shared "
        "rendering helpers consumed by the autodoc family.",
    ),
    (
        "build-seo",
        "Build & SEO",
        "PEP 517 backends, build orchestration, and crawl-indexing "
        "extensions auto-loaded by gp-sphinx when ``docs_url`` is set.",
    ),
)


def _grid_card_lines_for_record(record: PackageDocsRecord) -> list[str]:
    """Render one ``{grid-item-card}`` block for a workspace record."""
    if record.state == "emerging":
        # Emerging packages have no per-package landing yet — link to
        # the GitHub directory (or repo root) rather than a 404.
        link = record.repository_url or "https://github.com/git-pull/gp-sphinx"
        return [
            f":::{{grid-item-card}} {record.name}",
            f":link: {link}",
            "",
            "Coming soon — see GitHub for status.",
            "",
            ":::",
            "",
        ]

    return [
        f":::{{grid-item-card}} {record.name}",
        f":link: {_grid_link_for_legacy_record(record.name)}",
        ":link-type: doc",
        "",
        record.description,
        "",
        "+++",
        maturity_badge(record.maturity),
        ":::",
        "",
    ]


def _grid_link_for_legacy_record(name: str) -> str:
    """Return the docname a legacy ``:link:`` entry should target.

    Picks ``<name>/index`` when a per-package directory has migrated
    (``docs/packages/<name>/index.md`` exists); falls back to the
    flat ``<name>`` docname otherwise. Lets the workspace grid keep
    rendering during the per-package migration window without
    emitting unknown-document warnings.
    """
    docs_root = workspace_root() / "docs" / "packages"
    if (docs_root / name / "index.md").is_file():
        return f"{name}/index"
    return name


def _flat_workspace_grid_markdown() -> str:
    """Render the legacy single-grid layout (no per-cluster headings)."""
    lines = [
        "::::{grid} 1 1 2 2",
        ":gutter: 2 2 3 3",
        "",
    ]
    for package in workspace_packages():
        lines.extend(
            [
                f":::{{grid-item-card}} {package['name']}",
                f":link: {_grid_link_for_legacy_record(package['name'])}",
                ":link-type: doc",
                "",
                str(package["description"]),
                "",
                "+++",
                maturity_badge(package["maturity"]),
                ":::",
                "",
            ],
        )
    lines.append("::::")
    return "\n".join(lines)


def _grouped_workspace_grid_markdown() -> str:
    """Render the workspace inventory as one ``{grid}`` block per cluster.

    Each cluster gets a heading + framing prose + a grid containing
    only the records assigned to that cluster (Shipped + Emerging).
    Emerging cards link to the GitHub directory rather than a
    landing docname so the build does not 404.
    """
    records = workspace_package_records()
    by_cluster: dict[str, list[PackageDocsRecord]] = {}
    for record in records:
        by_cluster.setdefault(record.cluster, []).append(record)

    lines: list[str] = []
    for cluster_id, heading, prose in _CLUSTER_HEADINGS:
        members = sorted(
            by_cluster.get(cluster_id, []),
            key=lambda r: r.name,
        )
        if not members:
            continue
        lines.extend(
            [
                f"## {heading}",
                "",
                prose,
                "",
                "::::{grid} 1 1 2 2",
                ":gutter: 2 2 3 3",
                "",
            ],
        )
        for member in members:
            lines.extend(_grid_card_lines_for_record(member))
        lines.append("::::")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def workspace_package_grid_markdown(*, groups: str | None = None) -> str:
    """Render the workspace package index grid.

    Parameters
    ----------
    groups
        ``None`` (default) renders the legacy single grid of every
        Python-shipped package — backward compatible with existing
        ``{workspace-package-grid}`` invocations. ``"by-cluster"``
        emits one grid per sidebar cluster, with cluster headings,
        framing prose, and Emerging packages rendered as
        GitHub-linked cards.

    Examples
    --------
    >>> "grid-item-card" in workspace_package_grid_markdown()
    True
    >>> "+++" in workspace_package_grid_markdown()
    True
    >>> "## Autodoc extensions" in workspace_package_grid_markdown(
    ...     groups="by-cluster"
    ... )
    True
    """
    if groups is None:
        return _flat_workspace_grid_markdown()
    if groups == "by-cluster":
        return _grouped_workspace_grid_markdown()
    msg = f"unsupported groups argument: {groups!r}"
    raise ValueError(msg)


def _register_extension_objects(
    app: t.Any,
    env: t.Any,
) -> None:
    """Populate the Sphinx py domain so {py:obj} callables resolve as links.

    Runs on ``env-check-consistency`` — after all source files are read and
    ``clear_doc()`` calls are complete, but before the write phase resolves
    cross-references.  Registering earlier (e.g. ``env-before-read-docs``)
    fails because ``clear_doc()`` wipes domain entries whose docname matches
    the page being re-read.

    Examples
    --------
    >>> class _MockPyDomain:
    ...     objects: dict[str, object] = {}
    >>> class _MockEnv:
    ...     domains: dict[str, object] = {"py": _MockPyDomain()}
    >>> _register_extension_objects(None, _MockEnv())
    >>> "sphinx_autodoc_docutils._directives.AutoDirective" in _MockPyDomain.objects
    True
    """
    try:
        from sphinx.domains.python import ObjectEntry

        py_domain = env.domains["py"]
    except (KeyError, AttributeError, ImportError):
        return

    found_docs: set[str] = getattr(env, "found_docs", set())

    for record in workspace_package_records():
        if record.state != "shipped-py":
            # Emerging records have no source; shipped-js has no Python
            # module to introspect. Either way, nothing to register.
            continue

        # Prefer the per-package reference subpage when the package has
        # migrated (its docname is in env.found_docs); fall back to the
        # legacy flat page during the migration window so xrefs keep
        # resolving for un-migrated packages.
        reference_docname = f"packages/{record.name}/reference"
        flat_docname = f"packages/{record.name}"
        pkg_docname = (
            reference_docname if reference_docname in found_docs else flat_docname
        )

        for ext_module_name in extension_modules(record.module_name):
            recorder = replay_setup(ext_module_name)
            if recorder is None:
                continue

            raw_objs: list[tuple[object, str]] = []  # (obj, objtype)
            for call_name, args, _kwargs in recorder.calls:
                if call_name == "add_directive" and len(args) >= 2:
                    raw_objs.append((args[1], "class"))
                elif call_name == "add_directive_to_domain" and len(args) >= 3:
                    raw_objs.append((args[2], "class"))
                elif call_name == "add_role" and len(args) >= 2:
                    obj = args[1]
                    raw_objs.append(
                        (obj, "function" if not inspect.isclass(obj) else "class"),
                    )
                elif call_name == "add_role_to_domain" and len(args) >= 3:
                    obj = args[2]
                    raw_objs.append(
                        (obj, "function" if not inspect.isclass(obj) else "class"),
                    )
                elif call_name == "add_lexer" and len(args) >= 2:
                    raw_objs.append((args[1], "class"))

            for obj, objtype in raw_objs:
                mod = getattr(obj, "__module__", None) or type(obj).__module__
                name = getattr(obj, "__name__", None) or type(obj).__name__
                full_name = f"{mod}.{name}"
                if full_name in py_domain.objects:
                    continue
                node_id = full_name.replace(".", "-")
                py_domain.objects[full_name] = ObjectEntry(
                    docname=pkg_docname,
                    node_id=node_id,
                    objtype=objtype,
                    aliased=False,
                )


def _subpage_target_exists(env: t.Any, target: str) -> bool:
    """Return ``True`` if ``target`` resolves to an existing docname.

    Accepts a same-directory subpage name (``"how-to"``) — resolved
    relative to the current document — or an absolute docname
    (``"packages/sphinx-fonts/index"``).

    Examples
    --------
    >>> class _E:
    ...     found_docs = {"packages/foo/index", "packages/foo/how-to"}
    ...     docname = "packages/foo/tutorial"
    >>> _subpage_target_exists(_E(), "how-to")
    True
    >>> _subpage_target_exists(_E(), "errors")
    False
    >>> _subpage_target_exists(_E(), "packages/foo/index")
    True
    """
    found: set[str] = getattr(env, "found_docs", set())
    if target in found:
        return True
    current = getattr(env, "docname", "")
    if "/" in current:
        prefix = current.rsplit("/", 1)[0] + "/"
        if (prefix + target) in found:
            return True
    return False


def subpage_exists_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: t.Any,
    options: dict[str, t.Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[t.Any], list[t.Any]]:
    """Implement the ``{subpage-exists}`<target>`` MyST role.

    Renders a Sphinx ``:doc:`` cross-reference when ``<target>`` resolves
    to an existing docname (sibling-relative or absolute); otherwise
    emits plain text so the build does not fail. Used in tutorial /
    how-to "Where to next" sections so prose never refers to absent
    subpages.
    """
    from docutils import nodes as docutils_nodes
    from sphinx import addnodes

    text_clean = text.strip()
    env = inliner.document.settings.env

    if _subpage_target_exists(env, text_clean):
        ref = addnodes.pending_xref(
            rawtext,
            refdomain="std",
            reftype="doc",
            reftarget=text_clean,
            refexplicit=False,
            refwarn=True,
        )
        ref += docutils_nodes.inline(rawtext, text_clean, classes=["xref", "doc"])
        return [ref], []

    return [docutils_nodes.inline(rawtext, text_clean)], []


_DEFAULT_LANDING_SUBPAGES: tuple[str, ...] = (
    "tutorial",
    "how-to",
    "reference",
    "explanation",
    "examples",
)

_OCTICONS: dict[str, str] = {
    "tutorial": "rocket",
    "how-to": "tools",
    "reference": "book",
    "explanation": "light-bulb",
    "examples": "star",
    "errors": "alert",
    "cli": "terminal",
    "tokens": "paintbrush",
    "signatures": "code",
    "kitchen-sink": "device-camera",
    "surface-diff": "diff",
    "dependents": "link",
}

_TITLES: dict[str, str] = {
    "tutorial": "Tutorial",
    "how-to": "How to",
    "reference": "API Reference",
    "explanation": "Explanation",
    "examples": "Examples",
    "errors": "Errors",
    "cli": "CLI",
    "tokens": "Tokens",
    "signatures": "Signatures",
    "kitchen-sink": "Kitchen sink",
    "surface-diff": "Surface diff",
    "dependents": "Dependents",
}

_DEFAULT_SUMMARIES: dict[str, str] = {
    "tutorial": "Get started in ten minutes.",
    "how-to": "Task recipes for common workflows.",
    "reference": "Every directive, role, and config value.",
    "explanation": "Why the package is shaped this way.",
    "examples": "Live demos rendered from real code.",
    "errors": "Named failure modes and what to do about them.",
    "cli": "Command-line surface and modes.",
    "tokens": "Design-token tables and CSS custom properties.",
    "signatures": "Runtime-rendered signatures and drift alerts.",
    "kitchen-sink": "Every directive exercised on one page.",
    "surface-diff": "What changed since the last release.",
    "dependents": "Workspace packages that import this one.",
}


def _candidate_subpage_paths(record: PackageDocsRecord) -> dict[str, pathlib.Path]:
    """Return the on-disk paths the landing checks for each candidate subpage.

    Combines:

    * the Diátaxis defaults (tutorial / how-to / reference / explanation /
      examples)
    * ``[tool.gp-sphinx.docs].extra`` entries (errors / cli / tokens / …)
    * ``[tool.gp-sphinx.docs].showcase`` entries (signatures /
      kitchen-sink / surface-diff / dependents)

    The landing renders only those subpage cards whose target file
    exists. Currently looks in ``docs/packages/<name>/<subpage>.md``;
    a future commit will also probe the co-located
    ``packages/<name>/docs/`` tree.
    """
    docs_root = workspace_root() / "docs" / "packages" / record.name
    subpages = (
        list(_DEFAULT_LANDING_SUBPAGES)
        + list(record.docs_opts.extra)
        + list(record.docs_opts.showcase)
    )
    return {sub: docs_root / f"{sub}.md" for sub in subpages}


def _package_landing_markdown(
    record: PackageDocsRecord,
    present_subpages: list[str],
) -> str:
    """Render the per-package landing markdown for ``record``.

    The caller is responsible for env.note_dependency() on the candidate
    paths; this helper is pure (string in -> string out).
    """
    # The stub at docs/packages/<name>/index.md carries the anchor + H1
    # so Sphinx determines the page title at parse time (without it the
    # parent toctree promotes the page's children to its own level).
    # The directive emits everything else: meta badges, synopsis, grid,
    # hidden toctree.
    meta = f"```{{gp-sphinx-package-meta}} {record.name}\n```"
    synopsis = (
        f"> {record.description}"
        if record.description
        else "> No description provided."
    )

    lines: list[str] = [
        meta,
        "",
        synopsis,
        "",
    ]

    if present_subpages:
        # Sphinx-design's {grid} directive requires at least one
        # {grid-item-card} child — emit the grid only when we have
        # subpages to show. Packages with no subpages yet (newly
        # added, JS-only awaiting authoring) render meta + synopsis
        # without the grid.
        lines.extend(
            [
                "::::{grid} 1 2 2 3",
                ":gutter: 2 2 3 3",
                ":class-container: gp-sphinx-package__landing-grid",
                "",
            ],
        )
        for subpage in present_subpages:
            icon = _OCTICONS.get(subpage, "link")
            title_text = _TITLES.get(subpage, subpage.replace("-", " ").title())
            summary = _DEFAULT_SUMMARIES.get(subpage, "")
            lines.extend(
                [
                    f":::{{grid-item-card}} {{octicon}}`{icon}` {title_text}",
                    f":link: {subpage}",
                    ":link-type: doc",
                    summary,
                    ":::",
                    "",
                ],
            )
        lines.append("::::")
        lines.append("")
        lines.append("```{toctree}")
        lines.append(":hidden:")
        lines.append("")
        lines.extend(present_subpages)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


class PackageLandingDirective(SphinxDirective):
    """Render a synthesized landing page for a workspace package.

    Emits ``gp-sphinx-package-meta`` + synopsis + a conditional grid of
    cards over only those Diátaxis subpages whose target markdown
    exists on disk + a hidden toctree.

    Calls ``env.note_dependency()`` on every candidate subpage path so
    incremental builds rebuild the landing when an author drops a new
    ``tutorial.md`` (or removes one) without a clean rebuild.

    Usage in ``docs/packages/<name>/index.md``::

        ```{package-landing} sphinx-autodoc-fastmcp
        ```
    """

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0].strip()
        record = next(
            (r for r in workspace_package_records() if r.name == package_name),
            None,
        )
        if record is None:
            logger.warning("package-landing: unknown package %r", package_name)
            return []

        candidates = _candidate_subpage_paths(record)
        present: list[str] = []
        for subpage, path in candidates.items():
            self.env.note_dependency(str(path))
            if path.is_file():
                present.append(subpage)

        markdown = _package_landing_markdown(record, present)
        return self.parse_text_to_nodes(markdown)


def _cluster_toctree_markdown(
    cluster: str,
    *,
    caption: str | None,
    titlesonly: bool,
) -> str:
    """Render a hidden toctree of every Shipped package in ``cluster``.

    Emerging packages are silently skipped at emit time so the
    toctree never references a docname Sphinx has not discovered —
    this prevents cluster-toctree-on-Emerging crashes (Risk: see
    Group B2 commit message).

    Each entry points at ``packages/<name>/index`` (the per-package
    landing stub). Entries are sorted alphabetically within the
    cluster so the sidebar reads predictably.
    """
    members = sorted(
        record.name
        for record in workspace_package_records()
        if record.cluster == cluster and record.state in {"shipped-py", "shipped-js"}
    )
    if not members:
        return ""

    lines: list[str] = ["```{toctree}"]
    if caption is not None:
        lines.append(f":caption: {caption}")
    lines.append(":hidden:")
    if titlesonly:
        lines.append(":titlesonly:")
    lines.append("")
    lines.extend(f"packages/{name}/index" for name in members)
    lines.append("```")
    return "\n".join(lines)


class ClusterToctreeDirective(SphinxDirective):
    """Render a hidden toctree of every Shipped package in a sidebar cluster.

    Replaces the seven hand-edited toctree blocks in ``docs/index.md``
    with a single source of truth: package classifier plus
    ``[tool.gp-sphinx.docs]`` overrides drive both the workspace grid
    and the sidebar.

    Usage in ``docs/index.md``::

        ```{cluster-toctree} autodoc
        :caption: Autodoc
        :titlesonly:
        ```

    Skips Emerging packages so the build does not reference a missing
    docname.
    """

    required_arguments = 1
    has_content = False
    option_spec = {  # noqa: RUF012
        "caption": lambda v: str(v).strip(),
        "titlesonly": lambda v: True if v is None else bool(v),
    }

    def run(self) -> list[nodes.Node]:
        cluster = self.arguments[0].strip()
        caption = self.options.get("caption")
        titlesonly = "titlesonly" in self.options
        markdown = _cluster_toctree_markdown(
            cluster,
            caption=caption,
            titlesonly=titlesonly,
        )
        if not markdown:
            logger.warning(
                "cluster-toctree: no Shipped packages found in cluster %r",
                cluster,
            )
            return []
        return self.parse_text_to_nodes(markdown)


class PackageReferenceDirective(SphinxDirective):
    """Render a generated package reference block inside a page."""

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0]
        return self.parse_text_to_nodes(package_reference_markdown(package_name))


def _public_callables(module_name: str) -> list[tuple[str, str]]:
    """Return ``(qualname, signature)`` pairs for the module's public callables.

    Imports ``module_name`` once, walks ``dir(module)`` for callables
    not starting with ``_``, and renders each via :func:`inspect.signature`.
    Errors during inspection are logged and skipped so a single drift
    doesn't break the build.
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        logger.warning("live-signature: could not import %r", module_name)
        return []

    pairs: list[tuple[str, str]] = []
    for name in sorted(dir(module)):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if not callable(obj):
            continue
        if getattr(obj, "__module__", None) != module_name:
            continue  # re-exports are documented in their owning module
        try:
            sig = str(inspect.signature(obj))
        except (TypeError, ValueError):
            continue
        pairs.append((name, sig))
    return pairs


def _live_signature_markdown(package_name: str) -> str:
    """Render the live-signature subpage content for a workspace package."""
    record = next(
        (r for r in workspace_package_records() if r.name == package_name),
        None,
    )
    if record is None or record.state != "shipped-py":
        return ""

    pairs = _public_callables(record.module_name)
    if not pairs:
        return ""

    # Body-only: the surrounding stub at packages/<name>/<showcase>.md
    # provides the page anchor and H1 so Sphinx finds a page title at
    # parse time (same constraint the package-landing directive learned
    # in E2). Directives that emit H1 via parse_text_to_nodes do NOT
    # set the page title — Sphinx's title extraction has already run.
    lines = [
        f"Public callables in `{record.module_name}` rendered from the "
        "running interpreter at docs-build time. Drift between this "
        "block and the prose elsewhere on the page indicates a stale "
        "docstring or signature comment.",
        "",
    ]
    for name, sig in pairs:
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append("```python")
        lines.append(f"def {name}{sig}:")
        lines.append("    ...")
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


class LiveSignatureDirective(SphinxDirective):
    """Render runtime-introspected signatures for a workspace package's module.

    Imports the package's module and emits a ``### <name>`` section per
    public callable showing its live signature. Use on a package's
    ``signatures.md`` subpage when the author has opted in via
    ``[tool.gp-sphinx.docs].showcase = ["signatures"]``.

    No inline JavaScript is emitted by this directive; the signatures
    are rendered server-side at build time. (Risk 7 in the woven
    plan — Cloudflare Rocket Loader interaction — does not apply.)

    Usage in ``packages/<name>/docs/signatures.md``::

        ```{live-signature} sphinx-fonts
        ```
    """

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0].strip()
        markdown = _live_signature_markdown(package_name)
        if not markdown:
            logger.warning(
                "live-signature: no public callables for %r",
                package_name,
            )
            return []
        return self.parse_text_to_nodes(markdown)


def _kitchen_sink_markdown(package_name: str) -> str:
    """Render a kitchen-sink subpage exercising every directive a package registers.

    Reads the package's collected surface (via collect_extension_surface)
    and emits one example invocation per directive. Roles get an inline
    cross-reference example. The page is a single discoverable place
    where every directive and role is exercised, useful for quick
    visual regressions and as a reference card for downstream authors.
    """
    record = next(
        (r for r in workspace_package_records() if r.name == package_name),
        None,
    )
    if record is None or record.state != "shipped-py":
        return ""

    blocks = [
        collect_extension_surface(module)
        for module in extension_modules(record.module_name)
    ]
    directives_seen: list[str] = []
    roles_seen: list[str] = []
    for block in blocks:
        directives_seen.extend(item["name"] for item in block["directives"])
        roles_seen.extend(item["name"] for item in block["roles"])

    if not directives_seen and not roles_seen:
        return ""

    # Body-only: stub supplies anchor + H1 so Sphinx finds a page title.
    lines = [
        "Every directive and role this package registers, exercised once "
        "on the same page — useful as a reference card for downstream "
        "authors and as a visual-regression target.",
        "",
    ]
    if directives_seen:
        lines.append("## Directives")
        lines.append("")
        for name in sorted(set(directives_seen)):
            lines.append(f"### `{name}`")
            lines.append("")
            lines.append("```text")
            lines.append(f".. {name}::")
            lines.append("```")
            lines.append("")
    if roles_seen:
        lines.append("## Roles")
        lines.append("")
        for name in sorted(set(roles_seen)):
            lines.append(f"- `:{name}:` cross-reference")
        lines.append("")
    return "\n".join(lines)


class PackageKitchenSinkDirective(SphinxDirective):
    """Render a kitchen-sink page exercising every directive a package registers.

    Renders one example block per directive plus a list of registered
    roles. Used in the package's optional ``kitchen-sink.md`` showcase
    subpage when the author has opted in via
    ``[tool.gp-sphinx.docs].showcase = ["kitchen-sink"]``.

    Pairs with an out-of-band ``tox -e docs-screenshot`` Playwright
    job that captures the rendered HTML as a PNG for
    ``sphinx-gp-opengraph`` to use as the per-package OG image.
    The screenshot step is **not** part of the docs build, so the
    "pure function of disk state" CI gate (Risk 3) is not affected.

    Usage in ``packages/<name>/docs/kitchen-sink.md``::

        ```{package-kitchen-sink} sphinx-autodoc-fastmcp
        ```
    """

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0].strip()
        markdown = _kitchen_sink_markdown(package_name)
        if not markdown:
            logger.warning(
                "package-kitchen-sink: no surface for %r",
                package_name,
            )
            return []
        return self.parse_text_to_nodes(markdown)


def _surface_snapshot_path(package_name: str) -> pathlib.Path:
    """Return the path to a package's stored surface snapshot."""
    return (
        workspace_root()
        / "docs"
        / "_static"
        / "surface-snapshots"
        / f"{package_name}.json"
    )


def _current_surface_keys(record: PackageDocsRecord) -> set[str]:
    """Return the union of registered directives + roles + config-values names.

    A flat ``set[str]`` of ``"<kind>:<name>"`` keys per registered
    surface item is enough to detect adds / removes between releases.
    """
    blocks = [
        collect_extension_surface(module)
        for module in extension_modules(record.module_name)
    ]
    keys: set[str] = set()
    for block in blocks:
        keys.update(f"directive:{item['name']}" for item in block["directives"])
        keys.update(f"role:{item['name']}" for item in block["roles"])
        keys.update(f"config:{item['name']}" for item in block["config_values"])
    return keys


def _surface_changelog_markdown(package_name: str) -> str:
    """Render the surface-diff subpage comparing live surface vs snapshot.

    Reads ``docs/_static/surface-snapshots/<package>.json`` (a JSON
    array of surface keys captured at the previous release tag).
    Renders Added / Removed / Unchanged sections.
    """
    record = next(
        (r for r in workspace_package_records() if r.name == package_name),
        None,
    )
    if record is None or record.state != "shipped-py":
        return ""

    current = _current_surface_keys(record)
    snapshot_path = _surface_snapshot_path(package_name)
    if snapshot_path.is_file():
        snapshot_keys = set(json.loads(snapshot_path.read_text(encoding="utf-8")))
    else:
        snapshot_keys = set()

    added = sorted(current - snapshot_keys)
    removed = sorted(snapshot_keys - current)
    unchanged = sorted(current & snapshot_keys)

    # Body-only: stub supplies anchor + H1 so Sphinx finds a page title.
    lines = [
        "Comparison of the package's currently-registered directives, "
        "roles, and config values against the snapshot stored at "
        f"`docs/_static/surface-snapshots/{package_name}.json`.",
        "",
    ]
    if not snapshot_path.is_file():
        lines.append(
            "**No prior snapshot recorded.** Capture the current surface "
            f"by writing it to `docs/_static/surface-snapshots/{package_name}.json` "
            "before the next release.",
        )
        lines.append("")
    if added:
        lines.append("## Added")
        lines.append("")
        lines.extend(f"- `{key}`" for key in added)
        lines.append("")
    if removed:
        lines.append("## Removed")
        lines.append("")
        lines.extend(f"- `{key}`" for key in removed)
        lines.append("")
    if unchanged:
        lines.append(f"## Unchanged ({len(unchanged)})")
        lines.append("")
        lines.append("Stable across this release window.")
        lines.append("")
    return "\n".join(lines)


class SurfaceChangelogDirective(SphinxDirective):
    """Diff a package's current surface against a snapshotted previous version.

    Reads the JSON snapshot at
    ``docs/_static/surface-snapshots/<package>.json`` (typically
    captured at the previous release tag) and reports Added /
    Removed / Unchanged surface keys. Use on the package's optional
    ``surface-diff.md`` showcase subpage.

    Usage in ``packages/<name>/docs/surface-diff.md``::

        ```{surface-changelog} sphinx-autodoc-fastmcp
        ```
    """

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0].strip()
        markdown = _surface_changelog_markdown(package_name)
        if not markdown:
            logger.warning(
                "surface-changelog: nothing to diff for %r",
                package_name,
            )
            return []
        return self.parse_text_to_nodes(markdown)


def _package_dependents(target: str) -> list[str]:
    """Return workspace packages that depend on ``target`` per pyproject.toml.

    Walks every shipped-py record and reads the ``[project].dependencies``
    array from its manifest, plus ``[tool.uv.sources]`` for workspace
    pin entries. Returns the set of dependents sorted alphabetically.
    """
    dependents: set[str] = set()
    for record in workspace_package_records():
        if record.state != "shipped-py" or record.manifest_path is None:
            continue
        if record.name == target:
            continue
        with record.manifest_path.open("rb") as handle:
            manifest = tomllib.load(handle)
        deps = manifest.get("project", {}).get("dependencies", [])
        for dep_spec in deps:
            # dep_spec is e.g. "sphinx-ux-badges>=0.0.1" or just "sphinx-ux-badges"
            dep_name = (
                str(dep_spec)
                .split(">")[0]
                .split("=")[0]
                .split("<")[0]
                .split("!")[0]
                .split("~")[0]
                .split(";")[0]
                .strip()
                # PEP 508: extras may appear in []; strip them
                .split("[")[0]
                .strip()
            )
            if dep_name == target:
                dependents.add(record.name)
    return sorted(dependents)


def _package_dependents_markdown(package_name: str) -> str:
    """Render the dependents subpage for a package.

    Reverse-intersphinx: which workspace packages import or extend
    ``package_name``? Each becomes a Sphinx ``:doc:`` cross-reference
    so navigation lands on the dependent's per-package landing.
    """
    record = next(
        (r for r in workspace_package_records() if r.name == package_name),
        None,
    )
    if record is None:
        return ""

    dependents = _package_dependents(package_name)
    # Body-only: stub supplies anchor + H1 so Sphinx finds a page title.
    lines = [
        f"Workspace packages that declare a `{package_name}` dependency in "
        "their `pyproject.toml` `[project].dependencies` array.",
        "",
    ]
    if not dependents:
        lines.append(
            "_No workspace package currently depends on this one._",
        )
        lines.append("")
    else:
        for dep in dependents:
            lines.append(f"- {{doc}}`packages/{dep}/index`")
        lines.append("")
    return "\n".join(lines)


class PackageDependentsDirective(SphinxDirective):
    """Render reverse-intersphinx: workspace packages that depend on this one.

    Walks every shipped-py package's ``pyproject.toml`` and lists
    those whose ``[project].dependencies`` include the named package.
    Use on the package's optional ``dependents.md`` showcase subpage.

    Usage in ``packages/<name>/docs/dependents.md``::

        ```{package-dependents} sphinx-ux-badges
        ```
    """

    required_arguments = 1
    has_content = False

    def run(self) -> list[nodes.Node]:
        package_name = self.arguments[0].strip()
        markdown = _package_dependents_markdown(package_name)
        if not markdown:
            logger.warning(
                "package-dependents: unknown package %r",
                package_name,
            )
            return []
        return self.parse_text_to_nodes(markdown)


class WorkspacePackageGridDirective(SphinxDirective):
    """Render the workspace package index grid.

    By default emits a single grid of every Python-shipped package
    (backward compatible). Pass ``:groups: by-cluster`` to instead
    emit one grid per sidebar cluster, with headings, framing prose,
    and Emerging packages rendered as GitHub-linked cards.

    Usage in ``docs/packages/index.md``::

        ```{workspace-package-grid}
        ```

        ```{workspace-package-grid}
        :groups: by-cluster
        ```
    """

    has_content = False
    option_spec = {  # noqa: RUF012
        "groups": lambda v: str(v).strip(),
    }

    def run(self) -> list[nodes.Node]:
        groups = self.options.get("groups")
        markdown = workspace_package_grid_markdown(groups=groups)
        return self.parse_text_to_nodes(markdown)


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
    app.add_directive("package-landing", PackageLandingDirective)
    app.add_directive("cluster-toctree", ClusterToctreeDirective)
    app.add_directive("live-signature", LiveSignatureDirective)
    app.add_directive("package-kitchen-sink", PackageKitchenSinkDirective)
    app.add_directive("surface-changelog", SurfaceChangelogDirective)
    app.add_directive("package-dependents", PackageDependentsDirective)
    app.add_directive("package-reference", PackageReferenceDirective)
    app.add_directive("workspace-package-grid", WorkspacePackageGridDirective)
    app.add_role("subpage-exists", subpage_exists_role)
    app.connect("env-check-consistency", _register_extension_objects)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": "0.0.1",
    }
