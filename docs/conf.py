"""Sphinx configuration for gp-sphinx documentation."""

from __future__ import annotations

import pathlib
import sys

# Bootstrap: allow importing workspace packages during development
cwd = pathlib.Path(__file__).parent
project_root = cwd.parent
sys.path.insert(0, str(project_root / "packages" / "gp-sphinx" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-fonts" / "src"))
sys.path.insert(0, str(project_root / "packages" / "sphinx-gptheme" / "src"))

import gp_sphinx  # noqa: E402
from gp_sphinx.config import merge_sphinx_config  # noqa: E402

conf = merge_sphinx_config(
    project=gp_sphinx.__title__,
    version=gp_sphinx.__version__,
    copyright=gp_sphinx.__copyright__,
    source_repository=f"{gp_sphinx.__github__}/",
    docs_url=gp_sphinx.__docs__,
    source_branch="master",
    rediraffe_redirects="redirects.txt",
    intersphinx_mapping={
        "py": ("https://docs.python.org/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    },
)
globals().update(conf)
