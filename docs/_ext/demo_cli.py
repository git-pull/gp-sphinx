"""Synthetic argparse parser factory used by the docs site.

Examples
--------
>>> parser = create_parser()
>>> parser.prog
'myapp'
>>> parser.parse_args(["mysubcommand", "--output", "dist"]).output
'dist'
"""

from __future__ import annotations

import argparse


def create_parser() -> argparse.ArgumentParser:
    """Return a parser that exercises the extension's rendering features.

    Examples
    --------
    >>> parser = create_parser()
    >>> parser.prog
    'myapp'
    """
    parser = argparse.ArgumentParser(
        prog="myapp",
        description="Example CLI showing how sphinx-argparse-neo renders parsers.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )
    parser.add_argument(
        "--config",
        default="pyproject.toml",
        metavar="PATH",
        help="Path to configuration file.",
    )

    subparsers = parser.add_subparsers(dest="command")

    sub1 = subparsers.add_parser(
        "mysubcommand",
        help="Run the primary task.",
        description="Execute the primary task with configurable output.",
    )
    sub1.add_argument(
        "--output",
        "-o",
        default="build",
        metavar="DIR",
        help="Output directory.",
    )
    sub1.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    sub1.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous output first.",
    )

    sub2 = subparsers.add_parser(
        "myothersubcommand",
        help="Run a secondary task.",
        description="Execute a secondary task with network options.",
    )
    sub2.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number.",
    )
    sub2.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to.",
    )

    return parser
