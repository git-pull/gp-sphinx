(sphinx-autodoc-argparse-examples)=

# Examples

## Live demos

### Base parser rendering

```{argparse}
:module: demo_cli
:func: create_parser
:prog: myapp
```

### Subcommand rendering

Drill into a single subcommand with `:path:`:

```{argparse}
:module: demo_cli
:func: create_parser
:path: mysubcommand
:prog: myapp
```

### Inline roles

The exemplar layer also registers live inline roles for CLI prose:
{cli-command}`myapp`, {cli-option}`--verbose`, {cli-choice}`json`,
{cli-metavar}`DIR`, and {cli-default}`text`.
