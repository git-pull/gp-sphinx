"""Sphinx directives for FastMCP tool documentation."""

from __future__ import annotations

import logging
import typing as t

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

if t.TYPE_CHECKING:
    from sphinx.environment import BuildEnvironment

from sphinx_autodoc_fastmcp._badges import (
    build_prompt_badge_group,
    build_resource_badge_group,
    build_tool_badge_group,
)
from sphinx_autodoc_fastmcp._css import _CSS
from sphinx_autodoc_fastmcp._models import (
    ParamInfo,
    PromptArgInfo,
    PromptInfo,
    ResourceInfo,
    ResourceTemplateInfo,
    ToolInfo,
)
from sphinx_autodoc_fastmcp._parsing import (
    first_paragraph,
    make_para,
    make_table,
    parse_rst_inline,
)
from sphinx_autodoc_typehints_gp import (
    build_annotation_display_paragraph,
    build_annotation_paragraph,
    classify_annotation_display,
)
from sphinx_ux_autodoc_layout import (
    API,
    ApiFactRow,
    api_permalink,
    build_api_card_entry,
    build_api_facts_section,
    build_api_section,
    build_api_summary_section,
    build_api_table_section,
)

logger = logging.getLogger(__name__)


def _register_section_label(
    env: BuildEnvironment, section_id: str, display_name: str
) -> None:
    """Register section in Sphinx std domain at parse time so {ref} resolves it.

    Must run inside a directive's run() — at that point env.docname is set and
    domain.data is the live dict that gets pickled, surviving incremental builds.

    Direct dict writes mirror the same-package pattern in
    :func:`sphinx_autodoc_fastmcp._transforms.register_tool_labels`; Sphinx
    flags ``StandardDomain.note_hyperlink_target`` as internal-use-only.

    Examples
    --------
    >>> import types
    >>> std = types.SimpleNamespace(labels={}, anonlabels={})
    >>> domains = types.SimpleNamespace(standard_domain=std)
    >>> env = types.SimpleNamespace(docname="api", domains=domains)
    >>> _register_section_label(env, "fastmcp-tool-foo", "foo")
    >>> std.labels["fastmcp-tool-foo"]
    ('api', 'fastmcp-tool-foo', 'foo')
    >>> std.anonlabels["fastmcp-tool-foo"]
    ('api', 'fastmcp-tool-foo')
    """
    std = env.domains.standard_domain
    std.anonlabels[section_id] = (env.docname, section_id)
    std.labels[section_id] = (env.docname, section_id, display_name)


def _component_ids(kind: str, name: str) -> tuple[str, list[str]]:
    """Derive canonical section id + back-compat label aliases for a component.

    Canonical IDs always namespace by kind so a tool ``status`` and a
    prompt ``status`` cannot collide in ``std.labels``. Tools additionally
    keep the bare slug as a label alias because their unprefixed names were
    the public ``{ref}`` shape on ``main`` and live in downstream user docs;
    the alias resolves to the canonical ID and never becomes a physical
    HTML id, so it cannot collide with a same-slug page heading.
    Prompts/resources/templates have no such history, so they get the
    canonical ID only.

    Examples
    --------
    >>> _component_ids("tool", "list_sessions")
    ('fastmcp-tool-list-sessions', ['list-sessions'])
    >>> _component_ids("prompt", "greet_user")
    ('fastmcp-prompt-greet-user', [])
    >>> _component_ids("resource-template", "events_by_day")
    ('fastmcp-resource-template-events-by-day', [])
    """
    slug = name.replace("_", "-")
    canonical = f"fastmcp-{kind}-{slug}"
    aliases: list[str] = [slug] if kind == "tool" else []
    return canonical, aliases


def _register_alias_if_free(
    env: BuildEnvironment,
    *,
    alias: str,
    target_id: str,
    display_name: str,
    kind: str,
) -> bool:
    """Register a bare-slug label alias for *target_id* iff unclaimed.

    Aliases are tool-only by policy (back-compat with v1 ``{ref}`` URLs).
    Calling this for any other kind is a programming error — raises
    :class:`ValueError`. If the alias is already bound to a different
    target, log WARNING and return ``False`` (canonical-only, no
    silent overwrite).

    The alias is a pure label: it points at the canonical section ID
    (``std.labels[alias] = (docname, target_id, ...)``) and never becomes
    a physical HTML id of its own, so a same-slug page heading keeps sole
    ownership of the bare anchor (#48).

    Returns True if the alias was registered, False if skipped.

    Examples
    --------
    >>> import types
    >>> std = types.SimpleNamespace(labels={}, anonlabels={})
    >>> domains = types.SimpleNamespace(standard_domain=std)
    >>> env = types.SimpleNamespace(docname="api", domains=domains)
    >>> _register_alias_if_free(
    ...     env,
    ...     alias="delete-buffer",
    ...     target_id="fastmcp-tool-delete-buffer",
    ...     display_name="delete_buffer",
    ...     kind="tool",
    ... )
    True
    >>> std.labels["delete-buffer"]
    ('api', 'fastmcp-tool-delete-buffer', 'delete_buffer')
    >>> std.anonlabels["delete-buffer"]
    ('api', 'fastmcp-tool-delete-buffer')
    """
    if kind != "tool":
        msg = f"alias registration not permitted for kind={kind!r}"
        raise ValueError(msg)

    std = env.domains.standard_domain
    existing = std.labels.get(alias) or std.anonlabels.get(alias)
    if existing is not None:
        existing_doc = existing[0]
        existing_id = existing[1]
        if (existing_doc, existing_id) != (env.docname, target_id):
            logger.warning(
                "sphinx_autodoc_fastmcp: bare alias %r for %s already claimed "
                "by %s#%s; using canonical id only",
                alias,
                display_name,
                existing_doc,
                existing_id,
            )
            return False

    std.anonlabels[alias] = (env.docname, target_id)
    std.labels[alias] = (env.docname, target_id, display_name)
    return True


class FastMCPToolDirective(SphinxDirective):
    """Autodocument one MCP tool: section (ToC/labels) + card body.

    Supports the standard Sphinx ``:no-index:`` flag (mirrors
    :func:`autofunction`/:func:`autoclass` semantics): when set, the card
    still renders in full but its canonical section ID and bare-slug alias
    are not registered in :class:`StandardDomain` ``labels`` /
    ``anonlabels``. Use it when a tool needs to appear visually on more
    than one page (e.g. a gallery demo + a reference page) — exactly one
    invocation per tool should omit ``:no-index:`` so cross-references
    have a single canonical home.
    """

    required_arguments = 1
    optional_arguments = 0
    has_content = True
    final_argument_whitespace = False
    option_spec: t.ClassVar[dict[str, t.Callable[[str], t.Any]]] = {
        "no-index": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        """Build section with title row + docstring/returns for one tool."""
        arg = self.arguments[0]
        func_name = arg.split(".")[-1] if "." in arg else arg

        tools: dict[str, ToolInfo] = getattr(self.env, "fastmcp_tools", {})
        tool = tools.get(func_name)

        if tool is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-tool: tool '{func_name}' not found. "
                    f"Available: {', '.join(sorted(tools.keys()))}",
                    line=self.lineno,
                ),
            ]

        return self._build_tool_section(tool)

    def _build_tool_section(self, tool: ToolInfo) -> list[nodes.Node]:
        """Build section card with shared API layout regions."""
        document = self.state.document
        section_id, aliases = _component_ids("tool", tool.name)
        no_index = "no-index" in self.options

        section = nodes.section()
        section["ids"].append(section_id)
        section["classes"].extend((_CSS.TOOL_SECTION, API.CARD_SHELL))
        if no_index:
            # Marker consumed by ``register_tool_labels`` in _transforms.py
            # so the doctree-read pass mirrors the directive's skip.
            section["fastmcp_no_index"] = True
        else:
            _register_section_label(self.env, section_id, tool.name)
            # Marker consumed by ``register_tool_labels`` so incremental
            # rebuilds restore the same alias labels from the doctree cache.
            section["fastmcp_alias_labels"] = [
                alias
                for alias in aliases
                if _register_alias_if_free(
                    self.env,
                    alias=alias,
                    target_id=section_id,
                    display_name=tool.name,
                    kind="tool",
                )
            ]
            document.note_explicit_target(section)

        title_node = nodes.title("", "")
        title_node["classes"].append(f"{_CSS.PREFIX}-tool-title")
        title_node["classes"].append(_CSS.SECTION_TITLE_HIDDEN)
        title_node += nodes.literal("", tool.name)
        section += title_node

        link = api_permalink(
            href=f"#{section_id}",
            title="Link to this tool",
        )
        link["classes"] = ["headerlink", API.LINK]
        first_para = first_paragraph(tool.docstring)
        content_nodes: list[nodes.Node] = [
            build_api_section(
                API.DESCRIPTION,
                parse_rst_inline(first_para, self.state, self.lineno),
                classes=(_CSS.BODY_SECTION,),
            )
        ]

        if tool.return_annotation:
            content_nodes.append(
                build_api_facts_section(
                    [
                        ApiFactRow(
                            "Returns",
                            build_annotation_paragraph(
                                tool.return_annotation,
                                self.env,
                            ),
                        )
                    ],
                    classes=(_CSS.BODY_SECTION,),
                )
            )

        entry = build_api_card_entry(
            profile_class=API.profile("fastmcp-tool"),
            signature_children=(nodes.literal("", tool.name),),
            content_children=tuple(content_nodes),
            badge_group=build_tool_badge_group(tool.safety),
            permalink=link,
            entry_classes=(_CSS.TOOL_ENTRY,),
            signature_classes=(_CSS.TOOL_SIGNATURE,),
        )
        section += entry

        return [section]


class FastMCPToolInputDirective(SphinxDirective):
    """Emit the parameter table for a tool."""

    required_arguments = 1
    optional_arguments = 0
    has_content = False

    def run(self) -> list[nodes.Node]:
        """Build parameter table nodes."""
        arg = self.arguments[0]
        func_name = arg.split(".")[-1] if "." in arg else arg

        tools: dict[str, ToolInfo] = getattr(self.env, "fastmcp_tools", {})
        tool = tools.get(func_name)

        if tool is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-tool-input: tool '{func_name}' not found.",
                    line=self.lineno,
                ),
            ]

        result: list[nodes.Node] = []

        if tool.params:
            result.append(make_para(nodes.strong("", "Parameters")))
            headers = ["Parameter", "Type", "Required", "Default", "Description"]
            rows: list[list[str | nodes.Node]] = []
            for p in tool.params:
                desc_node = self._build_description(p)

                type_cell: str | nodes.Node = "—"
                if p.type_str:
                    type_cell = build_annotation_display_paragraph(
                        p.type_str,
                        self.env,
                    )

                type_display = (
                    classify_annotation_display(p.type_str) if p.type_str else None
                )
                if type_display and type_display.literal_members:
                    desc_node += nodes.Text(" One of: ")
                    for i, val in enumerate(type_display.literal_members):
                        if i > 0:
                            desc_node += nodes.Text(", ")
                        desc_node += nodes.literal("", val)
                    desc_node += nodes.Text(".")

                default_cell: str | nodes.Node = "—"
                if p.default and p.default != "None":
                    default_cell = make_para(nodes.literal("", p.default))

                rows.append(
                    [
                        make_para(nodes.literal("", p.name)),
                        type_cell,
                        "yes" if p.required else "no",
                        default_cell,
                        desc_node,
                    ],
                )
            result.append(
                build_api_table_section(
                    API.PARAMETERS,
                    make_table(headers, rows, col_widths=[15, 15, 8, 10, 52]),
                ),
            )

        return result

    def _build_description(self, p: ParamInfo) -> nodes.paragraph:
        """Build description paragraph with optional RST inline markup."""
        if p.description:
            return parse_rst_inline(
                p.description,
                self.state,
                self.lineno,
            )
        return nodes.paragraph("", "—")


class FastMCPToolSummaryDirective(SphinxDirective):
    """Summary tables of tools grouped by safety tier."""

    required_arguments = 0
    optional_arguments = 0
    has_content = False

    def run(self) -> list[nodes.Node]:
        """Build tier sections with tables."""
        tools: dict[str, ToolInfo] = getattr(self.env, "fastmcp_tools", {})

        if not tools:
            return [
                self.state.document.reporter.warning(
                    "fastmcp-tool-summary: no tools found.",
                    line=self.lineno,
                ),
            ]

        groups: dict[str, list[ToolInfo]] = {
            "readonly": [],
            "mutating": [],
            "destructive": [],
        }
        for tool in tools.values():
            groups.setdefault(tool.safety, []).append(tool)

        result_nodes: list[nodes.Node] = []

        tier_order = [
            ("readonly", "Inspect", "Read state without changing anything."),
            ("mutating", "Act", "Create or modify objects."),
            ("destructive", "Destroy", "Remove objects; not reversible."),
        ]

        for safety, label, desc in tier_order:
            tier_tools = groups.get(safety, [])
            if not tier_tools:
                continue

            section = nodes.section()
            section["ids"].append(label.lower())
            self.state.document.note_explicit_target(section)
            section += nodes.title("", label)
            section += nodes.paragraph("", desc)

            headers = ["Tool", "Description"]
            rows: list[list[str | nodes.Node]] = []
            for tool in sorted(tier_tools, key=lambda x: x.name):
                first_line = first_paragraph(tool.docstring)
                ref = nodes.reference("", "", internal=True)
                ref["refuri"] = f"{tool.area}/#{_component_ids('tool', tool.name)[0]}"
                ref += nodes.literal("", tool.name)
                rows.append(
                    [
                        make_para(ref),
                        parse_rst_inline(first_line, self.state, self.lineno),
                    ],
                )
            section += build_api_summary_section(
                make_table(headers, rows, col_widths=[30, 70]),
            )

            result_nodes.append(section)

        return result_nodes


def _arg_table(
    args: list[PromptArgInfo],
    *,
    env: t.Any,
    state: t.Any,
    lineno: int,
    heading_word: str,
) -> list[nodes.Node]:
    """Build a Parameters/Arguments section for prompt or template args."""
    if not args:
        return []
    headers = ["Argument", "Type", "Required", "Description"]
    rows: list[list[str | nodes.Node]] = []
    for arg in args:
        type_cell: str | nodes.Node = "—"
        if arg.type_str:
            try:
                type_cell = build_annotation_display_paragraph(arg.type_str, env)
            except Exception:  # pragma: no cover - defensive
                type_cell = make_para(nodes.literal("", arg.type_str))
        desc_node: nodes.Node
        if arg.description:
            desc_node = parse_rst_inline(arg.description, state, lineno)
        else:
            desc_node = nodes.paragraph("", "—")
        rows.append(
            [
                make_para(nodes.literal("", arg.name)),
                type_cell,
                "yes" if arg.required else "no",
                desc_node,
            ],
        )
    return [
        make_para(nodes.strong("", heading_word)),
        build_api_table_section(
            API.PARAMETERS,
            make_table(headers, rows, col_widths=[20, 20, 10, 50]),
        ),
    ]


class FastMCPPromptDirective(SphinxDirective):
    """Autodocument one MCP prompt: section + card body."""

    required_arguments = 1
    optional_arguments = 0
    has_content = True
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        """Build section with title + description for one prompt."""
        arg = self.arguments[0]
        prompt_name = arg.split(".")[-1] if "." in arg else arg
        prompts: dict[str, PromptInfo] = getattr(self.env, "fastmcp_prompts", {})
        prompt = prompts.get(prompt_name)
        if prompt is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-prompt: prompt '{prompt_name}' not found. "
                    f"Available: {', '.join(sorted(prompts.keys()))}",
                    line=self.lineno,
                ),
            ]

        document = self.state.document
        section_id, _ = _component_ids("prompt", prompt.name)
        section = nodes.section()
        section["ids"].append(section_id)
        section["classes"].extend((_CSS.PROMPT_SECTION, API.CARD_SHELL))
        _register_section_label(self.env, section_id, prompt.name)
        document.note_explicit_target(section)

        title_node = nodes.title("", "")
        title_node["classes"].append(_CSS.SECTION_TITLE_HIDDEN)
        title_node += nodes.literal("", prompt.name)
        section += title_node

        link = api_permalink(href=f"#{section_id}", title="Link to this prompt")
        link["classes"] = ["headerlink", API.LINK]

        description = prompt.description or first_paragraph(prompt.docstring)
        content_nodes: list[nodes.Node] = []
        if description:
            content_nodes.append(
                build_api_section(
                    API.DESCRIPTION,
                    parse_rst_inline(description, self.state, self.lineno),
                    classes=(_CSS.BODY_SECTION,),
                ),
            )

        section += build_api_card_entry(
            profile_class=API.profile("fastmcp-prompt"),
            signature_children=(nodes.literal("", prompt.name),),
            content_children=tuple(content_nodes),
            badge_group=build_prompt_badge_group(prompt.tags),
            permalink=link,
            entry_classes=(_CSS.PROMPT_ENTRY,),
            signature_classes=(_CSS.PROMPT_SIGNATURE,),
        )
        return [section]


class FastMCPPromptInputDirective(SphinxDirective):
    """Emit the argument table for a prompt."""

    required_arguments = 1
    optional_arguments = 0
    has_content = False

    def run(self) -> list[nodes.Node]:
        """Build argument table nodes."""
        arg = self.arguments[0]
        prompt_name = arg.split(".")[-1] if "." in arg else arg
        prompts: dict[str, PromptInfo] = getattr(self.env, "fastmcp_prompts", {})
        prompt = prompts.get(prompt_name)
        if prompt is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-prompt-input: prompt '{prompt_name}' not found.",
                    line=self.lineno,
                ),
            ]
        return _arg_table(
            prompt.arguments,
            env=self.env,
            state=self.state,
            lineno=self.lineno,
            heading_word="Arguments",
        )


def _build_resource_card(
    *,
    env: BuildEnvironment,
    state: t.Any,
    lineno: int,
    signature_text: str,
    description: str,
    docstring: str,
    badge_group: nodes.inline,
    mime_type: str,
    shell_class: str,
    entry_class: str,
    signature_class: str,
    profile_name: str,
    section_id: str,
    display_name: str,
    document: t.Any,
    permalink_title: str = "Link to this resource",
) -> nodes.Node:
    """Shared card builder for resources & resource templates."""
    content_nodes: list[nodes.Node] = []
    body = description or first_paragraph(docstring)
    if body:
        content_nodes.append(
            build_api_section(
                API.DESCRIPTION,
                parse_rst_inline(body, state, lineno),
                classes=(_CSS.BODY_SECTION,),
            ),
        )

    if mime_type:
        content_nodes.append(
            build_api_facts_section(
                [ApiFactRow("MIME type", nodes.literal("", mime_type))],
                classes=(_CSS.BODY_SECTION,),
            ),
        )

    section = nodes.section()
    section["ids"].append(section_id)
    section["classes"].extend((shell_class, API.CARD_SHELL))
    _register_section_label(env, section_id, display_name)
    document.note_explicit_target(section)

    title_node = nodes.title("", "")
    title_node["classes"].append(_CSS.SECTION_TITLE_HIDDEN)
    title_node += nodes.literal("", display_name)
    section += title_node

    link = api_permalink(href=f"#{section_id}", title=permalink_title)
    link["classes"] = ["headerlink", API.LINK]

    section += build_api_card_entry(
        profile_class=API.profile(profile_name),
        signature_children=(nodes.literal("", signature_text),),
        content_children=tuple(content_nodes),
        badge_group=badge_group,
        permalink=link,
        entry_classes=(entry_class,),
        signature_classes=(signature_class,),
    )
    return section


class FastMCPResourceDirective(SphinxDirective):
    """Autodocument one MCP resource (fixed URI)."""

    required_arguments = 1
    optional_arguments = 0
    has_content = True
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        """Build section card for a resource."""
        arg = self.arguments[0]
        resources: dict[str, ResourceInfo] = getattr(self.env, "fastmcp_resources", {})
        names: dict[str, str] = getattr(self.env, "fastmcp_resource_names", {})
        # Try literal URI first, then friendly-name lookup via the name index.
        name = arg.split(".")[-1] if "." in arg else arg
        res = resources.get(arg) or resources.get(names.get(name, ""))
        if res is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-resource: resource '{name}' not found. "
                    f"Available: {', '.join(sorted(resources.keys()))}",
                    line=self.lineno,
                ),
            ]
        return [
            _build_resource_card(
                env=self.env,
                state=self.state,
                lineno=self.lineno,
                signature_text=res.uri,
                description=res.description,
                docstring=res.docstring,
                badge_group=build_resource_badge_group(
                    res.mime_type,
                    res.tags,
                    kind="resource",
                ),
                mime_type=res.mime_type,
                shell_class=_CSS.RESOURCE_SECTION,
                entry_class=_CSS.RESOURCE_ENTRY,
                signature_class=_CSS.RESOURCE_SIGNATURE,
                profile_name="fastmcp-resource",
                section_id=_component_ids("resource", res.name)[0],
                display_name=res.name,
                document=self.state.document,
            ),
        ]


class FastMCPResourceTemplateDirective(SphinxDirective):
    """Autodocument one MCP resource template (parameterised URI)."""

    required_arguments = 1
    optional_arguments = 0
    has_content = True
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        """Build section card for a resource template."""
        arg = self.arguments[0]
        templates: dict[str, ResourceTemplateInfo] = getattr(
            self.env,
            "fastmcp_resource_templates",
            {},
        )
        names: dict[str, str] = getattr(self.env, "fastmcp_resource_template_names", {})
        # Try literal URI template first, then friendly-name lookup.
        name = arg.split(".")[-1] if "." in arg else arg
        tpl = templates.get(arg) or templates.get(names.get(name, ""))
        if tpl is None:
            return [
                self.state.document.reporter.warning(
                    f"fastmcp-resource-template: template '{name}' not found. "
                    f"Available: {', '.join(sorted(templates.keys()))}",
                    line=self.lineno,
                ),
            ]
        card = _build_resource_card(
            env=self.env,
            state=self.state,
            lineno=self.lineno,
            signature_text=tpl.uri_template,
            description=tpl.description,
            docstring=tpl.docstring,
            badge_group=build_resource_badge_group(
                tpl.mime_type,
                tpl.tags,
                kind="resource-template",
            ),
            mime_type=tpl.mime_type,
            shell_class=_CSS.RESOURCE_SECTION,
            entry_class=_CSS.RESOURCE_ENTRY,
            signature_class=_CSS.RESOURCE_SIGNATURE,
            profile_name="fastmcp-resource-template",
            section_id=_component_ids("resource-template", tpl.name)[0],
            display_name=tpl.name,
            document=self.state.document,
            permalink_title="Link to this resource template",
        )
        result: list[nodes.Node] = [card]
        if tpl.parameters:
            result.extend(
                _arg_table(
                    tpl.parameters,
                    env=self.env,
                    state=self.state,
                    lineno=self.lineno,
                    heading_word="Parameters",
                ),
            )
        return result
