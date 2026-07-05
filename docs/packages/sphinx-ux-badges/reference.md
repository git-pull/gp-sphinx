(sphinx-ux-badges-reference)=

# API Reference

## Colour palette

All semantic badge colours live in `sab_palettes.css` (registered by
this extension).  Every `sphinx-autodoc-*` package uses
{py:class}`~sphinx_ux_badges._css.SAB` constants instead of its own
colour classes.  The live demo below shows every variant.

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

All classes use the shared `gp-sphinx-badge` base class and
`gp-sphinx-badge--*` modifiers.

```{list-table}
:header-rows: 1
:widths: 25 15 60

* - Class
  - Applied by
  - Description
* - `gp-sphinx-badge`
  - {py:class}`~sphinx_ux_badges.BadgeNode`
  - Base class. Always present on every badge.
* - `gp-sphinx-badge--outline`
  - {py:func}`~sphinx_ux_badges.build_badge` with `fill="outline"`
  - Transparent background, inherits text color.
* - `gp-sphinx-badge--icon-only`
  - {py:func}`~sphinx_ux_badges.build_badge` with `style="icon-only"`
  - 16 × 16 colored box with emoji `::before`.
* - `gp-sphinx-badge--inline-icon`
  - {py:func}`~sphinx_ux_badges.build_badge` with `style="inline-icon"`
  - Bare emoji inside a code chip, no background.
* - `gp-sphinx-badge-group`
  - {py:func}`~sphinx_ux_badges.build_badge_group`
  - Flex container with `gap: 0.3rem` between badges.
* - `gp-sphinx-toolbar`
  - {py:func}`~sphinx_ux_badges.build_toolbar`
  - Flex push-right (`margin-left: auto`) for title rows.
* - `gp-sphinx-badge--size-xxs`
  - {py:func}`~sphinx_ux_badges.build_badge` with `size="xxs"` /
    {py:class}`~sphinx_ux_badges.BadgeNode` with `badge_size="xxs"`
  - Minimum size (status dots, very tight layouts).
* - `gp-sphinx-badge--size-xs`
  - {py:func}`~sphinx_ux_badges.build_badge` with `size="xs"` /
    {py:class}`~sphinx_ux_badges.BadgeNode` with `badge_size="xs"`
  - Extra small (dense tables, tight UI).
* - `gp-sphinx-badge--size-sm`
  - {py:func}`~sphinx_ux_badges.build_badge` with `size="sm"`
  - Small inline badges.
* - `gp-sphinx-badge--size-md`
  - {py:func}`~sphinx_ux_badges.build_badge` with `size="md"`
  - Medium — larger than the default but smaller than `lg`.
* - `gp-sphinx-badge--size-lg`
  - {py:func}`~sphinx_ux_badges.build_badge` with `size="lg"`
  - Large (section titles, callouts).
* - `gp-sphinx-badge--size-xl`
  - {py:func}`~sphinx_ux_badges.build_badge` with `size="xl"`
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
