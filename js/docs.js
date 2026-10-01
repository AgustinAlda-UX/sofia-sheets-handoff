/* SOFIA · Sheets handoff — comportamiento del sitio de docs (script clásico, funciona con file://).
   Copiar código, ver código, escalado de previews, scrollspy, buscador, sidebar mobile y lightbox. */
(function () {
  'use strict';
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ── Copiar ─────────────────────────────────────────────────────────── */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy') ? resolve() : reject(); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }
  function flash(btn, msg) {
    var label = btn.querySelector('.btn-text') || btn;
    var prev = label.textContent;
    label.textContent = msg;
    setTimeout(function () { label.textContent = prev; }, 1400);
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.docs-copy');
    if (!btn) return;
    var target = btn.getAttribute('data-copy-target');
    var el = null;
    if (target === 'prev') { var box = btn.closest('.docs-code'); el = box && box.querySelector('pre code, pre'); }
    else if (target) { el = document.querySelector(target); }
    if (!el) return;
    copyText(el.textContent).then(function () { flash(btn, 'Copiado ✓'); }, function () { flash(btn, 'No se pudo copiar'); });
  });

  /* ── Ver código ─────────────────────────────────────────────────────── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.docs-toggle-code');
    if (!btn) return;
    var wrap = document.getElementById(btn.getAttribute('aria-controls'));
    if (!wrap) return;
    var open = wrap.hasAttribute('hidden');
    if (open) wrap.removeAttribute('hidden'); else wrap.setAttribute('hidden', '');
    btn.setAttribute('aria-expanded', String(open));
    var label = btn.querySelector('.btn-text');
    if (label) label.textContent = open ? 'Ocultar código' : 'Ver código';
  });

  /* ── Escalado de previews (nunca más de 1x) ─────────────────────────── */
  function scalePreview(p) {
    var w = +p.getAttribute('data-w'), h = +p.getAttribute('data-h');
    var frame = p.querySelector('.docs-preview__frame');
    if (!frame || !w) return;
    var cs = getComputedStyle(p);
    var avail = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    var s = Math.min(1, avail / w);
    frame.style.transform = s < 1 ? 'scale(' + s + ')' : '';
    frame.style.marginBottom = s < 1 ? (-(1 - s) * h) + 'px' : '';
    var tag = p.querySelector('.docs-preview__scale');
    if (tag) tag.textContent = s < 1 ? Math.round(s * 100) + '%' : '';
  }
  var previews = $$('.docs-preview[data-w]');
  if ('ResizeObserver' in window) {
    var ro = new ResizeObserver(function (entries) { entries.forEach(function (en) { scalePreview(en.target); }); });
    previews.forEach(function (p) { ro.observe(p); });
  } else {
    var all = function () { previews.forEach(scalePreview); };
    window.addEventListener('resize', all); all();
  }

  /* ── Scrollspy ──────────────────────────────────────────────────────── */
  var navLinks = $$('.docs-nav a[data-nav]');
  var byId = {};
  navLinks.forEach(function (a) { byId[a.getAttribute('data-nav')] = a; });
  var targets = navLinks.map(function (a) { return document.getElementById(a.getAttribute('data-nav')); }).filter(Boolean);
  function spy() {
    var y = window.scrollY + 120, current = null;
    targets.forEach(function (t) { if (t.offsetParent !== null && t.getBoundingClientRect().top + window.scrollY <= y) current = t; });
    navLinks.forEach(function (a) { a.classList.remove('is-active'); });
    if (current && byId[current.id]) {
      byId[current.id].classList.add('is-active');
      var sec = current.closest('.docs-section');
      if (sec && sec.id !== current.id && byId[sec.id]) byId[sec.id].classList.add('is-active');
    }
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return; ticking = true;
    requestAnimationFrame(function () { spy(); ticking = false; });
  }, { passive: true });
  spy();

  /* ── Buscador ───────────────────────────────────────────────────────── */
  var input = $('#docs-search-input');
  var status = $('.docs-search__status');
  var noResults = $('.docs-noresults');
  var variants = $$('.docs-variant[data-search]');
  var norm = function (s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
  if (input) {
    input.addEventListener('input', function () {
      var q = norm(input.value.trim());
      var shown = 0;
      variants.forEach(function (v) {
        var ok = !q || norm(v.getAttribute('data-search')).indexOf(q) !== -1;
        if (ok) { v.removeAttribute('hidden'); shown++; } else { v.setAttribute('hidden', ''); }
      });
      $$('.docs-group').forEach(function (g) {
        var any = g.querySelector('.docs-variant:not([hidden])');
        g.style.display = (!q || any) ? '' : 'none';
      });
      $$('.docs-section').forEach(function (s) {
        if (!s.querySelector('.docs-variant')) { s.style.display = q ? 'none' : ''; return; }
        s.style.display = (!q || s.querySelector('.docs-variant:not([hidden])')) ? '' : 'none';
      });
      if (status) status.textContent = q ? shown + ' de ' + variants.length + ' variantes' : '';
      if (noResults) { if (q && !shown) noResults.removeAttribute('hidden'); else noResults.setAttribute('hidden', ''); }
      previews.forEach(scalePreview);
    });
  }

  /* ── Sidebar mobile ─────────────────────────────────────────────────── */
  var menuBtn = $('.docs-topbar__menu');
  var backdrop = $('.docs-backdrop');
  function setNav(open) {
    document.body.classList.toggle('is-nav-open', open);
    if (menuBtn) menuBtn.setAttribute('aria-expanded', String(open));
    if (backdrop) { if (open) backdrop.removeAttribute('hidden'); else backdrop.setAttribute('hidden', ''); }
  }
  if (menuBtn) menuBtn.addEventListener('click', function () { setNav(!document.body.classList.contains('is-nav-open')); });
  if (backdrop) backdrop.addEventListener('click', function () { setNav(false); });
  $$('.docs-nav a').forEach(function (a) { a.addEventListener('click', function () { setNav(false); }); });

  /* ── Lightbox ───────────────────────────────────────────────────────── */
  var lb = $('.docs-lightbox');
  function openLb(src, caption) {
    if (!lb) return;
    lb.querySelector('img').src = src;
    lb.querySelector('img').alt = caption || '';
    lb.querySelector('figcaption').textContent = caption || '';
    lb.removeAttribute('hidden');
    lb.querySelector('.docs-lightbox__close').focus();
  }
  function closeLb() { if (lb) lb.setAttribute('hidden', ''); }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-lightbox]');
    if (b) { openLb(b.getAttribute('data-lightbox'), b.getAttribute('data-caption')); return; }
    var z = e.target.closest('img.docs-zoom');
    if (z) { var cap = z.closest('figure'); openLb(z.getAttribute('src'), cap && cap.querySelector('figcaption') ? cap.querySelector('figcaption').textContent : z.alt); return; }
    if (lb && !lb.hasAttribute('hidden') && (e.target === lb || e.target.closest('.docs-lightbox__close'))) closeLb();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeLb(); setNav(false); }
  });
})();
