"""Octicon rendering primitives.

Loads bundled octicon data and renders inline SVG fragments under the
``gp-sphinx-octicon`` CSS namespace. ``render_octicon`` is independent of
Sphinx so callers may use it directly from other extensions or tests.

Examples
--------
>>> svg = render_octicon("rocket")
>>> svg.startswith("<svg ")
True
>>> 'class="gp-sphinx-octicon gp-sphinx-octicon--rocket"' in svg
True
"""

from __future__ import annotations

import functools
import importlib.resources
import json
import re
import typing as t

if t.TYPE_CHECKING:
    from collections.abc import Sequence

_HEIGHT_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>px|em|rem)$")


@functools.lru_cache(maxsize=1)
def load_octicons() -> dict[str, dict[str, t.Any]]:
    """Return the bundled octicon registry.

    Returns
    -------
    dict[str, dict[str, Any]]
        Mapping of icon name to ``{"width": int, "height": int, "path": str}``.

    Examples
    --------
    >>> data = load_octicons()
    >>> "rocket" in data
    True
    >>> sorted(data["rocket"].keys())
    ['height', 'path', 'width']
    """
    data_pkg = importlib.resources.files(__package__).joinpath("_data")
    raw = data_pkg.joinpath("octicons.json").read_text(encoding="utf-8")
    parsed: dict[str, dict[str, t.Any]] = json.loads(raw)
    return parsed


def render_octicon(
    name: str,
    *,
    height: str = "1em",
    classes: Sequence[str] = (),
) -> str:
    """Render an octicon as an inline SVG string.

    Parameters
    ----------
    name : str
        Icon name, e.g. ``"rocket"``.
    height : str, optional
        CSS length with a ``px``, ``em``, or ``rem`` unit (default ``"1em"``).
        The matching width is derived from the icon's aspect ratio.
    classes : Sequence[str], optional
        Additional CSS classes appended after the base
        ``gp-sphinx-octicon gp-sphinx-octicon--<name>`` pair.

    Returns
    -------
    str
        Inline SVG markup ready for embedding in HTML output.

    Raises
    ------
    KeyError
        If ``name`` is not a bundled icon.
    ValueError
        If ``height`` does not match ``<number><px|em|rem>``.

    Examples
    --------
    >>> svg = render_octicon("rocket", height="24px")
    >>> 'width="24.0px"' in svg
    True
    >>> 'height="24.0px"' in svg
    True
    """
    registry = load_octicons()
    if name not in registry:
        raise KeyError(name)
    entry = registry[name]

    match = _HEIGHT_RE.match(height)
    if match is None:
        msg = f"invalid height {height!r}; expected <number><px|em|rem>"
        raise ValueError(msg)
    value = round(float(match.group("value")), 3)
    unit = match.group("unit")

    original_width = int(entry["width"])
    original_height = int(entry["height"])
    width_value = round(original_width * value / original_height, 3)
    path = str(entry["path"])

    class_value = " ".join(
        ("gp-sphinx-octicon", f"gp-sphinx-octicon--{name}", *classes),
    ).strip()
    attrs = {
        "xmlns": "http://www.w3.org/2000/svg",
        "viewBox": f"0 0 {original_width} {original_height}",
        "width": f"{width_value}{unit}",
        "height": f"{value}{unit}",
        "class": class_value,
        "aria-hidden": "true",
    }
    attr_string = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<svg {attr_string}>{path}</svg>"
