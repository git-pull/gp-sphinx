# mypy: disable-error-code="arg-type, assignment, dict-item, misc, operator, union-attr"
"""Generate the navigation tree from Sphinx's toctree function's output.

Ported from furo @ 752bf80c, MIT (Pradyun Gedam). See LICENSE-FURO.

bs4's type stubs are imprecise for the dynamic attribute-bag manipulation
(``element["class"]`` reads as ``str | list[str] | None`` depending on the
parser state). Upstream Furo doesn't run mypy and the runtime behavior is
correct, so this file opts out of the affected error codes rather than
papering over with per-line ``type: ignore`` noise.
"""

from __future__ import annotations

import functools

from bs4 import BeautifulSoup, Tag


def _get_navigation_expand_image(soup: BeautifulSoup) -> Tag:
    retval = soup.new_tag("span", attrs={"class": "icon"})

    svg_element = soup.new_tag("svg")
    svg_use_element = soup.new_tag("use", href="#svg-arrow-right")
    svg_element.append(svg_use_element)

    retval.append(svg_element)
    return retval


@functools.cache
def get_navigation_tree(toctree_html: str) -> str:
    """Modify the given navigation tree, with furo-specific elements.

    Adds a checkbox + corresponding label to <li>s that contain a <ul> tag, to enable
    the I-spent-too-much-time-making-this-CSS-only collapsing sidebar tree.
    """
    if not toctree_html:
        return toctree_html

    soup = BeautifulSoup(toctree_html, "html.parser")

    toctree_checkbox_count = 0
    last_element_with_current = None
    for element in soup.find_all("li", recursive=True):
        # We check all "li" elements, to add a "current-page" to the correct li.
        classes = element.get("class", [])
        if "current" in classes:
            last_element_with_current = element

        # Nothing more to do, unless this has "children"
        if not element.find("ul"):
            continue

        # Add a class to indicate that this has children.
        element["class"] = [*classes, "has-children"]

        # We're gonna add a checkbox.
        toctree_checkbox_count += 1
        checkbox_name = f"toctree-checkbox-{toctree_checkbox_count}"
        accessible_name = f"Toggle navigation of {element.find('a').text}"

        # Add the "label" for the checkbox which will get filled.
        label = soup.new_tag(
            "label",
            attrs={
                "for": checkbox_name,
            },
        )
        label.append(_get_navigation_expand_image(soup))

        element.insert(1, label)

        # Add the checkbox that's used to store expanded/collapsed state.
        checkbox = soup.new_tag(
            "input",
            attrs={
                "type": "checkbox",
                "class": ["toctree-checkbox"],
                "id": checkbox_name,
                "name": checkbox_name,
                "role": "switch",
                "aria-label": accessible_name,
            },
        )
        # if this has a "current" class, expand it by default (check the checkbox)
        if "current" in classes:
            checkbox.attrs["checked"] = ""

        element.insert(1, checkbox)

    if last_element_with_current is not None:
        last_element_with_current["class"].append("current-page")

    return str(soup)
