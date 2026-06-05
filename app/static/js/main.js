document.addEventListener('DOMContentLoaded', function () {

  /* ── Toast global ─────────────────────────────── */
  window.showToast = function (msg, type) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'toast show ' + (type || '');
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.className = 'toast'; }, 3000);
  };

  /* ── Ripple effect em botões ─────────────────── */
  document.querySelectorAll('.btn, .share-btn, .rede-card, .action-btn, .toggle-btn, .qr-tab').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (el.classList.contains('rede-card') || el.tagName === 'A') return;
      var rect = el.getBoundingClientRect();
      var r = document.createElement('span');
      r.className = 'ripple';
      var d = Math.max(rect.width, rect.height);
      r.style.width = r.style.height = d + 'px';
      r.style.left = (e.clientX - rect.left - d / 2) + 'px';
      r.style.top = (e.clientY - rect.top - d / 2) + 'px';
      el.appendChild(r);
      setTimeout(function () { r.remove(); }, 600);
    });
  });

  /* ── Intersection Observer para animações ───── */
  var animEls = document.querySelectorAll('.anim-on-view');
  if (animEls.length && window.IntersectionObserver) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('anim-fade-up');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });
    animEls.forEach(function (el) { obs.observe(el); });
  }

  /* ── Scroll suave para âncoras ──────────────── */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = this.getAttribute('href');
      if (id === '#') return;
      var target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

});
