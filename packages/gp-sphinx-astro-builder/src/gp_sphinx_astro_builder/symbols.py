"""Build-scoped accumulator for :class:`Symbol` records.

The translator detects entry into an ``addnodes.desc`` and starts populating
a :class:`Symbol` record. Each completed record is appended to a
:class:`SymbolAccumulator` instance shared across all documents in one
build; ``AstroBuilder.finish()`` reads the accumulator and writes the
entries to ``src/content/api/symbols.json`` as a flat array.
"""

from __future__ import annotations

import json
import typing as t

from gp_sphinx_astro_builder.models import Symbol

# autodoc's ``desc.objtype`` to the canonical SymbolKind literal. The eight
# values listed here cover what ``sphinx.ext.autodoc`` emits for the Python
# domain plus the obvious aliases (``data`` → ``attribute``).
_OBJTYPE_TO_SYMBOL_KIND: dict[str, str] = {
    "function": "function",
    "class": "class",
    "method": "method",
    "classmethod": "method",
    "staticmethod": "method",
    "attribute": "attribute",
    "data": "attribute",
    "property": "property",
    "module": "module",
}


def normalize_symbol_kind(objtype: str) -> str:
    """Return the canonical :class:`SymbolKind` value for an autodoc objtype.

    Parameters
    ----------
    objtype
        The ``desc.objtype`` attribute from autodoc.

    Returns
    -------
    str
        One of the strings allowed by :data:`SymbolKind`. Unknown objtypes
        fall through to ``"function"`` — the safest default that lets the
        build proceed without losing the symbol entirely.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.symbols import normalize_symbol_kind
    >>> normalize_symbol_kind("function")
    'function'
    >>> normalize_symbol_kind("classmethod")
    'method'
    >>> normalize_symbol_kind("data")
    'attribute'
    >>> normalize_symbol_kind("totally_unknown")
    'function'
    """
    return _OBJTYPE_TO_SYMBOL_KIND.get(objtype, "function")


class SymbolAccumulator:
    r"""Mutable container that collects :class:`Symbol` records during a build.

    One instance per builder invocation; every ``DocTreeJSONTranslator`` for
    that build shares the accumulator so symbols from every document end up
    in one flat list.

    Examples
    --------
    >>> from gp_sphinx_astro_builder.symbols import SymbolAccumulator
    >>> acc = SymbolAccumulator()
    >>> len(acc)
    0
    >>> acc.to_json() == '[]\n'
    True
    """

    def __init__(self) -> None:
        self._symbols: list[Symbol] = []

    def append(self, symbol: Symbol) -> None:
        """Append ``symbol`` to the accumulator."""
        self._symbols.append(symbol)

    def to_json(self) -> str:
        """Serialise the collected symbols as a JSON array, newline-terminated."""
        return (
            json.dumps(
                [symbol.model_dump() for symbol in self._symbols],
                indent=2,
                sort_keys=False,
            )
            + "\n"
        )

    def __len__(self) -> int:
        """Return the number of accumulated symbols."""
        return len(self._symbols)

    def __iter__(self) -> t.Iterator[Symbol]:
        """Iterate over accumulated symbols in insertion order."""
        return iter(self._symbols)
