(sphinx-ux-badges-explanation)=

# Explanation

## Downstream extensions

All colour variants are provided by the shared palette above.  Downstream
extensions reference {py:class}`~sphinx_ux_badges._css.SAB` constants
instead of maintaining package-local colour-class palettes.

```{list-table}
:header-rows: 1
:widths: 35 65

* - Extension
  - Badge types used
* - {doc}`/packages/sphinx-autodoc-fastmcp/index`
  - Safety tiers (readonly / mutating / destructive), MCP tool type (`smf-*` — FastMCP-specific colours not in shared palette)
* - {doc}`/packages/sphinx-autodoc-api-style/index`
  - {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_FUNCTION`, {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_CLASS`, {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_METHOD`, modifiers, {py:attr}`~sphinx_ux_badges._css.SAB.STATE_DEPRECATED`
* - {doc}`/packages/sphinx-autodoc-pytest-fixtures/index`
  - {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_FIXTURE`, `SAB.SCOPE_*`, {py:attr}`~sphinx_ux_badges._css.SAB.STATE_FACTORY`, {py:attr}`~sphinx_ux_badges._css.SAB.STATE_OVERRIDE`, {py:attr}`~sphinx_ux_badges._css.SAB.STATE_AUTOUSE`
* - {doc}`/packages/sphinx-autodoc-sphinx/index`
  - {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_CONFIG`, {py:attr}`~sphinx_ux_badges._css.SAB.MOD_REBUILD`
* - {doc}`/packages/sphinx-autodoc-docutils/index`
  - {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_DIRECTIVE`, {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_ROLE`, {py:attr}`~sphinx_ux_badges._css.SAB.TYPE_OPTION`
```
