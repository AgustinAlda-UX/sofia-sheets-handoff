#!/usr/bin/env python3
"""Build del sitio de handoff SOFIA · Sheets & Modals.

Uso (desde la raíz sofia-sheets-handoff/):
    python3 tools/build.py                 # previews + js/motion/motion.global.js + index.html
    python3 tools/build.py --only bs-hero  # solo regenera las previews de ese grupo (+ motion.global.js + index.html)

Genera:
  1. previews/<group>--<id>.html  — página standalone por variante (EVA CDN + tokens + base + CSS de componentes + snippet).
  2. js/motion/motion.global.js   — copia DERIVADA de los 3 módulos de js/motion/*.js como script clásico (window.SofiaMotion).
  3. index.html                   — sitio de documentación de una sola página. Todo el contenido se embebe en build time
                                    (sin fetch en runtime), así funciona con file:// y por http.

Los grupos cuyo nombre empieza con "_" se ignoran. El exit code es 1 si falta algún snippet o un manifest es inválido.
"""
import argparse, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EVA_CORE = 'https://www.despegar.com/eva-core/static/eva/eva-core.min.css?'
EVA_CSS = 'https://www.despegar.com/eva-core/static/eva/eva.min.css?'
RUBIK = 'https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap'

# ──────────────────────────────────────────────────────────────────────────────
# 1. Previews (misma salida que la versión original)
# ──────────────────────────────────────────────────────────────────────────────
HEAD = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://www.despegar.com/eva-core/static/eva/eva-core.min.css?">
<link rel="stylesheet" href="https://www.despegar.com/eva-core/static/eva/eva.min.css?">
<link rel="stylesheet" href="../css/tokens.css">
<link rel="stylesheet" href="../css/base.css">
{css}
<style>html,body{{margin:0;padding:0;background:{stage};}}
.sofia-preview-stage{{position:relative;width:{w}px;height:{h}px;overflow:hidden;}}</style>
</head><body>
<div class="sofia-preview-stage" data-group="{group}" data-variant="{vid}">
{snippet}
</div>
{scripts}
</body></html>
"""


def esc(s):
    return html.escape('' if s is None else str(s), quote=True)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def load_groups(errors):
    groups = []
    for mf in sorted(glob.glob(os.path.join(ROOT, 'components/*/manifest.json'))):
        gdir = os.path.dirname(mf)
        group = os.path.basename(gdir)
        if group.startswith('_'):
            continue
        try:
            m = json.loads(read(mf))
        except Exception as e:  # noqa: BLE001
            errors.append(f'{mf}: JSON inválido: {e}')
            continue
        m.setdefault('group', group)
        m['_dir'] = gdir
        m['_group'] = group
        for v in m.get('variants', []):
            sp = os.path.join(gdir, v['file'])
            if os.path.exists(sp):
                v['_snippet'] = read(sp)
            else:
                v['_snippet'] = None
                errors.append(f'{group}/{v["id"]}: falta {v["file"]}')
        groups.append(m)
    groups.sort(key=lambda g: (g.get('order', 999), g['_group']))
    return groups


def build_previews(groups, only):
    comp_css = sorted(glob.glob(os.path.join(ROOT, 'css/components/*.css')))
    css_links = "\n".join(f'<link rel="stylesheet" href="../css/components/{os.path.basename(c)}">' for c in comp_css)
    os.makedirs(os.path.join(ROOT, 'previews'), exist_ok=True)
    count = 0
    for m in groups:
        group = m['_group']
        if only and group not in only:
            continue
        for v in m.get('variants', []):
            if v['_snippet'] is None:
                continue
            scripts = "\n".join(f'<script type="module" src="../{s}"></script>' for s in v.get('scripts', []))
            out = HEAD.format(title=html.escape(v.get('name', v['id'])), css=css_links,
                              stage=v.get('stage', '#ffffff'), w=v['width'], h=v['height'],
                              group=group, vid=v['id'], snippet=v['_snippet'], scripts=scripts)
            write(os.path.join(ROOT, 'previews', f'{group}--{v["id"]}.html'), out)
            count += 1
    return count


# ──────────────────────────────────────────────────────────────────────────────
# 2. motion.global.js (derivado)
# ──────────────────────────────────────────────────────────────────────────────
MOTION_FILES = ['bottom-sheet.js', 'modal.js', 'side-sheet.js']
MOTION_EXPORTS = ['openBottomSheet', 'closeBottomSheet', 'openModal', 'closeModal', 'openSideSheet', 'closeSideSheet']


def build_motion_global():
    parts = []
    for f in MOTION_FILES:
        src = read(os.path.join(ROOT, 'js/motion', f))
        src = re.sub(r'^(\s*)export\s+', r'\1', src, flags=re.M)
        parts.append(f'  // ── js/motion/{f} ──\n' + '\n'.join(('  ' + l) if l.strip() else '' for l in src.splitlines()))
    body = '\n\n'.join(parts)
    out = (
        "/* ============================================================================\n"
        "   ARCHIVO GENERADO por tools/build.py — NO EDITAR A MANO.\n"
        "   Derivado de js/motion/bottom-sheet.js, js/motion/modal.js y js/motion/side-sheet.js\n"
        "   (código literal del handoff de Figma) quitando la palabra \"export\" y envolviendo todo\n"
        "   en una IIFE que expone window.SofiaMotion para usarlo con <script> clásico (sitio de docs,\n"
        "   playgrounds). En producto, los devs deben importar los MÓDULOS ORIGINALES:\n"
        "     import { openBottomSheet } from './js/motion/bottom-sheet.js';\n"
        "   ============================================================================ */\n"
        "(function () {\n"
        "  'use strict';\n\n"
        f"{body}\n\n"
        f"  window.SofiaMotion = {{ {', '.join(MOTION_EXPORTS)} }};\n"
        "})();\n"
    )
    write(os.path.join(ROOT, 'js/motion/motion.global.js'), out)


def motion_usage(fname):
    """Devuelve las líneas del comentario 'Uso:' del módulo (literal)."""
    lines = read(os.path.join(ROOT, 'js/motion', fname)).splitlines()
    out, on = [], False
    for l in lines:
        if l.strip().startswith('// Uso:'):
            on = True
            out.append(l)
            continue
        if on:
            if l.strip().startswith('//') and l.strip() != '//':
                out.append(l)
            else:
                break
    return '\n'.join(out)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Utilidades para index.html
# ──────────────────────────────────────────────────────────────────────────────
def strip_css_comments(css):
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


def css_classes(css):
    """Clases sofia-* usadas en selectores de un CSS."""
    css = strip_css_comments(css)
    classes = set()
    for sel in re.findall(r'([^{}]+)\{', css):
        if sel.strip().startswith('@'):
            continue
        for c in re.findall(r'\.(-?[_a-zA-Z][\w-]*)', sel):
            if c.startswith('sofia-'):
                classes.add(c)
    return classes


def snippet_classes(snippet):
    out = set()
    for attr in re.findall(r'class\s*=\s*"([^"]*)"', snippet or ''):
        out.update(attr.split())
    return out


def display_snippet(s):
    return (s or '').replace('../assets/', 'assets/')


def figma_url(content, node_id):
    return content['figma']['fileUrl'] + '?node-id=' + node_id.replace(':', '-')


LIBRARY_URL = 'https://www.figma.com/design/zKKxNLAAWfsVWgd7psyLpq/Librer%C3%ADa-SOFIA'


def library_url(node_id):
    return LIBRARY_URL + '?node-id=' + node_id.replace(':', '-')


def inline_md(text):
    """Markdown inline mínimo: `code` y **bold**."""
    t = esc(text)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    return t


def variant_node_ids(v):
    ids = []
    if v.get('figmaNodeIds'):
        ids.extend(v['figmaNodeIds'])
    if v.get('figmaNodeId') and v['figmaNodeId'] not in ids:
        ids.insert(0, v['figmaNodeId'])
    return ids


def code_block(code, lang='', copy=True, label=None):
    btn = ('<button type="button" class="eva-3-btn-ghost -sm docs-copy" data-copy-target="prev">'
           '<em class="btn-text">Copiar</em></button>') if copy else ''
    lab = f'<span class="docs-code__label">{esc(label)}</span>' if label else ''
    return (f'<div class="docs-code"><div class="docs-code__bar">{lab}{btn}</div>'
            f'<pre><code class="docs-lang-{esc(lang)}">{esc(code)}</code></pre></div>')


def table(headers, rows, cls=''):
    th = ''.join(f'<th>{h}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<div class="docs-table-wrap"><table class="docs-table {cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def dash(v):
    return esc(v) if v not in (None, '', []) else '—'


# ── Tokens ────────────────────────────────────────────────────────────────────
def parse_tokens(css_text):
    """Parsea css/tokens.css → bloques [{title, groups:[{name, note, tokens:[{name,value,comment}]}]}]."""
    blocks = []
    pending_block = ('Tokens', '')
    cur_block = None
    cur_group = None
    pending_note = None
    i = 0
    text = css_text
    lines = text.splitlines()
    n = len(lines)
    in_root = False
    while i < n:
        line = lines[i]
        s = line.strip()
        # comentario multilínea
        if s.startswith('/*') and '*/' not in s:
            buf = [s]
            i += 1
            while i < n and '*/' not in lines[i]:
                buf.append(lines[i].strip())
                i += 1
            if i < n:
                buf.append(lines[i].strip())
            comment = '\n'.join(buf)
            body = re.sub(r'^/\*+|\*+/$', '', comment.strip(), flags=re.S).strip()
            if '=====' in comment:
                ls = [l.strip() for l in body.splitlines() if l.strip() and not set(l.strip()) <= set('=')]
                if not in_root:
                    pending_block = (ls[0] if ls else 'Tokens', ' '.join(ls[1:]))
            elif in_root and cur_group is not None:
                note = ' '.join(l.strip() for l in body.splitlines())
                cur_group['note'] = (cur_group['note'] + ' ' + note).strip()
                pending_note = None
            i += 1
            continue
        if s.startswith(':root'):
            in_root = True
            title, desc = pending_block
            cur_block = {'title': title, 'desc': desc, 'groups': []}
            blocks.append(cur_block)
            cur_group = None
            pending_note = None
            i += 1
            continue
        if s.startswith('}'):
            in_root = False
            i += 1
            continue
        if in_root:
            mh = re.match(r'^/\*\s*──\s*(.+?)\s*─+\s*\*/$', s)
            if mh:
                cur_group = {'name': mh.group(1).strip(), 'note': '', 'tokens': []}
                cur_block['groups'].append(cur_group)
                pending_note = None
                i += 1
                continue
            if s.startswith('/*') and s.endswith('*/') and not s.startswith('/* ──'):
                note = s[2:-2].strip()
                if cur_group is None:
                    cur_group = {'name': 'General', 'note': '', 'tokens': []}
                    cur_block['groups'].append(cur_group)
                pending_note = note
                i += 1
                continue
            decls = re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', line)
            if decls:
                if cur_group is None:
                    cur_group = {'name': 'General', 'note': '', 'tokens': []}
                    cur_block['groups'].append(cur_group)
                mc = re.search(r'/\*(.*?)\*/\s*$', line)
                comment = mc.group(1).strip() if mc else (pending_note or '')
                for name, value in decls:
                    cur_group['tokens'].append({'name': name, 'value': value.strip(), 'comment': comment})
            elif not s:
                pending_note = None
        i += 1
    return blocks


COLOR_RE = re.compile(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|var\(--(color|brand|accent)')


def token_kind(name, value):
    if 'shadow' in name:
        return 'shadow'
    if 'radius' in name:
        return 'radius'
    if 'font' in name or '-type-' in name or 'weight' in name or 'motion' in name or 'opacity' in name:
        return 'other'
    if COLOR_RE.search(value):
        return 'color'
    return 'other'


def render_token_preview(t):
    k = token_kind(t['name'], t['value'])
    n = esc(t['name'])
    if k == 'color':
        return f'<span class="docs-swatch" style="background:var({n})" title="{n}"></span>'
    if k == 'shadow':
        return f'<span class="docs-shadow-sample" style="box-shadow:var({n})"></span>'
    if k == 'radius':
        return f'<span class="docs-radius-sample" style="border-radius:var({n})"></span>'
    return ''


def render_typography_samples(blocks):
    styles = {}
    order = []
    for b in blocks:
        for g in b['groups']:
            for t in g['tokens']:
                m = re.match(r'--sofia-type-(.+)-(size|lh|ls)$', t['name'])
                if m:
                    key = m.group(1)
                    if key not in styles:
                        styles[key] = {'comment': ''}
                        order.append(key)
                    styles[key][m.group(2)] = t['value']
                    if t['comment']:
                        styles[key]['comment'] = t['comment']
    rows = []
    for key in order:
        st = styles[key]
        weight = 'var(--sofia-weight-medium)' if 'Medium' in st['comment'] else 'var(--sofia-weight-regular)'
        style = (f"font-family:var(--sofia-font-family);font-size:var(--sofia-type-{key}-size);"
                 f"line-height:var(--sofia-type-{key}-lh);letter-spacing:var(--sofia-type-{key}-ls);font-weight:{weight}")
        rows.append([
            f'<span class="docs-type-sample" style="{esc(style)}">{esc(st["comment"].split("·")[0].strip() or key)}</span>',
            f'<code>--sofia-type-{esc(key)}-*</code>',
            esc(f"{st.get('size','—')} / {st.get('lh','—')} / {st.get('ls','—')}"),
            esc(st['comment']),
        ])
    return table(['Muestra', 'Tokens', 'size / line-height / letter-spacing', 'Comentario'], rows, 'docs-table--type')


# ──────────────────────────────────────────────────────────────────────────────
# 4. index.html
# ──────────────────────────────────────────────────────────────────────────────
SECTIONS = [
    ('inicio', 'Inicio'),
    ('cuando-usar', 'Cuándo usar cada superficie'),
    ('fundamentos', 'Fundamentos'),
    ('bottom-sheet', 'Bottom Sheet'),
    ('side-sheet', 'Side Sheet'),
    ('modal', 'Modal'),
    ('formularios', 'Formularios y widgets'),
    ('persistencia', 'Modelo de persistencia'),
    ('spec', 'Spec (MD) vs Figma'),
    ('recursos', 'Recursos'),
]
CATEGORY_SECTION = {'bottom-sheet': 'bottom-sheet', 'side-sheet': 'side-sheet', 'modal': 'modal', 'forms': 'formularios'}


class Site:
    def __init__(self, groups, content):
        self.groups = groups
        self.c = content
        self.node_index = {}   # figma node id → (group, variant)
        self.section_index = {}  # figma section id → group
        for g in groups:
            if g.get('figmaSection'):
                self.section_index.setdefault(g['figmaSection'], g)
            for v in g.get('variants', []):
                for nid in variant_node_ids(v):
                    self.node_index.setdefault(nid, (g, v))
        comp = {}
        for f in sorted(glob.glob(os.path.join(ROOT, 'css/components/*.css'))):
            comp['css/components/' + os.path.basename(f)] = css_classes(read(f))
        self.comp_css = comp

    # helpers -----------------------------------------------------------------
    def furl(self, nid):
        return figma_url(self.c, nid)

    def figma_link(self, nid, label=None, cls='docs-figma-link'):
        if not nid or str(nid).startswith('I'):
            return esc(nid or '')
        return f'<a class="{cls}" href="{esc(self.furl(nid))}" target="_blank" rel="noopener">{esc(label or nid)}</a>'

    def variant_anchor(self, g, v):
        return f'v-{g["_group"]}--{v["id"]}'

    def node_ref(self, nid, name=None):
        """Link al nodo Figma + link a la variante del sitio si existe."""
        out = self.figma_link(nid, f'{nid}' + (f' · {name}' if name else ''))
        if nid in self.node_index:
            g, v = self.node_index[nid]
            out += f' <a class="docs-site-link" href="#{self.variant_anchor(g, v)}">→ {esc(g["_group"])}/{esc(v["id"])}</a>'
        elif nid in self.section_index:
            g = self.section_index[nid]
            out += f' <a class="docs-site-link" href="#g-{esc(g["_group"])}">→ grupo {esc(g["_group"])}</a>'
        return out

    def definition(self, surface):
        for d in self.c.get('definitions', []):
            if d['surface'] == surface:
                return d
        return None

    # variant card --------------------------------------------------------------
    def required_css(self, v):
        cls = snippet_classes(v['_snippet'])
        sofia = {c for c in cls if c.startswith('sofia-')}
        files = [f for f, cs in self.comp_css.items() if cs & sofia]
        return files, any(c.startswith('eva-') for c in cls)

    def card(self, g, v):
        group = g['_group']
        vid = v['id']
        anchor = self.variant_anchor(g, v)
        nodes = variant_node_ids(v)
        w, h = int(v['width']), int(v['height'])
        stage = v.get('stage', '#ffffff')
        props = v.get('props') or {}
        chips = ''.join(f'<span class="eva-3-tag docs-chip"><span class="tag-text">{esc(k)}={esc(val)}</span></span>'
                        for k, val in props.items())
        figma_links = ''.join(
            f'<a class="eva-3-btn-ghost -sm docs-btn" href="{esc(self.furl(n))}" target="_blank" rel="noopener">'
            f'<em class="btn-text">Ver en Figma · {esc(n)}</em></a>'
            for n in nodes if not str(n).startswith('I'))
        lib_nodes = v.get('libraryNodeIds') or []
        figma_links += ''.join(
            f'<a class="eva-3-btn-ghost -sm docs-btn" href="{esc(library_url(n))}" target="_blank" rel="noopener">'
            f'<em class="btn-text">Ver en Librería · {esc(n)}</em></a>' for n in lib_nodes)
        search = ' '.join([v.get('name', ''), vid, group, ' '.join(nodes + lib_nodes), g.get('title', '')]).lower()
        snippet = display_snippet(v['_snippet'])
        files, _ = self.required_css(v)
        req = ['EVA (CDN): eva-core.min.css + eva.min.css', 'Rubik (Google Fonts)', 'css/tokens.css', 'css/base.css'] + files
        req_html = ''.join(f'<li><code>{esc(r)}</code></li>' for r in req)
        guidelines = ''
        if v.get('guidelines'):
            guidelines = ('<div class="docs-callout docs-callout--figma"><strong>Pautas en Figma</strong><ul>' +
                          ''.join(f'<li>{esc(x)}</li>' for x in v['guidelines']) + '</ul></div>')
        notes = ''
        if v.get('notes'):
            notes = (f'<details class="docs-details"><summary>Notas de implementación</summary>'
                     f'<div class="docs-details__body">{inline_md(v["notes"])}</div></details>')
        scripts = ''
        if v.get('scripts'):
            scripts = '<p class="docs-meta">Scripts: ' + ', '.join(f'<code>{esc(s)}</code>' for s in v['scripts']) + '</p>'
        wide = ' docs-card--wide' if w > 600 else ''
        preview = f'previews/{group}--{vid}.html'
        return f'''
<article class="docs-card docs-variant{wide}" id="{esc(anchor)}" data-search="{esc(search)}" data-group="{esc(group)}">
  <header class="docs-variant__head">
    <h4 class="docs-variant__name">{esc(v.get("name", vid))}</h4>
    <div class="docs-variant__meta"><code class="docs-variant__id">{esc(group)}/{esc(vid)}</code><span class="docs-meta">{w} × {h}px · stage <code>{esc(stage)}</code></span></div>
    <div class="docs-chips">{chips}</div>
  </header>
  <div class="docs-preview" style="background:{esc(stage)}" data-w="{w}" data-h="{h}">
    <div class="docs-preview__frame" style="width:{w}px;height:{h}px">
      <iframe src="{esc(preview)}" title="{esc(v.get("name", vid))}" loading="lazy" width="{w}" height="{h}" style="width:{w}px;height:{h}px" tabindex="-1"></iframe>
    </div>
    <span class="docs-preview__scale" aria-hidden="true"></span>
  </div>
  <div class="docs-variant__body">
    <p class="docs-variant__desc">{esc(v.get("description", ""))}</p>
    {guidelines}
    {notes}
    {scripts}
    <div class="docs-actions">
      <button type="button" class="eva-3-btn -sm -primary docs-btn docs-copy" data-copy-target="#code-{esc(anchor)}"><em class="btn-text">Copiar HTML</em></button>
      <button type="button" class="eva-3-btn-ghost -sm docs-btn docs-toggle-code" aria-expanded="false" aria-controls="codewrap-{esc(anchor)}"><em class="btn-text">Ver código</em></button>
      <a class="eva-3-btn-ghost -sm docs-btn" href="{esc(preview)}" target="_blank" rel="noopener"><em class="btn-text">Abrir preview ↗</em></a>
      {figma_links}
    </div>
    <div class="docs-codewrap" id="codewrap-{esc(anchor)}" hidden>
      <div class="docs-code"><pre><code id="code-{esc(anchor)}" class="docs-lang-html">{esc(snippet)}</code></pre></div>
    </div>
    <details class="docs-details docs-details--css"><summary>CSS requerido</summary><ul class="docs-details__body docs-list">{req_html}</ul></details>
  </div>
</article>'''

    def group_block(self, g):
        group = g['_group']
        sec = g.get('figmaSection')
        sec_link = self.figma_link(sec, f'Sección Figma {sec}') if sec else '—'
        if g.get('librarySection'):
            ls = g['librarySection']
            sec_link = (f'<a class="docs-figma-link" href="{esc(library_url(ls))}" target="_blank" rel="noopener">'
                        f'Librería SOFIA {esc(ls)}</a>') + ('' if not sec else ' · ' + sec_link)
        cards = ''.join(self.card(g, v) for v in g.get('variants', []))
        return f'''
<section class="docs-group" id="g-{esc(group)}" data-group="{esc(group)}">
  <header class="docs-group__head">
    <h3 class="docs-group__title">{esc(g.get("title", group))}</h3>
    <p class="docs-group__desc">{esc(g.get("description", ""))}</p>
    <p class="docs-meta">{sec_link} · CSS: <code>{esc(g.get("css", ""))}</code> · {len(g.get("variants", []))} variantes · grupo <code>{esc(group)}</code></p>
  </header>
  <div class="docs-grid">{cards}</div>
</section>'''

    # motion ------------------------------------------------------------------
    def motion_block(self, key, fname):
        m = self.c['motion'][key]
        L = self.c['motion']['labels']
        code = read(os.path.join(ROOT, 'js/motion', fname))
        dec_rows = [[esc(d['variable']), f'<code>{esc(d["value"])}</code>', esc(d['reason'])] for d in m.get('decisions', [])]
        img = m.get('image') or {}
        img_html = ''
        if img.get('src'):
            img_html = (f'<figure class="docs-figure"><img class="docs-zoom" src="{esc(img["src"])}" alt="{esc(m["title"])} — referencia de Figma" loading="lazy" '
                        f'width="{esc(img.get("pixelWidth", ""))}" height="{esc(img.get("pixelHeight", ""))}">'
                        f'<figcaption>{esc(img.get("name", ""))} · {self.figma_link(img.get("figmaNodeId"))}</figcaption></figure>')
        code_meta = m.get('code', {})
        nodes = ' · '.join(x for x in [
            self.figma_link(m.get('textNodeId'), f'Texto {m.get("textNodeId")}') if m.get('textNodeId') else '',
            self.figma_link(m.get('avoidNodeId'), f'Qué evitar {m.get("avoidNodeId")}') if m.get('avoidNodeId') else '',
            self.figma_link(code_meta.get('figmaNodeId'), f'Código {code_meta.get("figmaNodeId")}') if code_meta.get('figmaNodeId') else '',
        ] if x)
        exp = ''
        if m.get('expectedBehavior'):
            exp = (f'<h5>{esc(m.get("expectedBehaviorLabel") or L["expectedBehavior"])}</h5>'
                   f'<pre class="docs-ascii">{esc(m["expectedBehavior"])}</pre>')
        return f'''
<section class="docs-card docs-motion" id="motion-{esc(key)}">
  <h3>Motion · {esc(m["title"])}</h3>
  <p class="docs-meta">{nodes}</p>
  <div class="docs-motion__cols">
    <div>
      <h5>{esc(L["whatIs"])}</h5><p>{esc(m["whatIs"])}</p>
      <h5>{esc(L["communicates"])}</h5>
      <p><strong>{esc(L["enter"])}</strong> {esc(m["communicates"]["enter"])}</p>
      <p><strong>{esc(L["exit"])}</strong> {esc(m["communicates"]["exit"])}</p>
      <h5>{esc(L["avoid"])}</h5>
      <ul class="docs-list docs-list--avoid">{''.join(f"<li>{esc(a)}</li>" for a in m.get("avoid", []))}</ul>
    </div>
    <div>{img_html}</div>
  </div>
  <h5>{esc(L["decisions"])}</h5>
  {table(['Variable', 'Valor', 'Por qué'], dec_rows)}
  {exp}
  <h5>Código literal del handoff · <code>js/motion/{esc(fname)}</code></h5>
  {code_block(code, 'js', True, 'js/motion/' + fname)}
</section>'''

    def playground(self, name):
        p = os.path.join(ROOT, 'playground', f'{name}.html')
        inner = read(p) if os.path.exists(p) else '<p class="docs-muted">Playground en construcción</p>'
        return f'<div class="docs-playground" id="playground-{esc(name)}" data-playground="{esc(name)}">{inner}</div>'

    def groups_of(self, category):
        return [g for g in self.groups if g.get('category') == category]

    # sections ------------------------------------------------------------------
    def s_inicio(self):
        c = self.c
        contract = read(os.path.join(ROOT, 'CONTRACT.md'))
        msec = re.search(r'## Nombres de clases.*?\n(\|.*?)(?:\n\n|\n(?=[^|]))(.*?)(?=\n## )', contract, re.S)
        conv_html = ''
        if msec:
            tlines = [l for l in msec.group(1).splitlines() if l.startswith('|')]
            hdr = [x.strip() for x in tlines[0].strip('|').split('|')]
            rows = [[inline_md(x.strip()) for x in l.strip('|').split('|')] for l in tlines[2:]]
            conv_html = table([esc(h) for h in hdr], rows)
            extra = msec.group(2).strip()
            if extra:
                conv_html += ''.join(f'<p>{inline_md(p)}</p>' for p in extra.split('\n') if p.strip())
        install = f'''<!-- 1. EVA (Despegar design system) — siempre primero -->
<link rel="stylesheet" href="{EVA_CORE}">
<link rel="stylesheet" href="{EVA_CSS}">
<!-- 2. Fuente Rubik -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{RUBIK}" rel="stylesheet">
<!-- 3. Tokens + base SOFIA -->
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/base.css">
<!-- 4. CSS del componente que uses (ver "CSS requerido" en cada card) -->
<link rel="stylesheet" href="css/components/bs-header.css">'''
        motion_code = ''
        for f, names in [('bottom-sheet.js', 'openBottomSheet, closeBottomSheet'),
                         ('modal.js', 'openModal, closeModal'),
                         ('side-sheet.js', 'openSideSheet, closeSideSheet')]:
            motion_code += f"import {{ {names} }} from './js/motion/{f}';\n{motion_usage(f)}\n\n"
        motion_code = motion_code.rstrip() + '\n'
        n_var = sum(len(g.get('variants', [])) for g in self.groups)
        return f'''
<section class="docs-section" id="inicio">
  <div class="docs-hero docs-card">
    <p class="docs-eyebrow">Handoff para devs</p>
    <h1>SOFIA Librería Devs</h1>
    <p class="docs-lead">Todas las instancias ya diseñadas en Figma de <strong>bottom sheet</strong> (mobile), <strong>side sheet</strong> (desktop),
    <strong>modales</strong> (desktop + mobile) y <strong>formularios / widgets</strong> en bottom sheet de SOFIA, el asistente conversacional de Despegar,
    implementadas en HTML + CSS sobre EVA. No hay nada nuevo: cada pieza sale del Figma o del MD de referencia.</p>
    <ul class="docs-stats">
      <li><strong>{n_var}</strong> variantes</li>
      <li><strong>{len(self.groups)}</strong> grupos</li>
      <li><strong>3</strong> animaciones (JS del handoff)</li>
      <li><strong>{len(c["persistence"]["cases"])}</strong> casos de persistencia</li>
    </ul>
    <div class="docs-actions">
      <a class="eva-3-btn -md -primary docs-btn" href="{esc(c["figma"]["pageUrl"])}" target="_blank" rel="noopener"><em class="btn-text">Abrir el Figma ↗</em></a>
      <a class="eva-3-btn-ghost -md docs-btn" href="#bottom-sheet"><em class="btn-text">Ir a los componentes</em></a>
    </div>
  </div>

  <div class="docs-card">
    <h2>Fuentes</h2>
    <ul class="docs-list">
      <li><strong>Figma:</strong> <a href="{esc(c["figma"]["pageUrl"])}" target="_blank" rel="noopener">{esc(c["figma"]["fileName"])}</a> · página <code>{esc(c["figma"]["pageId"])}</code> “{esc(c["figma"]["pageName"])}” (fileKey <code>{esc(c["figma"]["fileKey"])}</code>).</li>
      <li><strong>MD de referencia:</strong> <a href="docs/bottomsheet-dialogue-referencia.md" target="_blank">docs/bottomsheet-dialogue-referencia.md</a> (“{esc(c["spec"]["title"])}”). Las diferencias con Figma están en <a href="#spec">Spec</a>.</li>
      <li><strong>Contenido documental:</strong> <code>docs/content.json</code> (textos literales extraídos del Figma) y el código de animación literal en <code>js/motion/*.js</code>.</li>
    </ul>
  </div>

  <div class="docs-card">
    <h2>Cómo usarlo</h2>
    <h3>1 · Instalación</h3>
    <p>Cargá EVA desde el CDN, la fuente Rubik, los tokens y la base SOFIA, y después el CSS del grupo que uses. Cada card indica su <em>CSS requerido</em> exacto.</p>
    {code_block(install, 'html', True, 'HTML · <head>')}
    <h3>2 · Markup</h3>
    <p>Copiá el snippet de la card (“Copiar HTML”). Es HTML puro, sin estilos inline ni scripts. Los textos dentro del componente quedan como en Figma (“Title”, “Primary button”, “Content / Slot”…): reemplazalos por el contenido real.</p>
    <h3>3 · Motion</h3>
    <p>Las animaciones son los ES modules literales del handoff. Importalos y usalos tal cual indica el comentario <code>Uso:</code> de cada archivo:</p>
    {code_block(motion_code, 'js', True, 'JS · ES modules')}
    <p class="docs-muted"><code>js/motion/motion.global.js</code> es una copia generada (expone <code>window.SofiaMotion</code>) que usa este sitio para los playgrounds. En producto usá los módulos originales.</p>
    <h3>4 · Convenciones de clases</h3>
    <p>BEM con prefijo <code>sofia-</code> (tabla del CONTRACT). Las clases <code>eva-3-*</code> son de EVA y no se redefinen.</p>
    {conv_html}
    <h3>5 · Cómo regenerar</h3>
    {code_block("python3 tools/build.py            # previews + motion.global.js + index.html" + chr(10) + "python3 tools/build.py --only modal  # solo las previews de un grupo", 'sh', True, 'Terminal (desde sofia-sheets-handoff/)')}
  </div>

  <div class="docs-card">
    <h2>Leyenda</h2>
    <dl class="docs-legend">
      <dt><span class="eva-3-tag docs-chip"><span class="tag-text">EVA prevalece</span></span></dt>
      <dd>Cuando el nodo de Figma es una instancia EVA (botones, tags, tabs, íconos, inputs) se usa la clase EVA real. Si EVA y Figma difieren de forma visible, <strong>gana EVA</strong> y la diferencia queda anotada en las notas de la variante.</dd>
      <dt>Notas de implementación</dt>
      <dd>Desplegable en cada card: decisiones tomadas al traducir Figma a código (layout, ajustes mínimos sobre EVA, diferencias EVA vs Figma, tokens usados). Leelas antes de integrar.</dd>
      <dt>Chips <span class="eva-3-tag docs-chip"><span class="tag-text">Prop=Valor</span></span></dt>
      <dd>Propiedades de la variante tal como figuran en el componente de Figma.</dd>
      <dt>Preview</dt>
      <dd>Se muestra al tamaño exacto del nodo de Figma (ancho × alto) y se achica para entrar en la card (nunca se agranda). “Abrir preview ↗” la abre a 1x.</dd>
      <dt>Pautas en Figma</dt>
      <dd>Notas que el diseño dejó junto al componente, transcriptas literal.</dd>
    </dl>
  </div>
</section>'''

    def s_cuando_usar(self):
        c = self.c
        cards = ''
        for d in c.get('definitions', []):
            definition = d.get('definition')
            if definition and d.get('definitionHighlight') and definition.startswith(d['definitionHighlight']):
                hl = d['definitionHighlight']
                def_html = f'<span class="docs-hl">{esc(hl)}</span>{esc(definition[len(hl):])}'
            else:
                def_html = esc(definition) if definition else '—'
            uses = ''.join(f'<li>{esc(u["text"])} <span class="docs-node">{self.figma_link(u.get("figmaNodeId"))}</span></li>' for u in d.get('useCases', [])) or '<li>—</li>'
            notes = ''.join(f'<li>{esc(n.get("fullText") or n["text"])} <span class="docs-node">{self.figma_link(n.get("figmaNodeId"))}</span></li>' for n in d.get('notes', [])) or '<li>—</li>'
            plat = esc(d.get('platform', '—')) + (f' <span class="docs-muted">{esc(d["platformLiteral"])}</span>' if d.get('platformLiteral') else '')
            extra = f'<p class="docs-muted">{esc(d["handoffComponents"])}</p>' if d.get('handoffComponents') else ''
            cards += f'''
<article class="docs-card docs-def">
  <h3>{esc(d["title"])} <span class="docs-node">{self.figma_link(d.get("titleNodeId"))}</span></h3>
  <p class="docs-meta">Plataforma: {plat}</p>
  <h5>Definición (Figma) {('<span class="docs-node">' + self.figma_link(d.get("definitionNodeId")) + '</span>') if d.get("definitionNodeId") else ''}</h5>
  <p>{def_html}</p>
  <h5>Cuándo / para qué</h5><ul class="docs-list">{uses}</ul>
  <h5>Notas del canvas</h5><ul class="docs-list">{notes}</ul>
  {extra}
</article>'''
        t = c['definitionsTable']
        cols = t['columns']
        col_head = [f'{esc(col["text"])}<br><span class="docs-node">{self.figma_link(col["figmaNodeId"])}</span>' for col in cols]
        # Fila de definiciones: ubicar cada celda por su x en la columna más cercana a la izquierda
        def col_index(x):
            idx = 0
            for i, col in enumerate(cols):
                if x is not None and x >= col['x']:
                    idx = i
            return idx
        trs = []
        for r in t['rows']:
            row = [''] * len(cols)
            for cell in r['cells']:
                txt = '<br>'.join(esc(l) for l in cell['lines']) if cell.get('lines') else esc(cell['text'])
                ci = col_index(cell.get('x', cols[0]['x']))
                row[ci] += f'{txt} <span class="docs-node">{self.figma_link(cell.get("figmaNodeId"))}</span>'
            trs.append([x or '—' for x in row])
        attrs = ''.join(f'<li>{esc(a["text"])} <span class="docs-node">{self.figma_link(a["figmaNodeId"])}</span></li>' for a in t.get('bottomSheetAttributes', []))
        return f'''
<section class="docs-section" id="cuando-usar">
  <h2 class="docs-section__title">Cuándo usar cada superficie</h2>
  <p class="docs-lead">Definiciones transcriptas literal del canvas de Figma. Donde Figma no tiene definición se muestra “—”.</p>
  <div class="docs-grid docs-grid--defs">{cards}</div>
  <div class="docs-card">
    <h3>Tabla del canvas</h3>
    <p class="docs-muted">{esc(t.get("description", ""))}</p>
    {table(col_head, trs, 'docs-table--canvas')}
    <h5>Atributos del bottom sheet (a la izquierda de la tabla)</h5>
    <ul class="docs-list">{attrs}</ul>
  </div>
</section>'''

    def s_fundamentos(self):
        blocks = parse_tokens(read(os.path.join(ROOT, 'css/tokens.css')))
        tok_html = ''
        for b in blocks:
            tok_html += f'<div class="docs-card docs-tokens"><h3>{esc(b["title"])}</h3>'
            if b.get('desc'):
                tok_html += f'<p class="docs-muted">{esc(b["desc"])}</p>'
            for g in b['groups']:
                rows = [[f'<code>{esc(t["name"])}</code>', f'<span class="docs-token-val">{render_token_preview(t)}<code>{esc(t["value"])}</code></span>', esc(t['comment'])]
                        for t in g['tokens']]
                tok_html += f'<h4 class="docs-tokens__group">{esc(g["name"])}</h4>'
                if g.get('note'):
                    tok_html += f'<p class="docs-muted">{esc(g["note"])}</p>'
                tok_html += table(['Token', 'Valor', 'Comentario'], rows, 'docs-table--tokens')
            tok_html += '</div>'
        spec = self.c['spec']
        st = spec['tokens']
        color_rows = [[f'<code>{esc(t["token"])}</code>', f'<span class="docs-token-val"><span class="docs-swatch" style="background:{esc(t["value"])}"></span><code>{esc(t["value"])}</code></span>', esc(t['description']), f'<code>{esc(t["css"])}</code>' if t.get('css') else '—'] for t in st['color']]
        dim_rows = [[f'<code>{esc(t["token"])}</code>', f'<code>{esc(t["value"])}</code>', esc(t.get('scope', '—')), esc(t['description']),
                     (f'<code>{esc(t["css"])}</code>' if t.get('css') else '—') + (f'<br><span class="docs-muted">{esc(t["cssNote"])}</span>' if t.get('cssNote') else '')] for t in st['dimensionMotion']]
        typo_rows = [[esc(t['element']), esc(t['font']), esc(t['size']), f'<span class="docs-token-val"><span class="docs-swatch" style="background:{esc(t["color"])}"></span><code>{esc(t["color"])}</code></span>'] for t in spec['typography']]
        mot = self.c['motion']
        princ = ''
        for p in mot.get('principles', []):
            body = f'<p>{esc(p["text"])}</p>' if p.get('text') else ''
            if p.get('items'):
                body += '<ul class="docs-list">' + ''.join(f'<li>{esc(i)}</li>' for i in p['items']) + '</ul>'
            princ += f'<div class="docs-principle"><h5>{esc(p["title"])}</h5>{body}</div>'
        return f'''
<section class="docs-section" id="fundamentos">
  <h2 class="docs-section__title">Fundamentos</h2>
  <p class="docs-lead">Tokens leídos de <code>css/tokens.css</code> en build time (agrupados por sus comentarios). Usá siempre <code>var(--sofia-…)</code>; cada token apunta a la variable EVA cuando existe, con el hex de Figma como fallback.</p>
  <div class="docs-card">
    <h3>Tipografía · escala</h3>
    <p class="docs-muted">Muestra armada con los tokens <code>size</code> / <code>lh</code> / <code>ls</code> de cada estilo y el peso indicado en el comentario.</p>
    {render_typography_samples(blocks)}
  </div>
  {tok_html}
  <div class="docs-card">
    <h3>Tokens del MD de referencia</h3>
    <p class="docs-muted">Tabla de <code>{esc(spec["source"])}</code>. Columna CSS = variable equivalente en <code>{esc(st["cssFile"])}</code>.</p>
    <h4 class="docs-tokens__group">Color</h4>
    {table(['Token (MD)', 'Valor', 'Descripción', 'CSS'], color_rows)}
    <h4 class="docs-tokens__group">Dimensión y motion</h4>
    {table(['Token (MD)', 'Valor', 'Scope', 'Descripción', 'CSS'], dim_rows)}
    <h4 class="docs-tokens__group">Tipografía (MD)</h4>
    {table(['Elemento', 'Fuente', 'Tamaño', 'Color'], typo_rows)}
  </div>
  <div class="docs-card">
    <h3>Motion · {esc(mot.get("principlesTitle", "Principios"))}</h3>
    <p>{esc(mot.get("intro", ""))}</p>
    <div class="docs-principles">{princ}</div>
    <p class="docs-muted">Fuente: {esc(mot.get("principlesSource", ""))}. El detalle de cada animación está en <a href="#motion-bottomSheet">bottom sheet</a>, <a href="#motion-sideSheet">side sheet</a> y <a href="#motion-modal">modal</a>.</p>
  </div>
</section>'''

    def surface_section(self, sid, title, lead_html, category, motion=None, playground=None):
        groups = ''.join(self.group_block(g) for g in self.groups_of(category))
        mot = self.motion_block(*motion) if motion else ''
        pg = ''
        if playground:
            pg = f'<div class="docs-card"><h3>Playground</h3>{self.playground(playground)}</div>'
        return f'''
<section class="docs-section" id="{sid}">
  <h2 class="docs-section__title">{esc(title)}</h2>
  <div class="docs-card docs-intro">{lead_html}</div>
  {groups}
  {mot}
  {pg}
</section>'''

    def def_lead(self, surface, extra=''):
        d = self.definition(surface)
        if not d:
            return '<p>—</p>'
        definition = d.get('definition')
        uses = ''.join(f'<li>{esc(u["text"])}</li>' for u in d.get('useCases', []))
        out = f'<h5>Definición (Figma · “{esc(d["title"])}”)</h5><p>{esc(definition) if definition else "—"}</p>'
        if uses:
            out += f'<h5>Cuándo / para qué</h5><ul class="docs-list">{uses}</ul>'
        out += f'<p class="docs-meta">Plataforma: {esc(d.get("platform", "—"))} · <a href="#cuando-usar">Ver todas las definiciones</a></p>'
        return out + extra

    def s_persistencia(self):
        p = self.c['persistence']
        cases = ''
        for cs in p['cases']:
            title = cs.get('title') or cs.get('fallbackTitle') or cs['id']
            title_note = f'<p class="docs-muted">{esc(cs["titleNote"])}</p>' if cs.get('titleNote') else ''
            steps = ''
            for s in cs['steps']:
                frames = ''
                for f in s.get('frames', []):
                    ki = ''.join(f'<li>{self.node_ref(k["id"], k.get("name"))}</li>' for k in f.get('keyInstances', []))
                    ki = f'<ul class="docs-list docs-list--tight">{ki}</ul>' if ki else ''
                    frames += f'''
<figure class="docs-frame docs-frame--{esc(f.get("platform", ""))}">
  <button type="button" class="docs-frame__btn" data-lightbox="{esc(f["image"])}" data-caption="{esc(s.get("caption", ""))}">
    <img src="{esc(f["image"])}" alt="Frame {esc(f["n"])} · {esc(f.get("name", ""))} ({esc(f.get("platform", ""))})" loading="lazy" width="{int(f.get("width", 0))}" height="{int(f.get("height", 0))}">
  </button>
  <figcaption>#{esc(f["n"])} · {esc(f.get("platform", ""))} · {self.figma_link(f["figmaNodeId"])}{ki}</figcaption>
</figure>'''
                assoc = f'<p class="docs-muted">{esc(s["associationNote"])}</p>' if s.get('associationNote') else ''
                steps += f'''
<li class="docs-step">
  <p class="docs-step__caption"><span class="docs-step__n">{esc(s["n"])}</span>{"<br>".join(esc(l) for l in s.get("captionLines") or [s.get("caption", "")])}
    <span class="docs-node">{self.figma_link(s.get("captionNodeId"))}</span></p>
  {assoc}
  <div class="docs-frames">{frames}</div>
</li>'''
            cases += f'''
<article class="docs-card docs-case" id="persistencia-{esc(cs["id"])}">
  <h3>{esc(title)} <span class="docs-node">{self.figma_link(cs.get("titleNodeId") or cs.get("groupId"))}</span></h3>
  {title_note}
  <p class="docs-meta"><a href="{esc(cs["figmaUrl"])}" target="_blank" rel="noopener">Ver grupo en Figma ({esc(cs["groupId"])})</a></p>
  <ol class="docs-steps">{steps}</ol>
</article>'''
        typos = ', '.join(esc(t) for t in p.get('literalTypos', []))
        return f'''
<section class="docs-section" id="persistencia">
  <h2 class="docs-section__title">{esc(p["title"])}</h2>
  <div class="docs-card docs-intro">
    <p><strong>Son capturas de referencia del flujo en Figma</strong>, no implementación: muestran cómo se comportan los widgets y formularios a lo largo de la conversación. Las piezas implementadas están en <a href="#formularios">Formularios y widgets</a> (los links “→” llevan a la variante).</p>
    <p class="docs-muted">{esc(p.get("note", ""))} {esc(p.get("ordering", ""))}</p>
    <p class="docs-muted">Los captions se transcriben literal, con sus typos: {typos}.</p>
    <p class="docs-meta"><a href="{esc(p["figmaUrl"])}" target="_blank" rel="noopener">Sección en Figma ({esc(p["sectionId"])})</a></p>
  </div>
  {cases}
</section>'''

    def s_spec(self):
        s = self.c['spec']
        props_rows = [[f'<code>{esc(p["prop"])}</code>', ' · '.join(f'<code>{esc(o)}</code>' for o in p['options']), f'<code>{esc(p["default"])}</code>'] for p in s['dialogueProps']]
        d = s['dims']
        dims_rows = [
            ['Ancho', f'mobile <code>{esc(d["width"]["mobile"])}</code> · desktop <code>{esc(d["width"]["desktop"])}</code>'],
            ['Border radius', f'token <code>{esc(d["borderRadius"]["token"])}</code> = <code>{esc(d["borderRadius"]["value"])}</code>'],
            ['Sombra', f'mobile <code>{esc(d["shadow"]["mobile"])}</code><br>desktop <code>{esc(d["shadow"]["desktop"])}</code>'],
        ]
        subs = ''
        for sc in s['subcomponents']:
            body = ''
            if sc.get('types'):
                body += '<p>Tipos: ' + ' · '.join(f'<code>{esc(t)}</code>' for t in sc['types']) + '</p>'
            if sc.get('state'):
                body += f'<p class="docs-muted">{esc(sc["state"])}</p>'
            if sc.get('specs'):
                body += '<ul class="docs-list">' + ''.join(f'<li>{esc(x)}</li>' for x in sc['specs']) + '</ul>'
            if sc.get('variants'):
                body += '<ul class="docs-list">' + ''.join(f'<li><strong>{esc(x["variant"])}</strong> — {esc(x["description"])}</li>' for x in sc['variants']) + '</ul>'
            subs += f'<div class="docs-sub"><h5>{esc(sc["name"])}</h5>{body}</div>'
        pb = s['peekBar']
        pb_labels = {'size': 'Tamaño', 'background': 'Fondo', 'border': 'Borde', 'shadow': 'Sombra', 'shows': 'Muestra', 'note': 'Nota'}
        pb_rows = [[pb_labels[k], esc(pb[k])] for k in ['size', 'background', 'border', 'shadow', 'shows', 'note'] if pb.get(k)]
        comp_rows = [[esc(x['name']), esc(x['description'])] for x in s.get('componentsList', [])]
        map_rows = []
        for mp in s['mapping']:
            nodes = '<ul class="docs-list docs-list--tight">' + ''.join(f'<li>{self.node_ref(n["id"], n.get("name"))}</li>' for n in mp.get('figmaNodes', [])) + '</ul>'
            extra = ''
            if mp.get('figmaDescription'):
                extra += f'<p class="docs-muted"><em>Descripción del componente en Figma:</em> {esc(mp["figmaDescription"])}</p>'
            if mp.get('note'):
                extra += f'<p class="docs-muted">{esc(mp["note"])}</p>'
            map_rows.append([esc(mp['md']), esc(mp['figma']) + extra, nodes, f'<code>{esc(mp["cssClass"])}</code>' if mp.get('cssClass') else '—'])
        disc = ''
        for x in s['discrepancies']:
            conf = f'<span class="eva-3-tag docs-chip docs-chip--warn"><span class="tag-text">confianza {esc(x["confidence"])}</span></span>' if x.get('confidence') else ''
            tcss = f'<dt>tokens.css</dt><dd><code>{esc(x["tokensCss"])}</code></dd>' if x.get('tokensCss') else ''
            disc += f'''
<div class="docs-disc">
  <h5>{esc(x["topic"])} {conf}</h5>
  <dl><dt>MD</dt><dd>{esc(x["md"])}</dd><dt>Figma</dt><dd>{esc(x["figma"])}</dd>{tcss}<dt>Resolución</dt><dd><strong>{esc(x["resolution"])}</strong></dd></dl>
</div>'''
        refs = ''.join(f'<li><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["label"])}</a></li>' for r in s['references'])
        return f'''
<section class="docs-section" id="spec">
  <h2 class="docs-section__title">Spec · {esc(s["title"])}</h2>
  <div class="docs-card docs-intro">
    <p>{esc(s["description"])}</p>
    <p class="docs-muted">Fuente: <a href="{esc(s["source"])}" target="_blank">{esc(s["source"])}</a>. Esta spec describe la librería SOFIA; el handoff de Figma manda cuando difieren (ver discrepancias).</p>
  </div>
  <div class="docs-card"><h3>Props del Dialogue (MD)</h3>{table(['Prop', 'Opciones', 'Default'], props_rows)}</div>
  <div class="docs-card"><h3>Dimensiones (MD)</h3>{table(['Propiedad', 'Valor'], dims_rows)}</div>
  <div class="docs-card"><h3>Subcomponentes (MD)</h3><div class="docs-subs">{subs}</div></div>
  <div class="docs-card"><h3>{esc(pb["title"])}</h3>{table(['Propiedad', 'Valor (MD)'], pb_rows)}<p class="docs-muted">Implementación: <a href="#v-forms-trip--trip-desktop-peek">forms-trip/trip-desktop-peek</a>, <a href="#v-forms-trip--trip-mobile-peek">forms-trip/trip-mobile-peek</a>, <a href="#v-forms-coupon--coupon-peek">forms-coupon/coupon-peek</a>.</p></div>
  <div class="docs-card"><h3>Componentes listados en el MD</h3>{table(['Componente', 'Descripción'], comp_rows)}</div>
  <div class="docs-card"><h3>Mapping MD → componente del handoff</h3>{table(['MD', 'Figma', 'Nodos (→ variante del sitio)', 'Clase CSS'], map_rows, 'docs-table--mapping')}</div>
  <div class="docs-card docs-card--warn"><h3>Discrepancias MD vs Figma</h3><div class="docs-discs">{disc}</div></div>
  <div class="docs-card"><h3>Referencias</h3><ul class="docs-list">{refs}</ul></div>
</section>'''

    def s_recursos(self):
        c = self.c
        sec_rows = []
        for sct in c.get('sections', []):
            sec_rows.append([esc(sct.get('title') or '—'), esc(sct.get('name', '')),
                             f'<a href="{esc(sct["figmaUrl"])}" target="_blank" rel="noopener">{esc(sct["id"])} ↗</a>'])
        loose = [[esc(n.get('name', '')[:90] + ('…' if len(n.get('name', '')) > 90 else '')), esc(n.get('type', '')),
                  f'<a href="{esc(n["figmaUrl"])}" target="_blank" rel="noopener">{esc(n["id"])} ↗</a>'] for n in c.get('looseCanvasNodes', [])]
        css_files = ['css/tokens.css', 'css/base.css'] + ['css/components/' + os.path.basename(f) for f in sorted(glob.glob(os.path.join(ROOT, 'css/components/*.css')))]
        js_files = ['js/motion/bottom-sheet.js', 'js/motion/modal.js', 'js/motion/side-sheet.js', 'js/motion/motion.global.js (generado)']
        files = ''.join(f'<li><a href="{esc(f)}" target="_blank"><code>{esc(f)}</code></a></li>' for f in css_files)
        jfiles = ''.join(f'<li><a href="{esc(f.split(" ")[0])}" target="_blank"><code>{esc(f)}</code></a></li>' for f in js_files)
        return f'''
<section class="docs-section" id="recursos">
  <h2 class="docs-section__title">Recursos</h2>
  <div class="docs-card"><h3>Secciones del Figma</h3>{table(['Título en Figma', 'Nombre de la sección', 'Link'], sec_rows)}
    <h5>Nodos sueltos en el canvas</h5>{table(['Nodo', 'Tipo', 'Link'], loose)}</div>
  <div class="docs-card docs-files">
    <div><h3>CSS</h3><ul class="docs-list">{files}</ul></div>
    <div><h3>JS</h3><ul class="docs-list">{jfiles}</ul></div>
    <div><h3>Docs</h3><ul class="docs-list">
      <li><a href="README.md" target="_blank"><code>README.md</code></a> — cómo abrir, estructura y uso</li>
      <li><a href="CONTRACT.md" target="_blank"><code>CONTRACT.md</code></a> — reglas y convenciones</li>
      <li><a href="docs/bottomsheet-dialogue-referencia.md" target="_blank"><code>docs/bottomsheet-dialogue-referencia.md</code></a> — spec MD</li>
      <li><a href="docs/content.json" target="_blank"><code>docs/content.json</code></a> — contenido documental del Figma</li>
    </ul></div>
  </div>
</section>'''

    # nav ---------------------------------------------------------------------
    def nav(self):
        items = ''
        for sid, label in SECTIONS:
            sub = ''
            cat = next((k for k, v in CATEGORY_SECTION.items() if v == sid), None)
            if cat:
                links = ''.join(f'<li><a href="#g-{esc(g["_group"])}" data-nav="g-{esc(g["_group"])}">{esc(g.get("title", g["_group"]).split("·")[-1].strip())} <span class="docs-nav__count">{len(g.get("variants", []))}</span></a></li>' for g in self.groups_of(cat))
                if sid in ('bottom-sheet', 'side-sheet', 'modal'):
                    key = {'bottom-sheet': 'bottomSheet', 'side-sheet': 'sideSheet', 'modal': 'modal'}[sid]
                    links += f'<li><a href="#motion-{key}" data-nav="motion-{key}">Motion</a></li>'
                sub = f'<ul class="docs-nav__sub">{links}</ul>'
            items += f'<li><a href="#{sid}" data-nav="{sid}" class="docs-nav__sec">{esc(label)}</a>{sub}</li>'
        return f'<nav class="docs-nav" aria-label="Secciones"><ul>{items}</ul></nav>'

    def templates(self):
        out = []
        for g in self.groups:
            for v in g.get('variants', []):
                if v['_snippet'] is None:
                    continue
                out.append(f'<template data-snippet="{esc(g["_group"])}/{esc(v["id"])}">{display_snippet(v["_snippet"])}</template>')
        return '\n'.join(out)

    def render(self):
        c = self.c
        comp_css = sorted(glob.glob(os.path.join(ROOT, 'css/components/*.css')))
        css_links = '\n'.join(f'<link rel="stylesheet" href="css/components/{os.path.basename(f)}">' for f in comp_css)
        pg_css = '<link rel="stylesheet" href="css/playground.css">' if os.path.exists(os.path.join(ROOT, 'css/playground.css')) else ''
        pg_js = '<script src="js/playground.js"></script>' if os.path.exists(os.path.join(ROOT, 'js/playground.js')) else ''
        bs_lead = self.def_lead('bottomSheet')
        ss_lead = self.def_lead('sideSheet')
        modal_lead = self.def_lead('modal')
        forms_lead = self.def_lead('dialog', '<p class="docs-muted">Las instancias “bottomsheet pack” (viaje) y “bottomsheet form” (cupón / destino) salen del <a href="#persistencia">Modelo de persistencia</a>: cada una aparece en uno o más pasos del flujo.</p>')
        body = ''.join([
            self.s_inicio(),
            self.s_cuando_usar(),
            self.s_fundamentos(),
            self.surface_section('bottom-sheet', 'Bottom Sheet', bs_lead, 'bottom-sheet', ('bottomSheet', 'bottom-sheet.js'), 'bottom-sheet'),
            self.surface_section('side-sheet', 'Side Sheet', ss_lead, 'side-sheet', ('sideSheet', 'side-sheet.js'), 'side-sheet'),
            self.surface_section('modal', 'Modal', modal_lead, 'modal', ('modal', 'modal.js'), 'modal'),
            self.surface_section('formularios', 'Formularios y widgets', forms_lead, 'forms', None, 'forms'),
            self.s_persistencia(),
            self.s_spec(),
            self.s_recursos(),
        ])
        n_var = sum(len(g.get('variants', [])) for g in self.groups)
        return f'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOFIA Librería Devs</title>
<!-- ARCHIVO GENERADO por tools/build.py — no editar a mano. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{RUBIK}" rel="stylesheet">
<link rel="stylesheet" href="{EVA_CORE}">
<link rel="stylesheet" href="{EVA_CSS}">
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/base.css">
{css_links}
<link rel="stylesheet" href="css/docs.css">
{pg_css}
</head>
<body class="docs-body">
<a class="docs-skip" href="#docs-main">Saltar al contenido</a>
<header class="docs-topbar">
  <button type="button" class="docs-topbar__menu eva-3-btn-ghost -sm" aria-controls="docs-sidebar" aria-expanded="false" aria-label="Abrir navegación"><i class="eva-3-icon-hamburger-menu" aria-hidden="true"></i></button>
  <a class="docs-topbar__brand" href="#inicio"><span class="docs-topbar__logo">SOFIA</span> <span class="docs-topbar__sub">Librería Devs</span></a>
  <a class="eva-3-btn -sm -primary docs-btn docs-topbar__figma" href="{esc(c["figma"]["pageUrl"])}" target="_blank" rel="noopener"><em class="btn-text">Figma ↗</em></a>
</header>
<div class="docs-layout">
  <aside class="docs-sidebar" id="docs-sidebar">
    <div class="docs-search">
      <label class="docs-search__label" for="docs-search-input">Buscar variante</label>
      <div class="docs-search__field"><i class="eva-3-icon-search" aria-hidden="true"></i>
        <input id="docs-search-input" type="search" placeholder="Nombre, id o nodo (ej. 4048:3733)" autocomplete="off"></div>
      <p class="docs-search__status" aria-live="polite" data-total="{n_var}"></p>
    </div>
    {self.nav()}
  </aside>
  <div class="docs-backdrop" hidden></div>
  <main class="docs-main" id="docs-main">
    <p class="docs-noresults" hidden>No hay variantes que coincidan con la búsqueda.</p>
    {body}
    <footer class="docs-footer"><p>Generado por <code>tools/build.py</code> a partir de <code>components/*/manifest.json</code>, <code>css/tokens.css</code> y <code>docs/content.json</code>. Fuente: <a href="{esc(c["figma"]["pageUrl"])}" target="_blank" rel="noopener">Figma {esc(c["figma"]["fileKey"])}</a>.</p></footer>
  </main>
</div>
<div class="docs-lightbox" hidden role="dialog" aria-modal="true" aria-label="Imagen ampliada">
  <button type="button" class="docs-lightbox__close eva-3-btn -sm -primary" aria-label="Cerrar"><i class="eva-3-icon-close" aria-hidden="true"></i></button>
  <figure><img alt=""><figcaption></figcaption></figure>
</div>
<!-- Snippets para playgrounds: un template por variante (atributo data-snippet = grupo/id) -->
{self.templates()}
<script src="js/motion/motion.global.js"></script>
<script src="js/docs.js"></script>
{pg_js}
</body>
</html>
'''


def build_index(groups):
    content = json.loads(read(os.path.join(ROOT, 'docs/content.json')))
    site = Site(groups, content)
    write(os.path.join(ROOT, 'index.html'), site.render())
    return sum(len(g.get('variants', [])) for g in groups)


def main():
    ap = argparse.ArgumentParser(description='Build del sitio de handoff SOFIA')
    ap.add_argument('--only', action='append', default=[], metavar='GROUP',
                    help='regenerar solo las previews de este grupo (repetible)')
    args = ap.parse_args()
    errors = []
    groups = load_groups(errors)
    only = set(args.only)
    if only:
        unknown = only - {g['_group'] for g in groups}
        for u in sorted(unknown):
            errors.append(f'--only {u}: grupo inexistente')
    count = build_previews(groups, only)
    print(f'{count} previews generadas')
    try:
        build_motion_global()
        print('js/motion/motion.global.js generado')
    except Exception as e:  # noqa: BLE001
        errors.append(f'motion.global.js: {e}')
    try:
        n = build_index(groups)
        print(f'index.html generado ({n} variantes)')
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        errors.append(f'index.html: {e}')
    for e in errors:
        print('ERROR', e)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
