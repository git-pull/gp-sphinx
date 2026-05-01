# @gp-sphinx/furo-tokens

The Furo CSS custom-property contract as a Zod-validated TypeScript token map
and Tailwind v4 plugin. Consumed by `gp-furo-theme` to drive Tailwind's
`@theme inline` block while preserving Furo's public override surface
(`html_theme_options["light_css_variables"]`,
`html_theme_options["dark_css_variables"]`).

The token list is harvested programmatically from the upstream Furo SCSS
sources by the contract test, so adding or removing a token there triggers
a build failure here.

## Status

Scaffold only — token contract and Tailwind plugin land in subsequent commits.

## Attribution

Token names are derived from [Furo](https://github.com/pradyunsg/furo)
(MIT, Pradyun Gedam). Source values are transcribed from
`src/furo/assets/styles/_scaffold.sass` and
`src/furo/assets/styles/variables/{_colors,_layout,_spacing}.scss`.
