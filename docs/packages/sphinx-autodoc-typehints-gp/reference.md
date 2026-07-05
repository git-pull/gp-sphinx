(sphinx-autodoc-typehints-gp-reference)=

# API Reference

## Config reference

Generated from {py:meth}`~sphinx.application.Sphinx.add_config_value`
registrations in
[`sphinx_autodoc_typehints_gp/extension.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-typehints-gp/src/sphinx_autodoc_typehints_gp/extension.py).

```{eval-rst}
.. autoconfigvalues:: sphinx_autodoc_typehints_gp.extension
```

## Annotation rendering

```{eval-rst}
.. autofunction:: sphinx_autodoc_typehints_gp.build_annotation_paragraph

.. autofunction:: sphinx_autodoc_typehints_gp.build_annotation_display_paragraph

.. autofunction:: sphinx_autodoc_typehints_gp.build_resolved_annotation_paragraph

.. autofunction:: sphinx_autodoc_typehints_gp.build_resolved_annotation_display_paragraph

.. autofunction:: sphinx_autodoc_typehints_gp.render_annotation_nodes
```

## Annotation text and classification

```{eval-rst}
.. autofunction:: sphinx_autodoc_typehints_gp.normalize_annotation_text

.. autofunction:: sphinx_autodoc_typehints_gp.normalize_type_collection_text

.. autofunction:: sphinx_autodoc_typehints_gp.classify_annotation_display

.. autoclass:: sphinx_autodoc_typehints_gp.AnnotationDisplay
   :members:
```

## Extension entry point

```{eval-rst}
.. autofunction:: sphinx_autodoc_typehints_gp.setup
```
