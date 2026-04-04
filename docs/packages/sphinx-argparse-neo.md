# sphinx-argparse-neo

{bdg-success-line}`Beta` {bdg-primary}`extension`

Sphinx extension for documenting argparse-based CLI tools. Renders argument
parsers as structured documentation with usage sections, argument groups,
subcommands, and optional epilog-to-section transformation.

```console
$ pip install sphinx-argparse-neo
```

Or as a gp-sphinx optional extra:

```console
$ pip install gp-sphinx[argparse]
```

## Usage

Add to your Sphinx extensions:

```python
extensions = ["sphinx_argparse_neo"]
```

Then use the `argparse` directive:

```rst
.. argparse::
   :module: myapp.cli
   :func: create_parser
   :prog: myapp
```

## Base extension config values

| Config | Default | Description |
|--------|---------|-------------|
| `argparse_group_title_prefix` | `""` | Prefix for argument group titles |
| `argparse_show_defaults` | `True` | Show default values in argument docs |
| `argparse_show_choices` | `True` | Show choice constraints |
| `argparse_show_types` | `True` | Show type information |

## argparse directive options

Key options for the `.. argparse::` directive:

| Option | Description |
|--------|-------------|
| `:module:` | Python module containing the parser factory |
| `:func:` | Function that returns an `ArgumentParser` |
| `:prog:` | Program name for usage display |
| `:path:` | Subcommand path (e.g., `sub1 sub2`) |
| `:nodefault:` | Suppress default value display |
| `:nosubcommands:` | Suppress subcommand documentation |
| `:nosectionheading:` | Use rubrics instead of heading sections |

## Exemplar sub-extension

The exemplar layer adds enhanced features on top of the base directive.
Add it separately:

```python
extensions = ["sphinx_argparse_neo", "sphinx_argparse_neo.exemplar"]
```

### Exemplar config values

| Config | Default | Description |
|--------|---------|-------------|
| `argparse_examples_term_suffix` | `"examples"` | Term suffix for examples detection |
| `argparse_examples_base_term` | `"examples"` | Base term for examples matching |
| `argparse_examples_section_title` | `"Examples"` | Section title for extracted examples |
| `argparse_usage_pattern` | `"usage:"` | Pattern to detect usage blocks |
| `argparse_examples_command_prefix` | `"$ "` | Prefix for example commands |
| `argparse_examples_code_language` | `"console"` | Language for example code blocks |
| `argparse_examples_code_classes` | `("highlight-console",)` | CSS classes for example blocks |
| `argparse_usage_code_language` | `"cli-usage"` | Language for usage code blocks |
| `argparse_reorder_usage_before_examples` | `True` | Move usage before examples |

### Pygments lexers

Registered by the exemplar extension, not the base:

| Lexer | Description |
|-------|-------------|
| `argparse` | General argparse output |
| `argparse-usage` | Usage line formatting |
| `argparse-help` | Help text formatting |
| `cli-usage` | CLI usage block formatting |

### CLI inline roles

Registered by the exemplar via `register_roles()`:

| Role | Description |
|------|-------------|
| `:cli-option:` | CLI options (`--verbose`, `-h`) |
| `:cli-metavar:` | Metavar placeholders (`FILE`, `PATH`) |
| `:cli-command:` | Command names (`sync`, `add`) |
| `:cli-default:` | Default values (`None`, `"default"`) |
| `:cli-choice:` | Choice values (`json`, `yaml`) |

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-argparse-neo)
