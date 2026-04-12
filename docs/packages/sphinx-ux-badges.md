(sphinx-ux-badges)=

# sphinx-ux-badges

```{gp-sphinx-package-meta} sphinx-ux-badges
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Shared badge node, HTML visitors, and CSS infrastructure for Sphinx autodoc
extensions. Provides a single `BadgeNode` and builder API that
{doc}`sphinx-autodoc-api-style`, {doc}`sphinx-autodoc-pytest-fixtures`, and
{doc}`sphinx-autodoc-fastmcp` share instead of reimplementing badges
independently.

```console
$ pip install sphinx-ux-badges
```

## Live demos

Every variant rendered by the real `build_badge` / `build_badge_group` /
`build_toolbar` API:

```{gp-sphinx-badge-demo}
```

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

## Colour palette

All semantic badge colours live in `sab_palettes.css` (registered by
this extension).  Every `sphinx-autodoc-*` package uses the `SAB.*`
constants instead of its own colour classes.  The live demo below shows
every variant.

```{list-table}
:header-rows: 1
:widths: 30 30 40

* - Colour class
  - `SAB` constant
  - Used for
* - `gp-sphinx-badge--type-function`
  - `SAB.TYPE_FUNCTION`
  - Python functions (blue)
* - `gp-sphinx-badge--type-class`
  - `SAB.TYPE_CLASS`
  - Python classes (indigo)
* - `gp-sphinx-badge--type-method`
  - `SAB.TYPE_METHOD`
  - Instance / class / static methods (cyan)
* - `gp-sphinx-badge--type-property`
  - `SAB.TYPE_PROPERTY`
  - Properties (teal)
* - `gp-sphinx-badge--type-attribute`
  - `SAB.TYPE_ATTRIBUTE`
  - Attributes (slate)
* - `gp-sphinx-badge--type-data`
  - `SAB.TYPE_DATA`
  - Module-level data (grey)
* - `gp-sphinx-badge--type-exception`
  - `SAB.TYPE_EXCEPTION`
  - Exceptions (rose/red)
* - `gp-sphinx-badge--type-typealias`
  - `SAB.TYPE_TYPEALIAS`
  - Type aliases (violet)
* - `gp-sphinx-badge--type-module`
  - `SAB.TYPE_MODULE`
  - Modules (green)
* - `gp-sphinx-badge--mod-async`
  - `SAB.MOD_ASYNC`
  - async modifier (purple outline)
* - `gp-sphinx-badge--mod-classmethod`
  - `SAB.MOD_CLASSMETHOD`
  - classmethod modifier (amber outline)
* - `gp-sphinx-badge--mod-staticmethod`
  - `SAB.MOD_STATICMETHOD`
  - staticmethod modifier (grey outline)
* - `gp-sphinx-badge--mod-abstract`
  - `SAB.MOD_ABSTRACT`
  - abstract modifier (indigo outline)
* - `gp-sphinx-badge--mod-final`
  - `SAB.MOD_FINAL`
  - final modifier (emerald outline)
* - `gp-sphinx-badge--state-deprecated`
  - `SAB.STATE_DEPRECATED`
  - deprecated (muted red, shared across domains)
* - `gp-sphinx-badge--type-fixture`
  - `SAB.TYPE_FIXTURE`
  - pytest fixtures (green)
* - `gp-sphinx-badge--scope-session`
  - `SAB.SCOPE_SESSION`
  - session-scope fixtures (amber)
* - `gp-sphinx-badge--scope-module`
  - `SAB.SCOPE_MODULE`
  - module-scope fixtures (teal)
* - `gp-sphinx-badge--scope-class`
  - `SAB.SCOPE_CLASS`
  - class-scope fixtures (slate)
* - `gp-sphinx-badge--state-factory`
  - `SAB.STATE_FACTORY`
  - factory fixtures (amber outline)
* - `gp-sphinx-badge--state-override`
  - `SAB.STATE_OVERRIDE`
  - override hooks (violet outline)
* - `gp-sphinx-badge--state-autouse`
  - `SAB.STATE_AUTOUSE`
  - autouse fixtures (rose outline)
* - `gp-sphinx-badge--type-config`
  - `SAB.TYPE_CONFIG`
  - Sphinx config values (amber)
* - `gp-sphinx-badge--mod-rebuild`
  - `SAB.MOD_REBUILD`
  - Sphinx rebuild mode (grey outline)
* - `gp-sphinx-badge--type-directive`
  - `SAB.TYPE_DIRECTIVE`
  - docutils directives (violet)
* - `gp-sphinx-badge--type-role`
  - `SAB.TYPE_ROLE`
  - docutils roles (violet)
* - `gp-sphinx-badge--type-option`
  - `SAB.TYPE_OPTION`
  - docutils directive options (violet)
```

## API reference

```{eval-rst}
.. autoclass:: sphinx_ux_badges.BadgeSpec
   :members:

.. autofunction:: sphinx_ux_badges.build_badge_from_spec

.. autofunction:: sphinx_ux_badges.build_badge

.. autofunction:: sphinx_ux_badges.build_badge_group

.. autofunction:: sphinx_ux_badges.build_toolbar

.. autoclass:: sphinx_ux_badges.BadgeNode
   :no-members:

   .. rubric:: Constructor parameters

   .. list-table::
      :header-rows: 1
      :widths: 20 15 65

      * - Parameter
        - Default
        - Description
      * - ``text``
        - ``""``
        - Visible label. Empty string for icon-only badges.
      * - ``badge_tooltip``
        - ``""``
        - Hover text and ``aria-label``.
      * - ``badge_icon``
        - ``""``
        - Emoji character rendered via CSS ``::before``.
      * - ``badge_style``
        - ``"full"``
        - Structural variant: ``"full"``, ``"icon-only"``, ``"inline-icon"``.
      * - ``badge_size``
        - ``""``
        - Optional size: ``"xxs"``, ``"xs"``, ``"sm"``, ``"md"``, ``"lg"``, or ``"xl"``. Empty means default.
      * - ``tabindex``
        - ``"0"``
        - ``"0"`` for keyboard-focusable, ``""`` to skip.
      * - ``classes``
        - ``None``
        - Additional CSS classes (plugin prefix + color class).

.. autoclass:: sphinx_ux_badges._css.SAB
   :members:
   :undoc-members:

.. autofunction:: sphinx_ux_badges.setup
```

## CSS custom properties

All colors and metrics are exposed as CSS custom properties on `:root`.
Override them in your project's `custom.css` or via
{py:meth}`~sphinx.application.Sphinx.add_css_file`.

### Defaults

```css
:root {
  /* ── Color hooks (set by downstream extensions) ────── */
  --gp-sphinx-badge-bg: transparent;        /* badge background */
  --gp-sphinx-badge-fg: inherit;            /* badge text color */
  --gp-sphinx-badge-border: none;           /* badge border shorthand */

  /* ── Metrics ───────────────────────────────────────── */
  --gp-sphinx-badge-font-size: 0.75em;
  --gp-sphinx-badge-font-weight: 700;
  --gp-sphinx-badge-padding-v: 0.35em;      /* vertical padding */
  --gp-sphinx-badge-padding-h: 0.65em;      /* horizontal padding */
  --gp-sphinx-badge-radius: 0.25rem;        /* border-radius */
  --gp-sphinx-badge-icon-gap: 0.28rem;      /* gap between icon and label */

  /* ── Depth (inset shadow on solid badges) ──────────── */
  --gp-sphinx-badge-buff-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.2),
    inset 0 -1px 2px rgba(0, 0, 0, 0.12);
  --gp-sphinx-badge-buff-shadow-dark-ui:
    inset 0 1px 0 rgba(255, 255, 255, 0.1),
    inset 0 -1px 2px rgba(0, 0, 0, 0.28);
}
```

### Property reference

```{list-table}
:header-rows: 1
:widths: 30 70

* - Property
  - Purpose
* - `--gp-sphinx-badge-bg`
  - Badge background color. Extensions set this per badge class (e.g. green for "readonly").
* - `--gp-sphinx-badge-fg`
  - Badge text color. Falls back to `inherit` when unset.
* - `--gp-sphinx-badge-border`
  - Border shorthand (`1px solid #...`). Defaults to `none`.
* - `--gp-sphinx-badge-font-size`
  - Font size. Context-aware sizing (headings, body, TOC) overrides this.
* - `--gp-sphinx-badge-font-weight`
  - Font weight. Default `700` (bold).
* - `--gp-sphinx-badge-padding-v` / `--gp-sphinx-badge-padding-h`
  - Vertical and horizontal padding.
* - `--gp-sphinx-badge-radius`
  - Border radius for pill shape.
* - `--gp-sphinx-badge-icon-gap`
  - Gap between the `::before` icon and the label text.
* - `--gp-sphinx-badge-buff-shadow`
  - Subtle inset highlight + shadow for depth on light backgrounds.
* - `--gp-sphinx-badge-buff-shadow-dark-ui`
  - Stronger inset shadow variant for dark theme / `prefers-color-scheme: dark`.
```

## CSS class reference

All classes use the `sab-` prefix (**s**phinx **a**utodoc **b**adges).

```{list-table}
:header-rows: 1
:widths: 25 15 60

* - Class
  - Applied by
  - Description
* - `gp-sphinx-badge`
  - `BadgeNode`
  - Base class. Always present on every badge.
* - `gp-sphinx-badge--outline`
  - `build_badge(fill="outline")`
  - Transparent background, inherits text color.
* - `gp-sphinx-badge--icon-only`
  - `build_badge(style="icon-only")`
  - 16 × 16 colored box with emoji `::before`.
* - `gp-sphinx-badge--inline-icon`
  - `build_badge(style="inline-icon")`
  - Bare emoji inside a code chip, no background.
* - `gp-sphinx-badge-group`
  - `build_badge_group()`
  - Flex container with `gap: 0.3rem` between badges.
* - `gp-sphinx-toolbar`
  - `build_toolbar()`
  - Flex push-right (`margin-left: auto`) for title rows.
* - `gp-sphinx-badge--size-xxs`
  - `build_badge(size="xxs")` / `BadgeNode(..., badge_size="xxs")`
  - Minimum size (status dots, very tight layouts).
* - `gp-sphinx-badge--size-xs`
  - `build_badge(size="xs")` / `BadgeNode(..., badge_size="xs")`
  - Extra small (dense tables, tight UI).
* - `gp-sphinx-badge--size-sm`
  - `build_badge(size="sm")`
  - Small inline badges.
* - `gp-sphinx-badge--size-md`
  - `build_badge(size="md")`
  - Medium — larger than the default but smaller than `lg`.
* - `gp-sphinx-badge--size-lg`
  - `build_badge(size="lg")`
  - Large (section titles, callouts).
* - `gp-sphinx-badge--size-xl`
  - `build_badge(size="xl")`
  - Extra large (hero / landing emphasis).
```

## Context-aware sizing

Badge size adapts automatically based on where it appears in the document.
CSS selectors handle it. Explicit size classes (`gp-sphinx-badge--size-xs` … `gp-sphinx-badge--size-xl`) override
contextual sizing when present (higher specificity than context rules).

```{list-table}
:header-rows: 1
:widths: 25 20 55

* - Context
  - Font size
  - Selectors
* - Heading (`h2`, `h3`)
  - `0.68rem`
  - `.body h2 .gp-sphinx-badge`, `[role="main"] h3 .gp-sphinx-badge`
* - Body (`p`, `li`, `td`, `a`)
  - `0.62rem`
  - `.body p .gp-sphinx-badge`, `[role="main"] li .gp-sphinx-badge`, etc.
* - TOC sidebar
  - `0.58rem`
  - `.toc-tree .gp-sphinx-badge` (compact, with emoji icons)
```

## Downstream extensions

All colour variants are provided by the shared palette above.  Downstream
extensions reference `SAB.*` constants instead of maintaining their own
`sab-*` / `spf-*` / `sas-*` / `sadoc-*` colour classes.

```{list-table}
:header-rows: 1
:widths: 35 65

* - Extension
  - Badge types used
* - {doc}`sphinx-autodoc-fastmcp`
  - Safety tiers (readonly / mutating / destructive), MCP tool type (`smf-*` — FastMCP-specific colours not in shared palette)
* - {doc}`sphinx-autodoc-api-style`
  - `SAB.TYPE_FUNCTION`, `SAB.TYPE_CLASS`, `SAB.TYPE_METHOD`, modifiers, `SAB.STATE_DEPRECATED`
* - {doc}`sphinx-autodoc-pytest-fixtures`
  - `SAB.TYPE_FIXTURE`, `SAB.SCOPE_*`, `SAB.STATE_FACTORY`, `SAB.STATE_OVERRIDE`, `SAB.STATE_AUTOUSE`
* - {doc}`sphinx-autodoc-sphinx`
  - `SAB.TYPE_CONFIG`, `SAB.MOD_REBUILD`
* - {doc}`sphinx-autodoc-docutils`
  - `SAB.TYPE_DIRECTIVE`, `SAB.TYPE_ROLE`, `SAB.TYPE_OPTION`
```

## Package reference

```{package-reference} sphinx-ux-badges
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-ux-badges) · [PyPI](https://pypi.org/project/sphinx-ux-badges/)
