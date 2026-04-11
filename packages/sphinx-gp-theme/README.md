# sphinx-gp-theme

Furo child theme for [git-pull](https://github.com/git-pull) project documentation.

Inherits from [Furo](https://pradyunsg.me/furo/) and bundles shared templates,
custom CSS (heading refinements, TOC, typography, view transitions), SPA navigation
JS, and the git-pull project sidebar.

## Install

```console
$ pip install sphinx-gp-theme
```

## Usage

In your `docs/conf.py`:

```python
html_theme = "sphinx-gp-theme"
```

Or use with [gp-sphinx](https://gp-sphinx.git-pull.com) which sets the theme automatically.
