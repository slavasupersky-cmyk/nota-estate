#!/usr/bin/env python3
"""Сборка общих частей сайта NOTA.
Запуск из корня репозитория:  python3 tools/build.py
0) выгрузка из мастер-базы ../nota-baza в data/ (tools/baza.py, только публичные поля)
1) карточки домов из data/doma.csv + tools/doma.json → doma/<slug>/index.html, doma/index.html
2) шапка и подвал из tools/partials во все страницы сайта (клиентские nota-* не трогаем)
3) контакты и реквизиты из tools/site.json
"""
import json, re, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
T = ROOT / 'tools'
site = {k: v for k, v in json.loads((T / 'site.json').read_text()).items() if not k.startswith('_')}
HEADER = (T / 'partials/header.html').read_text()
FOOTER = (T / 'partials/footer.html').read_text()
CONTACT = (T / 'partials/contact.html').read_text()

SITE_PAGES = ['index.html', 'podbor.html', 'metod.html', 'karta.html', 'razbory.html', 'razbor-hamovniki.html', 'scenarii.html',
              'reytingi.html', 'politika.html']
# старые адреса → новые (страница-переадресация, в сборку не входит)
MOVED = {'nota-index.html': 'reytingi.html', 'index-2026-09.html': 'reytingi/shkoly-moskvy/',
         'index-2026-08.html': 'razbory/klassy-novostroek/'}

def section_of(rel):
    if rel == 'index.html': return 'home'
    if rel == 'podbor.html': return 'podbor'
    if rel == 'metod.html': return 'metod'
    if rel == 'karta.html' or rel.startswith('doma/'): return 'karta'
    if rel.startswith('razbor'): return 'razbory'
    if rel.startswith('reytingi'): return 'reytingi'
    return None

def fill(tpl, rel, extra=None):
    depth = rel.count('/')
    d = dict(site, R='../' * depth)
    cur = section_of(rel)
    for k in ('home', 'podbor', 'metod', 'karta', 'razbory', 'reytingi'):
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
    s2 = re.sub(r'<section class="contact" id="kontakt">[\s\S]*?</section>', lambda m: fill(CONTACT, rel).rstrip('\n'), s2, count=1)
    # реквизиты внутри текста (политика): <!--rekv-->…<!--/rekv-->
    s2 = re.sub(r'<!--rekv-->[\s\S]*?<!--/rekv-->',
                lambda m: '<!--rekv-->ИП {ip_name}, ИНН {inn}, ОГРНИП {ogrnip}<!--/rekv-->'.format(**site), s2)
    s2 = faq_ld(s2)
    if rel == 'index.html' and HOME_TABLE:
        s2 = re.sub(r'<!--baza-t-->[\s\S]*?<!--/baza-t-->', lambda m: '<!--baza-t-->\n' + HOME_TABLE + '\n   <!--/baza-t-->', s2, count=1)
    if s2 != s:
        path.write_text(s2); return True
    return False

HOME_TABLE = ''

def _txt(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h)).replace('&nbsp;', ' ').strip()

def faq_ld(s):
    """Разметка FAQPage (<script id="ld-faq">) собирается из вопросов на странице: <div class="faq"><details><summary>…</summary><p>…</p>."""
    if 'id="ld-faq"' not in s: return s
    m = re.search(r'<div class="faq">([\s\S]*?)</div>', s)
    if not m: return s
    qa = [(_txt(q), _txt(a)) for q, a in re.findall(r'<details><summary>([\s\S]*?)</summary>([\s\S]*?)</details>', m.group(1))]
    ld = {'@context': 'https://schema.org', '@type': 'FAQPage',
          'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in qa]}
    return re.sub(r'<script type="application/ld\+json" id="ld-faq">[\s\S]*?</script>',
                  lambda _: '<script type="application/ld+json" id="ld-faq">' + json.dumps(ld, ensure_ascii=False) + '</script>', s, count=1)

def stub(old, new):
    """Страница по старому адресу: сразу уводит на новый."""
    depth = old.count('/')
    href = '../' * depth + new
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Страница переехала — NOTA</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{href}">
<meta http-equiv="refresh" content="0; url={href}">
<script>location.replace({json.dumps(href)} + location.hash)</script>
</head>
<body style="font-family:Onest,Arial,sans-serif;background:#fff;color:#101317;padding:40px">
<p>Страница переехала: <a href="{href}">{href}</a></p>
</body>
</html>
'''

if __name__ == '__main__':
    sys.path.insert(0, str(T))
    import baza, doma, karta, images, reytingi

    def all_pages():
        ps = [ROOT / p for p in SITE_PAGES if (ROOT / p).exists()]
        ps += sorted((ROOT / 'doma').glob('**/index.html'))
        ps += sorted((ROOT / 'razbory').glob('**/index.html'))
        ps += sorted((ROOT / 'reytingi').glob('**/index.html'))
        return ps

    before = {p: p.read_bytes() for p in all_pages()}
    baza.export(ROOT)
    images.build(ROOT)
    doma.build(ROOT)
    karta.build(ROOT)
    reytingi.build(ROOT)
    HOME_TABLE = doma.home_table(ROOT)
    for old, new in MOVED.items():
        (ROOT / old).write_text(stub(old, new))
    pages = all_pages()
    for p in pages:
        apply_shell(p)
    # считаем по итоговому содержимому: карточки и карта пересобираются каждый раз, но если текст тот же — это не изменение
    n = sum(1 for p in pages if before.get(p) != p.read_bytes())
    print(f'страницы: изменилось {n} из {len(pages)}')
