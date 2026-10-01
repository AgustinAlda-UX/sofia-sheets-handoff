# CONTRACT — SOFIA Sheets handoff site

Contrato compartido para todos los agentes que construyen este sitio. **Leerlo completo antes de escribir código.**

## Objetivo
Sitio web estático para devs con TODAS las instancias ya diseñadas en Figma de:
bottom sheet (mobile), side sheet (desktop), modales (desktop + mobile), formularios / widgets en bottom sheet,
más tokens, animaciones y reglas de uso. **No se diseña nada nuevo**: se implementa exactamente lo que existe en Figma.

- Figma fileKey: `CATCPGSOAIUuXcPBLDY1dK` · página `49:73` "👍 Hand off".
- Metadata XML completa de la página: `docs/figma-handoff-metadata.xml.txt` (JSON de 3 chunks con `.text`; ya incluye todos los node ids).
- Spec textual de referencia: `docs/bottomsheet-dialogue-referencia.md`.

## Reglas de Figma (skill figma-design-to-code)
- Llamar `mcp__figma-remote__get_design_context` con `fileKey`, `nodeId`, `clientLanguages: "html,css,javascript"`, `clientFrameworks: "unknown"`, `skillNames: "figma-design-to-code"`. Pedir screenshot (default).
- Si la respuesta viene "sparse"/solo metadata, pedir los hijos visibles en paralelo hasta tener código de alta fidelidad.
- Implementar SOLO desde el código de `get_design_context`; el screenshot es el objetivo visual, **nunca** se usa como asset.
- Traducir el posicionamiento absoluto a layout nativo (flex/grid). Los contenedores tienen ancho fluido (`width:100%`); el ancho fijo lo da el contenedor raíz o la preview.
- Assets estáticos (fotos, íconos SVG que no existan en EVA): descargarlos con `curl -L` desde las URLs que devuelve `get_design_context` a `assets/img/` o `assets/icons/`, con nombre descriptivo en kebab-case. **Nunca** dejar URLs temporales de Figma en el código. No redibujar ni editar SVG. Respetar width/height del SVG raíz.
- Si un asset ya fue descargado por otro agente (mismo contenido), reutilizarlo; revisar `assets/` antes de descargar.

## EVA primero (Despegar design system)
EVA prevalece sobre Figma. El CSS de EVA se carga desde CDN en todas las páginas:
```html
<link rel="stylesheet" href="https://www.despegar.com/eva-core/static/eva/eva-core.min.css?">
<link rel="stylesheet" href="https://www.despegar.com/eva-core/static/eva/eva.min.css?">
```
Cuando en Figma el nodo es una instancia EVA (Button-contained, Button-ghost, Tag, Input-field, Stepper, .Tab Container, íconos),
usar la clase EVA real (consultar `mcp__eva-ui__eva_ui_get_component` para la estructura exacta):
- Botón primario: `<button class="eva-3-btn -md -primary"><em class="btn-text">Primary button</em></button>`
- Botón secundario/outline: consultar `button-ghost` (`eva-3-btn-ghost`) — verificar cuál matchea el "Secondary button" de Figma.
- Tag: `<span class="eva-3-tag"><span class="tag-text">Tag text</span></span>`
- Tabs: `eva-3-tabs` (ver doc; soporta `-subtitle` con dos `tab-label`).
- Íconos: fuente EVA `eva-3-icon-*` (ej. `eva-3-icon-close`, `eva-3-icon-chevron-left/right/down`, `eva-3-icon-coupon`, `eva-3-icon-copy`). Buscar en `eva.min.css` (`/private/tmp/claude-502/-Users-agustinaldazor-CLAUDEDESPE/04d4e1a1-1537-4c9e-9cc4-3b98dbacac5b/scratchpad/eva.min.css`) si existe el ícono antes de descargar un SVG.
Solo se escribe CSS propio (prefijo `sofia-`) para contenedores/estructura SOFIA que EVA no cubre, o para ajustes mínimos
que hagan que el componente EVA coincida con el Figma (documentar el ajuste en un comentario).
Si EVA y Figma difieren de forma visible, **gana EVA** y se anota la diferencia en `notes` del manifest.

## Tokens
- `css/tokens.css` (NO editar salvo el agente de tokens/ensamblado): variables `--sofia-*` con fallback EVA. Usar SIEMPRE `var(--sofia-…)` en lugar de hex.
- Si falta un token que aparece en `get_variable_defs`, agregarlo al principio del CSS del grupo en un bloque `:root { }` con comentario `/* TODO mover a tokens.css */` — el ensamblador lo moverá.
- `css/base.css`: box-sizing + font-family para todo `.sofia-*`.

## Nombres de clases (BEM con prefijo `sofia-`)
| Pieza Figma | Clase raíz | Modificadores |
|---|---|---|
| Overlay (`4028:3424`) | `.sofia-overlay` | — |
| BS_header (`4048:3730`) Handle=Title / Slot / Tabs / Icon Only | `.sofia-bs-header` | `--title`, `--slot`, `--tabs`, `--tags` (Icon Only muestra tags) |
| BS_imageBG_tittle (`4048:4371`) Header=Title / Tabs / Tags | `.sofia-bs-hero` | `--title`, `--tabs`, `--tags` |
| Content (`4116:1021`) / BS / Slot | `.sofia-bs-content`, placeholder `.sofia-slot` | — |
| Action Container (`4058:4744`) Footer=Single CTA / Dual CTA / CTA + Steps | `.sofia-bs-footer` | `--single`, `--dual`, `--steps` |
| Bottom sheet compuesta (mobile 360) | `.sofia-bs` | alturas `--h-default`, `--h-75`, `--h-50`, `--h-25`, `--full` |
| Side sheet (desktop 421) | `.sofia-ss` (+ `.sofia-ss-header`) | según variante |
| Modal desktop (800) | `.sofia-modal` (+ `.sofia-modal-header`, `.sofia-modal-footer`) | según variante |
| Modal mobile | `.sofia-modal-mobile` | — |
| Formularios / widgets (persistencia) | `.sofia-bs-form`, `.sofia-trip-widget`, `.sofia-peekbar`, `.sofia-coupon` | según variante |
Elementos: `__handle`, `__title`, `__close`, `__row`, `__tabs`, `__tags`, `__body`, `__actions`, etc. Estados con `is-active`, `is-open`.
El side sheet y el modal reutilizan las piezas `.sofia-bs-hero` / `.sofia-bs-footer` cuando en Figma son instancias del mismo componente.

## Archivos por grupo
Cada grupo tiene:
- `components/<group>/manifest.json`
- `components/<group>/<variant-id>.html` — **snippet puro** (sin `<html>`, `<head>`, `<style>` ni `<script>`), listo para copiar. Usa rutas de assets relativas a la raíz del sitio con prefijo `../` (ej. `../assets/img/house.jpg`) porque se renderiza desde `previews/`.
- `css/components/<group>.css` — solo los estilos del grupo.

Schema del manifest:
```json
{
  "group": "bs-parts",
  "title": "Bottom Sheet · Estructura base",
  "category": "bottom-sheet | side-sheet | modal | forms | foundations",
  "order": 10,
  "css": "css/components/bs-parts.css",
  "figmaSection": "49:79",
  "description": "texto corto en español para devs",
  "variants": [
    {
      "id": "header-title",
      "name": "BS_header · Handle=Title",
      "figmaNodeId": "4048:3733",
      "file": "header-title.html",
      "width": 360, "height": 56,
      "stage": "#ffffff",
      "props": {"Handle": "Title"},
      "description": "Cuándo usarlo / qué contiene",
      "notes": "diferencias EVA vs Figma, decisiones",
      "scripts": []
    }
  ]
}
```
`width`/`height` = tamaño exacto del nodo en Figma (la preview se captura a ese tamaño). `stage` = color de fondo de la preview.

## Verificación obligatoria (cada agente, antes de terminar)
1. `python3 tools/build.py` (desde la raíz del sitio) → genera `previews/<group>--<id>.html`.
2. `tools/shot.sh previews/<group>--<id>.html <scratch>/<group>--<id>.png <w> <h>` (tarda ~20 s; se puede correr en paralelo con `&` + `wait`).
3. Descargar el screenshot de Figma del mismo nodo (`get_screenshot` → curl) y comparar ambos PNG con Read.
4. Corregir diferencias de layout, tipografía, color, espaciado, radios, sombras, assets. Repetir hasta que coincidan.
Carpeta scratch para PNG temporales: `/private/tmp/claude-502/-Users-agustinaldazor-CLAUDEDESPE/04d4e1a1-1537-4c9e-9cc4-3b98dbacac5b/scratchpad/verify/`.

## Idioma
Todo el texto visible del sitio (descripciones, notas) en español rioplatense neutro. Los textos DENTRO de los componentes van exactamente como en Figma ("Title", "Primary button", "Content / Slot", "Titulo", "Bajada", "Tag text", etc.).

## Prohibido
- Inventar variantes, estados o contenido que no estén en Figma.
- Editar archivos de otros grupos (solo el propio `components/<group>/` y `css/components/<group>.css`; assets nuevos sí).
- Editar `css/tokens.css`, `css/base.css`, `tools/*`, `js/motion/*`.
