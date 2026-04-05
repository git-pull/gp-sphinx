"""Demo parser factories for the sphinx-argparse-neo docs page."""

from __future__ import annotations

import argparse
import textwrap


def build_parser() -> argparse.ArgumentParser:
    """Return a parser with groups, subcommands, and example epilogs."""
    parser = argparse.ArgumentParser(
        prog="gp-demo",
        description="Inspect and synchronize documentation metadata.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="output format",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="number of worker jobs",
    )

    subcommands = parser.add_subparsers(dest="command")

    sync = subcommands.add_parser(
        "sync",
        help="synchronize package docs",
        description="Synchronize package metadata into the docs site.",
        epilog=textwrap.dedent(
            """
            examples:
                gp-demo sync packages/sphinx-fonts
                gp-demo sync packages/sphinx-gptheme

            Machine-readable output examples:
                gp-demo sync --format json packages/sphinx-fonts
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sync.add_argument("target", metavar="PACKAGE", help="package to synchronize")
    sync.add_argument(
        "--strict",
        action="store_true",
        help="fail on missing docs coverage",
    )

    doctor = subcommands.add_parser(
        "doctor",
        help="check docs build health",
        description="Run validation checks for the documentation site.",
    )
    doctor.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="treat warnings as fatal",
    )

    return parser
