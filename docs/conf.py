"""Sphinx configuration for gp-sphinx documentation."""

from __future__ import annotations

import pathlib
import sys

# Bootstrap: allow importing workspace packages during development
cwd = pathlib.Path(__file__).parent
project_root = cwd.parent
sys.path.insert(0, str(project_root / "packages" / "gp-sphinx" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-fonts" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-gp-theme" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-argparse" / "src"))
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-pytest-fixtures" / "src"),
)
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-docutils" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-sphinx" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-autodoc-api-style" / "src"))
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-badges" / "src"),
)
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-fastmcp" / "src"),
)
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-layout" / "src"),
)
sys.path.insert(
    0,
    str(project_root / "packages" / "sphinx-autodoc-typehints-gp" / "src"),
)
sys.path.insert(0, str(cwd / "_ext"))  # docs demo modules

import gp_sphinx  # noqa: E402
from gp_sphinx.config import merge_sphinx_config  # noqa: E402

intersphinx_mapping = {
    "py": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

conf = merge_sphinx_config(
    project=gp_sphinx.__title__,
    version=gp_sphinx.__version__,
    copyright=gp_sphinx.__copyright__,
    source_repository=f"{gp_sphinx.__github__}/",
    docs_url=gp_sphinx.__docs__,
    source_branch="main",
    extra_extensions=[
        "package_reference",
        "sab_demo",
        "sab_meta",
        "sphinx_autodoc_badges",
        "sphinx_autodoc_api_style",
        "sphinx_autodoc_pytest_fixtures",
        "sphinx_autodoc_docutils",
        "sphinx_autodoc_fastmcp",
        "sphinx_autodoc_sphinx",
        "sphinx_autodoc_argparse.exemplar",
        "sphinx_autodoc_layout",
    ],
    fastmcp_tool_modules=["fastmcp_demo_tools"],
    fastmcp_area_map={"fastmcp_demo_tools": "packages/sphinx-autodoc-fastmcp"},
    fastmcp_collector_mode="introspect",
    api_layout_enabled=True,
    api_collapsed_threshold=10,
    pytest_fixture_lint_level="none",
    rediraffe_redirects="redirects.txt",
    intersphinx_mapping=intersphinx_mapping,
)
globals().update(conf)
