"""Tests for :mod:`gp_sphinx_astro_builder.models`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gp_sphinx_astro_builder.models import TextNode


def test_text_node_round_trips_through_model_dump() -> None:
    """``TextNode`` preserves type discriminator and value through ``model_dump``."""
    node = TextNode(type="text", value="hello")
    assert node.model_dump() == {"type": "text", "value": "hello"}


def test_text_node_validates_canonical_shape() -> None:
    """``TextNode.model_validate`` parses a dict with the canonical shape."""
    node = TextNode.model_validate({"type": "text", "value": "world"})
    assert node.value == "world"
    assert node.type == "text"


def test_text_node_rejects_wrong_type_discriminator() -> None:
    """``TextNode`` rejects a dict whose ``type`` is not the literal ``"text"``."""
    with pytest.raises(ValidationError):
        TextNode.model_validate({"type": "paragraph", "value": "x"})


def test_text_node_rejects_missing_value() -> None:
    """``TextNode`` rejects a dict missing the required ``value`` field."""
    with pytest.raises(ValidationError):
        TextNode.model_validate({"type": "text"})
