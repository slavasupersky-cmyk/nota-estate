#!/usr/bin/env python3
"""Сборка общих частей сайта NOTA.
Запуск из корня репозитория:  python3 tools/build.py
0) выгрузка из мастер-базы ../nota-baza в data/ (tools/baza.py, только публичные поля)
1) карточки домов из data/doma.csv + tools/doma.json → doma/<slug>/index.html, doma/index.html
2) шапка и подвал из tools/partials во все страницы сайта (клиентские nota-* не трогаем)
3) контакты и реквизиты из tools/site.json
4) живые цифры: <!--n:шаблон-->…<!--/n--> в тексте и data-n="шаблон" у <meta> пересчитываются из data/ при каждой сборке
   Шаблон: {doma} → 373; {doma:дом|дома|домов} → слово в форме для этого числа. Ключи — в numbers() ниже.
"""
import csv, json, re, pathlib, statistics, sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
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
    s2 = apply_numbers(s2, N)
    s2 = faq_ld(s2)
    if rel == 'metod.html' and ITOG_TABLE:
        s2 = re.sub(r'<!--itog-t-->[\s\S]*?<!--/itog-t-->', lambda m: '<!--itog-t-->\n' + ITOG_TABLE + '\n  <!--/itog-t-->', s2, count=1)
    if rel == 'index.html' and HOME_TABLE:
        s2 = re.sub(r'<!--baza-t-->[\s\S]*?<!--/baza-t-->', lambda m: '<!--baza-t-->\n' + HOME_TABLE + '\n   <!--/baza-t-->', s2, count=1)
    if s2 != s:
        path.write_text(s2); return True
    return False

HOME_TABLE = ''
N = {}

# ---------------------------------------------------------------- живые цифры
def _num(x):
    try: return float(str(x).replace(' ', '').replace(',', '.'))
    except ValueError: return None

def _plural(n, one, few, many):
    n = abs(int(n)); m10, m100 = n % 10, n % 100
    return one if m10 == 1 and m100 != 11 else few if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else many

def _m2(v):
    """Цена метра словами: 441 350 → «441 тыс», 1 025 000 → «1,03 млн» (половина — вверх)."""
    d = Decimal(str(v))
    if d >= 1000000:
        m = str((d / 1000000).quantize(Decimal('0.01'), ROUND_HALF_UP)).rstrip('0').rstrip('.')
        return m.replace('.', ',') + ' млн'
    return str((d / 1000).quantize(Decimal('1'), ROUND_HALF_UP)) + ' тыс'

def numbers(root, extra=None):
    """Цифры, которые меняются вместе с базой. Ключи для шаблонов:
    doma — домов на сайте; biz, prem, elit, dlx — по классам; spor — домов, которым источники дают разные классы;
    med_biz…med_dlx — медиана цены «от» за м² по классу (город, без Рублёвки и Сколкова); v_prodazhe — домов с предложением по комнатности;
    kartochki — карточек домов; shkoly, shkoly_mark, shkoly_zam, pent, pent_base, pent_min, pent_max — из рейтингов (tools/reytingi.py)."""
    rd = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []
    rows = rd(root / 'data/doma.csv')
    cls = Counter(r['class'] for r in rows)
    city = [r for r in rows if r['okrug'] not in ('Рублёвка', 'Сколково')]
    n = {'doma': len(rows), 'biz': cls['бизнес'], 'prem': cls['премиум'], 'elit': cls['элитный'], 'dlx': cls['делюкс'],
         'spor': sum(1 for r in rows if r['class_disputed'] == 'да'),
         'v_prodazhe': len({r['slug'] for r in rd(root / 'data/loty-po-tipam.csv')}),
         'kartochki': len(list((root / 'doma').glob('*/index.html')))}
    malo = [r for r in rows if (r.get('pasport_why') or '').startswith('мало данных')]
    n.update(otm=sum(1 for r in rows if r['pasport'] == 'Отметка'), bez=sum(1 for r in rows if r['pasport'] == 'Без отметки'),
             prism=sum(1 for r in rows if r['pasport'] == 'Присмотреться') - len(malo), malo=len(malo))
    for k, c in (('biz', 'бизнес'), ('prem', 'премиум'), ('elit', 'элитный'), ('dlx', 'делюкс')):
        v = [_num(r['price_from_m2']) for r in city if r['class'] == c and _num(r['price_from_m2'])]
        n['med_' + k] = _m2(statistics.median(v)) if v else '—'
    n.update(extra or {})
    return n

def itog_table(root):
    """Таблица допуска минусов по классам для metod.html (между <!--itog-t--> и <!--/itog-t-->): data/itog.csv + итоги по базе."""
    rd = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []
    tol, rows = rd(root / 'data/itog.csv'), rd(root / 'data/doma.csv')
    if not tol: return ''
    gen = lambda k: 'минуса' if k % 10 == 1 and k % 100 != 11 else 'минусов'
    name = {'бизнес': 'Бизнес', 'премиум': 'Премиум', 'элитный': 'Элит', 'делюкс': 'Делюкс'}
    out = ['  <div class="tablewrap"><table class="cls-t it-t">',
           '   <tr><th>Класс</th><th><span class="tag mark">Отметка</span></th><th><span class="tag look">Присмотреться</span></th><th><span class="tag no">Без отметки</span></th><th>Сейчас в базе</th></tr>']
    for t in tol:
        o, b = int(t['otmetka_max_minus']), int(t['bez_otmetki_from_minus'])
        otm = 'без минусов' if o == 0 else f'до {o} {gen(o)}'
        mid = list(range(o + 1, b))
        look = (f'{mid[0]} {_plural(mid[0], "минус", "минуса", "минусов")}' if len(mid) == 1 else
                f'{mid[0]}–{mid[-1]} {_plural(mid[-1], "минус", "минуса", "минусов")}' if mid else '—')
        cr = [r for r in rows if r['class'] == t['class']]
        cnt = [sum(1 for r in cr if r['pasport'] == v and not (r.get('pasport_why') or '').startswith('мало данных')) for v in ('Отметка', 'Присмотреться', 'Без отметки')]
        out.append(f'   <tr><td><b>{name.get(t["class"], t["class"])}</b></td><td>{otm}</td><td>{look}</td><td>с {b} {gen(b)}</td>'
                   f'<td>{cnt[0]} · {cnt[1]} · {cnt[2]}</td></tr>')
    out.append('  </table></div>')
    return '\n'.join(out)

ITOG_TABLE = ''

def render_n(tpl, nums):
    def rep(m):
        key, _, forms = m.group(1).partition(':')
        if key not in nums: return m.group(0)
        v = nums[key]
        if forms:
            f = forms.split('|')
            return _plural(v, *f) if len(f) == 3 and isinstance(v, (int, float)) else m.group(0)
        return f'{v:,}'.replace(',', '\u00a0') if isinstance(v, int) else str(v)
    return re.sub(r'\{(\w+(?::[^{}]*)?)\}', rep, tpl)

def apply_numbers(s, nums):
    if not nums: return s
    s = re.sub(r'<!--n:([\s\S]*?)-->[\s\S]*?<!--/n-->', lambda m: f'<!--n:{m.group(1)}-->{render_n(m.group(1), nums)}<!--/n-->', s)
    def attr(m):
        tag = m.group(0)
        tpl = re.search(r'data-n="([^"]*)"', tag).group(1).replace('&quot;', '"').replace('&amp;', '&')
        val = render_n(tpl, nums).replace('&', '&amp;').replace('"', '&quot;')
        return re.sub(r'content="[^"]*"', lambda _: f'content="{val}"', tag, count=1)
    return re.sub(r'<meta [^>]*data-n="[^"]*"[^>]*>', attr, s)

def _txt(h):
    h = re.sub(r'<!--[\s\S]*?-->', '', h)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h)).replace('&nbsp;', ' ').replace('\u00a0', ' ').strip()

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
    rstats = reytingi.build(ROOT) or {}
    HOME_TABLE = doma.home_table(ROOT)
    N = numbers(ROOT, rstats)
    ITOG_TABLE = itog_table(ROOT)
    for old, new in MOVED.items():
        (ROOT / old).write_text(stub(old, new))
    pages = all_pages()
    for p in pages:
        apply_shell(p)
    # считаем по итоговому содержимому: карточки и карта пересобираются каждый раз, но если текст тот же — это не изменение
    n = sum(1 for p in pages if before.get(p) != p.read_bytes())
    print(f'страницы: изменилось {n} из {len(pages)}')
