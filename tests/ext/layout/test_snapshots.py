"""Snapshot coverage for rendered layout HTML fragments."""

from __future__ import annotations

import re
import typing as t

import pytest


def _extract_init_header_fragment(html: str) -> str:
    """Return the full ``dt.api-header`` fragment for ``LayoutDemo.__init__``."""
    init_match = re.search(
        r'(<dt (?=[^>]*class="[^"]*api-header[^"]*")'
        r'(?=[^>]*id="gal_demo_api\.LayoutDemo\.__init__")[^>]*>.*?</dt>)',
        html,
        re.DOTALL,
    )
    assert init_match is not None
    return init_match.group(1).strip()


@pytest.mark.integration
def test_layout_demo_init_header_snapshot_annotated(
    layout_default_html: str,
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    snapshot_html_fragment(
        _extract_init_header_fragment(layout_default_html),
        name="annotated",
    )


@pytest.mark.integration
def test_layout_demo_init_header_snapshot_annotation_disabled(
    layout_annotation_disabled_html: str,
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    snapshot_html_fragment(
        _extract_init_header_fragment(layout_annotation_disabled_html),
        name="annotation_disabled",
    )
