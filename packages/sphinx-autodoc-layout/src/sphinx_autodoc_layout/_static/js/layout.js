/**
 * sphinx_autodoc_layout — layout.js
 *
 * Hash-based auto-expansion for both block <details> folds and the
 * custom api-signature disclosure panel.
 */

(function () {
  'use strict';

  function setSignatureExpanded(button, expanded) {
    if (!button) return;

    var panelId = button.getAttribute('aria-controls');
    if (!panelId) return;

    var panel = document.getElementById(panelId);
    if (!panel) return;

    button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    if (expanded) {
      panel.hidden = false;
      panel.setAttribute('data-expanded', 'true');
      panel.setAttribute('aria-hidden', 'false');
    } else {
      panel.hidden = true;
      panel.setAttribute('data-expanded', 'false');
      panel.setAttribute('aria-hidden', 'true');
    }
  }

  function expandAncestors(target) {
    var node = target;
    while (node) {
      if (node.tagName === 'DETAILS' && !node.open) {
        node.open = true;
      }
      node = node.parentElement;
    }
  }

  function expandSignatureForTarget(target) {
    var header = null;

    if (target.classList && target.classList.contains('api-header')) {
      header = target;
    } else if (target.closest) {
      header = target.closest('.api-header');
    }

    if (!header) return;

    var button = header.querySelector('.api-signature-toggle');
    if (!button) return;

    setSignatureExpanded(button, true);
  }

  function expandForHash() {
    var hash = window.location.hash;
    if (!hash) return;

    var id = hash.slice(1);
    var target = document.getElementById(id);
    if (!target) return;

    expandAncestors(target);
    expandSignatureForTarget(target);

    setTimeout(function () {
      target.scrollIntoView({ block: 'center' });
    }, 50);
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('.api-signature-toggle');
    if (!button) return;

    event.preventDefault();
    var expanded = button.getAttribute('aria-expanded') === 'true';
    setSignatureExpanded(button, !expanded);
  });

  document.addEventListener('DOMContentLoaded', expandForHash);
  window.addEventListener('hashchange', expandForHash);
})();
