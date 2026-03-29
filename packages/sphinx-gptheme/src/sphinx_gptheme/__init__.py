"""sphinx-gptheme — Furo child theme for git-pull projects.

Provides a shared visual identity for git-pull project documentation
by inheriting from Furo and bundling common templates, CSS, and JS.

Examples
--------
>>> import pathlib

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

__version__ = "0.0.1a0"


def get_theme_path() -> pathlib.Path:
    """Return the path to the sphinx-gptheme theme directory.

    Returns
    -------
    pathlib.Path
        Absolute path to the theme directory containing
        ``theme.conf`` and associated templates/static files.

    Examples
    --------
    >>> theme_path = get_theme_path()
    >>> (theme_path / "theme.conf").exists()
    True

    >>> (theme_path / "static" / "css" / "custom.css").exists()
    True
    """
    return pathlib.Path(__file__).parent / "theme"


def setup(app: Sphinx) -> dict[str, bool | str]:
    """Register the bundled theme with Sphinx.

    Parameters
    ----------
    app : Sphinx
        The Sphinx application object.

    Returns
    -------
    dict[str, bool | str]
        Extension metadata for Sphinx.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.calls: list[tuple[str, pathlib.Path]] = []
    ...     def add_html_theme(self, name: str, theme_path: pathlib.Path) -> None:
    ...         self.calls.append((name, theme_path))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> fake.calls[0][0]
    'sphinx-gptheme'
    >>> metadata["parallel_read_safe"]
    True
    """
    app.add_html_theme("sphinx-gptheme", get_theme_path())
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": __version__,
    }
