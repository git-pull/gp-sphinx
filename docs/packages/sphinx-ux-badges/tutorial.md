(sphinx-ux-badges-tutorial)=

# Tutorial

## Working usage examples

`setup()` registers the extension with Sphinx:

1. {py:meth}`~sphinx.application.Sphinx.add_node` registers `BadgeNode` with
   HTML visitors (`visit_badge_html` / `depart_badge_html`).
2. {py:meth}`~sphinx.application.Sphinx.add_css_file` injects the shared
   `sphinx_ux_badges.css` stylesheet.
3. Downstream extensions call
   {py:meth}`~sphinx.application.Sphinx.setup_extension` to load the badge
   layer:

```python
def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension("sphinx_ux_badges")
```

`BadgeNode` subclasses {py:class}`docutils.nodes.inline`, so unregistered
builders (text, LaTeX, man) fall back to `visit_inline` via Sphinx's
MRO-based dispatch — no special handling needed.

Build a grouped toolbar in your own directive or transform:

```python
from sphinx_ux_badges import build_badge, build_badge_group, build_toolbar

badge_group = build_badge_group(
    [
        build_badge(
            "readonly",
            tooltip="Read-only operation",
            classes=["gp-sphinx-fastmcp__safety-readonly"],
        ),
        build_badge(
            "tool",
            tooltip="FastMCP tool entry",
            classes=["gp-sphinx-fastmcp__type-tool"],
        ),
    ],
)
toolbar = build_toolbar(badge_group, classes=["my-extension-toolbar"])
```
