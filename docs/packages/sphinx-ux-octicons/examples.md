(sphinx-ux-octicons-examples)=

# Examples

## Every bundled icon

Each icon below is rendered by the real `{octicon}` role at `1.5rem`:

```{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Rendered
  - Role
* - `rocket`
  - {octicon}`rocket;1.5rem`
  - `` {octicon}`rocket;1.5rem` ``
* - `tools`
  - {octicon}`tools;1.5rem`
  - `` {octicon}`tools;1.5rem` ``
* - `book`
  - {octicon}`book;1.5rem`
  - `` {octicon}`book;1.5rem` ``
* - `light-bulb`
  - {octicon}`light-bulb;1.5rem`
  - `` {octicon}`light-bulb;1.5rem` ``
* - `star`
  - {octicon}`star;1.5rem`
  - `` {octicon}`star;1.5rem` ``
* - `alert`
  - {octicon}`alert;1.5rem`
  - `` {octicon}`alert;1.5rem` ``
* - `terminal`
  - {octicon}`terminal;1.5rem`
  - `` {octicon}`terminal;1.5rem` ``
* - `paintbrush`
  - {octicon}`paintbrush;1.5rem`
  - `` {octicon}`paintbrush;1.5rem` ``
* - `code`
  - {octicon}`code;1.5rem`
  - `` {octicon}`code;1.5rem` ``
* - `device-camera`
  - {octicon}`device-camera;1.5rem`
  - `` {octicon}`device-camera;1.5rem` ``
* - `diff`
  - {octicon}`diff;1.5rem`
  - `` {octicon}`diff;1.5rem` ``
* - `link`
  - {octicon}`link;1.5rem`
  - `` {octicon}`link;1.5rem` ``
* - `home`
  - {octicon}`home;1.5rem`
  - `` {octicon}`home;1.5rem` ``
* - `gear`
  - {octicon}`gear;1.5rem`
  - `` {octicon}`gear;1.5rem` ``
* - `package`
  - {octicon}`package;1.5rem`
  - `` {octicon}`package;1.5rem` ``
* - `info`
  - {octicon}`info;1.5rem`
  - `` {octicon}`info;1.5rem` ``
* - `check-circle`
  - {octicon}`check-circle;1.5rem`
  - `` {octicon}`check-circle;1.5rem` ``
* - `x-circle`
  - {octicon}`x-circle;1.5rem`
  - `` {octicon}`x-circle;1.5rem` ``
```

## Icons inherit text colour

Wrap the role in a span with a colour class to tint the icon:

<span style="color: var(--color-brand-primary, #2962ff)">{octicon}`rocket` Ship it</span>

<span style="color: var(--color-warning, #b08800)">{octicon}`alert` Heads up</span>

<span style="color: var(--color-success, #2ea043)">{octicon}`check-circle` Looks good</span>

## RST authoring

The role is also available as a reStructuredText role. Both syntaxes
emit the same SVG markup.

```{eval-rst}
Build it with :octicon:`rocket;1.5rem`, document it with :octicon:`book;1.5rem`,
ship it with :octicon:`check-circle;1.5rem`.
```
