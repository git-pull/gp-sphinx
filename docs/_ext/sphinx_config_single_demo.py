"""Single-value config registration for the autoconfigvalue demo.

Examples
--------
>>> stub = type("App", (), {"add_config_value": lambda *a, **kw: None})()
>>> metadata = setup(stub)
>>> metadata["parallel_write_safe"]
True
"""

from __future__ import annotations

import typing as t


def setup(app: t.Any) -> dict[str, object]:
    """Register one config value for single-entry rendering demos."""
    app.add_config_value(
        "demo_debug",
        False,
        "env",
        types=[bool],
    )
    return {
        "version": "0.0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
