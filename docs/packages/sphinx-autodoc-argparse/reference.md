(sphinx-autodoc-argparse-reference)=

# API Reference

## Cross-reference roles

Every `.. argparse::` block populates a dedicated `argparse` domain
alongside the existing `std:cmdoption` entries.  Use these roles to
link to programs, options, subcommands, and positional arguments
declared anywhere in the project:

| Role | Resolves to | Example |
|------|-------------|---------|
| `:argparse:program:` | A top-level program | `` :argparse:program:`myapp` `` |
| `:argparse:option:` | An optional flag, scoped by program | `` :argparse:option:`myapp --verbose` `` or `` :argparse:option:`myapp sync --force` `` |
| `:argparse:subcommand:` | A subcommand under a parent program | `` :argparse:subcommand:`myapp sync` `` |
| `:argparse:positional:` | A positional argument, scoped by program | `` :argparse:positional:`myapp FILE` `` |

Whitespace-joined targets (`myapp sync --force`) are split on the final
space to match the stored `(program, name)` tuple.  Bare forms
(`--verbose`) also resolve when only one registration matches, though
the fully-qualified form is preferred for multi-program sites.

### Auto-generated indices

Two domain indices are built into every project that loads the
extension:

- `argparse-programsindex` — alphabetised list of every registered
  program; link via `` :ref:`argparse-programsindex` ``.
- `argparse-optionsindex` — options grouped by program, alphabetised
  within each group; link via `` :ref:`argparse-optionsindex` ``.

### Intersphinx compatibility

The classic `:option:` / `std:cmdoption` emission is preserved — both
roles resolve and both appear in `objects.inv`.  Downstream consumers
linking via intersphinx continue to work; new authoring inside
projects using this extension can prefer the `:argparse:*` namespace
for program-scoped clarity.

## Configuration values

### Base extension

```{eval-rst}
.. autoconfigvalues:: sphinx_autodoc_argparse
```

### Exemplar layer

```{eval-rst}
.. autoconfigvalues:: sphinx_autodoc_argparse.exemplar
```

## Extension entry point

```{eval-rst}
.. autofunction:: sphinx_autodoc_argparse.setup
```
