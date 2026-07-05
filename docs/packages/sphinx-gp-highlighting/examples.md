(sphinx-gp-highlighting-examples)=

# Examples

## Directory trees

Use `tree` for static project layouts. It highlights connector glyphs,
directory names, filenames, and comments without pretending the snippet
is a shell transcript.

```tree
python_module
├── tmuxp_plugin_my_plugin_module
│   ├── __init__.py
│   └── plugin.py
└── pyproject.toml  # Python project configuration file
```

The longer aliases render the same way:

```directory-tree
docs/
├── conf.py
├── index.md
└── packages/
```

```dir-tree
src/
└── package_name/
    └── __init__.py
```

## Inline literals

Explicit roles let prose declare intent while keeping the familiar
inline-code shape:

Run {cmd}`tmuxp freeze my-session`, then edit
{path}`~/.config/tmuxp/config.yaml`.

Store plugin modules under {dir}`./plugins/`.

## Safe automatic highlighting

Safe automatic highlighting is opt-in and command allow-list based:

```python
gp_highlighting_inline_literals = "safe"
gp_highlighting_inline_commands = ["tmuxp", "agentgrep"]
```

With that configuration, ordinary backtick literals such as
`tmuxp freeze my-session`, `agentgrep search mermaid`, and
`~/.config/tmuxp/` can receive the same package-owned inline classes,
while names such as `module_name` stay unchanged.
