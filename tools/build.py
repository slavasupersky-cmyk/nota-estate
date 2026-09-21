#!/usr/bin/env python3
"""Сборка общих частей сайта NOTA.
Запуск из корня репозитория:  python3 tools/build.py
1) карточки домов из data/zhk-moskva-biznes-plus-geo.csv + tools/doma.json → doma/<slug>/index.html, doma/index.html
2) шапка и подвал из tools/partials во все страницы сайта (клиентские nota-* не трогаем)
3) контакты и реквизиты из tools/site.json
"""
import json, re, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
T = ROOT / 'tools'
site = {k: v for k, v in json.loads((T / 'site.json').read_text()).items() if not k.startswith('_')}
HEADER = (T / 'partials/header.html').read_text()
FOOTER = (T / 'partials/footer.html').read_text()

SITE_PAGES = ['index.html', 'podbor.html', 'metod.html', 'karta.html', 'razbory.html', 'razbor-hamovniki.html',
              'nota-index.html', 'index-2026-08.html', 'index-2026-09.html', 'politika.html']

def section_of(rel):
    if rel == 'podbor.html': return 'podbor'
    if rel == 'metod.html': return 'metod'
    if rel == 'karta.html' or rel.startswith('doma/'): return 'karta'
    if rel.startswith('razbor'): return 'razbory'
    if rel == 'nota-index.html' or re.match(r'index-\d', rel): return 'index'
    return None

def fill(tpl, rel, extra=None):
    depth = rel.count('/')
    d = dict(site, R='../' * depth)
    cur = section_of(rel)
    for k in ('podbor', 'metod', 'karta', 'razbory', 'index'):
        d['CUR_' + k] = ' class="cur"' if k == cur else ''
    d.update(extra or {})
    return re.sub(r'\{(\w+)\}', lambda m: d.get(m.group(1), m.group(0)), tpl)

def apply_shell(path):
    rel = path.relative_to(ROOT).as_posix()
    s = path.read_text()
    fm = re.search(r'<footer([^>]*)>', s)
    foot_attr = fm.group(1) if fm else ''
    s2 = re.sub(r'<header class="top[\s\S]*?</header>', lambda m: fill(HEADER, rel).rstrip('\n'), s, count=1)
    s2 = re.sub(r'<footer[^>]*>[\s\S]*?</footer>', lambda m: fill(FOOTER, rel, {'FOOT_ATTR': foot_attr}).rstrip('\n'), s2, count=1)
    # реквизиты внутри текста (политика): <!--rekv-->…<!--/rekv-->
    s2 = re.sub(r'<!--rekv-->[\s\S]*?<!--/rekv-->',
                lambda m: '<!--rekv-->ИП {ip_name}, ИНН {inn}, ОГРНИП {ogrnip}<!--/rekv-->'.format(**site), s2)
    if s2 != s:
        path.write_text(s2); return True
    return False

if __name__ == '__main__':
    sys.path.insert(0, str(T))
    import doma
    doma.build(ROOT)
    pages = [ROOT / p for p in SITE_PAGES if (ROOT / p).exists()]
    pages += sorted((ROOT / 'doma').glob('**/index.html'))
    n = sum(apply_shell(p) for p in pages)
    print(f'шапка/подвал: обновлено {n} из {len(pages)} страниц')
