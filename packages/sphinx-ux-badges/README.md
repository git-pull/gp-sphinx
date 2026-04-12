# sphinx-ux-badges

Shared badge node and CSS for Sphinx autodoc extensions in the gp-sphinx ecosystem.

Provides `BadgeNode`, HTML visitors, and builder helpers shared by
`sphinx-autodoc-api-style`, `sphinx-autodoc-pytest-fixtures`,
`sphinx-autodoc-sphinx`, `sphinx-autodoc-docutils`, and
`sphinx-autodoc-fastmcp`.

## Install

```console
$ pip install sphinx-ux-badges
```

## Usage

Load the badge layer from your own extension's `setup()`:

```python
def setup(app):
    app.setup_extension("sphinx_ux_badges")
```

Then build badges in your directives or transforms:

```python
from sphinx_ux_badges import build_badge, build_badge_group, build_toolbar

group = build_badge_group([
    build_badge(
        "readonly",
        tooltip="Read-only",
        classes=["gp-sphinx-fastmcp__safety-readonly"],
    ),
])
```

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-ux-badges/)
for the colour palette reference, `BadgeSpec` API, and live demos.
