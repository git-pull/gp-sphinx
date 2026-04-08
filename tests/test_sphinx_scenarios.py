"""Tests for typed Sphinx scenario caching helpers."""

from __future__ import annotations

import pathlib
import textwrap

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SphinxScenario,
    build_shared_sphinx_result,
    copy_scenario_tree,
    derive_sphinx_scenario_cache_root,
)


def _make_demo_scenario(
    *,
    index_title: str = "Demo",
) -> SphinxScenario:
    """Return a small Sphinx scenario for cache helper tests."""
    conf_py = textwrap.dedent(
        f"""\
        from __future__ import annotations

        import sys

        sys.path.insert(0, "{SCENARIO_SRCDIR_TOKEN}")

        extensions = ["sphinx.ext.autodoc"]
        master_doc = "index"
        exclude_patterns = ["_build"]
        html_theme = "alabaster"
        """,
    )
    module_source = textwrap.dedent(
        """\
        from __future__ import annotations


        def demo() -> str:
            \"\"\"Return a demo value.\"\"\"
            return "demo"
        """,
    )
    index_rst = textwrap.dedent(
        f"""\
        {index_title}
        {"=" * len(index_title)}

        .. automodule:: demo_module
           :members:
        """,
    )
    return SphinxScenario(
        files=(
            ScenarioFile("demo_module.py", module_source),
            ScenarioFile("conf.py", conf_py, substitute_srcdir=True),
            ScenarioFile("index.rst", index_rst),
        ),
    )


def test_shared_sphinx_result_reuses_identical_builds(tmp_path: pathlib.Path) -> None:
    """Reuse the same completed build for identical scenarios."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = _make_demo_scenario()

    result_one = build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("demo_module",),
    )
    result_two = build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("demo_module",),
    )

    assert result_one is result_two
    assert (result_one.outdir / "index.html").exists()


def test_sphinx_scenario_key_changes_when_inputs_change() -> None:
    """Change the cache digest when scenario inputs differ."""
    scenario_one = _make_demo_scenario(index_title="Demo")
    scenario_two = _make_demo_scenario(index_title="Demo Two")

    assert scenario_one.cache_key().digest() != scenario_two.cache_key().digest()


def test_copy_scenario_tree_keeps_cached_source_pristine(
    tmp_path: pathlib.Path,
) -> None:
    """Keep the cached source tree unchanged when copied trees are mutated."""
    cache_root = derive_sphinx_scenario_cache_root(tmp_path)
    scenario = _make_demo_scenario()
    digest = scenario.cache_key().digest()

    first_copy = copy_scenario_tree(cache_root, scenario, tmp_path / "copy-one")
    mutated_module = first_copy / "demo_module.py"
    mutated_module.write_text(
        mutated_module.read_text(encoding="utf-8") + "\nMUTATED = True\n",
        encoding="utf-8",
    )

    second_copy = copy_scenario_tree(cache_root, scenario, tmp_path / "copy-two")
    cached_module = cache_root / f"{digest}-source" / "demo_module.py"

    assert "MUTATED = True" not in second_copy.joinpath("demo_module.py").read_text(
        encoding="utf-8",
    )
    assert "MUTATED = True" not in cached_module.read_text(encoding="utf-8")
