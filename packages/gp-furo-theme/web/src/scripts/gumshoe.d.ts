/**
 * Minimal type surface for the vendored gumshoe.js scrollspy library.
 *
 * Covers only the constructor signature and option fields furo.ts uses;
 * the underlying library exposes more (`destroy()`, `setup()`, custom
 * events). Extend this stub if more surface lands.
 */
declare module "./gumshoe.js" {
  export interface GumshoeOptions {
    /** Re-detect headings on every scroll. Furo sets this to true. */
    reflow?: boolean;
    /** Highlight every ancestor in nested lists. Furo sets this to true. */
    recursive?: boolean;
    /** Class added to the active link's `<li>`. Furo sets `"scroll-current"`. */
    navClass?: string;
    /** Pixels to offset detection by; can be a function recomputed per scroll. */
    offset?: number | (() => number);
  }

  export default class Gumshoe {
    constructor(selector: string, options?: GumshoeOptions);
  }
}

// Marks this `.d.ts` file as a module so the ambient `declare module`
// above is parsed as an external module declaration rather than a
// script-scoped block.
export {};
