"""Sphinx configuration for the gp-sphinx-docs dogfood site.

The site documents :mod:`gp_sphinx` itself. Every workspace member is
already installed in the active uv environment, so :mod:`gp_sphinx` is
importable without ``sys.path`` adjustments.
"""

from __future__ import annotations

project = "gp-sphinx"
copyright = "2026, Tony Narlock"  # noqa: A001 — Sphinx reads this name
author = "Tony Narlock"
extensions = ["sphinx.ext.autodoc", "gp_sphinx_astro_builder"]
master_doc = "index"
exclude_patterns = ["_build"]
