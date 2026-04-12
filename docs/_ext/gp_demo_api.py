"""Synthetic Python objects for the sphinx_autodoc_api_style badge demo page.

Each object exercises one badge combination so the demo page can show
every type and modifier badge side-by-side:

  Types:      function | class | method | property | attribute | data | exception
  Modifiers:  async | classmethod | staticmethod | abstract | final | deprecated

These definitions are purely for documentation; they are never used in
production code.
"""

from __future__ import annotations

import abc
import typing as t


def demo_function(name: str, count: int = 1) -> list[str]:
    """Plain function. Shows ``function`` type badge.

    Parameters
    ----------
    name : str
        The name to repeat.
    count : int
        Number of repetitions.

    Returns
    -------
    list[str]
        A list of repeated names.
    """
    return [name] * count


async def demo_async_function(url: str) -> bytes:
    """Asynchronous function. Shows ``async`` + ``function`` badges.

    Parameters
    ----------
    url : str
        The URL to fetch.

    Returns
    -------
    bytes
        The fetched content.
    """
    return b""


def demo_deprecated_function() -> None:
    """Do nothing (deprecated placeholder).

    Shows ``deprecated`` + ``function`` badges.

    .. deprecated:: 2.0
        Use :func:`demo_function` instead.
    """


DEMO_CONSTANT: int = 42
"""Module-level constant. Shows ``data`` type badge."""


class DemoError(Exception):
    """Custom exception class. Shows ``exception`` type badge.

    Raised when a demo operation fails unexpectedly.
    """


class DemoClass:
    """Demonstration class with various method types.

    Shows ``class`` type badge on the class itself, and per-method
    badges for each method kind.

    Parameters
    ----------
    value : str
        Initial value for the demo instance.
    """

    demo_attr: str = "hello"
    """Class attribute. Shows ``attribute`` type badge."""

    def __init__(self, value: str) -> None:
        self.value = value

    def regular_method(self, x: int) -> str:
        """Regular instance method. Shows ``method`` type badge.

        Parameters
        ----------
        x : int
            Input value.

        Returns
        -------
        str
            String representation.
        """
        return f"{self.value}:{x}"

    @classmethod
    def from_int(cls, n: int) -> DemoClass:
        """Class method. Shows ``classmethod`` + ``method`` badges.

        Parameters
        ----------
        n : int
            Integer to convert.

        Returns
        -------
        DemoClass
            A new instance.
        """
        return cls(str(n))

    @staticmethod
    def utility(a: int, b: int) -> int:
        """Add two integers. Shows ``staticmethod`` + ``method`` badges.

        Parameters
        ----------
        a : int
            First operand.
        b : int
            Second operand.

        Returns
        -------
        int
            Sum of operands.
        """
        return a + b

    @property
    def computed(self) -> str:
        """Computed property. Shows ``property`` type badge.

        Returns
        -------
        str
            The uppercased value.
        """
        return self.value.upper()

    async def async_method(self) -> None:
        """Asynchronous method. Shows ``async`` + ``method`` badges."""

    def deprecated_method(self) -> None:
        """Do nothing (deprecated placeholder).

        Shows ``deprecated`` + ``method`` badges.

        .. deprecated:: 1.5
            Use :meth:`regular_method` instead.
        """


class DemoAbstractBase(abc.ABC):
    """Abstract base class. Shows ``class`` type badge.

    Subclass this to provide concrete implementations.
    """

    @abc.abstractmethod
    def must_implement(self) -> str:
        """Abstract method. Shows ``abstract`` + ``method`` badges.

        Returns
        -------
        str
            Implementation-specific value.
        """

    @abc.abstractmethod
    async def async_abstract(self) -> None:
        """Async abstract method. Shows ``async`` + ``abstract`` + ``method`` badges."""


if t.TYPE_CHECKING:
    DemoAlias = str | int
