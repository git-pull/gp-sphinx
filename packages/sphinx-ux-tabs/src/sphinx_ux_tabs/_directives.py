"""Directive implementations for ``tab``, ``tab-set``, and ``tab-item``.

The package ships three directives:

* :class:`TabDirective` — sphinx-inline-tabs-compatible ``.. tab::``
  with an optional ``:new-set:`` flag.  Emits a transient
  :class:`~sphinx_ux_tabs._nodes.TabContainer` that the post-transform
  grouping pass folds into a :class:`TabSetNode`.
* :class:`TabSetDirective` — sphinx-design-compatible ``.. tab-set::``.
  Parses its children, validates that each is a :class:`TabItemNode`,
  and emits a :class:`TabSetNode` directly (skipping the grouping pass).
* :class:`TabItemDirective` — sphinx-design-compatible ``.. tab-item::``
  with ``:selected:``, ``:sync:``, ``:name:``, and ``:class-*:`` options.

Examples
--------
>>> TabDirective.has_content
True

>>> TabSetDirective.has_content
True

>>> TabItemDirective.required_arguments
1
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger

from sphinx_ux_tabs._css import SUT
from sphinx_ux_tabs._nodes import (
    TabContainer,
    TabItemNode,
    TabSetNode,
)

_LOGGER = getLogger(__name__)
_WARNING_TYPE = "gp-sphinx-tabs"


class TabDirective(SphinxDirective):
    """The ``.. tab::`` directive — sphinx-inline-tabs compatible.

    The argument is the tab label (may contain inline markup).  The
    content is the tab's body.  ``:new-set:`` forces the post-transform
    to break a tab-set run at this directive — useful when two tab
    groups would otherwise be glued together by the grouping pass.

    Examples
    --------
    >>> TabDirective.has_content
    True

    >>> TabDirective.required_arguments
    1
    """

    required_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec: t.ClassVar[dict[str, t.Callable[..., t.Any]]] = {
        "new-set": directives.flag,
        "selected": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        """Build a :class:`TabContainer` from the directive arguments.

        Examples
        --------
        >>> TabDirective.run.__qualname__
        'TabDirective.run'
        """
        self.assert_has_content()
        container = TabContainer(
            new_set="new-set" in self.options,
            selected="selected" in self.options,
        )
        self.set_source_info(container)

        # Label — preserve inline markup the author wrote.
        textnodes, _messages = self.state.inline_text(self.arguments[0], self.lineno)
        label = nodes.label("", "", *textnodes)
        container += label

        # Panel body — nested-parsed into a plain container.
        panel = nodes.container("", is_div=True)
        self.state.nested_parse(self.content, self.content_offset, panel)
        container += panel

        return [container]


class TabSetDirective(SphinxDirective):
    """The ``.. tab-set::`` directive — sphinx-design compatible.

    Wraps a sequence of ``.. tab-item::`` children in a
    :class:`TabSetNode`.  Children that are not :class:`TabItemNode` are
    dropped with a warning (matching sphinx-design's behavior).

    Examples
    --------
    >>> TabSetDirective.has_content
    True
    """

    has_content = True
    option_spec: t.ClassVar[dict[str, t.Callable[..., t.Any]]] = {
        "sync-group": directives.unchanged_required,
        "class": directives.class_option,
    }

    def run(self) -> list[nodes.Node]:
        """Build a :class:`TabSetNode` from the directive content.

        Examples
        --------
        >>> TabSetDirective.run.__qualname__
        'TabSetDirective.run'
        """
        self.assert_has_content()
        tab_set = TabSetNode(classes=list(self.options.get("class", [])))
        self.set_source_info(tab_set)
        self.state.nested_parse(self.content, self.content_offset, tab_set)

        sync_group = self.options.get("sync-group", "tab")
        valid_children: list[nodes.Node] = []
        for child in tab_set.children:
            if not isinstance(child, TabItemNode):
                _LOGGER.warning(
                    "all children of a 'tab-set' should be 'tab-item' [%s.tab]",
                    _WARNING_TYPE,
                    location=child,
                    type=_WARNING_TYPE,
                    subtype="tab",
                )
                continue
            # If the child carries a sync_id, surface the resolved sync-group.
            if child.get("sync_id"):
                child["sync_group"] = sync_group
            valid_children.append(child)
        tab_set.children = valid_children
        return [tab_set]


class TabItemDirective(SphinxDirective):
    """The ``.. tab-item::`` directive — sphinx-design compatible.

    Parses its argument (the tab label) and content (the tab body) into
    a :class:`TabItemNode`.  Options:

    * ``:selected:`` — flag; marks this tab as the initially-checked
      radio of its enclosing set.
    * ``:sync:`` — string; opt-in cross-set synchronisation key.  Two
      labels in different sets sharing the same ``:sync:`` value will
      stay in lockstep (the bundled JS handles this at runtime).
    * ``:name:`` — passed through to ``add_name`` so the tab is
      cross-referenceable.
    * ``:class-container:`` / ``:class-label:`` / ``:class-content:`` —
      extra CSS classes for the panel container, the label, and the
      content nodes respectively.

    Examples
    --------
    >>> TabItemDirective.required_arguments
    1

    >>> TabItemDirective.has_content
    True
    """

    required_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec: t.ClassVar[dict[str, t.Callable[..., t.Any]]] = {
        "selected": directives.flag,
        "sync": directives.unchanged_required,
        "name": directives.unchanged,
        "class-container": directives.class_option,
        "class-label": directives.class_option,
        "class-content": directives.class_option,
    }

    def run(self) -> list[nodes.Node]:
        """Build a :class:`TabItemNode` from the directive arguments.

        Examples
        --------
        >>> TabItemDirective.run.__qualname__
        'TabItemDirective.run'
        """
        self.assert_has_content()
        item = TabItemNode(
            selected="selected" in self.options,
            sync_id=self.options.get("sync", ""),
            class_container=list(self.options.get("class-container", [])),
        )
        self.set_source_info(item)

        # Label — preserve inline markup the author wrote.
        textnodes, _messages = self.state.inline_text(self.arguments[0], self.lineno)
        label = nodes.label("", "", *textnodes)
        for extra_class in self.options.get("class-label", []):
            if extra_class and extra_class not in label["classes"]:
                label["classes"].append(extra_class)
        self.add_name(label)
        item += label

        # Panel content.
        panel = nodes.container("", is_div=True)
        for extra_class in self.options.get("class-content", []):
            if extra_class and extra_class not in panel["classes"]:
                panel["classes"].append(extra_class)
        # The expansion pass tags the panel with SUT.PANEL — anticipate it
        # here so other passes (and unit tests) see the same shape.
        if SUT.PANEL not in panel["classes"]:
            panel["classes"].append(SUT.PANEL)
        self.state.nested_parse(self.content, self.content_offset, panel)
        item += panel

        return [item]


__all__ = [
    "TabDirective",
    "TabItemDirective",
    "TabSetDirective",
]
