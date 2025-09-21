(function () {
  function setExternalTarget() {
    var links = document.querySelectorAll('a[href]');
    links.forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href) {
        return;
      }
      if (href.endsWith('grammar/diagrams.html')) {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener noreferrer');
      }
    });
  }

  if (window.document$) {
    window.document$.subscribe(setExternalTarget);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setExternalTarget);
  } else {
    setExternalTarget();
  }
})();
