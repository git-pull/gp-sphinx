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
    extra_extensions=["argparse_exemplar", "sphinx_click"],
)
```

### Removing default extensions

```python
conf = merge_sphinx_config(
    # ...
    remove_extensions=["sphinx_design"],
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

[pip]: https://pip.pypa.io/en/stable/
[pipx]: https://pypa.github.io/pipx/docs/
[uv]: https://docs.astral.sh/uv/
