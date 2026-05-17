# sphinx-ux-octicons

Curated GitHub Octicons exposed as a Sphinx `{octicon}` role under the
`gp-sphinx-octicon` CSS namespace.

## Install

```console
$ pip install sphinx-ux-octicons
```

## Usage

Add the extension to your `conf.py`:

```python
extensions = ["sphinx_ux_octicons"]
```

Then reference any bundled icon in MyST or reStructuredText:

```markdown
Launch with {octicon}`rocket` or {octicon}`rocket;1.5em` or
{octicon}`rocket;24px;my-extra-class`.
```

## Bundled icons

`rocket`, `tools`, `book`, `light-bulb`, `star`, `alert`, `terminal`,
`paintbrush`, `code`, `device-camera`, `diff`, `link`, `home`, `gear`,
`package`, `info`, `check-circle`, `x-circle`.
