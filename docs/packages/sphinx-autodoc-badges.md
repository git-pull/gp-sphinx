(sphinx-autodoc-badges)=

# sphinx-autodoc-badges

```{sab-package-meta} sphinx-autodoc-badges
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
$ pip install sphinx-autodoc-badges
```

## Live demos

Every variant rendered by the real `build_badge` / `build_badge_group` /
`build_toolbar` API:

```{sab-badge-demo}
```

## Working usage examples

`setup()` registers the extension with Sphinx:

1. {py:meth}`~sphinx.application.Sphinx.add_node` registers `BadgeNode` with
   HTML visitors (`visit_badge_html` / `depart_badge_html`).
2. {py:meth}`~sphinx.application.Sphinx.add_css_file` injects the shared
   `sphinx_autodoc_badges.css` stylesheet.
3. Downstream extensions call
   {py:meth}`~sphinx.application.Sphinx.setup_extension` to load the badge
   layer:

```python
def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension("sphinx_autodoc_badges")
```

`BadgeNode` subclasses {py:class}`docutils.nodes.inline`, so unregistered
builders (text, LaTeX, man) fall back to `visit_inline` via Sphinx's
MRO-based dispatch — no special handling needed.

Build a grouped toolbar in your own directive or transform:

```python
from sphinx_autodoc_badges import build_badge, build_badge_group, build_toolbar

badge_group = build_badge_group(
    [
        build_badge(
            "readonly",
            tooltip="Read-only operation",
            classes=["smf-safety-readonly"],
        ),
        build_badge(
            "tool",
            tooltip="FastMCP tool entry",
            classes=["smf-type-tool"],
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
* - `sab-type-function`
  - `SAB.TYPE_FUNCTION`
  - Python functions (blue)
* - `sab-type-class`
  - `SAB.TYPE_CLASS`
  - Python classes (indigo)
* - `sab-type-method`
  - `SAB.TYPE_METHOD`
  - Instance / class / static methods (cyan)
* - `sab-type-property`
  - `SAB.TYPE_PROPERTY`
  - Properties (teal)
* - `sab-type-attribute`
  - `SAB.TYPE_ATTRIBUTE`
  - Attributes (slate)
* - `sab-type-data`
  - `SAB.TYPE_DATA`
  - Module-level data (grey)
* - `sab-type-exception`
  - `SAB.TYPE_EXCEPTION`
  - Exceptions (rose/red)
* - `sab-type-typealias`
  - `SAB.TYPE_TYPEALIAS`
  - Type aliases (violet)
* - `sab-type-module`
  - `SAB.TYPE_MODULE`
  - Modules (green)
* - `sab-mod-async`
  - `SAB.MOD_ASYNC`
  - async modifier (purple outline)
* - `sab-mod-classmethod`
  - `SAB.MOD_CLASSMETHOD`
  - classmethod modifier (amber outline)
* - `sab-mod-staticmethod`
  - `SAB.MOD_STATICMETHOD`
  - staticmethod modifier (grey outline)
* - `sab-mod-abstract`
  - `SAB.MOD_ABSTRACT`
  - abstract modifier (indigo outline)
* - `sab-mod-final`
  - `SAB.MOD_FINAL`
  - final modifier (emerald outline)
* - `sab-state-deprecated`
  - `SAB.STATE_DEPRECATED`
  - deprecated (muted red, shared across domains)
* - `sab-type-fixture`
  - `SAB.TYPE_FIXTURE`
  - pytest fixtures (green)
* - `sab-scope-session`
  - `SAB.SCOPE_SESSION`
  - session-scope fixtures (amber)
* - `sab-scope-module`
  - `SAB.SCOPE_MODULE`
  - module-scope fixtures (teal)
* - `sab-scope-class`
  - `SAB.SCOPE_CLASS`
  - class-scope fixtures (slate)
* - `sab-state-factory`
  - `SAB.STATE_FACTORY`
  - factory fixtures (amber outline)
* - `sab-state-override`
  - `SAB.STATE_OVERRIDE`
  - override hooks (violet outline)
* - `sab-state-autouse`
  - `SAB.STATE_AUTOUSE`
  - autouse fixtures (rose outline)
* - `sab-type-config`
  - `SAB.TYPE_CONFIG`
  - Sphinx config values (amber)
* - `sab-mod-rebuild`
  - `SAB.MOD_REBUILD`
  - Sphinx rebuild mode (grey outline)
* - `sab-type-directive`
  - `SAB.TYPE_DIRECTIVE`
  - docutils directives (violet)
* - `sab-type-role`
  - `SAB.TYPE_ROLE`
  - docutils roles (violet)
* - `sab-type-option`
  - `SAB.TYPE_OPTION`
  - docutils directive options (violet)
```

## API reference

```{eval-rst}
.. autoclass:: sphinx_autodoc_badges.BadgeSpec
   :members:

.. autofunction:: sphinx_autodoc_badges.build_badge_from_spec

.. autofunction:: sphinx_autodoc_badges.build_badge

.. autofunction:: sphinx_autodoc_badges.build_badge_group

.. autofunction:: sphinx_autodoc_badges.build_toolbar

.. autoclass:: sphinx_autodoc_badges.BadgeNode
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

.. autoclass:: sphinx_autodoc_badges._css.SAB
   :members:
   :undoc-members:

.. autofunction:: sphinx_autodoc_badges.setup
```

## CSS custom properties

All colors and metrics are exposed as CSS custom properties on `:root`.
Override them in your project's `custom.css` or via
{py:meth}`~sphinx.application.Sphinx.add_css_file`.

### Defaults

```css
:root {
  /* ── Color hooks (set by downstream extensions) ────── */
  --sab-bg: transparent;        /* badge background */
  --sab-fg: inherit;            /* badge text color */
  --sab-border: none;           /* badge border shorthand */

  /* ── Metrics ───────────────────────────────────────── */
  --sab-font-size: 0.75em;
  --sab-font-weight: 700;
  --sab-padding-v: 0.35em;      /* vertical padding */
  --sab-padding-h: 0.65em;      /* horizontal padding */
  --sab-radius: 0.25rem;        /* border-radius */
  --sab-icon-gap: 0.28rem;      /* gap between icon and label */

  /* ── Depth (inset shadow on solid badges) ──────────── */
  --sab-buff-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.2),
    inset 0 -1px 2px rgba(0, 0, 0, 0.12);
  --sab-buff-shadow-dark-ui:
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
* - `--sab-bg`
  - Badge background color. Extensions set this per badge class (e.g. green for "readonly").
* - `--sab-fg`
  - Badge text color. Falls back to `inherit` when unset.
* - `--sab-border`
  - Border shorthand (`1px solid #...`). Defaults to `none`.
* - `--sab-font-size`
  - Font size. Context-aware sizing (headings, body, TOC) overrides this.
* - `--sab-font-weight`
  - Font weight. Default `700` (bold).
* - `--sab-padding-v` / `--sab-padding-h`
  - Vertical and horizontal padding.
* - `--sab-radius`
  - Border radius for pill shape.
* - `--sab-icon-gap`
  - Gap between the `::before` icon and the label text.
* - `--sab-buff-shadow`
  - Subtle inset highlight + shadow for depth on light backgrounds.
* - `--sab-buff-shadow-dark-ui`
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
* - `sab-badge`
  - `BadgeNode`
  - Base class. Always present on every badge.
* - `sab-outline`
  - `build_badge(fill="outline")`
  - Transparent background, inherits text color.
* - `sab-icon-only`
  - `build_badge(style="icon-only")`
  - 16 × 16 colored box with emoji `::before`.
* - `sab-inline-icon`
  - `build_badge(style="inline-icon")`
  - Bare emoji inside a code chip, no background.
* - `sab-badge-group`
  - `build_badge_group()`
  - Flex container with `gap: 0.3rem` between badges.
* - `sab-toolbar`
  - `build_toolbar()`
  - Flex push-right (`margin-left: auto`) for title rows.
* - `sab-xxs`
  - `build_badge(size="xxs")` / `BadgeNode(..., badge_size="xxs")`
  - Minimum size (status dots, very tight layouts).
* - `sab-xs`
  - `build_badge(size="xs")` / `BadgeNode(..., badge_size="xs")`
  - Extra small (dense tables, tight UI).
* - `sab-sm`
  - `build_badge(size="sm")`
  - Small inline badges.
* - `sab-md`
  - `build_badge(size="md")`
  - Medium — larger than the default but smaller than `lg`.
* - `sab-lg`
  - `build_badge(size="lg")`
  - Large (section titles, callouts).
* - `sab-xl`
  - `build_badge(size="xl")`
  - Extra large (hero / landing emphasis).
```

## Context-aware sizing

Badge size adapts automatically based on where it appears in the document.
CSS selectors handle it. Explicit size classes (`sab-xs` … `sab-xl`) override
contextual sizing when present (higher specificity than context rules).

```{list-table}
:header-rows: 1
:widths: 25 20 55

* - Context
  - Font size
  - Selectors
* - Heading (`h2`, `h3`)
  - `0.68rem`
  - `.body h2 .sab-badge`, `[role="main"] h3 .sab-badge`
* - Body (`p`, `li`, `td`, `a`)
  - `0.62rem`
  - `.body p .sab-badge`, `[role="main"] li .sab-badge`, etc.
* - TOC sidebar
  - `0.58rem`
  - `.toc-tree .sab-badge` (compact, with emoji icons)
```

## Downstream extensions

All colour variants are provided by the shared palette above.  Downstream
extensions reference `SAB.*` constants instead of maintaining their own
`gas-*` / `spf-*` / `sas-*` / `sadoc-*` colour classes.

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

```{package-reference} sphinx-autodoc-badges
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-badges) · [PyPI](https://pypi.org/project/sphinx-autodoc-badges/)
