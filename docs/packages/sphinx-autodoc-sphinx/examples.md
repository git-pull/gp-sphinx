(sphinx-autodoc-sphinx-examples)=

# Examples

## Live demos

This page also uses `sphinx-autodoc-docutils` to document the config-doc
directives themselves, so the page demonstrates both config-value output and
directive documentation.

### Render a single demo config value

```{eval-rst}
.. autoconfigvalue:: sphinx_config_single_demo.demo_debug
   :no-index:
```

### Bulk config values demo

Renders all config values from a module at once:

```{eval-rst}
.. autoconfigvalues:: sphinx_config_demo
```
