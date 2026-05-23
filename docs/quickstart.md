(quickstart)=

# Quickstart

## Installation

For latest official version:

```console
$ pip install --user gp-sphinx
```

Upgrading:

```console
$ pip install --user --upgrade gp-sphinx
```

(developmental-releases)=

### Developmental releases

New versions of gp-sphinx are published to PyPI as alpha, beta, or release candidates.
In their versions you will see notification like `a1`, `b1`, and `rc1`, respectively.
`1.0.0b4` would mean the 4th beta release of `1.0.0` before general availability.

- [pip]\:

  ```console
  $ pip install --user --upgrade --pre gp-sphinx
  ```

- [pipx]\:

  ```console
  $ pipx install --suffix=@next 'gp-sphinx' --pip-args '\--pre' --force
  ```

- [uv]\:

  ```console
  $ uv add gp-sphinx --prerelease allow
  ```

via trunk (can break easily):

- [pip]\:

  ```console
  $ pip install --user -e git+https://github.com/git-pull/gp-sphinx.git#egg=gp-sphinx
  ```

- [uv]\:

  ```console
  $ uv add gp-sphinx --from git+https://github.com/git-pull/gp-sphinx.git
  ```

## Usage

In your project's `docs/conf.py`:

```python
"""Sphinx configuration for my-project."""
from __future__ import annotations

from gp_sphinx.config import merge_sphinx_config

import my_project

conf = merge_sphinx_config(
    project="my-project",
    version=my_project.__version__,
    copyright="2026, Tony Narlock",
    source_repository="https://github.com/git-pull/my-project/",
    intersphinx_mapping={
        "py": ("https://docs.python.org/", None),
    },
)
globals().update(conf)
```

### Adding extra extensions

```python
conf = merge_sphinx_config(
    # ...
    extra_extensions=["sphinx_autodoc_argparse.exemplar", "sphinx_click"],
)
```

### Removing default extensions

```python
conf = merge_sphinx_config(
    # ...
    remove_extensions=["sphinx_copybutton"],
)
```

### Custom theme options

```python
conf = merge_sphinx_config(
    # ...
    light_logo="img/my-logo.svg",
    dark_logo="img/my-logo-dark.svg",
    theme_options={"sidebar_hide_name": True},
)
```

## Your first build

Create a docs directory with a static assets folder:

```console
$ mkdir -p docs/_static
```

Create a minimal `docs/index.md`:

```markdown
# My Project

Welcome to my project documentation.
```

Create `docs/conf.py` using the pattern from {ref}`Usage <quickstart>` above.

Build the HTML output:

```console
$ uv run sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in your browser to see the result.

## Seeing the autodoc design system

The build above renders a Furo-themed page with IBM Plex fonts.  To see the
full autodoc stack — badges, type hints, and card layout — document a Python
module.

Create a file `my_module.py` next to your `docs/` directory:

```python
"""Demo module for the autodoc design system."""
from __future__ import annotations

from typing import Any


def get_user(
    *,
    user_id: int,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Fetch a user from the database.

    Parameters
    ----------
    user_id : int
        The ID of the user to fetch.
    use_cache : bool
        If ``True``, attempts to use a cache.

    Returns
    -------
    dict[str, Any]
        A dictionary of user properties.
    """
    return {"id": user_id, "name": "Demo User"}
```

Enable the API style extension in your `docs/conf.py`:

```python
conf = merge_sphinx_config(
    # ... existing parameters ...
    extra_extensions=["sphinx_autodoc_api_style"],
)
```

Create `docs/api.md`:

````markdown
# API Reference

```{eval-rst}
.. automodule:: my_module
   :members:
```
````

Rebuild:

```console
$ uv run sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/api.html`.  The function renders with type and modifier
**badges**, clean **type hints** with cross-referenced links, and a **card
layout** with parameter sections.

See the {doc}`gallery` for a full showcase of every component.

[pip]: https://pip.pypa.io/en/stable/
[pipx]: https://pypa.github.io/pipx/docs/
[uv]: https://docs.astral.sh/uv/
