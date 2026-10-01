/* SOFIA · Sheets handoff — playgrounds interactivos (script clásico, funciona con file://).
   Solo clona los snippets del handoff (<template data-snippet="grupo/id">) y los anima con las
   funciones literales del handoff (window.SofiaMotion, generado desde js/motion/*.js).
   No compone variantes nuevas: cada opción es una instancia que existe en Figma. */
(function () {
  'use strict';
  var M = window.SofiaMotion;
  if (!M) return;

  /* ── Utilidades ─────────────────────────────────────────────────────── */
  function tpl(key) {
    var t = document.querySelector('template[data-snippet="' + key + '"]');
    if (!t) throw new Error('Falta el template ' + key);
    return t;
  }
  function clone(key) { var d = document.createElement('div'); d.appendChild(tpl(key).content.cloneNode(true)); return d; }
  function snippetHTML(key) { return tpl(key).innerHTML.trim(); }
  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function el(html) { var d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstElementChild; }
  function btn(label, primary) {
    return el('<button type="button" class="' + (primary ? 'eva-3-btn -md -primary' : 'eva-3-btn-ghost -md -primary') + '"><em class="btn-text">' + label + '</em></button>');
  }
  function select(label, options) {
    var f = el('<label class="pg__field"><span class="pg__label">' + label + '</span><select class="pg__select"></select></label>');
    var s = f.querySelector('select');
    options.forEach(function (o, i) { var op = document.createElement('option'); op.value = i; op.textContent = o.label; s.appendChild(op); });
    return { field: f, select: s };
  }
  function dummyOverlay(parent) { var o = document.createElement('div'); o.style.cssText = 'position:absolute;width:0;height:0;'; parent.appendChild(o); return o; }

  /* Stage con tamaño exacto del frame de Figma, escalado para entrar en el ancho disponible. */
  function makeStage(w, h, mobile) {
    var viewport = el('<div class="pg__viewport"><div class="pg__scaler"><div class="pg__stage' + (mobile ? ' pg__stage--mobile' : '') + '"></div></div></div>');
    var scaler = viewport.firstElementChild, stage = scaler.firstElementChild;
    function size(nw, nh) {
      w = nw; h = nh;
      stage.style.width = w + 'px'; stage.style.height = h + 'px';
      fit();
    }
    function fit() {
      var avail = viewport.clientWidth - 32;
      if (avail <= 0) return;
      var s = Math.min(1, avail / w);
      stage.style.transform = s < 1 ? 'scale(' + s + ')' : '';
      scaler.style.width = (w * s) + 'px';
      scaler.style.height = (h * s) + 'px';
    }
    if ('ResizeObserver' in window) new ResizeObserver(fit).observe(viewport); else window.addEventListener('resize', fit);
    size(w, h);
    return { viewport: viewport, stage: stage, size: size, fit: fit };
  }

  function codePanel() {
    var wrap = el('<div class="pg__code" hidden><div class="docs-code"><div class="docs-code__bar"><span class="docs-code__label">HTML del snippet + JS de uso</span><button type="button" class="eva-3-btn-ghost -sm docs-copy" data-copy-target="prev"><em class="btn-text">Copiar</em></button></div><pre><code class="docs-lang-html"></code></pre></div></div>');
    return { el: wrap, set: function (txt) { wrap.querySelector('code').innerHTML = esc(txt); } };
  }
  function codeToggle(panel) {
    var b = btn('Ver código', false);
    b.addEventListener('click', function () {
      var open = panel.el.hasAttribute('hidden');
      if (open) panel.el.removeAttribute('hidden'); else panel.el.setAttribute('hidden', '');
      b.querySelector('.btn-text').textContent = open ? 'Ocultar código' : 'Ver código';
    });
    return b;
  }

  /* Abre/cierra una instancia y conecta cerrar (X, overlay, Esc). */
  var activeClose = null;
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && activeClose) activeClose(); });

  function shell(container, controls, stageObj, panel) {
    container.innerHTML = '';
    var root = el('<div class="pg"><div class="pg__controls"></div><div class="pg__view"></div></div>');
    controls.forEach(function (c) { root.firstElementChild.appendChild(c); });
    root.lastElementChild.appendChild(stageObj.viewport);
    root.appendChild(panel.el);
    container.appendChild(root);
    stageObj.fit();
  }

  /* ── Bottom sheet ───────────────────────────────────────────────────── */
  var BS_OPTIONS = [
    { label: 'Header Title + Dual CTA', key: 'bs-sheets/sheet-title-dual', mode: 'bottom' },
    { label: 'Header Slot + Single CTA', key: 'bs-sheets/sheet-slot-single', mode: 'bottom' },
    { label: 'Header Tabs + Single CTA', key: 'bs-sheets/sheet-tabs-single', mode: 'bottom' },
    { label: 'Header imagen · Title', key: 'bs-sheets/sheet-hero-title', mode: 'bottom' },
    { label: 'Header imagen · Tags', key: 'bs-sheets/sheet-hero-tags', mode: 'bottom' },
    { label: 'Header imagen · Tabs', key: 'bs-sheets/sheet-hero-tabs', mode: 'bottom' },
    { label: 'Altura = Default', key: 'bs-sheets/height-default', mode: 'abs' },
    { label: 'Altura = 75%', key: 'bs-sheets/height-75', mode: 'abs' },
    { label: 'Altura = 50%', key: 'bs-sheets/height-50', mode: 'abs' },
    { label: 'Altura = 25%', key: 'bs-sheets/height-25', mode: 'abs' },
    { label: 'En el chat · 25%', key: 'bs-chat/chat-bs-25', mode: 'chat' },
    { label: 'En el chat · 50%', key: 'bs-chat/chat-bs-50', mode: 'chat' },
    { label: 'En el chat · 75%', key: 'bs-chat/chat-bs-75', mode: 'chat' },
    { label: 'En el chat · 100% (full screen)', key: 'bs-chat/chat-bs-100', mode: 'chat' }
  ];
  function bottomSheet(container) {
    var st = makeStage(360, 753, true);
    var panel = codePanel();
    var sel = select('Instancia (Figma)', BS_OPTIONS);
    var open = btn('Abrir', true), close = btn('Cerrar', false);
    var buttons = el('<div class="pg__buttons"></div>'); buttons.append(open, close, codeToggle(panel));
    var hint = el('<p class="pg__hint">Cerrá con la X, tocando el overlay o con Esc. Animación: openBottomSheet / closeBottomSheet (320 ms).</p>');
    shell(container, [sel.field, buttons, hint], st, panel);
    var cur = null;

    function render() {
      var o = BS_OPTIONS[+sel.select.value];
      st.stage.innerHTML = '';
      var sheet, overlay;
      if (o.mode === 'chat') {
        var full = clone(o.key);
        st.stage.appendChild(full);
        sheet = full.querySelector('.sofia-chat__panel');
        overlay = full.querySelector('.sofia-chat__sheet .sofia-overlay');
        st.stage.querySelector('.sofia-chat__sheet').style.pointerEvents = 'none';
        sheet.style.pointerEvents = overlay.style.pointerEvents = 'auto';
      } else {
        st.stage.appendChild(clone('bs-chat/chat-empty'));
        var layer = el('<div class="pg__layer' + (o.mode === 'bottom' ? ' pg__layer--bottom' : '') + '"></div>');
        if (o.mode === 'bottom') layer.appendChild(clone('bs-header/overlay').firstElementChild);
        var frag = clone(o.key);
        while (frag.firstChild) layer.appendChild(frag.firstChild);
        st.stage.appendChild(layer);
        sheet = layer.querySelector('.sofia-bs');
        overlay = layer.querySelector('.sofia-overlay');
      }
      sheet.style.display = 'none'; overlay.style.display = 'none';
      cur = { sheet: sheet, overlay: overlay, open: false };
      st.stage.querySelectorAll('[aria-label="Cerrar"]').forEach(function (b) { b.addEventListener('click', doClose); });
      overlay.addEventListener('click', doClose);
      panel.set(snippetHTML(o.key) + '\n\n<script type="module">\n  import { openBottomSheet, closeBottomSheet } from \'./js/motion/bottom-sheet.js\';\n  const sheet = document.querySelector(\'' + (o.mode === 'chat' ? '.sofia-chat__panel' : '.sofia-bs') + '\');\n  const overlay = document.querySelector(\'.sofia-overlay\');\n  openBottomSheet(sheet, overlay);\n  // cerrar: closeBottomSheet(sheet, overlay)\n</script>');
    }
    function doOpen() {
      if (!cur || cur.open) return;
      M.openBottomSheet(cur.sheet, cur.overlay); cur.open = true; activeClose = doClose;
    }
    function doClose() {
      if (!cur || !cur.open) return;
      M.closeBottomSheet(cur.sheet, cur.overlay); cur.open = false; activeClose = null;
    }
    sel.select.addEventListener('change', function () { render(); doOpen(); });
    open.addEventListener('click', doOpen);
    close.addEventListener('click', doClose);
    render();
  }

  /* ── Side sheet ─────────────────────────────────────────────────────── */
  var SS_OPTIONS = [
    { label: 'Title', key: 'side-sheet/ss-title' },
    { label: 'Title + Tabs', key: 'side-sheet/ss-tabs' },
    { label: 'Title + Tags', key: 'side-sheet/ss-tags' },
    { label: 'Header imagen · Title', key: 'side-sheet/ss-hero-title' },
    { label: 'Header imagen · Tags', key: 'side-sheet/ss-hero-tags' },
    { label: 'Header imagen · Tabs', key: 'side-sheet/ss-hero-tabs' }
  ];
  function sideSheet(container) {
    var st = makeStage(1366, 772, false);
    var panel = codePanel();
    var sel = select('Instancia (Figma)', SS_OPTIONS);
    var radios = el('<div class="pg__field"><span class="pg__label">origin</span><div class="pg__radios"><label><input type="radio" name="pg-ss-origin" value="right" checked> right</label><label><input type="radio" name="pg-ss-origin" value="left"> left</label></div></div>');
    var open = btn('Abrir', true), close = btn('Cerrar', false);
    var buttons = el('<div class="pg__buttons"></div>'); buttons.append(open, close, codeToggle(panel));
    var hint = el('<p class="pg__hint">openSideSheet(sheet, overlay, { origin }) · 340 ms. En Figma el side sheet está anclado a la derecha; "left" es la opción que expone la API del JS del handoff.</p>');
    shell(container, [sel.field, radios, buttons, hint], st, panel);
    var cur = null;
    function origin() { return radios.querySelector('input:checked').value; }
    function render() {
      var o = SS_OPTIONS[+sel.select.value];
      st.stage.innerHTML = '<div class="pg__desktop-bg"></div>';
      var layer = el('<div class="pg__layer' + (origin() === 'left' ? ' pg__ss-left' : '') + '"></div>');
      var overlay = clone('side-sheet/ss-context').querySelector('.sofia-overlay');
      layer.appendChild(overlay);
      var sheet = clone(o.key).querySelector('.sofia-ss');
      sheet.classList.add('sofia-ss--docked');
      layer.appendChild(sheet);
      st.stage.appendChild(layer);
      sheet.style.display = 'none'; overlay.style.display = 'none';
      cur = { sheet: sheet, overlay: overlay, open: false };
      sheet.querySelectorAll('[aria-label="Cerrar"]').forEach(function (b) { b.addEventListener('click', doClose); });
      overlay.addEventListener('click', doClose);
      panel.set(snippetHTML('side-sheet/ss-context').split('<aside')[0].trim() + '\n' + snippetHTML(o.key).replace('class="sofia-ss ', 'class="sofia-ss sofia-ss--docked ') + '\n\n<script type="module">\n  import { openSideSheet, closeSideSheet } from \'./js/motion/side-sheet.js\';\n  const sheet = document.querySelector(\'.sofia-ss\');\n  const overlay = document.querySelector(\'.sofia-ss-overlay\');\n  openSideSheet(sheet, overlay, { origin: "' + origin() + '" });\n  // cerrar: closeSideSheet(sheet, overlay, { origin: "' + origin() + '" })\n</script>');
    }
    function doOpen() { if (!cur || cur.open) return; M.openSideSheet(cur.sheet, cur.overlay, { origin: origin() }); cur.open = true; activeClose = doClose; }
    function doClose() { if (!cur || !cur.open) return; M.closeSideSheet(cur.sheet, cur.overlay, { origin: origin() }); cur.open = false; activeClose = null; }
    sel.select.addEventListener('change', function () { render(); doOpen(); });
    radios.addEventListener('change', function () { render(); doOpen(); });
    open.addEventListener('click', doOpen);
    close.addEventListener('click', doClose);
    render();
  }

  /* ── Modal ──────────────────────────────────────────────────────────── */
  var MODAL_OPTIONS = [
    { label: 'Desktop · Tabs', key: 'modal/modal-tabs' },
    { label: 'Desktop · Basic', key: 'modal/modal-basic' },
    { label: 'Desktop · Tags', key: 'modal/modal-tags' },
    { label: 'Mobile', key: 'modal/modal-mobile', mobile: true }
  ];
  function modal(container) {
    var st = makeStage(1366, 772, false);
    var panel = codePanel();
    var sel = select('Instancia (Figma)', MODAL_OPTIONS);
    var open = btn('Abrir', true), close = btn('Cerrar', false);
    var buttons = el('<div class="pg__buttons"></div>'); buttons.append(open, close, codeToggle(panel));
    var hint = el('<p class="pg__hint">openModal / closeModal · 260 ms, entrada con leve spring. Cerrá con la X, el overlay o Esc.</p>');
    shell(container, [sel.field, buttons, hint], st, panel);
    var cur = null;
    function render() {
      var o = MODAL_OPTIONS[+sel.select.value];
      var m, overlay;
      if (o.mobile) {
        st.size(360, 640); st.stage.classList.add('pg__stage--mobile');
        st.stage.innerHTML = '';
        st.stage.appendChild(clone('bs-chat/chat-empty'));
        overlay = clone(o.key).querySelector('.sofia-modal-mobile');
        st.stage.appendChild(overlay);
        m = overlay.querySelector('.sofia-modal-mobile__card');
        panel.set(snippetHTML(o.key) + usage('.sofia-modal-mobile__card', '.sofia-modal-mobile'));
      } else {
        st.size(1366, 772); st.stage.classList.remove('pg__stage--mobile');
        st.stage.innerHTML = '<div class="pg__desktop-bg"></div>';
        overlay = el('<div class="sofia-modal-overlay"></div>');
        m = clone(o.key).querySelector('.sofia-modal');
        overlay.appendChild(m);
        st.stage.appendChild(overlay);
        panel.set('<div class="sofia-modal-overlay">\n' + snippetHTML(o.key) + '\n</div>' + usage('.sofia-modal', '.sofia-modal-overlay'));
      }
      m.style.display = 'none'; overlay.style.display = 'none';
      cur = { m: m, overlay: overlay, open: false };
      m.querySelectorAll('[aria-label="Cerrar"]').forEach(function (b) { b.addEventListener('click', doClose); });
      overlay.addEventListener('click', function (e) { if (e.target === overlay) doClose(); });
    }
    function usage(ms, os) {
      return '\n\n<script type="module">\n  import { openModal, closeModal } from \'./js/motion/modal.js\';\n  const modal = document.querySelector(\'' + ms + '\');\n  const overlay = document.querySelector(\'' + os + '\');\n  openModal(modal, overlay);\n  // cerrar: closeModal(modal, overlay)\n</script>';
    }
    function doOpen() { if (!cur || cur.open) return; M.openModal(cur.m, cur.overlay); cur.open = true; activeClose = doClose; }
    function doClose() { if (!cur || !cur.open) return; M.closeModal(cur.m, cur.overlay); cur.open = false; activeClose = null; }
    sel.select.addEventListener('change', function () { render(); doOpen(); });
    open.addEventListener('click', doOpen);
    close.addEventListener('click', doClose);
    render();
  }

  /* ── Formularios / widgets · Modelo de persistencia ─────────────────── */
  /* Captions literales de Figma (docs/content.json → persistence). */
  var CAP = {
    persist1: 'Sofia responde con la start_package Se levanta automaticamente el widget',
    persist2: 'El widget se colapsa y permeance persistido',
    noPersist1: 'En contexto de cupones, Sofia responde con la tool de search_hotel Se levanta automaticamente el widget',
    noPersist3: 'El usuario cierra el bottomsheet, este desaparace',
    noPersist4: 'El usuario vuelve a “traer” el BS con el trigger en el cluster corresponciente',
    form1: 'El usuario hace tap en un accionable y activa el bottom sheet',
    form2: 'El usuario ve un form para completar',
    form3: 'Si cierra o completa el BS desaparece',
    semi1: 'En contexto de cupones, Sofia responde con la tool de earch_hotel Se levanta automaticamente el widget',
    semi2: 'El usuario hace clik en la cruz y minimiza el cupón',
    semi3: 'Lo puede cerrar por completo y usar el trigger para traerlo de nuevo'
  };
  var FLOWS = [
    { label: 'Widget persistente · desktop', id: 'persist', mobile: false, expanded: 'forms-trip/trip-desktop-expanded-start', peek: 'forms-trip/trip-desktop-peek' },
    { label: 'Widget persistente · mobile', id: 'persist', mobile: true, expanded: 'forms-trip/trip-mobile-expanded-flights', peek: 'forms-trip/trip-mobile-peek' },
    { label: 'Widget NO persistente · desktop (cupón)', id: 'noPersist', mobile: false, card: 'forms-coupon/coupon-desktop' },
    { label: 'Widget NO persistente · mobile (cupón)', id: 'noPersist', mobile: true, card: 'forms-coupon/coupon-mobile' },
    { label: 'Widget semi persistente · desktop (cupón)', id: 'semi', mobile: false, card: 'forms-coupon/coupon-desktop-semi', peek: 'forms-coupon/coupon-peek' },
    { label: 'Form · tap en accionable (destino)', id: 'form', mobile: false, card: 'forms-coupon/destination-form' }
  ];
  /* Ancho de cada nodo en Figma (manifest width): las piezas son fluidas y el ancho lo da el contenedor. */
  var WIDTHS = {
    'forms-trip/trip-desktop-expanded-start': 567, 'forms-trip/trip-desktop-peek': 360, 'forms-trip/trip-mobile-peek': 328,
    'forms-coupon/coupon-desktop': 575, 'forms-coupon/coupon-desktop-semi': 575, 'forms-coupon/coupon-peek': 360,
    'forms-coupon/destination-form': 575
  };
  function forms(container) {
    var st = makeStage(1366, 772, false);
    var panel = codePanel();
    var sel = select('Caso (Modelo de persistencia)', FLOWS);
    var trigger = btn('Disparar', true), reset = btn('Reiniciar', false);
    var buttons = el('<div class="pg__buttons"></div>'); buttons.append(trigger, reset, codeToggle(panel));
    var caption = el('<div class="pg__caption"><small>Paso en Figma</small><span></span></div>');
    var hint = el('<p class="pg__hint">"Disparar" simula la respuesta de Sofia (tool) o el trigger del cluster. Animación de entrada/salida: openBottomSheet / closeBottomSheet del handoff.</p>');
    shell(container, [sel.field, buttons, caption, hint], st, panel);
    var flow, layer, current = null;

    function say(t) { caption.querySelector('span').textContent = t || '—'; }
    function mount(key) {
      var frag = clone(key);
      var root = frag.firstElementChild;
      while (frag.firstChild) layer.appendChild(frag.firstChild);
      var sheet = root, overlay;
      var inner = root.querySelector('section');
      if (root.classList.contains('sofia-trip-sheet') || root.classList.contains('sofia-bs-form-layer')) {
        sheet = inner;
        overlay = root.querySelector('[class*="__scrim"]');
        root.style.position = 'absolute'; root.style.inset = '0';
      } else {
        overlay = dummyOverlay(layer);
        if (WIDTHS[key]) { root.style.width = WIDTHS[key] + 'px'; root.style.flex = 'none'; root.style.alignSelf = 'center'; }
      }
      sheet.style.display = 'none'; overlay.style.display = 'none';
      return { root: root, sheet: sheet, overlay: overlay, key: key };
    }
    function show(key, after) {
      var go = function () {
        current = mount(key);
        M.openBottomSheet(current.sheet, current.overlay);
        wire(current);
        panel.set(snippetHTML(key) + '\n\n<script type="module">\n  import { openBottomSheet, closeBottomSheet } from \'./js/motion/bottom-sheet.js\';\n  // abrir / cerrar el widget con las mismas funciones del bottom sheet\n</script>');
        if (after) after();
      };
      if (current) hide(go); else go();
    }
    function hide(done) {
      if (!current) { if (done) done(); return; }
      var c = current; current = null;
      var anim = M.closeBottomSheet(c.sheet, c.overlay);
      setTimeout(function () { if (c.root.parentNode) c.root.parentNode.removeChild(c.root); if (c.overlay.parentNode) c.overlay.parentNode.removeChild(c.overlay); if (done) done(); }, 340);
    }
    function wire(c) {
      var r = c.root;
      if (flow.id === 'persist') {
        r.querySelectorAll('.sofia-trip-widget__toggle, .sofia-peekbar').forEach(function (t) {
          t.addEventListener('click', function (e) {
            e.stopPropagation();
            if (c.key === flow.expanded) show(flow.peek, function () { say(CAP.persist2); });
            else show(flow.expanded, function () { say(CAP.persist1); });
          });
        });
        return;
      }
      r.querySelectorAll('.sofia-bs-form__close').forEach(function (b) {
        b.addEventListener('click', function () {
          if (flow.id === 'semi' && c.key === flow.card) { show(flow.peek, function () { say(CAP.semi2); }); return; }
          hide(function () { say(flow.id === 'semi' ? CAP.semi3 : flow.id === 'form' ? CAP.form3 : CAP.noPersist3); });
        });
      });
      if (flow.id === 'form') {
        r.querySelectorAll('.eva-3-btn').forEach(function (b) {
          if (/Siguiente/.test(b.textContent)) b.addEventListener('click', function () { hide(function () { say(CAP.form3); }); });
        });
      }
    }
    function start() {
      flow = FLOWS[+sel.select.value];
      current = null;
      if (flow.mobile) { st.size(360, 800); st.stage.classList.add('pg__stage--mobile'); }
      else { st.size(1366, 772); st.stage.classList.remove('pg__stage--mobile'); }
      st.stage.innerHTML = flow.mobile ? '' : '<div class="pg__desktop-bg"></div>';
      if (flow.mobile) st.stage.appendChild(clone('bs-chat/chat-empty'));
      layer = el('<div class="pg__layer ' + (flow.mobile ? 'pg__layer--float-mobile' : 'pg__layer--float') + '"></div>');
      st.stage.appendChild(layer);
      say(flow.id === 'form' ? CAP.form1 : '');
      panel.set(snippetHTML(flow.expanded || flow.card));
    }
    trigger.addEventListener('click', function () {
      if (current && flow.id !== 'persist') return;
      var key = flow.expanded || flow.card;
      var cap = flow.id === 'persist' ? CAP.persist1 : flow.id === 'semi' ? CAP.semi1 : flow.id === 'form' ? CAP.form2 : (layer.dataset.shown ? CAP.noPersist4 : CAP.noPersist1);
      layer.dataset.shown = '1';
      show(key, function () { say(cap); });
    });
    reset.addEventListener('click', start);
    sel.select.addEventListener('change', start);
    start();
  }

  /* ── Montaje ────────────────────────────────────────────────────────── */
  var MAP = { 'bottom-sheet': bottomSheet, 'side-sheet': sideSheet, 'modal': modal, 'forms': forms };
  document.querySelectorAll('.docs-playground[data-playground]').forEach(function (c) {
    var fn = MAP[c.getAttribute('data-playground')];
    if (!fn) return;
    try { fn(c); } catch (e) { c.innerHTML = '<p class="docs-muted">No se pudo iniciar el playground: ' + esc(String(e.message || e)) + '</p>'; console.error(e); }
  });
})();
