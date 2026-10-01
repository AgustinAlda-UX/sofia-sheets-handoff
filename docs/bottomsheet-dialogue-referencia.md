# Bottomsheet / Dialogue — Referencia de diseño

**Descripción general**
Contenedor modal deslizable desde abajo. Muestra opciones, filtros o contenido adicional sin abandonar el flujo principal de SOFIA.

---

## Variantes del componente `Dialogue`

| Prop | Opciones | Default |
|---|---|---|
| `platform` | `Mobile` / `Desktop` | `Desktop` |
| `headerType` | `Simple` / `WithActions` | `Simple` |
| `showHeader` | `true` / `false` | `true` |
| `title` | string | `"Título del panel"` |

- **Ancho:** 360px (Mobile) / 575px (Desktop)
- **Border radius:** `large` = 24px
- **Sombra:** `0px -4px 4px rgba(84,89,98,0.1)` (mobile) / `0px 8px 12px rgba(0,0,0,0.15)` (desktop)

---

## Sub-componentes

### BS / Header
Tipos: `mobile`, `mobile-compact`, `desktop`, `desktop-compact`

- Handle drag: 40×4px, color `Neutral/400` (#C0C4CC), radius 100px
- Título: Subtitle Medium (Rubik Medium, 14px) en mobile-compact / Title Small (Rubik Medium, 20px) en desktop
- Icono de cierre: 16×16px

### BS / Slot
Placeholder de contenido 200px de alto. Reemplazable via INSTANCE_SWAP en Figma o children en código.

### BS / Footer — 3 variantes

| Variante | Descripción |
|---|---|
| `SingleCTA` | CTA centrado, layout en columna |
| `DualCTA` | Dos botones en fila, alineados a la derecha |
| `Pagination` | Stepper "1 de 3" + botón primario |

### Dialogue Chat PeekBar (estado colapsado)
- Tamaño: 360×36px
- Border activo: `Actionable/Brand/Primary/Enabled` = #4300D2 (stroke 1px)
- Layout: auto-layout vertical

---

## Tokens de color — SOFIA / Bottom Sheet

| Token | Valor hex | Descripción |
|---|---|---|
| `cta/primary/bg` | #4300D2 | Fondo botón primario |
| `cta/primary/bg-hover` | #270570 | Hover botón primario |
| `cta/primary/bg-pressed` | #270570 | Pressed botón primario |
| `cta/primary/bg-disabled` | #C0C4CC | Disabled botón primario |
| `cta/primary/text` | #FFFFFF | Texto botón primario |
| `cta/secondary/text` | #4300D2 | Texto botón secundario |
| `cta/secondary/text-hover` | #270570 | Hover texto secundario |
| `overlay/color` | #323439 | Color del dimmer |

---

## Tokens de dimensión y motion

| Token | Valor | Scope | Descripción |
|---|---|---|---|
| `overlay/opacity` | 0.8 | OPACITY | Opacidad del dimmer |
| `cta/gap` | 12px | GAP | Separación entre CTAs en footer |
| `header/height` | 101px | WIDTH_HEIGHT | Alto del header del shell |
| `input-area/height` | 124px | WIDTH_HEIGHT | Alto del área de input |
| `turn-gap` | 24px | GAP | Separación entre turnos de conversación |
| `motion/duration/slow` | 300ms | — | Duración de apertura/cierre del BS |

---

## Estado colapsado (Peek Bar)

- Tamaño: **360 × 36px**
- Fondo: `Background/Low` (white)
- Border activo: stroke 1px `Actionable/Brand/Primary/Enabled` = #4300D2
- Sombra: `0px -4px 8px rgba(84,89,98,0.1)`
- Muestra: precio del viaje + íconos de productos (16×16px) + chevron para expandir
- El stroke Brand-Primary-500 distingue el modo activo/seleccionado del shell

---

## Tipografías usadas

| Elemento | Tipografía | Tamaño | Color |
|---|---|---|---|
| Título mobile-compact | Rubik Medium | 14px / lh 20px | #323439 |
| Título desktop | Rubik Medium | 20px / lh 28px | #323439 |
| Stepper / texto secundario | Rubik Regular | 12px / lh 16px | #72777F |

---

## Componentes en esta página

- **BS / Shell / Mobile** — Shell completo (handle + header + slot + footer)
- **BS / Shell / Desktop** — Shell completo desktop
- **BS / Footer** — SingleCTA · DualCTA · Pagination
- **BS / Header/tab menu** — Tabs de navegación interna
- **BS / Dimmer** — Overlay oscuro (Overlay-Primary)
- **BS / Slot** — Área de contenido intercambiable
- **.BS_header** — mobile · mobile-compact · desktop · desktop-compact

---

## Referencias

- [Figma — Librería SOFIA (Bottomsheet)](https://www.figma.com/design/zKKxNLAAWfsVWgd7psyLpq/Librer%C3%ADa-SOFIA?node-id=2129-29394)
- [EVA UI — Button](https://eva.despegar.design/ui/components/button/docs/)
- [EVA UI — Button Ghost](https://eva.despegar.design/ui/components/button-ghost/docs/)
