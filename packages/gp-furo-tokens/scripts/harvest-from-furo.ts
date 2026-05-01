import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SOURCES = [
  "src/furo/assets/styles/_scaffold.sass",
  "src/furo/assets/styles/variables/_colors.scss",
  "src/furo/assets/styles/variables/_layout.scss",
  "src/furo/assets/styles/variables/_spacing.scss",
] as const;

const VAR_PATTERN = /(?<![\w-])(--[a-z][a-z0-9-]*)/g;

function extractVars(content: string): Set<string> {
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
  for (const rel of SOURCES) {
    const full = join(root, rel);
    const content = readFileSync(full, "utf-8");
    for (const name of extractVars(content)) {
      allNames.add(name);
    }
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
    sources: SOURCES,
    names: [...allNames].sort(),
  };

  const here = dirname(fileURLToPath(import.meta.url));
  const out = join(here, "..", "upstream", "furo-vars.json");
  writeFileSync(out, `${JSON.stringify(fixture, null, 2)}\n`);
  console.log(`harvested ${allNames.size} tokens at ${commit.slice(0, 12)} -> ${out}`);
}

main();
