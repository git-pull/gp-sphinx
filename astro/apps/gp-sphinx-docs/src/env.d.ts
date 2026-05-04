/// <reference types="astro/client" />

// @pagefind/default-ui ships no .d.ts and isn't on DefinitelyTyped. The
// SearchBox component already narrows the dynamic import via an inline
// `as { PagefindUI: ... }` cast; this declaration just satisfies tsc's
// ts(7016) "implicitly any" check at the import site.
declare module '@pagefind/default-ui'
