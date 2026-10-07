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
    ('bottom-sheet', 'Bottom Sheet'),
    ('modal', 'Modal'),
    ('side-sheet', 'Side Sheet'),
]
CATEGORY_SECTION = {'bottom-sheet': 'bottom-sheet', 'side-sheet': 'side-sheet', 'modal': 'modal'}


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
        install = f'''<!-- 1. EVA -->
<link rel=”stylesheet” href=”{EVA_CORE}”>
<link rel=”stylesheet” href=”{EVA_CSS}”>
<!-- 2. Rubik -->
<link href=”{RUBIK}” rel=”stylesheet”>
<!-- 3. Tokens + base SOFIA -->
<link rel=”stylesheet” href=”css/tokens.css”>
<link rel=”stylesheet” href=”css/base.css”>
<!-- 4. CSS del componente (ver “CSS requerido” en cada card) -->
<link rel=”stylesheet” href=”css/components/bs-header.css”>'''
        n_var = sum(len(g.get('variants', [])) for g in self.groups)
        return f'''
<section class=”docs-section docs-section--hero” id=”inicio”>
  <div class=”docs-hero docs-card”>
    <p class=”docs-eyebrow”>Handoff para devs · SOFIA</p>
    <h1>SOFIA Librería Devs</h1>
    <p class=”docs-lead”>Componentes de <strong>Bottom Sheet</strong>, <strong>Modal</strong> y <strong>Side Sheet</strong> de SOFIA — el asistente conversacional de Despegar — implementados en HTML + CSS sobre EVA.</p>
    <ul class=”docs-stats”>
      <li><strong>{n_var}</strong> variantes</li>
      <li><strong>{len(self.groups)}</strong> grupos</li>
      <li><strong>3</strong> animaciones JS</li>
    </ul>
    <div class=”docs-actions”>
      <a class=”eva-3-btn -md -primary docs-btn” href=”{esc(c['figma']['pageUrl'])}” target=”_blank” rel=”noopener”><em class=”btn-text”>Figma ↗</em></a>
      <a class=”eva-3-btn-ghost -md docs-btn” href=”#bottom-sheet”><em class=”btn-text”>Ver componentes</em></a>
    </div>
  </div>
  <div class=”docs-card”>
    <h2>Instalación</h2>
    <p class=”docs-muted”>Cargá EVA, Rubik, los tokens SOFIA y el CSS del componente que uses. Cada card muestra su <em>CSS requerido</em> exacto.</p>
    {code_block(install, 'html', True, 'HTML · &lt;head&gt;')}
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

    def s_grilla(self):
        bp_rows = [
            ['Mobile',  '1–767',   '2',  '16px', '16px', '360px'],
            ['Tablet',  '768–1023','12', '24px', '24px', '—'],
            ['Desktop', '1024–∞',  '12', '24px', '24px', '1366px'],
        ]
        bp_table = table(['Breakpoint', 'Rango (px)', 'Columnas', 'Gutter', 'Margen', 'Artboard ref.'], bp_rows)

        spacing_rows = [
            ['Entre tools (input + compose + board + follow-up)', '48px',
             '<span class="eva-3-tag docs-chip"><span class="tag-text">Definido</span></span>'],
            ['Input → compose', '24px',
             '<span class="eva-3-tag docs-chip"><span class="tag-text">Definido</span></span>'],
            ['Compose → board', '16px',
             '<span class="eva-3-tag docs-chip"><span class="tag-text">Definido</span></span>'],
            ['Board → follow-up', '16px',
             '<span class="eva-3-tag docs-chip docs-chip--pending"><span class="tag-text">⚠ Propuesta, sin confirmar</span></span>'],
        ]
        spacing_table = table(['Tramo', 'Medida', 'Estado'], spacing_rows)

        cards_rows = [
            ['1366', '~613px', '242px fija · scroll'],
            ['1440+', '~628px', '242px fija · scroll'],
            ['768', '~314px', '242px fija · scroll'],
            ['360', '~328px (2 col)', '242px fija · scroll'],
        ]
        cards_table = table(['Viewport', 'Compose (6 col)', 'Card'], cards_rows)

        alt_rows = [
            ['6 col, card = 2 col', '188–193px', 'Todo calza en la grilla de 12, incluido board full. Se aleja de los 242px de Figma.'],
            ['Cards fijas 242px', '242px', 'Respeta Figma. Para ver 3 enteras hace falta compose ≥ 758px (8 columnas ~825–845px).'],
        ]
        alt_table = table(['Opción', 'Ancho card', 'Trade-off'], alt_rows)

        css_props = ''':root {
  /* ── Grilla EVA · chat de SOFIA ─────────────────────────────── */
  --grid-cols-mobile:   2;    --grid-gutter-mobile:  16px; --grid-margin-mobile:  16px;
  --grid-cols-tablet:  12;    --grid-gutter-tablet:  24px; --grid-margin-tablet:  24px;
  --grid-cols-desktop: 12;    --grid-gutter-desktop: 24px; --grid-margin-desktop: 24px;

  --grid-container-max: 1280px;   /* contenedor large */
  --grid-rail:           68px;    /* rail lateral (no se superpone) */

  /* En el artboard 1366: 1366 − 68 − 2×24 = 1250px */
  --grid-container-w: min(var(--grid-container-max), 100% - var(--grid-rail) - 2 * var(--grid-margin-desktop));

  /* Compose = 6 columnas (4–9), centrado */
  --grid-compose-cols:    6;
  --grid-compose-span: calc(
    (var(--grid-compose-cols) / var(--grid-cols-desktop)) * var(--grid-container-w)
  );
}

/* Ancho de columna (fórmula) */
/* col = (container − (cols − 1) × gutter) / cols */
/* En 1366: (1250 − 11×24) / 12 = (1250 − 264) / 12 = 986 / 12 ≈ 82.2px/col */'''

        demo_html = '''<div class="grilla-demo" id="grilla-demo">
  <div class="grilla-demo__bar">
    <div class="grilla-demo__vp-btns" role="group" aria-label="Viewport">
      <button class="grilla-demo__vp-btn is-active" data-vp="360">360 <span>Mobile</span></button>
      <button class="grilla-demo__vp-btn" data-vp="768">768 <span>Tablet</span></button>
      <button class="grilla-demo__vp-btn" data-vp="1366">1366 <span>Desktop</span></button>
    </div>
    <label class="grilla-demo__overlay-toggle">
      <input type="checkbox" id="grilla-overlay" checked> Overlay columnas <kbd>G</kbd>
    </label>
  </div>
  <div class="grilla-demo__stage-wrap">
    <div class="grilla-demo__stage" id="grilla-stage">
      <div class="grilla-demo__overlay" id="grilla-overlay-el" aria-hidden="true"></div>
      <div class="grilla-demo__content">
        <div class="grilla-demo__rail" title="Rail lateral 68px"></div>
        <div class="grilla-demo__container" id="grilla-container">
          <div class="grilla-demo__block grilla-demo__block--compose" id="grilla-compose">
            <span class="grilla-demo__lbl" id="grilla-lbl-compose">Compose · 6 col</span>
          </div>
          <div class="grilla-demo__block grilla-demo__block--full" id="grilla-full">
            <span class="grilla-demo__lbl">Board full · contenedor</span>
          </div>
          <div class="grilla-demo__measurements" id="grilla-measurements"></div>
        </div>
      </div>
    </div>
    <p class="docs-muted grilla-demo__hint">Ancho simulado; el overlay dibuja columnas reales para el viewport seleccionado.</p>
  </div>
</div>
<script>
(function(){
  var GRIDS = {
    360:  { cols: 2,  gutter: 16, margin: 16, container: null,  rail: 0,   label: 'Mobile' },
    768:  { cols: 12, gutter: 24, margin: 24, container: null,  rail: 0,   label: 'Tablet' },
    1366: { cols: 12, gutter: 24, margin: 24, container: 1280,  rail: 68,  label: 'Desktop' },
  };
  var compose_cols = 6;
  var stage = document.getElementById('grilla-stage');
  var overlay = document.getElementById('grilla-overlay-el');
  var container = document.getElementById('grilla-container');
  var composeEl = document.getElementById('grilla-compose');
  var fullEl = document.getElementById('grilla-full');
  var lblCompose = document.getElementById('grilla-lbl-compose');
  var measureEl = document.getElementById('grilla-measurements');
  var currentVp = 360;

  function colWidth(g, w) {
    return (w - (g.cols - 1) * g.gutter) / g.cols;
  }
  function containerW(g, stageW) {
    var avail = stageW - g.rail - 2 * g.margin;
    return g.container ? Math.min(g.container, avail) : avail;
  }

  function render(vp) {
    var g = GRIDS[vp];
    var stageW = stage.getBoundingClientRect().width || 640;
    var cw = containerW(g, stageW);
    var col = colWidth(g, cw);
    var composeCols = (g.cols >= 12) ? compose_cols : g.cols;
    var composeW = composeCols * col + (composeCols - 1) * g.gutter;

    container.style.width = cw + 'px';
    container.style.marginLeft = g.rail ? g.rail + 'px' : 'auto';
    container.style.marginRight = 'auto';
    composeEl.style.width = composeW + 'px';
    composeEl.style.marginLeft = 'auto';
    composeEl.style.marginRight = 'auto';
    fullEl.style.width = cw + 'px';
    lblCompose.textContent = 'Compose · ' + composeCols + ' col · ' + Math.round(composeW) + 'px';

    measureEl.innerHTML =
      '<span>Contenedor: <strong>' + Math.round(cw) + 'px</strong></span>' +
      (g.rail ? '<span>Rail: <strong>' + g.rail + 'px</strong></span>' : '') +
      '<span>Col: <strong>' + col.toFixed(1) + 'px</strong></span>' +
      '<span>Compose (' + composeCols + ' col): <strong>' + Math.round(composeW) + 'px</strong></span>';

    // overlay columns
    var cols = '';
    for (var i = 0; i < g.cols; i++) {
      var left = i * (col + g.gutter);
      cols += '<span class="grilla-demo__col" style="left:' + left + 'px;width:' + col + 'px"></span>';
    }
    overlay.innerHTML = cols;
    overlay.style.left = (g.rail || (stageW - cw)/2) + 'px';
    overlay.style.width = cw + 'px';
  }

  document.querySelectorAll('.grilla-demo__vp-btn').forEach(function(btn){
    btn.addEventListener('click', function(){
      document.querySelectorAll('.grilla-demo__vp-btn').forEach(function(b){ b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      currentVp = parseInt(btn.dataset.vp);
      render(currentVp);
    });
  });
  document.getElementById('grilla-overlay').addEventListener('change', function(){
    overlay.hidden = !this.checked;
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'g' || e.key === 'G') {
      var cb = document.getElementById('grilla-overlay');
      cb.checked = !cb.checked;
      overlay.hidden = !cb.checked;
    }
  });
  window.addEventListener('resize', function(){ render(currentVp); });
  setTimeout(function(){ render(currentVp); }, 100);
})();
</script>'''

        return f'''
<section class="docs-section" id="grilla">
  <h2 class="docs-section__title">Grilla del chat</h2>

  <div class="docs-card docs-intro">
    <p>La grilla que usa el chat de SOFIA es la <strong>grilla de EVA Foundations</strong>, con los valores exactos que quedaron definidos en la sesión de Grid Inspector (1–2 oct 2026).
    Antes de publicar, verificar contra <a href="https://www.figma.com/design/lFKYrtVFFtv5Un9UHHTlbY/Home---SOFIA?node-id=1940-7999" target="_blank" rel="noopener">Home — SOFIA · diseño del chat (1940:7999)</a>
    y <a href="https://www.figma.com/design/9rtCLd5yqc4RKZYn76ByXy/Foundations?node-id=3903-2045" target="_blank" rel="noopener">Foundations · Spacing, Grid &amp; Container (3903:2045)</a>.</p>
  </div>

  <div class="docs-card">
    <h3>Breakpoints y geometría</h3>
    {bp_table}
    <ul class="docs-list" style="margin-top:12px">
      <li>Contenedor large <strong>1280px</strong> (medium 1062, small 844 — el chat usa <em>large</em>).</li>
      <li>Rail lateral <strong>68px</strong>: el contenedor lo reserva, no se superpone.</li>
      <li>En el artboard 1366: <code>1366 − 68 − 2×24 = 1250px</code> (no llega al tope de 1280).</li>
      <li>Compose: span centrado de <strong>6 columnas</strong> (col 4 a col 9).</li>
    </ul>
  </div>

  <div class="docs-card">
    <h3>Fórmulas como custom properties</h3>
    <p class="docs-muted">Copiá esto en tu <code>:root</code>. El ancho de columna se calcula con la fórmula estándar de EVA: <code>(contenedor − (cols − 1) × gutter) / cols</code>.</p>
    {code_block(css_props, 'css', True, 'CSS · :root')}
  </div>

  <div class="docs-card">
    <h3>Demo interactiva</h3>
    <p class="docs-muted">Seleccioná un viewport para ver el contenedor, el compose (6 col) y el overlay de columnas. Atajo: <kbd>G</kbd> para toggle del overlay.</p>
    {demo_html}
  </div>

  <div class="docs-card">
    <h3>Reglas de producto</h3>
    <h4 style="margin-top:16px">Ancho de boards</h4>
    <ul class="docs-list">
      <li>≤ 3 ítems → ancho del <strong>compose</strong> (6 col).</li>
      <li>≥ 4 ítems → <strong>full</strong> (ancho del contenedor).</li>
      <li>Mapa → siempre <strong>full</strong>.</li>
      <li>Estado de vuelo → siempre <strong>compose</strong> (un solo cluster).</li>
    </ul>
    <h4>Una tool</h4>
    <p>Cada componente es: input del usuario + compose (≥ 2 oraciones) + board + follow-up (pregunta en texto, mismo ancho que el compose). Los chips de sugerencia van arriba del composer y no pertenecen a ninguna tool.</p>
    <h4>Espaciado vertical</h4>
    {spacing_table}
  </div>

  <div class="docs-card">
    <h3>Cards de carrusel</h3>
    <p>Foundations dice que los carruseles <em>no</em> se adhieren a la grilla de EVA: el contenedor del carrusel sí, pero las cards tienen ancho fijo. En Figma (Cards / Vuelo) ese ancho es <strong>242px</strong>.</p>
    <h4>Estado actual</h4>
    {cards_table}
    <p class="docs-muted">3 × 242 + 2 × 24 = 774px &gt; compose de 6 col (~613px en 1366): las cards no llenan el compose, el carrusel scrollea.</p>
    <h4>Alternativas evaluadas <span class="docs-chip-pending">(en discusión)</span></h4>
    {alt_table}
  </div>

  <div class="docs-card docs-card--warn">
    <h3>⚠ Pendiente de definición</h3>
    <ul class="docs-list">
      <li>Confirmar el espaciado board → follow-up (hoy 16px, marcado como propuesta sin confirmar).</li>
      <li>Elegir una sola regla de cards: <strong>6 col + card = 2 col (188–193px)</strong> vs <strong>cards fijas 242px</strong>.</li>
    </ul>
    <p class="docs-muted">Estos ítems quedan marcados en esta sección como pendientes hasta que diseño los confirme.</p>
  </div>
</section>'''

    def inline_playground(self, category):
        cat_groups = self.groups_of(category)
        variants = [(g, v) for g in cat_groups for v in g.get('variants', []) if v['_snippet'] is not None]
        if not variants:
            return '<p class="docs-muted">Sin variantes disponibles.</p>'
        pg_id = f'pg-{category}'
        first_g, first_v = variants[0]
        picks = ''
        for g, v in variants:
            group = g['_group']
            vid = v['id']
            name = v.get('name', vid)
            short = name.split('·')[-1].strip() if '·' in name else name
            src = f'previews/{group}--{vid}.html'
            active = ' is-active' if (g is first_g and v is first_v) else ''
            picks += (f'<button class="docs-pg__pick{active}" '
                      f'data-group="{esc(group)}" data-id="{esc(vid)}" '
                      f'data-src="{esc(src)}" data-w="{v["width"]}" data-h="{v["height"]}" '
                      f'data-stage="{esc(v.get("stage","#d8d8d8"))}">{esc(short)}</button>')
        first_src = f'previews/{first_g["_group"]}--{first_v["id"]}.html'
        first_stage = first_v.get('stage', '#d8d8d8')
        first_w, first_h = first_v['width'], first_v['height']
        return f'''<div class="docs-pg" id="{esc(pg_id)}">
  <div class="docs-pg__bar">
    <div class="docs-pg__picks" role="group" aria-label="Seleccionar variante">{picks}</div>
    <a class="eva-3-btn-ghost -sm docs-btn docs-pg__open" href="{esc(first_src)}" target="_blank" rel="noopener"><em class="btn-text">Abrir ↗</em></a>
  </div>
  <div class="docs-pg__stage" id="{esc(pg_id)}-stage" style="background:{esc(first_stage)}">
    <iframe class="docs-pg__frame" id="{esc(pg_id)}-frame" src="{esc(first_src)}"
            width="{first_w}" height="{first_h}"
            style="width:{first_w}px;height:{first_h}px"
            title="Preview {esc(category)}"></iframe>
  </div>
  <div class="docs-pg__footer">
    <button type="button" class="eva-3-btn -sm -primary docs-btn docs-copy docs-pg__copy" data-copy-target="#{esc(pg_id)}-code"><em class="btn-text">Copiar HTML</em></button>
    <button type="button" class="eva-3-btn-ghost -sm docs-btn docs-pg__toggle" aria-expanded="false" aria-controls="{esc(pg_id)}-codewrap"><em class="btn-text">Ver código</em></button>
    <a class="eva-3-btn-ghost -sm docs-btn" href="{esc(first_src)}" target="_blank" rel="noopener"><em class="btn-text">↗ 1:1</em></a>
  </div>
  <div id="{esc(pg_id)}-codewrap" class="docs-pg__codewrap" hidden>
    <pre><code id="{esc(pg_id)}-code"></code></pre>
  </div>
</div>
<script>
(function(){{
  var pgEl = document.getElementById('{esc(pg_id)}');
  if (!pgEl) return;
  var frame = document.getElementById('{esc(pg_id)}-frame');
  var stage = document.getElementById('{esc(pg_id)}-stage');
  var codeEl = document.getElementById('{esc(pg_id)}-code');
  var openLink = pgEl.querySelector('.docs-pg__open');
  var codeWrap = document.getElementById('{esc(pg_id)}-codewrap');
  var toggleBtn = pgEl.querySelector('.docs-pg__toggle');
  function activate(btn) {{
    pgEl.querySelectorAll('.docs-pg__pick').forEach(function(b){{ b.classList.remove('is-active'); }});
    btn.classList.add('is-active');
    frame.src = btn.dataset.src;
    frame.style.width = btn.dataset.w + 'px';
    frame.style.height = btn.dataset.h + 'px';
    if (stage) stage.style.background = btn.dataset.stage;
    if (openLink) openLink.href = btn.dataset.src;
    var tmpl = document.querySelector('[data-snippet="' + btn.dataset.group + '/' + btn.dataset.id + '"]');
    if (codeEl) codeEl.textContent = tmpl ? tmpl.innerHTML.trim() : '';
  }}
  pgEl.querySelectorAll('.docs-pg__pick').forEach(function(btn) {{
    btn.addEventListener('click', function() {{ activate(btn); }});
  }});
  if (toggleBtn && codeWrap) {{
    toggleBtn.addEventListener('click', function() {{
      var open = !codeWrap.hidden;
      codeWrap.hidden = open;
      toggleBtn.setAttribute('aria-expanded', String(!open));
      toggleBtn.querySelector('.btn-text').textContent = open ? 'Ver código' : 'Ocultar código';
    }});
  }}
  var first = pgEl.querySelector('.docs-pg__pick');
  if (first) activate(first);
}})();
</script>'''

    def surface_section(self, sid, title, lead_html, category, motion=None):
        groups = ''.join(self.group_block(g) for g in self.groups_of(category))
        mot = self.motion_block(*motion) if motion else ''
        pg = f'<div class="docs-card docs-pg-card"><h3>Playground · {esc(title)}</h3>{self.inline_playground(category)}</div>'
        return f'''
<section class="docs-section" id="{sid}">
  <h2 class="docs-section__title">{esc(title)}</h2>
  <div class="docs-card docs-intro">{lead_html}</div>
  {pg}
  {groups}
  {mot}
</section>'''

    def def_lead(self, surface, extra=''):
        d = self.definition(surface)
        if not d:
            return '<p>—</p>'
        definition = d.get('definition')
        uses = ''.join(f'<li>{esc(u["text"])}</li>' for u in d.get('useCases', []))
        out = f'<h5>Definición (Figma · “{esc(d["title"])}”)</h5><p>{esc(definition) if definition else "—"}</p>'
        if d.get('definitionPlatformNote'):
            out += f'<p><strong>{esc(d["definitionPlatformNote"])}</strong></p>'
        if uses:
            out += f'<h5>Cuándo / para qué</h5><ul class="docs-list">{uses}</ul>'
        out += f'<p class="docs-meta">Plataforma: {esc(d.get("platform", "—"))}</p>'
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
        css_links = '\n'.join(f'<link rel=”stylesheet” href=”css/components/{os.path.basename(f)}”>' for f in comp_css)
        bs_lead = self.def_lead('bottomSheet')
        ss_lead = self.def_lead('sideSheet')
        modal_lead = self.def_lead('modal')
        body = ''.join([
            self.s_inicio(),
            self.surface_section('bottom-sheet', 'Bottom Sheet', bs_lead, 'bottom-sheet', ('bottomSheet', 'bottom-sheet.js')),
            self.surface_section('modal', 'Modal', modal_lead, 'modal', ('modal', 'modal.js')),
            self.surface_section('side-sheet', 'Side Sheet', ss_lead, 'side-sheet', ('sideSheet', 'side-sheet.js')),
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
</body>
</html>
'''


def build_index(groups):
    content = json.loads(read(os.path.join(ROOT, 'docs/content.json')))
    allowed = {'bottom-sheet', 'modal', 'side-sheet'}
    filtered = [g for g in groups if g.get('category') in allowed]
    site = Site(filtered, content)
    write(os.path.join(ROOT, 'index.html'), site.render())
    return sum(len(g.get('variants', [])) for g in filtered)


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
