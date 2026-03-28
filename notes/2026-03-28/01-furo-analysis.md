# Furo Theme: Deep Analysis

> [Back to Overview](00-overview.md) | Next: [Phase 0 -- Shared Platform](02-phase-0-shared-platform.md)

## What Furo Is

Furo is a Sphinx documentation theme built on a four-layer stack:

1. **SCSS/SASS** compiled through Webpack + PostCSS (autoprefixer)
2. **Jinja2 templates** inheriting from `sphinx-basic-ng`
3. **Vanilla JavaScript** (~177 lines in `furo.js` + ~466 lines in `gumshoe-patched.js`)
4. **Python glue** (~576 lines across `__init__.py`, `navigation.py`, `sphinxext.py`)

**It does NOT use Tailwind.** All styling is hand-written SCSS with semantic CSS custom properties.

## Asset Pipeline

```
SASS source files (src/furo/assets/styles/)
    -> sass-loader (SCSS -> CSS)
    -> postcss-loader (autoprefixer)
    -> css-loader
    -> MiniCssExtractPlugin
    -> static output (src/furo/theme/furo/static/)
```

**Source**: `~/study/python/furo/webpack.config.js` (34 lines), `~/study/python/furo/postcss.config.js` (single plugin: `autoprefixer`).

Entry points in webpack: `furo` (main theme CSS + JS) and `furo-extensions` (extension compatibility CSS). The compiled artifacts land in `src/furo/theme/furo/static/`, which `sphinx-theme-builder` packages into the installable Python wheel.

## CSS Variable System

### Runtime-configurable (CSS custom properties)

`~/study/python/furo/src/furo/assets/styles/variables/_colors.scss` (~197 lines) defines:
- `@mixin colors` (light mode) and `@mixin colors-dark` (dark mode)
- Base colors: foreground (primary/secondary/muted/border), background
- Brand colors: primary, content, visited
- Component-specific: API docs, admonitions, tables, cards, headers, sidebar, ToC, links

Users override via `html_theme_options["light_css_variables"]` / `dark_css_variables` in `conf.py`. These are injected into `<style>` tags at runtime through:
- `~/study/python/furo/src/furo/theme/furo/partials/_head_css_variables.html` (29 lines)

After verification, ~185 unique CSS custom properties across compiled output.

### Compile-time (SCSS $variables)

`~/study/python/furo/src/furo/assets/styles/variables/_layout.scss` defines:
- `$content-padding: 3em`
- `$content-width: 46em`
- `$sidebar-width: 15em`
- `$full-width` (calculated)

These are used in **media queries** throughout `_scaffold.sass` (~430 lines). As the file itself notes: *"The fact that this makes the layout non-user-configurable is a good thing."* This means breakpoints and layout widths are baked in at compile time and cannot be changed without rebuilding the SCSS.

### Additional variable files

| File | Purpose |
|---|---|
| `_fonts.scss` | Font stacks (system fonts), font sizes as percentages |
| `_spacing.scss` | Header, sidebar, TOC spacing (CSS variables) |
| `_admonitions.scss` | SCSS map of admonition types to color + icon |

### Total CSS

| Category | Lines | Files |
|---|---|---|
| Variables | ~380 | 7 |
| Content styles | ~400 | 17 |
| Component styles | ~200 | 5 |
| Layout/scaffold | ~430 | 1 |
| Extensions | ~210 | 6 |
| Base | ~170 | 5 |
| **Total** | **~2,465** | **~40** |

## Template Architecture

**Theme config**: `~/study/python/furo/src/furo/theme/furo/theme.conf`

```ini
[theme]
inherit = basic-ng
stylesheet = styles/furo.css
pygments_style = a11y-light
```

**Base hierarchy**: `page.html` -> `base.html` -> (Sphinx's basic-ng templates)

- `page.html` (229 lines): Three-column layout (sidebar | main | TOC), announcement banner, mobile header, prev/next navigation, back-to-top button, theme toggle
- `base.html` (114 lines): HTML skeleton, meta tags, CSS/JS loading, dark mode detection script

**Sidebar components** (in `sidebar/`):
- `brand.html`, `search.html`, `navigation.html`, `variant-selector.html`

## JavaScript

`~/study/python/furo/src/furo/assets/scripts/furo.js` (177 lines):
1. **Theme toggle**: Light/Dark/Auto cycling, stores in `localStorage`
2. **Scroll handling**: Header shadow, back-to-top visibility
3. **TOC sync**: Uses Gumshoe (patched scrollspy, 466 lines) for current-section highlighting

## Python Integration

`~/study/python/furo/src/furo/__init__.py` (~398 lines):

- `setup(app)`: Registers theme via `app.add_html_theme("furo", THEME_PATH)`, adds config values, connects to hooks
- `_html_page_context()`: Injects `furo_navigation_tree`, `furo_hide_toc`, `furo_pygments`
- `get_pygments_stylesheet()`: Generates dynamic `pygments.css` for light/dark code highlighting
- `_overwrite_pygments_css()`: Overwrites Sphinx's default Pygments output (workaround)

`~/study/python/furo/src/furo/navigation.py` (83 lines):
- Uses **BeautifulSoup** to post-process Sphinx's toctree HTML
- Injects CSS-only collapsible navigation via checkbox/label pairs
- Marks current page in navigation tree

**Entry point** (from `~/study/python/furo/pyproject.toml`):
```toml
[project.entry-points]
"sphinx.html_themes" = { furo = "furo" }
```

## Strengths

- Clean separation of concerns in SCSS (variables -> base -> components -> content)
- CSS variables enable runtime customization without rebuilding
- Mobile-first responsive design
- Minimal JavaScript (only what is necessary)
- Handles Sphinx content complexity: admonitions, API domain signatures, nested toctrees, intersphinx, Pygments dark mode
- Thin Python integration (~576 lines total)
- Good accessibility (aria labels, keyboard navigation, skip links)

## Why It Hurts Across 14 Projects

### Duplicated Configuration

Every project repeats the same extension stack. Compare:

**vcspull** (`~/work/python/vcspull/docs/conf.py`):
```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_fonts",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "argparse_exemplar",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
    "sphinxext.opengraph",
    "sphinxext.rediraffe",
    "sphinx_design",
    "myst_parser",
    "linkify_issues",
]
```

**libtmux**, **libvcs**, **gp-libs**, **cihai**, **unihan-etl**, **unihan-db** -- all have nearly identical lists.

### Duplicated Workarounds

Every project carries the same `setup()` hack:
```python
def setup(app: Sphinx) -> None:
    # Remove sphinx_inline_tabs tabs.js (workaround for #18)
    # Add spa-nav.js for SPA-like navigation
    ...
```

### Duplicated Theme Configuration

Each `conf.py` repeats the same `html_theme_options`:
- Custom logos (light/dark SVG)
- GitHub footer icons
- IBM Plex fonts via Fontsource
- Custom sidebars (brand, search, navigation, projects)

## Fork Difficulty Assessment

### If forking Furo as a theme: **Medium**

- **Easy**: Branding, tokens, typography, JS cleanup, layout changes
- **Moderate**: Redesigning nav generation, cleaning template system, reducing build complexity
- **Hard**: Preserving compatibility with arbitrary Sphinx extensions

### If replacing the asset pipeline: **Medium**

The SCSS/Webpack pipeline can be replaced with Tailwind CSS v4 + Vite. Furo's CSS variables map naturally to Tailwind's `@theme` system. The few SCSS-specific features used:

| SCSS Feature | Tailwind/CSS Equivalent |
|---|---|
| `@mixin`/`@include` | CSS cascade layers or class selectors |
| `$variable` for layout | CSS custom properties + `@container` queries |
| `@each` loops for admonitions | Tailwind plugin or build script |
| `rgba()` with SCSS vars | `color-mix()` in modern CSS |
| `@use`/`@forward` module system | CSS `@import` or `@layer` |

### The real cost: ongoing maintenance

Furo is actively maintained and handles edge cases:
- New Sphinx versions changing internal APIs
- Docutils version differences
- Extension compatibility (`furo-extensions.css` bridges sphinx-design, sphinx-inline-tabs, sphinx-copybutton, sphinx-panels, ReadTheDocs)
- Accessibility improvements

With 14+ projects depending on the theme, every Sphinx minor bump is a potential breakage point.

## Bottom Line

Furo is not the problem. The duplicated docs platform is the problem. The practical path is to consolidate shared configuration into `gp_sphinx` first (see [Phase 0](02-phase-0-shared-platform.md)), then evaluate whether the rendering layer needs to change.
