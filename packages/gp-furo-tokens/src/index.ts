import pkg from "../package.json" with { type: "json" };

export { FURO_TOKEN_NAMES, FuroTokenNameSchema, type FuroTokenName } from "./contract.js";
export {
  GP_SPHINX_ROLE_NAMES,
  GpSphinxRoleNameSchema,
  type GpSphinxRoleName,
} from "./contract.js";
export {
  FuroPartialTokenMapSchema,
  FuroTokenMapSchema,
  GpSphinxRoleMapSchema,
} from "./contract.js";
export { FURO_LIGHT_TOKENS } from "./light.js";
export { FURO_DARK_TOKENS } from "./dark.js";
export { GP_SPHINX_ROLE_TOKENS } from "./roles.js";

// Derived from the manifest so the export can never drift from the
// published version.
export const FURO_TOKENS_VERSION: string = pkg.version;
