"""Conftest.py for the docs tree's doctest collection.

``fastmcp`` is a dev dependency on Python 3.11+ only, so the demo server that
imports it cannot be collected without it.
"""

from __future__ import annotations

import importlib.util

collect_ignore: list[str] = []

if importlib.util.find_spec("fastmcp") is None:
    collect_ignore.append("_ext/fastmcp_demo_server.py")
