// ─── Bottom Sheet · Mobile ───────────────────────────────────────────────────
// Desliza desde el borde inferior. Incluye overlay con fade.
// Uso:
//   openBottomSheet(sheetEl, overlayEl)
//   closeBottomSheet(sheetEl, overlayEl)

const BOTTOM_SHEET = {
  duration: 320,
  easing: "cubic-bezier(0.32, 0.72, 0, 1)", // spring suave
};

export function openBottomSheet(sheet, overlay) {
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

export function closeBottomSheet(sheet, overlay) {
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
