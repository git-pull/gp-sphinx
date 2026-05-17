#!/usr/bin/env python3
"""Refresh the bundled ``octicons.json`` from an upstream @primer/octicons checkout.

Reads ``_data/octicons_curated.txt`` for the audited icon list, locates the
upstream SVG for each name in either an installed ``@primer/octicons`` npm
package (``node_modules/@primer/octicons/build/svg``) or a local clone at
``~/study/octicons/icons``, parses out the ``<path …/>`` payload of the
16px variant, and writes the result to ``_data/octicons.json`` in this
package.

This script is a maintainer one-shot — consumers install the bundled
``octicons.json`` directly from the wheel and never invoke it.

Usage
-----

::

    $ python scripts/sync_octicons.py                # auto-detect
    $ python scripts/sync_octicons.py /path/to/svgs  # explicit source
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_PKG_ROOT = _HERE.parent
_DATA_DIR = _PKG_ROOT / "src" / "sphinx_ux_octicons" / "_data"
_CURATED = _DATA_DIR / "octicons_curated.txt"
_OUTPUT = _DATA_DIR / "octicons.json"

_SVG_PATH_RE = re.compile(r"(<path\s[^/]*?/>)", re.DOTALL)
_SVG_WIDTH_RE = re.compile(r'width="(\d+)"')
_SVG_HEIGHT_RE = re.compile(r'height="(\d+)"')


def _candidate_roots() -> list[pathlib.Path]:
    npm_relative = pathlib.Path("node_modules/@primer/octicons/build/svg")
    return [
        pathlib.Path.home() / "study" / "octicons" / "icons",
        _PKG_ROOT.parents[2] / npm_relative,
        pathlib.Path.cwd() / npm_relative,
    ]


def _resolve_root(explicit: str | None) -> pathlib.Path:
    if explicit is not None:
        root = pathlib.Path(explicit).expanduser().resolve()
        if not root.is_dir():
            msg = f"source path is not a directory: {root}"
            raise SystemExit(msg)
        return root
    for candidate in _candidate_roots():
        if candidate.is_dir():
            return candidate
    candidates_text = "\n  ".join(str(c) for c in _candidate_roots())
    msg = (
        "could not locate upstream @primer/octicons SVGs. Install them with:\n"
        "  npm install @primer/octicons\n"
        "or clone https://github.com/primer/octicons to ~/study/octicons,\n"
        f"or pass the SVG directory explicitly. Tried:\n  {candidates_text}"
    )
    raise SystemExit(msg)


def _read_curated() -> list[str]:
    text = _CURATED.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_svg(svg_text: str) -> dict[str, int | str]:
    width_match = _SVG_WIDTH_RE.search(svg_text)
    height_match = _SVG_HEIGHT_RE.search(svg_text)
    path_match = _SVG_PATH_RE.search(svg_text)
    if width_match is None or height_match is None or path_match is None:
        msg = "could not parse width/height/path from SVG"
        raise ValueError(msg)
    return {
        "width": int(width_match.group(1)),
        "height": int(height_match.group(1)),
        "path": path_match.group(1),
    }


def _build(root: pathlib.Path, names: list[str]) -> dict[str, dict[str, int | str]]:
    out: dict[str, dict[str, int | str]] = {}
    missing: list[str] = []
    for name in names:
        svg_file = root / f"{name}-16.svg"
        if not svg_file.is_file():
            missing.append(name)
            continue
        out[name] = _parse_svg(svg_file.read_text(encoding="utf-8"))
    if missing:
        msg = f"missing 16px SVGs under {root}: {', '.join(missing)}"
        raise SystemExit(msg)
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    """Entry point for the sync script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to the @primer/octicons build/svg directory.",
    )
    args = parser.parse_args(argv)
    root = _resolve_root(args.source)
    names = _read_curated()
    payload = _build(root, names)
    _OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    sys.stdout.write(f"wrote {len(payload)} icons to {_OUTPUT}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
