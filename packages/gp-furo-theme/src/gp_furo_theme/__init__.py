"""gp-furo-theme — Tailwind-v4-driven port of the Furo Sphinx theme.

Owns templates, styles, and scripts that previously came from the upstream
``furo`` package. Asset values track Furo at the pinned commit recorded in
``packages/gp-furo-tokens/upstream/furo-vars.json``; templates carry per-file
attribution headers; the LICENSE-FURO file at the package root reproduces
upstream's MIT license.

The package ships a ``setup()`` callable that registers the theme name
``gp-furo`` against Sphinx via ``app.add_html_theme``. Subsequent
implementation steps land:

- Jinja templates ported from upstream Furo
- Asset hooks (``_html_page_context``, ``_builder_inited``,
  ``_overwrite_pygments_css``, ``_asset_hash``) ported from
  ``furo/__init__.py``
- ``WrapTableAndMathInAContainerTransform`` post-transform

Examples
--------
>>> theme_path = get_theme_path()
>>> theme_path.is_dir()
True

>>> (theme_path / "theme.conf").is_file()
True
"""

from __future__ import annotations

import pathlib
import typing as t

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

__version__ = "0.0.1a12"

THEME_NAME = "gp-furo"


def get_theme_path() -> pathlib.Path:
    """Return the absolute path to the bundled ``gp-furo`` theme directory.

    Returns
    -------
    pathlib.Path
        Directory containing ``theme.conf`` and the (eventually) ported
        Jinja templates and Vite-built assets.

    Examples
    --------
    >>> theme_path = get_theme_path()
    >>> (theme_path / "theme.conf").exists()
    True
    """
    return pathlib.Path(__file__).parent / "theme" / THEME_NAME


def setup(app: Sphinx) -> dict[str, bool | str]:
    """Register the ``gp-furo`` theme with Sphinx.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    dict[str, bool | str]
        Extension metadata: ``parallel_read_safe`` and
        ``parallel_write_safe`` are both ``True`` (matching upstream Furo's
        guarantees), and ``version`` reports the package version.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.themes: list[tuple[str, pathlib.Path]] = []
    ...     def add_html_theme(self, name: str, theme_path: pathlib.Path) -> None:
    ...         self.themes.append((name, theme_path))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> fake.themes[0][0]
    'gp-furo'
    >>> metadata["parallel_read_safe"]
    True
    """
    app.add_html_theme(THEME_NAME, get_theme_path())
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": __version__,
    }
