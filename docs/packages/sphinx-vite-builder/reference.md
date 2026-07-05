(sphinx-vite-builder-reference)=

# API Reference

## Config reference

Generated from {py:meth}`~sphinx.application.Sphinx.add_config_value`
registrations in
[`sphinx_vite_builder/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-vite-builder/src/sphinx_vite_builder/__init__.py).

```{eval-rst}
.. autoconfigvalues:: sphinx_vite_builder
```

## PEP 517 backend

```{eval-rst}
.. autofunction:: sphinx_vite_builder.build.build_wheel

.. autofunction:: sphinx_vite_builder.build.build_editable

.. autofunction:: sphinx_vite_builder.build.build_sdist
```

## Hatchling hook

```{eval-rst}
.. autoclass:: sphinx_vite_builder.hatch_plugin.ViteBuildHook
   :members:

.. autofunction:: sphinx_vite_builder.hatch_plugin.hatch_register_build_hook
```

## Diagnostic errors

```{eval-rst}
.. autoclass:: sphinx_vite_builder._internal.errors.SphinxViteBuilderError

.. autoclass:: sphinx_vite_builder._internal.errors.PnpmMissingError

.. autoclass:: sphinx_vite_builder._internal.errors.NodeModulesInstallError

.. autoclass:: sphinx_vite_builder._internal.errors.ViteFailedError
```
