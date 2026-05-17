/*
 * sphinx-ux-tabs sync.
 *
 * Listens for `gp-sphinx:navigated` from sphinx-gp-theme/spa-nav.js and
 * re-binds tab-sync click handlers on freshly-swapped labels. spa-nav
 * replaces the entire .article-container, destroying old labels and
 * inserting new ones without the `data-gp-sphinx-tabs-bound` marker —
 * the idempotent guard ensures we only bind once per label.
 *
 * Cross-tab-set synchronization: clicking a label that carries
 * `data-sync-id` activates every label sharing the same sync-id within
 * the same sync-group, regardless of tab-set.  This is the runtime
 * counterpart of sphinx-design's `:sync:` option.
 */

(function () {
  "use strict";

  function onSyncClick(event) {
    var label = event.currentTarget;
    var syncId = label.getAttribute("data-sync-id");
    var syncGroup = label.getAttribute("data-sync-group") || "tab";
    if (!syncId) {
      return;
    }
    var selector =
      'label.gp-sphinx-tabs__label[data-sync-id="' +
      syncId +
      '"][data-sync-group="' +
      syncGroup +
      '"]';
    var peers = document.querySelectorAll(selector);
    peers.forEach(function (peer) {
      if (peer === label) {
        return;
      }
      var forAttr = peer.getAttribute("for");
      if (!forAttr) {
        return;
      }
      var input = document.getElementById(forAttr);
      if (input && !input.checked) {
        input.checked = true;
      }
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

  window.gpSphinxTabsSync = bindLabels;

  // Initial bind on first parse.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindLabels);
  } else {
    bindLabels();
  }

  // Re-bind after each SPA navigation.
  document.addEventListener("gp-sphinx:navigated", bindLabels);
})();
