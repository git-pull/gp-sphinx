(sphinx-ux-octicons-reference)=

# API Reference

## Role syntax

The `{octicon}` role accepts up to three `;`-separated arguments:

| Form | Example |
|---|---|
| `name` | `` {octicon}`rocket` `` |
| `name;height` | `` {octicon}`rocket;1.5rem` `` |
| `name;height;classes` | `` {octicon}`rocket;1.5rem;text-success` `` |

- `name` — bundled icon name (see {ref}`bundled-icons` below).
- `height` — CSS length (`em`, `rem`, `px`). Default `1em`. Width
  scales to preserve the icon's 1:1 aspect ratio.
- `classes` — space-separated extra classes appended to the SVG.

Unknown icon names emit a docutils error pointing at the source line.

(bundled-icons)=
## Bundled icons

```{list-table}
:header-rows: 1
:widths: 30 70

* - Name
  - Used for
* - `rocket`
  - Tutorials and getting-started entry points
* - `tools`
  - How-to guides and configuration recipes
* - `book`
  - Reference / API pages
* - `light-bulb`
  - Explanation and design rationale
* - `star`
  - Example showcases and highlights
* - `alert`
  - Errors, warnings, breaking-change callouts
* - `terminal`
  - CLI documentation and command reference
* - `paintbrush`
  - Theme tokens and styling content
* - `code`
  - Signature and code-example pages
* - `device-camera`
  - Gallery / kitchen-sink content
* - `diff`
  - Surface-diff and migration content
* - `link`
  - Dependents and cross-package references
* - `home`
  - Landing pages
* - `gear`
  - Settings and configuration
* - `package`
  - Package-level content
* - `info`
  - Informational notes
* - `check-circle`
  - Validation passes and success states
* - `x-circle`
  - Validation failures and error states
```

Need an icon that isn't in the bundle? Add it via the recipe in
{doc}`how-to`.

## CSS class

`gp-sphinx-octicon` is the only class shipped by this extension. The
rendered SVG receives both `gp-sphinx-octicon` and a per-icon modifier
`gp-sphinx-octicon--<name>`:

```html
<svg class="gp-sphinx-octicon gp-sphinx-octicon--rocket"
     viewBox="0 0 16 16" width="1em" height="1em"
     aria-hidden="true"><path d="..."/></svg>
```

The CSS rule lives in `_static/css/sphinx_ux_octicons.css`:

```css
@layer gp-sphinx {
  .gp-sphinx-octicon {
    display: inline-block;
    vertical-align: text-top;
    fill: currentColor;
  }
}
```

`fill: currentColor` lets the icon inherit its colour from the
surrounding text — no per-role styling required.

## Non-HTML builders

`OcticonNode` subclasses {py:class}`docutils.nodes.inline`, so non-HTML
builders (text, man, LaTeX) fall back via Sphinx MRO dispatch to
`visit_inline` and render the icon name as visible text. Documents
build cleanly across every Sphinx builder.

## Python API

```{eval-rst}
.. autofunction:: sphinx_ux_octicons.setup
```
