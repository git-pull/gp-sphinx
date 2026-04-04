"""Synthetic config registrations for live autodoc-sphinx demos.

Examples
--------
>>> stub = type("App", (), {"add_config_value": lambda *a, **kw: None})()
>>> metadata = setup(stub)
>>> metadata["parallel_read_safe"]
True
"""

from __future__ import annotations

import typing as t


def setup(app: t.Any) -> dict[str, object]:
    """Register a small config surface for documentation demos."""
    app.add_config_value(
        "demo_theme_accent",
        {"light": "mint", "dark": "teal"},
        "html",
        types=[dict],
    )
    app.add_config_value(
        "demo_show_callouts",
        True,
        "html",
        types=[bool],
    )
    return {
        "version": "0.0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
