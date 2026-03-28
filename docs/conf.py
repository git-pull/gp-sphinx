"""Sphinx configuration for gp-sphinx documentation."""

from __future__ import annotations

import pathlib
import sys

# Bootstrap: allow importing local package during development
cwd = pathlib.Path(__file__).parent
project_root = cwd.parent
sys.path.insert(0, str(project_root / "src"))

import gp_sphinx  # noqa: E402
from gp_sphinx.config import merge_sphinx_config  # noqa: E402

# package data
about: dict[str, str] = {}
about["__version__"] = gp_sphinx.__version__
about["__title__"] = gp_sphinx.__title__
about["__github__"] = gp_sphinx.__github__
about["__docs__"] = gp_sphinx.__docs__
about["__copyright__"] = gp_sphinx.__copyright__

conf = merge_sphinx_config(
    project=about["__title__"],
    version=about["__version__"],
    copyright=about["__copyright__"],
    source_repository=f"{about['__github__']}/",
    source_branch="master",
    intersphinx_mapping={
        "py": ("https://docs.python.org/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    },
    # Per-project overrides
    html_extra_path=["manifest.json"],
    exclude_patterns=["_build"],
    # linkify_issues
    issue_url_tpl=f"{about['__github__']}/issues/{{issue_id}}",
    # sphinxext.opengraph
    ogp_site_url=about["__docs__"],
    ogp_site_name=about["__title__"],
)
globals().update(conf)
