"""gp-sphinx Furo child theme.

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


def get_theme_path() -> pathlib.Path:
    """Return the path to the gp-sphinx theme directory.

    Returns
    -------
    pathlib.Path
        Absolute path to the ``gp-sphinx/`` theme directory containing
        ``theme.conf`` and associated templates/static files.

    Examples
    --------
    >>> theme_path = get_theme_path()
    >>> (theme_path / "theme.conf").exists()
    True

    >>> (theme_path / "static" / "css" / "custom.css").exists()
    True
    """
    return pathlib.Path(__file__).parent / "gp-sphinx"
