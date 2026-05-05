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
