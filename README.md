# SOFIA · Sheets & Modals — Handoff para devs

Sitio estático con **todas las instancias ya diseñadas** en el Figma
[SOFIA - Bottom sheet - modal - site sheet](https://www.figma.com/design/CATCPGSOAIUuXcPBLDY1dK/SOFIA---Bottom-sheet---modal---site-sheet?node-id=49-73)
(página "👍 Hand off") más el MD `docs/bottomsheet-dialogue-referencia.md`:
bottom sheet (mobile), side sheet (desktop), modales (desktop + mobile) y formularios / widgets en bottom sheet.
Nada es nuevo: cada snippet sale de `get_design_context` de un nodo de Figma (el node id está en cada card).

## Cómo abrirlo
- Doble click en `index.html` (funciona con `file://`), o
- `python3 -m http.server` dentro de esta carpeta, o
- desde `/Users/agustinaldazor/CLAUDEDESPE` con la config `sheets-handoff` de `.claude/launch.json` → http://127.0.0.1:8790/

Necesita internet para EVA (CDN de despegar.com) y la fuente Rubik (Google Fonts).

## Qué hay en el sitio
- **Cuándo usar** cada superficie (definiciones literales del canvas de Figma).
- **Fundamentos**: todos los tokens de `css/tokens.css` (color, tipografía, radios, sombras, motion).
- **Una card por variante** (50): preview al tamaño exacto de Figma, props, link al nodo, notas de implementación,
  “Copiar HTML”, “Ver código”, “Abrir preview” y el CSS requerido.
- **Motion**: definición, decisiones, qué evitar y el JS literal del handoff.
- **Playgrounds**: abrir/cerrar cada instancia con las animaciones reales; forms reproduce el modelo de persistencia.
- **Modelo de persistencia** (capturas de referencia del flujo) y **Spec MD vs Figma** (mapeo + discrepancias).

## Usar un componente en código
```html
<!-- 1. EVA -->
<link rel="stylesheet" href="https://www.despegar.com/eva-core/static/eva/eva-core.min.css?">
<link rel="stylesheet" href="https://www.despegar.com/eva-core/static/eva/eva.min.css?">
<!-- 2. Rubik -->
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap" rel="stylesheet">
<!-- 3. Tokens + base SOFIA -->
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/base.css">
<!-- 4. CSS del/los grupo(s) que indica la card -->
<link rel="stylesheet" href="css/components/bs-header.css">
```
Pegá el snippet de la card y animalo con los módulos del handoff:
```js
import { openBottomSheet, closeBottomSheet } from './js/motion/bottom-sheet.js';
import { openModal, closeModal } from './js/motion/modal.js';
import { openSideSheet, closeSideSheet } from './js/motion/side-sheet.js';
```
`js/motion/motion.global.js` es una copia generada para el sitio (expone `window.SofiaMotion`); no usarla en producto.

## Estructura
```
components/<grupo>/manifest.json   variantes (node id, tamaño, props, notas)
components/<grupo>/<id>.html       snippet HTML puro
css/tokens.css · css/base.css      tokens (EVA primero, con fallback) y base
css/components/<grupo>.css         estilos de cada grupo
js/motion/*.js                     animaciones literales del handoff (ES modules)
previews/                          una página por variante (generada)
docs/content.json                  textos literales del Figma (definiciones, motion, persistencia, spec)
reference/persistence/             capturas de referencia del flujo
tools/build.py                     regenera previews + index.html + motion.global.js
```
Grupos: `bs-header`, `bs-hero`, `bs-footer`, `bs-sheets`, `bs-chat`, `side-sheet`, `modal`, `forms-trip`, `forms-coupon`.

## Regenerar
```bash
python3 tools/build.py
```
`index.html`, `previews/` y `js/motion/motion.global.js` son generados: no editarlos a mano.

## Convenciones
- EVA prevalece sobre Figma: botones, tags, tabs, inputs e íconos son clases EVA (`eva-3-*`). Las diferencias
  visibles EVA vs Figma están anotadas en las notas de cada variante.
- Clases propias con prefijo `sofia-` (BEM). Ver `CONTRACT.md`.
- Los textos dentro de los componentes son los de Figma ("Title", "Primary button", "Content / Slot"…): reemplazalos por contenido real.
