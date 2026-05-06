(sphinx-ux-badges-explanation)=

# Explanation

## Downstream extensions

All colour variants are provided by the shared palette above.  Downstream
extensions reference `SAB.*` constants instead of maintaining their own
`sab-*` / `spf-*` / `sas-*` / `sadoc-*` colour classes.

```{list-table}
:header-rows: 1
:widths: 35 65

* - Extension
  - Badge types used
* - {doc}`/packages/sphinx-autodoc-fastmcp/index`
  - Safety tiers (readonly / mutating / destructive), MCP tool type (`smf-*` — FastMCP-specific colours not in shared palette)
* - {doc}`/packages/sphinx-autodoc-api-style/index`
  - `SAB.TYPE_FUNCTION`, `SAB.TYPE_CLASS`, `SAB.TYPE_METHOD`, modifiers, `SAB.STATE_DEPRECATED`
* - {doc}`/packages/sphinx-autodoc-pytest-fixtures/index`
  - `SAB.TYPE_FIXTURE`, `SAB.SCOPE_*`, `SAB.STATE_FACTORY`, `SAB.STATE_OVERRIDE`, `SAB.STATE_AUTOUSE`
* - {doc}`/packages/sphinx-autodoc-sphinx/index`
  - `SAB.TYPE_CONFIG`, `SAB.MOD_REBUILD`
* - {doc}`/packages/sphinx-autodoc-docutils/index`
  - `SAB.TYPE_DIRECTIVE`, `SAB.TYPE_ROLE`, `SAB.TYPE_OPTION`
```
