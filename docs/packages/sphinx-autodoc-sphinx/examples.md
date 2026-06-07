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

### Document one demo builder

Builders surface their CLI name, output format, supported image types,
and parallel-safety:

```{eval-rst}
.. autobuilder:: sphinx_demo_builder.DemoArchiveBuilder
```

### Bulk builders demo

Renders every builder a module registers via `setup()`:

```{eval-rst}
.. autobuilders:: sphinx_demo_builder
   :no-index:
```

### Document one demo domain

Domains surface their registered name, label, object types, roles, and
indices:

```{eval-rst}
.. autodomain:: sphinx_demo_builder.DemoTopicDomain
```

### Bulk domains demo

The bulk form replays a package's `setup()` — here documenting the
`docutils` domain that `sphinx-autodoc-docutils` itself registers:

```{eval-rst}
.. autodomains:: sphinx_autodoc_docutils
   :no-index:
```

### Cross-referencing components

Component entries register targets in the `sphinxext` domain, so prose
can link to them: {sphinxext:builder}`DemoArchiveBuilder` and
{sphinxext:domain}`DemoTopicDomain` resolve to the entries above.
