r"""Audit rendered Sphinx default-value strings across built docs.

Walks every ``<em class="sig-param">…</em>`` and every long
``<dt class="sig sig-object py">…</dt>`` (data/attribute) in a tree of
built HTML and classifies each occurrence.

The audit pattern matters: matching only ``class="default_value"`` spans
silently misses the cases this audit exists to find. When a default's
``repr()`` contains ``<`` (e.g.
``scope=<libtmux.constants._DefaultOptionScope object>``), Sphinx's
``ast.parse`` of the arglist fails and rendering falls back to
``_pseudo_parse_arglist``
(``sphinx/domains/python/_annotations.py:541-600``), which emits the
whole ``name=value`` as one ``desc_sig_name`` text run — no
``default_value`` span exists. Match ``<em class="sig-param">…</em>``
instead.

Usage
-----

::

    uv run python packages/sphinx-autodoc-typehints-gp/scripts/audit_defaults.py \
        ~/work/python/libtmux/docs/_build \
        ~/work/python/libvcs/docs/_build/html

Prints a per-tree summary plus an aggregate breakdown by ugliness
class. Pass ``--samples N`` to also print N example ugly defaults per
class.

The classes are:

- ``clean`` — no ``<``, no ``0x``, no `` object``; render fine.
- ``factory_sentinel`` — ``=<factory>``; from
  ``dataclasses._HAS_DEFAULT_FACTORY`` for fields declared with
  ``field(default_factory=…)`` on synthetic ``__init__``.
- ``instance_sentinel`` — ``=<some.module.Class object>``; a custom
  sentinel instance used as a default (libtmux's
  ``DEFAULT_OPTION_SCOPE`` is the canonical case).
- ``missing_sentinel`` — ``_MISSING_TYPE``-shaped repr; rare today
  because Sphinx's ``object_description`` strips memory addresses.
- ``other`` — contains ``<`` or ``0x`` but doesn't match the above.
- ``long_data_value`` — for module/class data (not parameters):
  ``<dt class="sig sig-object py">`` whose rendered text exceeds the
  --threshold (default 200 chars).
"""

from __future__ import annotations

import argparse
import collections
import html as html_module
import pathlib
import re
import sys
import typing as t

_SIG_PARAM_RE = re.compile(r'<em class="sig-param">(.*?)</em>', re.DOTALL)
_DATA_DT_RE = re.compile(
    r'<dt class="sig sig-object py[^"]*"[^>]*>(.*?)</dt>',
    re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(fragment: str) -> str:
    """Strip tags and decode entities to plain text.

    Examples
    --------
    >>> _strip_html('<span class="n"><span class="pre">x=42</span></span>')
    'x=42'
    >>> _strip_html('<span>scope=&lt;a&gt;</span>')
    'scope=<a>'
    """
    text = _TAG_RE.sub("", fragment)
    text = html_module.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def classify_param(text: str) -> str:
    """Classify a sig-param text run by ugliness category.

    Examples
    --------
    >>> classify_param("count=1")
    'clean'
    >>> classify_param("alert_bell=<factory>")
    'factory_sentinel'
    >>> classify_param("scope=<libtmux.constants._DefaultOptionScope object>")
    'instance_sentinel'
    >>> classify_param("x=<dataclasses._MISSING_TYPE object>")
    'missing_sentinel'
    """
    if "=" not in text:
        return "clean"
    if "=<factory>" in text:
        return "factory_sentinel"
    if "_MISSING_TYPE" in text or "_MISSING " in text:
        return "missing_sentinel"
    if " object" in text and "<" in text:
        return "instance_sentinel"
    if "<" in text or "0x" in text:
        return "other"
    return "clean"


class _ParamRow(t.NamedTuple):
    repo: str
    page: str
    text: str
    cls: str


class _DataRow(t.NamedTuple):
    repo: str
    page: str
    qualname: str
    char_count: int


def _audit_tree(
    label: str,
    root: pathlib.Path,
    *,
    long_threshold: int,
) -> tuple[list[_ParamRow], list[_DataRow]]:
    """Walk *root* and return parameter and data audit rows."""
    params: list[_ParamRow] = []
    data: list[_DataRow] = []
    for path in root.rglob("*.html"):
        try:
            html = path.read_text(encoding="utf-8")
        except OSError:
            continue
        page = str(path.relative_to(root))
        for fragment in _SIG_PARAM_RE.findall(html):
            text = _strip_html(fragment)
            if "=" not in text:
                continue
            params.append(_ParamRow(label, page, text, classify_param(text)))
        for fragment in _DATA_DT_RE.findall(html):
            text = _strip_html(fragment)
            if len(text) <= long_threshold:
                continue
            head = text.split("=", 1)[0].strip()
            data.append(_DataRow(label, page, head, len(text)))
    return params, data


def _summary(rows: list[_ParamRow]) -> dict[str, int]:
    """Return a class -> count mapping for the given rows."""
    counts: collections.Counter[str] = collections.Counter()
    for row in rows:
        counts[row.cls] += 1
    return dict(counts)


def _report(
    trees: list[tuple[str, pathlib.Path]],
    *,
    long_threshold: int,
    samples_per_class: int,
) -> int:
    """Run the audit across all *trees* and print a summary report."""
    grand_params: list[_ParamRow] = []
    grand_data: list[_DataRow] = []
    for label, root in trees:
        params, data = _audit_tree(label, root, long_threshold=long_threshold)
        grand_params.extend(params)
        grand_data.extend(data)
        summary = _summary(params)
        ugly = sum(v for k, v in summary.items() if k != "clean")
        print(f"=== {label} ({root}) ===")
        print(f"  sig-params with defaults: {len(params)}")
        print(f"  ugly: {ugly}  ({summary})")
        print(f"  long data values (>{long_threshold} chars): {len(data)}")

    print()
    print("=== aggregate ===")
    print(f"  total sig-params: {len(grand_params)}")
    print(f"  ugly: {_summary(grand_params)}")
    print(f"  long data values: {len(grand_data)}")

    if samples_per_class:
        by_cls: dict[str, list[_ParamRow]] = collections.defaultdict(list)
        for row in grand_params:
            if row.cls != "clean" and len(by_cls[row.cls]) < samples_per_class:
                by_cls[row.cls].append(row)
        print()
        print("=== samples ===")
        for cls, rows in sorted(by_cls.items()):
            print(f"-- {cls} --")
            for row in rows:
                print(f"  [{row.repo}] {row.page} :: {row.text!r}")

    return 0


def main(argv: list[str]) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "trees",
        nargs="+",
        help="Pairs of LABEL=PATH or just PATH (label inferred from basename).",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=200,
        help="Char-count threshold for long_data_value (default: 200).",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=0,
        help="Print up to N sample ugly defaults per class.",
    )
    args = parser.parse_args(argv)

    trees: list[tuple[str, pathlib.Path]] = []
    for spec in args.trees:
        if "=" in spec:
            label, _, raw_path = spec.partition("=")
            path = pathlib.Path(raw_path)
        else:
            path = pathlib.Path(spec)
            label = path.parent.name or str(path)
        trees.append((label, path))
    return _report(
        trees,
        long_threshold=args.threshold,
        samples_per_class=args.samples,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
