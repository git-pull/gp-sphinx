import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Source files containing statically-declared CSS custom properties — every
 * `--name:` declaration in these is a public-contract member.
 */
const STATIC_SOURCES = [
  "src/furo/assets/styles/_scaffold.sass",
  "src/furo/assets/styles/variables/_colors.scss",
  "src/furo/assets/styles/variables/_fonts.scss",
  "src/furo/assets/styles/variables/_layout.scss",
  "src/furo/assets/styles/variables/_spacing.scss",
] as const;

/**
 * Names from `$admonitions` in
 * `src/furo/assets/styles/variables/_admonitions.scss`. The Sass `@each`
 * inside `@mixin admonitions` expands them into
 * `--color-admonition-title--<name>` and
 * `--color-admonition-title-background--<name>` declarations.
 *
 * Refresh this list by re-reading `_admonitions.scss` when bumping the Furo
 * pin; we keep it duplicated here because regex'ing through Sass `@each`
 * loops is a sharper edge than maintaining the list.
 */
const ADMONITION_NAMES = [
  "caution",
  "warning",
  "danger",
  "attention",
  "error",
  "hint",
  "tip",
  "important",
  "note",
  "seealso",
  "admonition-todo",
] as const;

/**
 * Names from `$icons` in
 * `src/furo/assets/styles/variables/_icons.scss`. The `@mixin icons` `@each`
 * expands them into `--icon-<name>` declarations.
 */
const ICON_NAMES = [
  "search",
  "pencil",
  "abstract",
  "info",
  "flame",
  "question",
  "warning",
  "failure",
  "spark",
] as const;

/**
 * Default-mixin tokens declared by `@mixin default-admonition` and
 * `@mixin default-topic` in `_admonitions.scss`. These mixins are invoked
 * once with a default color/icon, producing fixed token names.
 */
const DEFAULT_MIXIN_NAMES = [
  "--color-admonition-title",
  "--color-admonition-title-background",
  "--icon-admonition-default",
  "--color-topic-title",
  "--color-topic-title-background",
  "--icon-topic-default",
] as const;

const VAR_PATTERN = /(?<![\w-])(--[a-z][a-z0-9-]*)/g;

function extractStaticVars(content: string): Set<string> {
  const names = new Set<string>();
  for (const match of content.matchAll(VAR_PATTERN)) {
    const name = match[1];
    const start = match.index ?? 0;
    if (name && !content.slice(start, start + 64).includes("#{")) {
      names.add(name);
    }
  }
  return names;
}

function expandAdmonitionTokens(): string[] {
  const out: string[] = [];
  for (const name of ADMONITION_NAMES) {
    out.push(`--color-admonition-title--${name}`);
    out.push(`--color-admonition-title-background--${name}`);
  }
  return out;
}

function expandIconTokens(): string[] {
  return ICON_NAMES.map((name) => `--icon-${name}`);
}

function main(): void {
  const furoSourceDir = process.env.FURO_SOURCE_DIR;
  if (!furoSourceDir) {
    console.error(
      "FURO_SOURCE_DIR is not set. Point it at a Furo checkout, e.g.\n" +
        "  FURO_SOURCE_DIR=~/study/python/furo pnpm harvest",
    );
    process.exit(1);
  }

  const root = resolve(furoSourceDir);
  const allNames = new Set<string>();

  for (const rel of STATIC_SOURCES) {
    const full = join(root, rel);
    const content = readFileSync(full, "utf-8");
    for (const name of extractStaticVars(content)) {
      allNames.add(name);
    }
  }

  for (const name of expandAdmonitionTokens()) {
    allNames.add(name);
  }
  for (const name of expandIconTokens()) {
    allNames.add(name);
  }
  for (const name of DEFAULT_MIXIN_NAMES) {
    allNames.add(name);
  }

  const commit = execFileSync("git", ["-C", root, "rev-parse", "HEAD"], {
    encoding: "utf-8",
  }).trim();
  const harvestDate = new Date().toISOString().slice(0, 10);

  const fixture = {
    $comment:
      "Public CSS custom-property contract harvested from upstream Furo. " +
      "Regenerate with `pnpm harvest` (requires FURO_SOURCE_DIR pointing at a Furo checkout). " +
      "Do not edit by hand.",
    furoCommit: commit,
    harvestDate,
    sources: STATIC_SOURCES,
    dynamicSources: {
      admonitions: {
        file: "src/furo/assets/styles/variables/_admonitions.scss",
        names: ADMONITION_NAMES,
        emits: ["--color-admonition-title--<name>", "--color-admonition-title-background--<name>"],
      },
      icons: {
        file: "src/furo/assets/styles/variables/_icons.scss",
        names: ICON_NAMES,
        emits: ["--icon-<name>"],
      },
      defaultMixins: {
        file: "src/furo/assets/styles/variables/_admonitions.scss",
        names: DEFAULT_MIXIN_NAMES,
      },
    },
    names: [...allNames].sort(),
  };

  const here = dirname(fileURLToPath(import.meta.url));
  const out = join(here, "..", "upstream", "furo-vars.json");
  writeFileSync(out, `${JSON.stringify(fixture, null, 2)}\n`);
  console.log(`harvested ${allNames.size} tokens at ${commit.slice(0, 12)} -> ${out}`);
}

main();
