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

export function openModal(modal, overlay) {
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

export function closeModal(modal, overlay) {
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
