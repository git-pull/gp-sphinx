// Ported from furo 2025.12.19 (b788b8a) (assets/scripts/furo.js), MIT (Pradyun
// Gedam). See LICENSE-FURO at the package root. Behavioral parity with
// upstream Furo is the byte-equivalence target; structure mirrors
// upstream's section comments to keep diffs reviewable.
//
// Strict TypeScript per gp-sphinx porting policy: code we author from
// scratch passes strict mypy/tsc rather than carrying upstream's loose
// JS-ism into the bundle.

import Gumshoe from "./gumshoe.js";

// IIFE wrapper to isolate top-level declarations from the page's global
// scope. The bundle is loaded as a classic <script> by Sphinx (no
// type="module" attribute), so anything at module scope here would leak.
// doctools.js:147 already declares `const _ = Documentation.gettext` at
// global scope — without this wrapper, Rollup's minifier collapses our
// `readTheme()` helper to `function _()` at the top level of the bundle,
// triggering a `SyntaxError: Identifier '_' has already been declared`
// on every page load and silently breaking the theme toggle, scroll-spy,
// back-to-top, and mobile drawer behaviours.
//
// Matches upstream Furo's bundling approach: their `furo.js` is also
// IIFE-wrapped at the source level. The `import` above stays at module
// scope (ESM imports must be top-level) so Rollup can resolve Gumshoe;
// `Gumshoe` is captured by closure inside the IIFE.
(function (): void {
type ThemeMode = "light" | "dark" | "auto";

const GO_TO_TOP_OFFSET = 64;

// Module-level state populated by ``main()`` at DOMContentLoaded.
let tocScroll: HTMLElement | null = null;
let header: HTMLElement | null = null;
let lastScrollTop = document.documentElement.scrollTop;

////////////////////////////////////////////////////////////////////////////////
// Scroll Handling
////////////////////////////////////////////////////////////////////////////////

function scrollHandlerForHeader(positionY: number): void {
  if (header === null) {
    return;
  }
  if (positionY > 0) {
    header.classList.add("scrolled");
  } else {
    header.classList.remove("scrolled");
  }
}

function scrollHandlerForBackToTop(positionY: number): void {
  const root = document.documentElement;
  if (positionY < GO_TO_TOP_OFFSET) {
    root.classList.remove("show-back-to-top");
  } else if (positionY < lastScrollTop) {
    root.classList.add("show-back-to-top");
  } else if (positionY > lastScrollTop) {
    root.classList.remove("show-back-to-top");
  }
  lastScrollTop = positionY;
}

function scrollHandlerForTOC(positionY: number): void {
  if (tocScroll === null) {
    return;
  }

  // top of page.
  if (positionY === 0) {
    tocScroll.scrollTo(0, 0);
    return;
  }

  // bottom of page.
  if (
    Math.ceil(positionY) >=
    Math.floor(document.documentElement.scrollHeight - window.innerHeight)
  ) {
    tocScroll.scrollTo(0, tocScroll.scrollHeight);
    return;
  }

  // somewhere in the middle: confirm there's a current entry but don't
  // scroll-into-view (https://github.com/pypa/pip/issues/9159 — broke
  // scroll behaviors). Mirrors upstream Furo's commented-out block.
  document.querySelector(".scroll-current");
}

function scrollHandler(positionY: number): void {
  scrollHandlerForHeader(positionY);
  scrollHandlerForBackToTop(positionY);
  scrollHandlerForTOC(positionY);
}

////////////////////////////////////////////////////////////////////////////////
// Theme Toggle
////////////////////////////////////////////////////////////////////////////////

function setTheme(mode: ThemeMode): void {
  document.body.dataset.theme = mode;
  localStorage.setItem("theme", mode);
  console.log(`Changed to ${mode} mode.`);
}

function readTheme(): ThemeMode {
  const stored = localStorage.getItem("theme");
  if (stored === "light" || stored === "dark" || stored === "auto") {
    return stored;
  }
  return "auto";
}

function cycleThemeOnce(): void {
  const currentTheme = readTheme();
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  if (prefersDark) {
    // Auto (dark) -> Light -> Dark -> Auto
    if (currentTheme === "auto") {
      setTheme("light");
    } else if (currentTheme === "light") {
      setTheme("dark");
    } else {
      setTheme("auto");
    }
  } else {
    // Auto (light) -> Dark -> Light -> Auto
    if (currentTheme === "auto") {
      setTheme("dark");
    } else if (currentTheme === "dark") {
      setTheme("light");
    } else {
      setTheme("auto");
    }
  }
}

////////////////////////////////////////////////////////////////////////////////
// Setup
////////////////////////////////////////////////////////////////////////////////

function setupScrollHandler(): void {
  // Pattern from MDN — debounce scroll handler to one rAF tick.
  let lastKnownScrollPosition = 0;
  let ticking = false;

  window.addEventListener("scroll", () => {
    lastKnownScrollPosition = window.scrollY;
    if (!ticking) {
      window.requestAnimationFrame(() => {
        scrollHandler(lastKnownScrollPosition);
        ticking = false;
      });
      ticking = true;
    }
  });

  // Trigger initial state by no-op scroll. Upstream Furo's `window.scroll()`
  // call resolves to scrolling to (0, 0) which fires a scroll event so the
  // header / back-to-top / ToC handlers run once on load.
  window.scroll();
}

function setupScrollSpy(): void {
  if (tocScroll === null) {
    return;
  }

  // Scrollspy — highlight ToC entries based on scroll position.
  new Gumshoe(".toc-tree a", {
    reflow: true,
    recursive: true,
    navClass: "scroll-current",
    offset: () => {
      const rem = Number.parseFloat(getComputedStyle(document.documentElement).fontSize);
      const headerRect = header?.getBoundingClientRect();
      if (!headerRect) {
        return 2.5 * rem + 1;
      }
      return headerRect.top + headerRect.height + 2.5 * rem + 1;
    },
  });
}

function setupTheme(): void {
  // Wire click handlers on every theme-toggle button.
  for (const btn of document.getElementsByClassName("theme-toggle")) {
    btn.addEventListener("click", cycleThemeOnce);
  }
}

function setup(): void {
  setupTheme();
  setupScrollHandler();
  setupScrollSpy();
}

////////////////////////////////////////////////////////////////////////////////
// Main entrypoint
////////////////////////////////////////////////////////////////////////////////

function main(): void {
  // Remove the no-js gate Furo adds to <html>.
  document.documentElement.classList.remove("no-js");

  header = document.querySelector("header");
  tocScroll = document.querySelector(".toc-scroll");

  setup();
}

document.addEventListener("DOMContentLoaded", main);
})();
