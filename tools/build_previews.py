#!/usr/bin/env python3
"""Genera previews/<group>--<id>.html para cada variante declarada en components/*/manifest.json.
Uso: python3 tools/build_previews.py [--only <group>]  (solo previews; copia congelada para QA visual)
Cada preview es una página standalone con EVA CSS (CDN) + tokens + CSS de componentes + el snippet.
"""
import json, glob, os, html, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
def main():
    comp_css = sorted(glob.glob(os.path.join(ROOT, 'css/components/*.css')))
    css_links = "\n".join(f'<link rel="stylesheet" href="../css/components/{os.path.basename(c)}">' for c in comp_css)
    os.makedirs(os.path.join(ROOT, 'previews'), exist_ok=True)
    count = 0; errors = []
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    for mf in sorted(glob.glob(os.path.join(ROOT, 'components/*/manifest.json'))):
        gdir = os.path.dirname(mf); group = os.path.basename(gdir)
        if group.startswith('_') or (only and group != only):
            continue
        try:
            m = json.load(open(mf))
        except Exception as e:
            errors.append(f'{mf}: JSON inválido: {e}'); continue
        for v in m.get('variants', []):
            sp = os.path.join(gdir, v['file'])
            if not os.path.exists(sp):
                errors.append(f'{group}/{v["id"]}: falta {v["file"]}'); continue
            snippet = open(sp).read()
            scripts = "\n".join(f'<script type="module" src="../{s}"></script>' for s in v.get('scripts', []))
            out = HEAD.format(title=html.escape(v.get('name', v['id'])), css=css_links,
                              stage=v.get('stage', '#ffffff'), w=v['width'], h=v['height'],
                              group=group, vid=v['id'], snippet=snippet, scripts=scripts)
            open(os.path.join(ROOT, 'previews', f'{group}--{v["id"]}.html'), 'w').write(out)
            count += 1
    print(f'{count} previews generadas')
    for e in errors: print('ERROR', e)
    sys.exit(1 if errors else 0)
if __name__ == '__main__':
    main()
