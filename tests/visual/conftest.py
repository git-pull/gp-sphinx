"""Shared fixtures for visual regression tests.

Starts a tiny HTTP server in a background thread serving the built
docs at ``docs/_build/html`` so Playwright can drive it as a real
origin (``http://127.0.0.1:<port>``). The server is session-scoped
so the 72 baseline captures share a single process.

Visual tests are gated by the ``GP_SPHINX_VISUAL`` environment
variable (default ``py.test`` runs skip them — see test files for
the explicit ``skipif``). Reasons:

- Chromium download is ~110 MiB and may not be present on every
  developer's machine; the test would fail at ``browser.launch()``
  rather than skipping cleanly.
- A full 72-screenshot capture takes ~30s; not warranted on every
  pre-commit run.
- The baselines are captured once per pivot phase (step 9.0) and
  re-used for the regression suite (step 9.11).
"""

from __future__ import annotations

import contextlib
import http.server
import pathlib
import socket
import threading
import typing as t

import pytest


def _find_free_port() -> int:
    """Pick an unused TCP port on 127.0.0.1."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def docs_root() -> pathlib.Path:
    """Path to the built docs site (the directory containing ``index.html``)."""
    root = pathlib.Path(__file__).resolve().parents[2] / "docs" / "_build" / "html"
    if not (root / "index.html").exists():
        pytest.skip(
            f"Docs not built at {root}; run `just build-docs` before visual tests.",
        )
    return root


@pytest.fixture(scope="session")
def http_server_url(docs_root: pathlib.Path) -> t.Iterator[str]:
    """Serve ``docs_root`` over HTTP for the test session; yield the URL."""

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
            super().__init__(*args, directory=str(docs_root), **kwargs)

        def log_message(self, format: str, *args: t.Any) -> None:  # noqa: A002 — stdlib signature
            return

    port = _find_free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
