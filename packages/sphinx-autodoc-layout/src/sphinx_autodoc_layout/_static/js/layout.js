/**
 * sphinx_autodoc_layout — layout.js
 *
 * Hash-based auto-expansion: when the URL fragment targets an
 * element inside a closed <details>, open it so the target is
 * visible.
 */

(function () {
  'use strict';

  function expandForHash() {
    var hash = window.location.hash;
    if (!hash) return;

    var id = hash.slice(1);
    var target = document.getElementById(id);
    if (!target) return;

    var node = target;
    while (node) {
      if (node.tagName === 'DETAILS' && !node.open) {
        node.open = true;
      }
      node = node.parentElement;
    }

    setTimeout(function () {
      target.scrollIntoView({ block: 'center' });
    }, 50);
  }

  document.addEventListener('DOMContentLoaded', expandForHash);
  window.addEventListener('hashchange', expandForHash);
})();
