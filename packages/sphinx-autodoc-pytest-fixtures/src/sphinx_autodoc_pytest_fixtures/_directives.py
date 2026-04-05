"""Sphinx directive classes for sphinx_autodoc_pytest_fixtures."""

from __future__ import annotations

import importlib
import pathlib
import typing as t

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.domains.python import PyFunction
from sphinx.util import logging as sphinx_logging
from sphinx.util.docfields import Field, GroupedField
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_pytest_fixtures._constants import (
    _CALLOUT_MESSAGES,
    _CONFIG_BUILTIN_LINKS,
    _CONFIG_EXTERNAL_LINKS,
    _DEFAULTS,
    _FIELD_LABELS,
    _KNOWN_KINDS,
    PYTEST_BUILTIN_LINKS,
)
from sphinx_autodoc_pytest_fixtures._css import _CSS
from sphinx_autodoc_pytest_fixtures._detection import (
    _get_fixture_fn,
    _get_fixture_marker,
    _is_pytest_fixture,
)
from sphinx_autodoc_pytest_fixtures._metadata import (
    _build_usage_snippet,
    _has_authored_example,
    _summary_insert_index,
)
from sphinx_autodoc_pytest_fixtures._models import (
    FixtureDep,
    FixtureMeta,
    autofixture_index_node,
)
from sphinx_autodoc_pytest_fixtures._store import _get_spf_store, _resolve_builtin_url

if t.TYPE_CHECKING:
    pass

logger = sphinx_logging.getLogger(__name__)


def _iter_public_fixture_entries(
    module: t.Any,
    *,
    excluded: set[str] | None = None,
) -> list[tuple[str, str, t.Any]]:
    """Collect public pytest fixtures from a module.

    Parameters
    ----------
    module : Any
        Imported module object to scan.
    excluded : set[str] | None, optional
        Public fixture names to skip.

    Returns
    -------
    list[tuple[str, str, Any]]
        Tuples of ``(attr_name, public_name, fixture_obj)`` in source order.
    """
    excluded = excluded or set()
    entries: list[tuple[str, str, t.Any]] = []
    seen_public: set[str] = set()

    for attr_name, value in vars(module).items():
        if not _is_pytest_fixture(value):
            continue
        try:
            marker = _get_fixture_marker(value)
        except AttributeError:
            continue
        public_name = marker.name or _get_fixture_fn(value).__name__
        if public_name in excluded:
            continue
        if public_name in seen_public:
            logger.warning(
                "pytest fixture scan skipped duplicate public name %r in %s",
                public_name,
                module.__name__,
            )
            continue
        seen_public.add(public_name)
        entries.append((attr_name, public_name, value))

    return entries


def _note_module_dependency(document: nodes.document, module: t.Any) -> None:
    """Register an imported module file as a Sphinx dependency.

    Parameters
    ----------
    document : nodes.document
        Current document node carrying the Sphinx environment.
    module : Any
        Imported module object that may expose ``__file__``.
    """
    env = document.settings.env
    if hasattr(module, "__file__") and module.__file__:
        env.note_dependency(module.__file__)


def _render_autofixtures_nodes(
    directive: SphinxDirective,
    *,
    modname: str,
    entries: list[tuple[str, str, t.Any]],
    order: str = "source",
) -> list[nodes.Node]:
    """Render ``autofixture`` directives into doctree nodes.

    Parameters
    ----------
    directive : SphinxDirective
        Directive instance used for nested parsing.
    modname : str
        Imported fixture module name.
    entries : list[tuple[str, str, Any]]
        Public fixture entries as ``(attr_name, public_name, fixture_obj)``.
    order : str, optional
        ``"source"`` keeps module order; ``"alpha"`` sorts by public name.

    Returns
    -------
    list[nodes.Node]
        Parsed fixture reference nodes.
    """
    if order == "alpha":
        entries = sorted(entries, key=lambda entry: entry[1])

    lines: list[str] = []
    for _attr_name, public_name, _value in entries:
        lines.append(f".. autofixture:: {modname}.{public_name}")
        lines.append("")

    content = "\n".join(lines).strip()
    if _is_markdown_source(directive):
        content = f"```{{eval-rst}}\n{content}\n```"

    return directive.parse_text_to_nodes(
        content,
        offset=directive.content_offset,
    )


def _is_markdown_source(directive: SphinxDirective) -> bool:
    """Return ``True`` when the current document source is Markdown/MyST."""
    source, _line = directive.get_source_info()
    if not source:
        source = getattr(directive.state.document, "current_source", "")
    if not source:
        return False

    return pathlib.Path(source).suffix.lower() in {
        ".md",
        ".markdown",
        ".myst",
    }


def _build_doc_pytest_plugin_index_node(modname: str) -> autofixture_index_node:
    """Create an autofixture-index placeholder node for *modname*."""
    node = autofixture_index_node()
    node["module"] = modname
    node["exclude"] = set()
    return node


class PyFixtureDirective(PyFunction):
    """Sphinx directive for documenting pytest fixtures: ``.. py:fixture::``.

    Registered as ``fixture`` in the Python domain. Renders as::

        fixture server -> Server

    instead of::

        server(request, monkeypatch, config_file) -> Server
    """

    option_spec = PyFunction.option_spec.copy()
    option_spec.update(
        {
            "scope": directives.unchanged,
            "autouse": directives.flag,
            "depends": directives.unchanged,
            "factory": directives.flag,
            "overridable": directives.flag,
            "kind": directives.unchanged,  # explicit kind override
            "return-type": directives.unchanged,
            "usage": directives.unchanged,  # "auto" (default) or "none"
            "params": directives.unchanged,  # e.g. ":params: val1, val2"
            "teardown": directives.flag,  # ":teardown:" flag for yield fixtures
            "async": directives.flag,  # ":async:" flag for async fixtures
            "deprecated": directives.unchanged,  # version string
            "replacement": directives.unchanged,  # canonical replacement fixture
            "teardown-summary": directives.unchanged,  # teardown description
        },
    )

    doc_field_types = [  # noqa: RUF012
        Field(
            "scope",
            label=_FIELD_LABELS["scope"],
            has_arg=False,
            names=("scope",),
        ),
        GroupedField(
            "depends",
            label=_FIELD_LABELS["depends"],
            rolename="fixture",
            names=("depends", "depend"),
            can_collapse=True,
        ),
        Field(
            "factory",
            label="Factory",
            has_arg=False,
            names=("factory",),
        ),
        Field(
            "overridable",
            label="Override hook",
            has_arg=False,
            names=("overridable",),
        ),
    ]

    def needs_arglist(self) -> bool:
        """Suppress ``()`` — fixtures are not called with arguments."""
        return False

    def get_signature_prefix(
        self,
        sig: str,
    ) -> t.Sequence[addnodes.desc_sig_element]:
        """Render the ``fixture`` keyword before the fixture name.

        Parameters
        ----------
        sig : str
            The raw signature string from the directive.

        Returns
        -------
        Sequence[addnodes.desc_sig_element]
            Prefix nodes rendering as ``fixture `` before the fixture name.
        """
        return [
            addnodes.desc_sig_keyword("", "fixture"),
            addnodes.desc_sig_space(),
        ]

    def handle_signature(
        self,
        sig: str,
        signode: addnodes.desc_signature,
    ) -> tuple[str, str]:
        """Store fixture metadata on signode for badge injection.

        Parameters
        ----------
        sig : str
            The raw signature string from the directive.
        signode : addnodes.desc_signature
            The signature node to annotate.

        Returns
        -------
        tuple[str, str]
            ``(fullname, prefix)`` from the parent implementation.
        """
        result = super().handle_signature(sig, signode)
        signode["spf_scope"] = self.options.get("scope", _DEFAULTS["scope"])
        signode["spf_kind"] = self.options.get("kind", _DEFAULTS["kind"])
        signode["spf_autouse"] = "autouse" in self.options
        signode["spf_deprecated"] = "deprecated" in self.options
        signode["spf_ret_type"] = self.options.get("return-type", "")
        return result

    def get_index_text(self, modname: str, name_cls: tuple[str, str]) -> str:
        """Return index entry text for the fixture.

        Parameters
        ----------
        modname : str
            The module name containing the fixture.
        name_cls : tuple[str, str]
            ``(fullname, classname_prefix)`` from ``handle_signature``.

        Returns
        -------
        str
            Index entry in the form ``name (pytest fixture in modname)``.
        """
        name, _cls = name_cls
        return f"{name} (pytest fixture in {modname})"

    def transform_content(
        self,
        content_node: addnodes.desc_content,
    ) -> None:
        """Inject fixture metadata as doctree nodes before DocFieldTransformer.

        ``transform_content`` runs at line 108 of ``ObjectDescription.run()``;
        ``DocFieldTransformer.transform_all()`` runs at line 112 — so
        ``nodes.field_list`` entries inserted here ARE processed by
        ``DocFieldTransformer`` and receive full field styling.

        Parameters
        ----------
        content_node : addnodes.desc_content
            The content node to prepend metadata into.
        """
        scope = self.options.get("scope", _DEFAULTS["scope"])
        depends_str = self.options.get("depends", "")
        ret_type = self.options.get("return-type", "")
        show_usage = self.options.get("usage", _DEFAULTS["usage"]) != "none"
        kind = self.options.get("kind", "")
        autouse = "autouse" in self.options
        has_teardown = "teardown" in self.options
        is_async = "async" in self.options

        field_list = nodes.field_list()

        # Scope field removed — badges communicate scope at a glance,
        # the index table provides comparison.  See P2-2 in the enhancement spec.

        # --- Autouse field ---
        if autouse:
            field_list += nodes.field(
                "",
                nodes.field_name("", _FIELD_LABELS["autouse"]),
                nodes.field_body(
                    "",
                    nodes.paragraph("", "yes \u2014 runs automatically for every test"),
                ),
            )

        # --- Kind field (only for custom/nonstandard kinds not covered by badges) ---
        if kind and kind not in _KNOWN_KINDS:
            field_list += nodes.field(
                "",
                nodes.field_name("", _FIELD_LABELS["kind"]),
                nodes.field_body("", nodes.paragraph("", kind)),
            )

        # --- Depends-on fields — project deps as :fixture: xrefs,
        #     builtin/external deps as external hyperlinks ---
        if depends_str:
            # Resolve builtin/external link mapping from config
            app_obj = getattr(getattr(self, "env", None), "app", None)
            builtin_links: dict[str, str] = (
                getattr(
                    app_obj.config,
                    _CONFIG_BUILTIN_LINKS,
                    PYTEST_BUILTIN_LINKS,
                )
                if app_obj is not None
                else PYTEST_BUILTIN_LINKS
            )
            external_links: dict[str, str] = (
                getattr(app_obj.config, _CONFIG_EXTERNAL_LINKS, {})
                if app_obj is not None
                else {}
            )
            all_links = {**builtin_links, **external_links}

            # Collect all dep nodes, then emit one comma-separated row
            # (matches the "Used by" pattern in _on_doctree_resolved).
            dep_ref_nodes: list[nodes.Node] = []
            for dep in (d.strip() for d in depends_str.split(",") if d.strip()):
                # Resolve URL: intersphinx → config → hardcoded fallback
                url: str | None = None
                if dep in all_links:
                    url = _resolve_builtin_url(dep, app_obj) or all_links[dep]
                if url:
                    dep_ref_nodes.append(
                        nodes.reference(dep, "", nodes.literal(dep, dep), refuri=url)
                    )
                else:
                    ref_ns, _ = self.state.inline_text(
                        f":fixture:`{dep}`",
                        self.lineno,
                    )
                    dep_ref_nodes.extend(ref_ns)

            if dep_ref_nodes:
                body_para = nodes.paragraph()
                for i, dn in enumerate(dep_ref_nodes):
                    body_para += dn
                    if i < len(dep_ref_nodes) - 1:
                        body_para += nodes.Text(", ")
                field_list += nodes.field(
                    "",
                    nodes.field_name("", _FIELD_LABELS["depends"]),
                    nodes.field_body("", body_para),
                )

        # --- Deprecation warning (before lifecycle callouts) ---
        deprecated_version = self.options.get("deprecated")
        replacement_name = self.options.get("replacement")

        if deprecated_version is not None:
            warning = nodes.warning()
            dep_para = nodes.paragraph()
            dep_para += nodes.Text(f"Deprecated since version {deprecated_version}.")
            if replacement_name:
                dep_para += nodes.Text(" Use ")
                ref_ns, _ = self.state.inline_text(
                    f":fixture:`{replacement_name}`",
                    self.lineno,
                )
                dep_para.extend(ref_ns)
                dep_para += nodes.Text(" instead.")
            warning += dep_para
            # Add spf-deprecated class to the parent desc node for CSS muting
            for parent in self.state.document.findall(addnodes.desc):
                for sig in parent.findall(addnodes.desc_signature):
                    if sig.get("spf_deprecated"):
                        if _CSS.DEPRECATED not in parent["classes"]:
                            parent["classes"].append(_CSS.DEPRECATED)
                        break

        # --- Lifecycle callouts (session note + override hook tip) ---
        callout_nodes: list[nodes.Node] = []

        if deprecated_version is not None:
            callout_nodes.append(warning)

        if scope == "session":
            note = nodes.note()
            note += nodes.paragraph("", _CALLOUT_MESSAGES["session_scope"])
            callout_nodes.append(note)

        if kind == "override_hook":
            tip = nodes.tip()
            tip += nodes.paragraph("", _CALLOUT_MESSAGES["override_hook"])
            callout_nodes.append(tip)

        if has_teardown:
            note = nodes.note()
            note += nodes.paragraph("", _CALLOUT_MESSAGES["yield_fixture"])
            teardown_text = self.options.get("teardown-summary", "")
            if teardown_text:
                note += nodes.paragraph(
                    "",
                    "",
                    nodes.strong("", "Teardown: "),
                    nodes.Text(teardown_text),
                )
            callout_nodes.append(note)

        if is_async:
            note = nodes.note()
            note += nodes.paragraph("", _CALLOUT_MESSAGES["async_fixture"])
            callout_nodes.append(note)

        # --- Usage snippet (five-zone insertion after first paragraph) ---
        raw_arg = self.arguments[0] if self.arguments else ""
        fixture_name = raw_arg.split("(")[0].strip()

        snippet: nodes.Node | None = None
        if show_usage and fixture_name and not _has_authored_example(content_node):
            snippet = _build_usage_snippet(
                fixture_name,
                ret_type or None,
                kind or _DEFAULTS["kind"],
                scope,
                autouse,
            )

        # Collect generated nodes and insert in five-zone order after summary.
        # Insertion uses reversed() so nodes end up in forward order.
        generated: list[nodes.Node] = [*callout_nodes]
        if field_list.children:
            generated.append(field_list)
        if snippet is not None:
            generated.append(snippet)

        if generated:
            insert_idx = _summary_insert_index(content_node)
            for node in reversed(generated):
                content_node.insert(insert_idx, node)

    def add_target_and_index(
        self,
        name_cls: tuple[str, str],
        sig: str,
        signode: addnodes.desc_signature,
    ) -> None:
        """Register the fixture target and index entry.

        Notes
        -----
        Bypasses ``PyFunction.add_target_and_index``, which always appends a
        ``name() (in module X)`` index entry — wrong for fixtures. Calls
        ``PyObject.add_target_and_index`` directly so only the fixture-style
        ``get_index_text`` entry is produced.

        Stores ``spf_canonical_name`` on *signode* for metadata-driven
        rendering in :func:`_on_doctree_resolved`.
        """
        modname = self.options.get("module", self.env.ref_context.get("py:module", ""))
        name = name_cls[0]
        canonical = f"{modname}.{name}" if modname else name
        signode["spf_canonical_name"] = canonical
        super(PyFunction, self).add_target_and_index(name_cls, sig, signode)

        # Scope/kind-qualified pair index entries for the general index.
        node_id = signode.get("ids", [""])[0] if signode.get("ids") else ""
        scope = self.options.get("scope", _DEFAULTS["scope"])
        kind = self.options.get("kind", _DEFAULTS["kind"])
        if scope != "function" and node_id:
            self.indexnode["entries"].append(
                ("pair", f"{scope}-scoped fixtures; {name}", node_id, "", None)
            )
        if kind not in ("resource",) and node_id:
            kind_label = {
                "factory": "factory fixtures",
                "override_hook": "override hooks",
            }.get(kind, f"{kind} fixtures")
            self.indexnode["entries"].append(
                ("pair", f"{kind_label}; {name}", node_id, "", None)
            )

        # Register minimal FixtureMeta for manual directives so they
        # participate in short-name xrefs, "Used by", and reverse_deps.
        # Guard: don't overwrite richer autodoc-generated metadata.
        store = _get_spf_store(self.env)
        if canonical not in store["fixtures"]:
            public = canonical.rsplit(".", 1)[-1]
            deps: list[FixtureDep] = []
            if depends_str := self.options.get("depends"):
                deps.extend(
                    FixtureDep(display_name=d.strip(), kind="fixture")
                    for d in depends_str.split(",")
                    if d.strip()
                )
            store["fixtures"][canonical] = FixtureMeta(
                docname=self.env.docname,
                canonical_name=canonical,
                public_name=public,
                source_name=public,
                scope=self.options.get("scope", _DEFAULTS["scope"]),
                autouse="autouse" in self.options,
                kind=self.options.get("kind", _DEFAULTS["kind"]),
                return_display=self.options.get("return-type", ""),
                return_xref_target=None,
                deps=tuple(deps),
                param_reprs=tuple(
                    p.strip()
                    for p in self.options.get("params", "").split(",")
                    if p.strip()
                ),
                has_teardown="teardown" in self.options,
                is_async="async" in self.options,
                summary="",
                deprecated=self.options.get("deprecated"),
                replacement=self.options.get("replacement"),
                teardown_summary=self.options.get("teardown-summary"),
            )


class AutofixturesDirective(SphinxDirective):
    """Bulk fixture autodoc directive: ``.. autofixtures:: module.name``.

    Scans *module.name* for all pytest fixtures and emits one
    ``.. autofixture::`` directive per fixture found.  This eliminates
    the need to list every fixture manually in docs.

    Usage::

        .. autofixtures:: libtmux.pytest_plugin
           :order: source
           :exclude: clear_env

    Options
    -------
    order : str, optional
        ``"source"`` (default) preserves module attribute order.
        ``"alpha"`` sorts fixtures alphabetically by public name.
    exclude : str, optional
        Comma-separated list of fixture public names to skip.
    """

    required_arguments = 1
    optional_arguments = 0
    has_content = False
    option_spec: t.ClassVar[dict[str, t.Any]] = {
        "order": directives.unchanged,
        "exclude": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Scan the module and emit autofixture directives."""
        modname = self.arguments[0].strip()
        order = self.options.get("order", "source")
        exclude_str = self.options.get("exclude", "")
        excluded: set[str] = {
            name.strip() for name in exclude_str.split(",") if name.strip()
        }

        try:
            module = importlib.import_module(modname)
        except ImportError:
            logger.warning(
                "autofixtures: cannot import module %r — skipping.",
                modname,
            )
            return []

        _note_module_dependency(self.state.document, module)
        entries = _iter_public_fixture_entries(module, excluded=excluded)

        return _render_autofixtures_nodes(
            self,
            modname=modname,
            entries=entries,
            order=order,
        )


class DocPytestPluginDirective(SphinxDirective):
    """Render a reusable pytest-plugin documentation page block.

    Parameters
    ----------
    self : SphinxDirective
        Directive instance populated by the Sphinx parser.

    Notes
    -----
    ``page`` mode emits a compact install/autodiscovery intro before the
    generated fixture summary and reference blocks. ``reference`` mode only
    emits any authored body content plus the generated fixture sections.
    """

    required_arguments = 1
    optional_arguments = 0
    has_content = True
    option_spec: t.ClassVar[dict[str, t.Any]] = {
        "project": directives.unchanged,
        "package": directives.unchanged,
        "summary": directives.unchanged,
        "mode": lambda arg: directives.choice(arg, ("page", "reference")),
        "tests-url": directives.unchanged,
        "install-command": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Render intro prose plus generated fixture index/reference blocks."""
        modname = self.arguments[0].strip()
        project = self._require_option("project")
        package = self._require_option("package")
        summary = self._require_option("summary")
        mode = self.options.get("mode", "page")
        tests_url = self.options.get("tests-url")
        install_command = self.options.get(
            "install-command",
            f"pip install {package}",
        )

        children: list[nodes.Node] = []
        if mode == "page":
            children.extend(
                self._build_page_intro_nodes(
                    project=project,
                    summary=summary,
                    install_command=install_command,
                    tests_url=tests_url,
                ),
            )

        if self.content:
            children.extend(
                self.parse_content_to_nodes(
                    allow_section_headings=True,
                ),
            )

        entries = self._get_module_fixture_entries(modname)
        if entries is not None:
            children.extend(
                self._build_fixture_section_nodes(
                    modname=modname,
                    entries=entries,
                ),
            )

        return children

    def _require_option(self, name: str) -> str:
        """Return a required option value or raise a directive error."""
        value = self.options.get(name, "").strip()
        if not value:
            msg = f"{self.name} requires the :{name}: option"
            raise self.error(msg)
        return value

    def _get_module_fixture_entries(
        self,
        modname: str,
    ) -> list[tuple[str, str, t.Any]] | None:
        """Import *modname* and return discovered fixture entries."""
        try:
            module = importlib.import_module(modname)
        except ImportError:
            logger.warning(
                "doc-pytest-plugin could not import module %r; "
                "skipping generated fixture sections",
                modname,
            )
            return None

        _note_module_dependency(self.state.document, module)
        entries = _iter_public_fixture_entries(module)
        if entries:
            return entries

        logger.warning(
            "doc-pytest-plugin found no pytest fixtures in %r; "
            "skipping generated fixture sections",
            modname,
        )
        return None

    def _build_page_intro_nodes(
        self,
        *,
        project: str,
        summary: str,
        install_command: str,
        tests_url: str | None,
    ) -> list[nodes.Node]:
        """Build the generated intro nodes for ``page`` mode."""
        intro_nodes: list[nodes.Node] = [nodes.paragraph("", summary)]
        intro_nodes.append(nodes.rubric("", "Install"))

        install_block = nodes.literal_block("", f"$ {install_command}")
        install_block["language"] = "console"
        intro_nodes.append(install_block)

        note = nodes.note()
        note_para = nodes.paragraph()
        note_para += nodes.Text("pytest auto-detects this plugin through the ")
        note_para += nodes.literal("", "pytest11")
        note_para += nodes.Text(
            " entry point. Its fixtures are available without extra "
        )
        note_para += nodes.literal("", "conftest.py")
        note_para += nodes.Text(" imports.")
        note += note_para
        intro_nodes.append(note)

        if tests_url:
            tests_para = nodes.paragraph()
            tests_para += nodes.Text("For real-world usage examples, see the ")
            tests_para += nodes.reference(
                "",
                "",
                nodes.Text(f"{project} test suite"),
                refuri=tests_url,
            )
            tests_para += nodes.Text(".")
            intro_nodes.append(tests_para)

        return intro_nodes

    def _build_fixture_section_nodes(
        self,
        *,
        modname: str,
        entries: list[tuple[str, str, t.Any]],
    ) -> list[nodes.Node]:
        """Build generated fixture summary/reference nodes."""
        return [
            nodes.rubric("", "Fixture Summary"),
            _build_doc_pytest_plugin_index_node(modname),
            nodes.rubric("", "Fixture Reference"),
            *_render_autofixtures_nodes(
                self,
                modname=modname,
                entries=entries,
                order="source",
            ),
        ]


class AutofixtureIndexDirective(SphinxDirective):
    """Generate a fixture index table from the :class:`FixtureStoreDict`.

    Emits a :class:`autofixture_index_node` placeholder at parse time.
    The placeholder is resolved into a ``nodes.table`` during
    ``doctree-resolved``, when the store has been finalized by ``env-updated``.

    Usage::

        .. autofixture-index:: libtmux.pytest_plugin
           :exclude: _internal_helper
    """

    required_arguments = 1
    optional_arguments = 0
    has_content = False
    option_spec: t.ClassVar[dict[str, t.Any]] = {
        "exclude": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Return a placeholder node with module and exclude metadata."""
        node = autofixture_index_node()
        node["module"] = self.arguments[0].strip()
        node["exclude"] = {
            s.strip() for s in self.options.get("exclude", "").split(",") if s.strip()
        }
        return [node]
