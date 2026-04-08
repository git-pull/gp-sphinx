"""Snapshot coverage for rendered layout HTML fragments."""

from __future__ import annotations

import pathlib
import re
import typing as t

import pytest

from tests.ext.layout.test_integration import _build_layout_demo


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
    tmp_path: pathlib.Path,
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    html = _build_layout_demo(tmp_path)

    snapshot_html_fragment(_extract_init_header_fragment(html), name="annotated")


@pytest.mark.integration
def test_layout_demo_init_header_snapshot_annotation_disabled(
    tmp_path: pathlib.Path,
    snapshot_html_fragment: t.Callable[..., None],
) -> None:
    html = _build_layout_demo(
        tmp_path,
        extra_conf="gal_signature_show_annotations = False",
    )

    snapshot_html_fragment(
        _extract_init_header_fragment(html),
        name="annotation_disabled",
    )
