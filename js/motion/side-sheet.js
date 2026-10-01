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

export function openSideSheet(sheet, overlay, { origin = "right" } = {}) {
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

export function closeSideSheet(sheet, overlay, { origin = "right" } = {}) {
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
