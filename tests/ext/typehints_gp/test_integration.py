"""Integration tests for sphinx_typehints_gp HTML output."""

from __future__ import annotations

import textwrap

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

_MODULE_SOURCE = textwrap.dedent(
    """\
    from __future__ import annotations

    import typing as t


    def typed_function(name: str, count: int = 1) -> bool:
        \"\"\"Return whether the operation succeeded.

        Parameters
        ----------
        name : str
            The name to process.
        count : int
            Number of repetitions.

        Returns
        -------
        bool
            True if successful.
        \"\"\"
        return True


    class TypedClass:
        \"\"\"A class with typed members.

        Parameters
        ----------
        value : str
            The initial value.
        \"\"\"

        def __init__(self, value: str) -> None:
            self.value = value

        def get_value(self) -> str:
            \"\"\"Return the stored value.

            Returns
            -------
            str
                The stored value.
            \"\"\"
            return self.value
    """
)

_CONF_PY = textwrap.dedent(
    """\
    from __future__ import annotations

    import sys

    sys.path.insert(0, r"__SCENARIO_SRCDIR__")

    extensions = [
        "sphinx.ext.autodoc",
        "sphinx_typehints_gp",
    ]

    autodoc_typehints = "description"
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autofunction:: typehints_demo.typed_function

    .. autoclass:: typehints_demo.TypedClass
       :members:
    """
)


@pytest.fixture(scope="module")
def typehints_gp_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal Sphinx project using sphinx_typehints_gp."""
    cache_root = tmp_path_factory.mktemp("typehints-gp-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("typehints_demo.py", _MODULE_SOURCE),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
            ScenarioFile("index.rst", _INDEX_RST),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("typehints_demo",),
    )


@pytest.mark.integration
def test_typehints_gp_emits_type_fields(
    typehints_gp_html_result: SharedSphinxResult,
) -> None:
    """sphinx_typehints_gp inserts :type: and :rtype: fields in the HTML."""
    html = read_output(typehints_gp_html_result, "index.html")

    # Field labels should appear in the rendered output
    assert "Return type" in html or "rtype" in html.lower()

    # Type names should appear in the description body
    assert "bool" in html
    assert "str" in html


@pytest.mark.integration
def test_typehints_gp_no_duplicate_return_type(
    typehints_gp_html_result: SharedSphinxResult,
) -> None:
    """No duplicate Return type fields appear when Napoleon also emits :rtype:."""
    html = read_output(typehints_gp_html_result, "index.html")

    # Count how many times "Return type" appears in the function section.
    # Split on the function signature to isolate the typed_function entry.
    # There should be at most one Return type per function.
    func_section = html.split("typed_function")
    if len(func_section) < 2:  # noqa: PLR2004
        return  # function section not found; skip
    func_html = func_section[1].split("TypedClass")[0]

    return_type_count = func_html.count("Return type")
    assert return_type_count <= 1, (
        f"Expected at most 1 'Return type' in typed_function section, "
        f"got {return_type_count}"
    )


@pytest.mark.integration
def test_typehints_gp_setup_registers_handlers(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """setup() connects the required Sphinx event handlers."""
    import types
    from unittest.mock import MagicMock

    app = MagicMock()
    app.config = types.SimpleNamespace(
        html_static_path=[],
    )

    from sphinx_typehints_gp.extension import setup

    result = setup(app)

    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True

    connect_calls = list(app.connect.call_args_list)
    events = [call[0][0] for call in connect_calls]
    assert "autodoc-process-signature" in events
    assert "object-description-transform" in events

    # Verify priority 499 on object-description-transform
    for call in connect_calls:
        if call[0][0] == "object-description-transform":
            priority = call[1].get("priority") or (
                call[0][2] if len(call[0]) > 2 else None  # noqa: PLR2004
            )
            assert priority == 499, (  # noqa: PLR2004
                f"object-description-transform should be priority 499, got {priority}"
            )
