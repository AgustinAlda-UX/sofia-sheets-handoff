/* ============================================================================
   ARCHIVO GENERADO por tools/build.py — NO EDITAR A MANO.
   Derivado de js/motion/bottom-sheet.js, js/motion/modal.js y js/motion/side-sheet.js
   (código literal del handoff de Figma) quitando la palabra "export" y envolviendo todo
   en una IIFE que expone window.SofiaMotion para usarlo con <script> clásico (sitio de docs,
   playgrounds). En producto, los devs deben importar los MÓDULOS ORIGINALES:
     import { openBottomSheet } from './js/motion/bottom-sheet.js';
   ============================================================================ */
(function () {
  'use strict';

  // ── js/motion/bottom-sheet.js ──
  // ─── Bottom Sheet · Mobile ───────────────────────────────────────────────────
  // Desliza desde el borde inferior. Incluye overlay con fade.
  // Uso:
  //   openBottomSheet(sheetEl, overlayEl)
  //   closeBottomSheet(sheetEl, overlayEl)

  const BOTTOM_SHEET = {
    duration: 320,
    easing: "cubic-bezier(0.32, 0.72, 0, 1)", // spring suave
  };

  function openBottomSheet(sheet, overlay) {
    overlay.style.display = "block";

    overlay.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: BOTTOM_SHEET.duration, easing: "ease", fill: "forwards" }
    );

    sheet.style.display = "flex";
    sheet.animate(
      [
        { transform: "translateY(100%)", opacity: 0.6 },
        { transform: "translateY(0)",    opacity: 1   },
      ],
      { duration: BOTTOM_SHEET.duration, easing: BOTTOM_SHEET.easing, fill: "forwards" }
    );
  }

  function closeBottomSheet(sheet, overlay) {
    const anim = sheet.animate(
      [
        { transform: "translateY(0)",    opacity: 1   },
        { transform: "translateY(100%)", opacity: 0.6 },
      ],
      { duration: BOTTOM_SHEET.duration, easing: BOTTOM_SHEET.easing, fill: "forwards" }
    );

    overlay.animate(
      [{ opacity: 1 }, { opacity: 0 }],
      { duration: BOTTOM_SHEET.duration, easing: "ease", fill: "forwards" }
    );

    anim.onfinish = () => {
      sheet.style.display   = "none";
      overlay.style.display = "none";
    };
  }

  // ── js/motion/modal.js ──
  // ─── Modal · Desktop ─────────────────────────────────────────────────────────
  // Aparece centrado con scale + fade. Overlay con blur opcional.
  // Uso:
  //   openModal(modalEl, overlayEl)
  //   closeModal(modalEl, overlayEl)

  const MODAL = {
    duration: 260,
    easingIn:  "cubic-bezier(0.34, 1.56, 0.64, 1)", // leve spring en entrada
    easingOut: "cubic-bezier(0.4, 0, 0.2, 1)",       // ease-out estándar en salida
  };

  function openModal(modal, overlay) {
    overlay.style.display = "flex";
    modal.style.display   = "flex";

    overlay.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: MODAL.duration, easing: "ease", fill: "forwards" }
    );

    modal.animate(
      [
        { transform: "scale(0.92) translateY(8px)", opacity: 0 },
        { transform: "scale(1)    translateY(0)",   opacity: 1 },
      ],
      { duration: MODAL.duration, easing: MODAL.easingIn, fill: "forwards" }
    );
  }

  function closeModal(modal, overlay) {
    const anim = modal.animate(
      [
        { transform: "scale(1)    translateY(0)",   opacity: 1 },
        { transform: "scale(0.94) translateY(4px)", opacity: 0 },
      ],
      { duration: MODAL.duration, easing: MODAL.easingOut, fill: "forwards" }
    );

    overlay.animate(
      [{ opacity: 1 }, { opacity: 0 }],
      { duration: MODAL.duration, easing: "ease", fill: "forwards" }
    );

    anim.onfinish = () => {
      modal.style.display   = "none";
      overlay.style.display = "none";
    };
  }

  // ── js/motion/side-sheet.js ──
  // ─── Side Sheet · Desktop ─────────────────────────────────────────────────────
  // Desliza desde el borde derecho (o izquierdo pasando origin: "left").
  // Uso:
  //   openSideSheet(sheetEl, overlayEl, { origin: "right" | "left" })
  //   closeSideSheet(sheetEl, overlayEl, { origin: "right" | "left" })

  const SIDE_SHEET = {
    duration: 340,
    easing: "cubic-bezier(0.32, 0.72, 0, 1)",
  };

  function getTranslate(origin) {
    return origin === "left" ? "translateX(-100%)" : "translateX(100%)";
  }

  function openSideSheet(sheet, overlay, { origin = "right" } = {}) {
    const offscreen = getTranslate(origin);

    overlay.style.display = "block";
    sheet.style.display   = "flex";

    overlay.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: SIDE_SHEET.duration, easing: "ease", fill: "forwards" }
    );

    sheet.animate(
      [
        { transform: offscreen,        opacity: 0.8 },
        { transform: "translateX(0)",  opacity: 1   },
      ],
      { duration: SIDE_SHEET.duration, easing: SIDE_SHEET.easing, fill: "forwards" }
    );
  }

  function closeSideSheet(sheet, overlay, { origin = "right" } = {}) {
    const offscreen = getTranslate(origin);

    const anim = sheet.animate(
      [
        { transform: "translateX(0)", opacity: 1   },
        { transform: offscreen,       opacity: 0.8 },
      ],
      { duration: SIDE_SHEET.duration, easing: SIDE_SHEET.easing, fill: "forwards" }
    );

    overlay.animate(
      [{ opacity: 1 }, { opacity: 0 }],
      { duration: SIDE_SHEET.duration, easing: "ease", fill: "forwards" }
    );

    anim.onfinish = () => {
      sheet.style.display   = "none";
      overlay.style.display = "none";
    };
  }

  window.SofiaMotion = { openBottomSheet, closeBottomSheet, openModal, closeModal, openSideSheet, closeSideSheet };
})();
