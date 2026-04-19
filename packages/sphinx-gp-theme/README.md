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

## JavaScript events

The bundled SPA-navigation layer dispatches the following `CustomEvent`s on
`document`:

| Event | When | `event.detail` |
|-------|------|----------------|
| `gp-sphinx:navigated` | After an SPA page swap completes — the new `.article-container` / `.sidebar-tree` / `.toc-drawer` are in the DOM and the built-in reinit (copybutton, scroll-spy, theme toggle) has run. | `{ url: string }` — the new page URL. |

Widgets that bind event listeners to DOM inside `.article-container` should
listen for `gp-sphinx:navigated` in addition to `DOMContentLoaded`, because
that region is replaced in-place on every link click and old listeners are
destroyed along with it. Listeners on `document` or `window` (including those
added inside the handler) persist across swaps.

Minimal pattern:

```javascript
function init() {
  document.querySelectorAll(".my-widget").forEach(/* ... */);
}
document.addEventListener("DOMContentLoaded", init);
document.addEventListener("gp-sphinx:navigated", init);
```
