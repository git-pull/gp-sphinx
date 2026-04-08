# sphinx-autodoc-layout

Componentized layout for Sphinx autodoc output. It preserves Sphinx's
outer `dl / dt / dd` structure while rebuilding managed Python autodoc
entries into stable `api-*` components, folding block parameter sections
with native `<details>`, and rendering inline signature disclosure with
Sphinx's native multiline parameter-list markup. Expanded folded
signatures show annotations by default and can be configured with
`gal_signature_show_annotations`.
