"""Regenerate the committed example SVGs from the ``src/*.mmd`` sources.

Every source is rendered through sphinx-gp-mermaid's own pipeline — the
furo light/dark palette, the ``mmdc`` subprocess, and the same
``_normalize_svg`` id/size rewriting the extension applies at build time —
so ``rendered/<name>.<theme>.svg`` is exactly what a diagram of that source
looks like on a gp-sphinx site.

Requires a local mermaid-cli (a headless Chrome from the puppeteer cache is
discovered automatically)::

    pnpm install --ignore-workspace --dir packages/sphinx-gp-mermaid/examples

Then, from anywhere in the repo::

    uv run python packages/sphinx-gp-mermaid/examples/generate.py
"""

from __future__ import annotations

import json
import pathlib
import types
import typing as t

import sphinx_gp_mermaid as sgm

_HERE = pathlib.Path(__file__).parent
_SRC = _HERE / "src"
_RENDERED = _HERE / "rendered"
_MMDC = _HERE / "node_modules" / ".bin" / "mmdc"

_THEMES = (sgm._THEME_LIGHT, sgm._THEME_DARK)


def _fake_app() -> t.Any:
    """Return the minimal Sphinx-like object ``_render`` needs.

    Typed ``Any`` because it only duck-types the handful of ``app`` attributes
    the renderer reads (``confdir``, ``config.mermaid_cmd``,
    ``config.mermaid_puppeteer_config``), not the full Sphinx surface.
    """
    return types.SimpleNamespace(
        confdir=str(_HERE),
        config=types.SimpleNamespace(
            mermaid_cmd=str(_MMDC),
            mermaid_puppeteer_config="",
        ),
    )


def _render_example(app: t.Any, source: str, theme: str) -> str:
    """Render one source in one theme to a normalized, furo-palette SVG."""
    config_json = json.dumps(sgm._mermaid_config(theme), sort_keys=True)
    raw = sgm._render(app, source, config_json)
    digest = sgm._diagram_digest(source, "")
    return sgm._normalize_svg(raw, svg_id=sgm._svg_element_id(digest, theme))


def main() -> int:
    """Render every ``src/*.mmd`` to dual-theme SVGs; return an exit status."""
    if not _MMDC.exists():
        missing = (
            f"mmdc not found at {_MMDC}; install it first:\n"
            "  pnpm install --ignore-workspace "
            "--dir packages/sphinx-gp-mermaid/examples"
        )
        raise SystemExit(missing)
    sources = sorted(_SRC.glob("*.mmd"))
    if not sources:
        empty = f"no .mmd sources under {_SRC}"
        raise SystemExit(empty)
    _RENDERED.mkdir(exist_ok=True)
    app = _fake_app()
    failures: list[str] = []
    for src in sources:
        source = src.read_text(encoding="utf-8")
        for theme in _THEMES:
            try:
                svg = _render_example(app, source, theme)
            except sgm.MermaidError as exc:
                failures.append(f"{src.name} [{theme}]: {exc}")
                continue
            out = _RENDERED / f"{src.stem}.{theme}.svg"
            out.write_text(svg, encoding="utf-8")
            print(f"  wrote {out.relative_to(_HERE)}")
    if failures:
        print("\nfailures:")
        for line in failures:
            print(f"  {line}")
        return 1
    print(f"\nrendered {len(sources)} diagrams x {len(_THEMES)} themes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
