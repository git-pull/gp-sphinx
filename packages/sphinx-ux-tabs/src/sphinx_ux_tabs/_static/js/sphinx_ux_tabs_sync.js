/*
 * sphinx-ux-tabs sync.
 *
 * Three jobs:
 *
 *  1. Bind a click handler on every label carrying `data-sync-id` so
 *     clicking the bash label in one set checks the bash label in every
 *     other set sharing the same sync-group.
 *
 *  2. Persist sync choices to `localStorage` under
 *     `gp-sphinx-tabs.sync.<group>` and restore them on script-load
 *     and on every `gp-sphinx:navigated` event (spa-nav swaps the
 *     article container, destroying the old DOM).
 *
 *  3. Parse the URL query-string on script-load.  `?tabs=Python`
 *     pre-selects every tab whose visible label text matches
 *     "Python" (case-insensitive).  `?<group>=<id>` pre-selects the
 *     matching label in the named sync-group and writes the choice
 *     into `localStorage` so it sticks on subsequent visits.  URL
 *     params win over `localStorage` on first paint.
 *
 * No-ops cleanly when no `data-sync-id` labels are present.  The
 * basic radio-input tab switching is CSS-only — JS is a progressive
 * enhancement.
 */

(function () {
  "use strict";

  var STORAGE_PREFIX = "gp-sphinx-tabs.sync.";

  function storageKey(syncGroup) {
    return STORAGE_PREFIX + syncGroup;
  }

  function readStorage(syncGroup) {
    try {
      return window.localStorage.getItem(storageKey(syncGroup));
    } catch (_err) {
      return null;
    }
  }

  function writeStorage(syncGroup, syncId) {
    try {
      window.localStorage.setItem(storageKey(syncGroup), syncId);
    } catch (_err) {
      /* localStorage unavailable (private mode, full quota) — fail silent. */
    }
  }

  function syncLabels() {
    return document.querySelectorAll("label.gp-sphinx-tabs__label[data-sync-id]");
  }

  function findLabel(syncGroup, syncId) {
    /* `syncId` comes from `window.location.search` in `applyUrlParams`;
     * a hostile URL like `?shell=x"][data-other="y` would otherwise
     * break out of the attribute-value string and throw a SyntaxError
     * inside querySelectorAll, silently aborting tab restoration for
     * the whole page.  `syncGroup` is escaped defensively even though
     * its values come from author-controlled `data-*` attributes. */
    var selector =
      'label.gp-sphinx-tabs__label[data-sync-group="' +
      CSS.escape(syncGroup) +
      '"][data-sync-id="' +
      CSS.escape(syncId) +
      '"]';
    return document.querySelectorAll(selector);
  }

  function checkRadioFor(label) {
    /* The radio sibling sits immediately before the label in the
     * `[input, label, panel]` triple emitted by `_expand_one_tab_set`. */
    var input = label.previousElementSibling;
    if (!input || input.tagName !== "INPUT" || input.type !== "radio") {
      var forAttr = label.getAttribute("for");
      if (forAttr) {
        input = document.getElementById(forAttr);
      }
    }
    if (input && !input.checked) {
      input.checked = true;
      /* Dispatch with `bubbles: true` so any change listener attached
       * to a containing form / panel receives the event (matches
       * native radio click behaviour). */
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function onSyncClick(event) {
    var label = event.currentTarget;
    var syncId = label.getAttribute("data-sync-id");
    var syncGroup = label.getAttribute("data-sync-group") || "tab";
    if (!syncId) {
      return;
    }
    writeStorage(syncGroup, syncId);
    var peers = findLabel(syncGroup, syncId);
    peers.forEach(function (peer) {
      if (peer === label) {
        return;
      }
      checkRadioFor(peer);
    });
  }

  function bindLabels() {
    var labels = document.querySelectorAll(
      "label.gp-sphinx-tabs__label[data-sync-id]:not([data-gp-sphinx-tabs-bound])",
    );
    labels.forEach(function (label) {
      label.dataset.gpSphinxTabsBound = "1";
      label.addEventListener("click", onSyncClick);
    });
  }

  function distinctSyncGroups() {
    var groups = {};
    syncLabels().forEach(function (label) {
      var group = label.getAttribute("data-sync-group") || "tab";
      groups[group] = true;
    });
    return Object.keys(groups);
  }

  function activate(syncGroup, syncId) {
    var peers = findLabel(syncGroup, syncId);
    if (!peers.length) {
      return false;
    }
    peers.forEach(checkRadioFor);
    return true;
  }

  function restoreFromStorage() {
    distinctSyncGroups().forEach(function (group) {
      var syncId = readStorage(group);
      if (syncId) {
        activate(group, syncId);
      }
    });
  }

  function findLabelsByText(text) {
    var target = text.trim().toLowerCase();
    var matches = [];
    document
      .querySelectorAll("label.gp-sphinx-tabs__label")
      .forEach(function (label) {
        if ((label.textContent || "").trim().toLowerCase() === target) {
          matches.push(label);
        }
      });
    return matches;
  }

  function applyUrlParams() {
    if (!window.location.search) {
      return;
    }
    var params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (_err) {
      return;
    }
    var groups = distinctSyncGroups();
    var groupSet = {};
    groups.forEach(function (g) {
      groupSet[g] = true;
    });
    params.forEach(function (value, key) {
      if (key === "tabs") {
        findLabelsByText(value).forEach(checkRadioFor);
        return;
      }
      if (groupSet[key]) {
        if (activate(key, value)) {
          /* URL deep-link wins for this paint AND writes through to
           * localStorage so it sticks on subsequent visits. */
          writeStorage(key, value);
        }
      }
    });
  }

  function hydrate() {
    if (!syncLabels().length) {
      return;
    }
    bindLabels();
    restoreFromStorage();
  }

  function initialHydrate() {
    if (!syncLabels().length) {
      return;
    }
    bindLabels();
    /* URL params take precedence — apply them first (they also write
     * through to localStorage), then let `restoreFromStorage` fill in
     * any groups the URL didn't specify. */
    applyUrlParams();
    restoreFromStorage();
  }

  /* Public hook used by tests / spa-nav consumers. */
  window.gpSphinxTabsSync = hydrate;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialHydrate);
  } else {
    initialHydrate();
  }

  /* Re-bind + restore after every SPA navigation.  URL params are not
   * re-applied here — they apply on first paint only, matching
   * sphinx-inline-tabs semantics. */
  document.addEventListener("gp-sphinx:navigated", hydrate);
})();
