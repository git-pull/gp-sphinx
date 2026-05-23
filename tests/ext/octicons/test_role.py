"""Role-level coverage for ``OcticonRole``.

Instead of standing up a Sphinx app, these tests wire ``OcticonRole``
against a minimal stub inliner so the three role syntaxes
(``name``, ``name;height``, ``name;height;classes``) and the error path
can be exercised in microseconds.
"""

from __future__ import annotations

import types
import typing as t

from docutils import nodes

from sphinx_ux_octicons._nodes import OcticonNode
from sphinx_ux_octicons._role import OcticonRole


class _StubReporter:
    """Capture reported errors and provide stable source/line tuples."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str, *, line: int | None = None) -> nodes.system_message:
        self.errors.append(message)
        return nodes.system_message(message, type="ERROR", level=3, line=line or 0)

    def get_source_and_line(self, lineno: int | None = None) -> tuple[str, int]:
        return ("<stub>", lineno or 0)


class _StubInliner:
    """Mimic the ``docutils`` ``Inliner`` surface used by ``SphinxRole``."""

    def __init__(self) -> None:
        self.reporter = _StubReporter()

    def problematic(
        self,
        rawtext: str,
        text: str,
        message: nodes.system_message,
    ) -> nodes.problematic:
        return nodes.problematic(rawtext, text)


def _make_role(text: str) -> OcticonRole:
    role = OcticonRole()
    role.name = "octicon"
    role.rawtext = f"`{text}`"
    role.text = text
    role.lineno = 1
    role.inliner = t.cast(t.Any, _StubInliner())
    role.options = {}
    role.content = ()
    return role


def test_role_name_only_produces_octicon_node() -> None:
    """``{octicon}`rocket`` emits an :class:`OcticonNode` carrying the SVG."""
    role = _make_role("rocket")
    out, messages = role.run()
    assert messages == []
    assert len(out) == 1
    node = out[0]
    assert isinstance(node, OcticonNode)
    svg = node["svg_markup"]
    assert svg.startswith("<svg ")
    assert "gp-sphinx-octicon--rocket" in svg
    # The name surrogate is carried as a Text child for non-HTML builders.
    assert node.astext() == "rocket"


def test_role_name_and_height() -> None:
    """``name;height`` propagates the height through to the rendered SVG."""
    role = _make_role("rocket;24px")
    out, messages = role.run()
    assert messages == []
    node = out[0]
    assert isinstance(node, OcticonNode)
    svg = node["svg_markup"]
    assert 'height="24.0px"' in svg
    assert 'width="24.0px"' in svg


def test_role_name_height_and_classes() -> None:
    """``name;height;classes`` appends extra classes after the namespace pair."""
    role = _make_role("rocket;1em;my-class other-class")
    out, _ = role.run()
    node = out[0]
    assert isinstance(node, OcticonNode)
    svg = node["svg_markup"]
    assert (
        'class="gp-sphinx-octicon gp-sphinx-octicon--rocket my-class other-class"'
        in svg
    )


def test_role_unknown_icon_reports_error() -> None:
    """Unknown icons report a docutils system message and emit a problematic node."""
    role = _make_role("nope")
    out, messages = role.run()
    assert len(messages) == 1
    assert len(out) == 1
    assert isinstance(out[0], nodes.problematic)
    assert "nope" in role.inliner.reporter.errors[0]  # type: ignore[attr-defined]


def test_role_invalid_height_reports_error() -> None:
    """Invalid height strings surface as system messages, not raises."""
    role = _make_role("rocket;1")
    out, messages = role.run()
    assert len(messages) == 1
    assert isinstance(out[0], nodes.problematic)


def test_role_empty_height_falls_back_to_default() -> None:
    """An empty height segment falls back to the ``1em`` default."""
    role = _make_role("rocket;")
    out, messages = role.run()
    assert messages == []
    node = out[0]
    assert isinstance(node, OcticonNode)
    svg = node["svg_markup"]
    assert 'height="1.0em"' in svg


def test_role_set_source_info_uses_inliner_reporter() -> None:
    """``set_source_info`` populates ``node.source`` / ``node.line``."""

    class _SourceInliner(_StubInliner):
        pass

    role = OcticonRole()
    role.name = "octicon"
    role.rawtext = "`rocket`"
    role.text = "rocket"
    role.lineno = 42
    role.inliner = t.cast(t.Any, _SourceInliner())
    # SphinxRole.set_source_info reads inliner.document.settings.env for env
    # access; we never trigger env access here so a placeholder is enough.
    role.inliner.document = t.cast(t.Any, types.SimpleNamespace())
    role.options = {}
    role.content = ()

    out, _ = role.run()
    node = out[0]
    assert node.line == 42
    assert node.source == "<stub>"
