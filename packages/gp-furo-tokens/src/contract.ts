import { z } from "zod";

/**
 * Furo's public CSS custom-property contract.
 *
 * Sourced from upstream Furo's SCSS at the pinned commit; see
 * `upstream/furo-vars.json` for provenance and `pnpm harvest` for
 * regeneration. Consumers depend on this set as a literal-union type so
 * downstream Tailwind plugins and theme configs get exhaustive checks.
 */
export const FURO_TOKEN_NAMES = [
  "--admonition-font-size",
  "--admonition-title-font-size",
  "--api-font-size",
  "--code-font-size",
  "--color-admonition-background",
  "--color-admonition-title",
  "--color-admonition-title--admonition-todo",
  "--color-admonition-title--attention",
  "--color-admonition-title--caution",
  "--color-admonition-title--danger",
  "--color-admonition-title--error",
  "--color-admonition-title--hint",
  "--color-admonition-title--important",
  "--color-admonition-title--note",
  "--color-admonition-title--seealso",
  "--color-admonition-title--tip",
  "--color-admonition-title--warning",
  "--color-admonition-title-background",
  "--color-admonition-title-background--admonition-todo",
  "--color-admonition-title-background--attention",
  "--color-admonition-title-background--caution",
  "--color-admonition-title-background--danger",
  "--color-admonition-title-background--error",
  "--color-admonition-title-background--hint",
  "--color-admonition-title-background--important",
  "--color-admonition-title-background--note",
  "--color-admonition-title-background--seealso",
  "--color-admonition-title-background--tip",
  "--color-admonition-title-background--warning",
  "--color-announcement-background",
  "--color-announcement-text",
  "--color-api-added",
  "--color-api-added-border",
  "--color-api-background",
  "--color-api-background-hover",
  "--color-api-changed",
  "--color-api-changed-border",
  "--color-api-deprecated",
  "--color-api-deprecated-border",
  "--color-api-keyword",
  "--color-api-name",
  "--color-api-overall",
  "--color-api-paren",
  "--color-api-pre-name",
  "--color-api-removed",
  "--color-api-removed-border",
  "--color-background-border",
  "--color-background-hover",
  "--color-background-hover--transparent",
  "--color-background-item",
  "--color-background-muted",
  "--color-background-primary",
  "--color-background-secondary",
  "--color-brand-content",
  "--color-brand-primary",
  "--color-brand-visited",
  "--color-card-background",
  "--color-card-border",
  "--color-card-marginals-background",
  "--color-content-background",
  "--color-content-foreground",
  "--color-foreground-border",
  "--color-foreground-muted",
  "--color-foreground-primary",
  "--color-foreground-secondary",
  "--color-guilabel-background",
  "--color-guilabel-border",
  "--color-guilabel-text",
  "--color-header-background",
  "--color-header-border",
  "--color-header-text",
  "--color-highlight-on-target",
  "--color-highlighted-background",
  "--color-highlighted-text",
  "--color-inline-code-background",
  "--color-link",
  "--color-link--hover",
  "--color-link--visited",
  "--color-link--visited--hover",
  "--color-link-underline",
  "--color-link-underline--hover",
  "--color-link-underline--visited",
  "--color-link-underline--visited--hover",
  "--color-problematic",
  "--color-sidebar-background",
  "--color-sidebar-background-border",
  "--color-sidebar-brand-text",
  "--color-sidebar-caption-text",
  "--color-sidebar-item-background",
  "--color-sidebar-item-background--current",
  "--color-sidebar-item-background--hover",
  "--color-sidebar-item-expander-background",
  "--color-sidebar-item-expander-background--hover",
  "--color-sidebar-link-text",
  "--color-sidebar-link-text--top-level",
  "--color-sidebar-search-background",
  "--color-sidebar-search-background--focus",
  "--color-sidebar-search-border",
  "--color-sidebar-search-icon",
  "--color-sidebar-search-text",
  "--color-table-border",
  "--color-table-header-background",
  "--color-toc-background",
  "--color-toc-item-text",
  "--color-toc-item-text--active",
  "--color-toc-item-text--hover",
  "--color-toc-title-text",
  "--color-topic-title",
  "--color-topic-title-background",
  "--font-size--normal",
  "--font-size--small",
  "--font-size--small--2",
  "--font-size--small--3",
  "--font-size--small--4",
  "--font-stack",
  "--font-stack--headings",
  "--font-stack--monospace",
  "--header-height",
  "--header-padding",
  "--icon-abstract",
  "--icon-admonition-default",
  "--icon-failure",
  "--icon-flame",
  "--icon-info",
  "--icon-pencil",
  "--icon-question",
  "--icon-search",
  "--icon-spark",
  "--icon-topic-default",
  "--icon-warning",
  "--sidebar-caption-font-size",
  "--sidebar-caption-space-above",
  "--sidebar-expander-width",
  "--sidebar-item-font-size",
  "--sidebar-item-height",
  "--sidebar-item-line-height",
  "--sidebar-item-spacing-horizontal",
  "--sidebar-item-spacing-vertical",
  "--sidebar-search-icon-size",
  "--sidebar-search-input-font-size",
  "--sidebar-search-input-height",
  "--sidebar-search-input-spacing-horizontal",
  "--sidebar-search-input-spacing-vertical",
  "--sidebar-search-space-above",
  "--sidebar-tree-space-above",
  "--toc-font-size",
  "--toc-font-size--mobile",
  "--toc-item-spacing-horizontal",
  "--toc-item-spacing-vertical",
  "--toc-spacing-horizontal",
  "--toc-spacing-vertical",
  "--toc-title-font-size",
  "--toc-title-padding",
] as const;

export type FuroTokenName = (typeof FURO_TOKEN_NAMES)[number];

export const FuroTokenNameSchema = z.enum(FURO_TOKEN_NAMES);

/**
 * gp-sphinx semantic type-role names — workspace additions, distinct from
 * Furo's contract.
 *
 * Kept as a separate const so the Furo contract test's "does not invent
 * CSS custom properties Furo does not declare" assertion still passes.
 * Values live in {@link GP_SPHINX_ROLE_TOKENS} (`./roles.js`).
 */
export const GP_SPHINX_ROLE_NAMES = [
  "--gp-sphinx-type-body",
  "--gp-sphinx-type-code-inline",
  "--gp-sphinx-type-icon-glyph",
  "--gp-sphinx-type-metadata",
] as const;

export type GpSphinxRoleName = (typeof GP_SPHINX_ROLE_NAMES)[number];

export const GpSphinxRoleNameSchema = z.enum(GP_SPHINX_ROLE_NAMES);

/**
 * Runtime validators for token value maps.
 *
 * zod 4's `z.record` with an enum key schema is exhaustive — every
 * contract name must be present and unknown keys are rejected — while
 * `z.partialRecord` accepts any subset but still rejects names outside
 * the contract. Exported so downstream consumers can validate override
 * maps (e.g. values destined for Furo's `light_css_variables` /
 * `dark_css_variables`) against the contract before shipping them.
 *
 * Values are plain `z.string()` on purpose: the contract preserves
 * Furo's values verbatim, including the intentionally-empty
 * `--color-background-muted` slot (see `light.ts`).
 */
export const FuroTokenMapSchema = z.record(FuroTokenNameSchema, z.string());

export const FuroPartialTokenMapSchema = z.partialRecord(FuroTokenNameSchema, z.string());

export const GpSphinxRoleMapSchema = z.record(GpSphinxRoleNameSchema, z.string());
