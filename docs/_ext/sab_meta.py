"""SAB metadata badge directive for package docs pages.

Replaces sphinx-design ``{bdg-warning-line}`Alpha``` and
``{bdg-link-secondary-line}`GitHub <url>``` roles with SAB-native
``BadgeNode`` badges so the entire badge system is unified.

Usage
-----
In any ``docs/packages/*.md`` page, replace the sphinx-design role line::

    {bdg-warning-line}`Alpha` {bdg-link-secondary-line}`GitHub <url>` …

with::

    ```{gp-sphinx-package-meta} sphinx-autodoc-api-style
    ```

The directive looks up the package's maturity, GitHub URL, and PyPI URL
from the workspace ``pyproject.toml`` data, then emits three SAB badges
as an inline paragraph.
"""

from __future__ import annotations

import typing as t

import package_reference
from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective

from sphinx_ux_badges import SAB, BadgeNode, build_badge

_MATURITY_CLASS: dict[str, str] = {
    "Alpha": SAB.META_ALPHA,
    "Beta": SAB.META_BETA,
}


def _maturity_badge(maturity: str) -> BadgeNode:
    """Return a filled maturity BadgeNode (Alpha = amber, Beta = green)."""
    colour = _MATURITY_CLASS.get(maturity, SAB.META_LINK)
    return build_badge(maturity, tooltip=f"Maturity: {maturity}", classes=[colour])


def _link_badge(label: str, url: str) -> nodes.reference:
    """Return an anchor node styled as an outline SAB badge."""
    ref = nodes.reference("", label, refuri=url, internal=False)
    # Apply badge classes directly on the anchor node so it renders as
    # <a class="gp-sphinx-badge gp-sphinx-badge--outline
    #           gp-sphinx-badge--meta-link …" href="…">label</a>
    ref["classes"].extend([SAB.BADGE, SAB.OUTLINE, SAB.META_LINK])
    return ref


def _package_meta_nodes(package_name: str) -> list[nodes.Node]:
    """Return inline badge nodes for a workspace package."""
    packages = {p["name"]: p for p in package_reference.workspace_packages()}
    pkg = packages.get(package_name)
    if pkg is None:
        msg = nodes.inline(text=f"[unknown package: {package_name!r}]")
        return [msg]

    maturity = pkg.get("maturity", "Unknown")
    repo = pkg.get("repository", "")
    github_url = repo if repo else "https://github.com/git-pull/gp-sphinx"
    pypi_url = f"https://pypi.org/project/{package_name}/"

    badge_nodes: list[nodes.Node] = [
        _maturity_badge(maturity),
        nodes.Text(" "),
        _link_badge("GitHub", github_url),
        nodes.Text(" "),
        _link_badge("PyPI", pypi_url),
    ]
    return badge_nodes


class PackageMetaBadgesDirective(SphinxDirective):
    """Emit maturity + GitHub + PyPI SAB badges for a workspace package.

    The single required argument is the distribution name as it appears in
    ``pyproject.toml``, e.g. ``sphinx-autodoc-api-style``.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0

    def run(self) -> list[nodes.Node]:
        """Build badge nodes from workspace package metadata."""
        package_name = self.arguments[0].strip()
        badge_nodes = _package_meta_nodes(package_name)
        para = nodes.paragraph()
        for n in badge_nodes:
            para += n
        return [para]


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the ``gp-sphinx-package-meta`` directive."""
    app.add_directive("gp-sphinx-package-meta", PackageMetaBadgesDirective)
    return {"version": "0.1", "parallel_read_safe": True, "parallel_write_safe": True}
