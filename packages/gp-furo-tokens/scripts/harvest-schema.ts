import { z } from "zod";

/**
 * Structural contract for `upstream/furo-vars.json`.
 *
 * `z.strictObject` rejects unknown keys, so a hand-edit or a harvest
 * script regression that adds, drops, or renames a field fails loudly —
 * on write (harvest validates before serializing) and on read
 * (contract.test parses the shipped fixture).
 *
 * Lives in `scripts/` rather than `src/` because the harvest script runs
 * under Node's native type stripping, which resolves literal import
 * paths only — it cannot follow the `.js`-suffixed specifiers used
 * between `src/` modules. Self-contained (imports zod only) so both the
 * script and the tests can reach it with an explicit `.ts` import.
 */

const CssVarName = z.string().regex(/^--[a-z][a-z0-9-]*$/);

const HarvestedSourceFile = z.string().regex(/^src\/furo\/assets\/styles\//);

export const FuroVarsSchema = z.strictObject({
  $comment: z.string().min(1),
  furoCommit: z.string().regex(/^[0-9a-f]{40}$/),
  harvestDate: z.iso.date(),
  sources: z.array(HarvestedSourceFile).min(1),
  dynamicSources: z.strictObject({
    admonitions: z.strictObject({
      file: HarvestedSourceFile,
      names: z.array(z.string().min(1)).min(1),
      emits: z.array(z.string().min(1)).min(1),
    }),
    icons: z.strictObject({
      file: HarvestedSourceFile,
      names: z.array(z.string().min(1)).min(1),
      emits: z.array(z.string().min(1)).min(1),
    }),
    defaultMixins: z.strictObject({
      file: HarvestedSourceFile,
      names: z.array(CssVarName).min(1),
    }),
  }),
  names: z
    .array(CssVarName)
    .min(1)
    .refine((names) => names.every((name, i) => i === 0 || (names[i - 1] as string) < name), {
      error: "names must be sorted and unique",
    }),
});

export type FuroVarsFixture = z.infer<typeof FuroVarsSchema>;
