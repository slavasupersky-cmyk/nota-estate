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

SITE_PAGES = ['index.html', 'podbor.html', 'metod.html', 'karta.html', 'razbory.html', 'razbor-hamovniki.html', 'razbor-zamoskvorechye.html', 'razbor-ostozhenka.html', 'scenarii.html',
              'reytingi.html', 'politika.html', 'soglasie.html']
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
                lambda m: '<!--rekv-->' + site['rekv'] + '<!--/rekv-->', s2)
    if is_article(rel):
        s2 = article_lead(article_body(article_tables(s2)), rel)
    elif rel.startswith('test/'):
        # тестовые страницы (test/<slug>/): шапка, подвал и таблицы как в разборах; закрыты своей меткой robots, в карту сайта не попадают
        s2 = article_body(article_tables(s2))
    s2 = apply_numbers(s2, N)
    s2 = faq_ld(s2)
    s2 = seo(s2, rel)
    s2 = metrika(s2, rel)
    s2 = bust(s2, rel)
    if rel == 'metod.html' and ITOG_TABLE:
        s2 = re.sub(r'<!--itog-t-->[\s\S]*?<!--/itog-t-->', lambda m: '<!--itog-t-->\n' + ITOG_TABLE + '\n  <!--/itog-t-->', s2, count=1)
    if rel == APART_PAGE and APART_LIST:
        s2 = re.sub(r'<!--apart-l-->[\s\S]*?<!--/apart-l-->', lambda m: '<!--apart-l-->\n' + APART_LIST + '\n  <!--/apart-l-->', s2, count=1)
    if rel == KAMIN_PAGE and KAMIN_LIST:
        s2 = re.sub(r'<!--kamin-l-->[\s\S]*?<!--/kamin-l-->', lambda m: '<!--kamin-l-->\n' + KAMIN_LIST + '\n  <!--/kamin-l-->', s2, count=1)
    if rel == 'index.html' and KARTA_BAND:
        s2 = re.sub(r'<!--karta-band-->[\s\S]*?<!--/karta-band-->', lambda m: '<!--karta-band-->' + KARTA_BAND + '<!--/karta-band-->', s2, count=1)
    if rel == 'index.html' and HOME_RAZBORY:
        s2 = re.sub(r'<!--home-razbory-->[\s\S]*?<!--/home-razbory-->', lambda m: '<!--home-razbory-->\n' + HOME_RAZBORY + '\n  <!--/home-razbory-->', s2, count=1)
    if rel == 'index.html' and HOME_TABLE:
        s2 = re.sub(r'<!--baza-t-->[\s\S]*?<!--/baza-t-->', lambda m: '<!--baza-t-->\n' + HOME_TABLE + '\n   <!--/baza-t-->', s2, count=1)
    if s2 != s:
        path.write_text(s2); return True
    return False


# ---------------------------------------------------------------- читаемость разборов
def is_article(rel):
    """Статьи-разборы: razbory/<slug>/ и razbor-<район>.html (хаб razbory.html — не статья)."""
    return (rel.startswith('razbory/') or rel.startswith('razbor-')) and rel != 'razbory.html'

def _cell_txt(h):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h)).strip()

def article_tables(s):
    """Таблицы в разборах. Каждой ячейке — data-label с названием колонки. Таблицам из 4+ колонок или с длинным текстом
    в ячейках — класс t-cards: на телефоне строка становится карточкой (css/nota.css, раздел «разборы: читаемость»).
    Короткие таблицы (формат · площадь · вход) остаются таблицами, просто без минимальной ширины."""
    def one(m):
        t = m.group(0)
        rows = re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', t)
        if not rows: return t
        heads = [_cell_txt(x) for x in re.findall(r'<th[^>]*>([\s\S]*?)</th>', rows[0])]
        if not heads: return t
        cells = [_cell_txt(x) for r in rows[1:] for x in re.findall(r'<td[^>]*>([\s\S]*?)</td>', r)]
        avg = sum(map(len, cells)) / len(cells) if cells else 0
        cards = len(heads) >= 4 or avg > 28
        if 'data-scroll' in re.match(r'<table[^>]*>', t).group(0):
            cards = False  # таблица цифр: на телефоне листается вбок внутри .tablewrap, а не разваливается на карточки
        def row(rm):
            i = [-1]
            def td(cm):
                i[0] += 1
                attrs = re.sub(r'\s*data-label="[^"]*"', '', cm.group(1))
                lab = heads[i[0]] if i[0] < len(heads) else ''
                return f'<td{attrs} data-label="{lab}">' if lab else f'<td{attrs}>'
            return re.sub(r'<td([^>]*)>', td, rm.group(0))
        t = re.sub(r'<tr[^>]*>[\s\S]*?</tr>', row, t)
        open_tag = re.match(r'<table[^>]*>', t).group(0)
        tag = re.sub(r'\s*class="t-cards"', '', open_tag)
        tag = re.sub(r'(class="[^"]*?)\s*\bt-cards\b', r'\1', tag)  # t-cards внутри своего class="…"
        if cards:
            if 'class="' in tag: tag = tag.replace('class="', 'class="t-cards ', 1)  # у таблицы свой класс — дописываем, а не второй атрибут
            else: tag = tag.replace('<table', '<table class="t-cards"', 1)
        tag = re.sub(r'class="([^"]*)"', lambda m: 'class="' + ' '.join(m.group(1).split()) + '"', tag)  # без лишних пробелов: они копились от сборки к сборке
        tag = tag.replace(' class=""', '')
        return tag + t[len(open_tag):]
    return re.sub(r'<table[^>]*>[\s\S]*?</table>', one, s)


def article_lead(s, rel):
    """Окно консультации в разборе: если на странице есть кнопка [data-lead], сборка кладёт окно #lead перед </main>
    (между <!--lead-m--> и <!--/lead-m-->, пересобирается каждый раз). Кнопка: <button class="btn" type="button" data-lead="Тема заявки">."""
    s = re.sub(r'\n?<!--lead-m-->[\s\S]*?<!--/lead-m-->', '', s)
    if 'data-lead=' not in s or 'id="lead"' in s: return s
    import reytingi
    title = re.search(r'<h1>([\s\S]*?)</h1>', s)
    m = reytingi.lead_modal('Разбор «' + (_cell_txt(title.group(1)) if title else rel) + '»', ttl='Консультация',
                            text='Расскажите, какой дом у вас или какой смотрите. Сверим его с новыми домами рядом: метр, число объявлений, срок экспозиции — и ответим, обычно в тот же день.',
                            btn='Записаться на консультацию', note_ph='Адрес или название дома, что хотите понять')
    m = m.replace('../../', '../' * rel.count('/'))
    return s.replace('</main>', '<!--lead-m-->' + m + '<!--/lead-m-->\n</main>', 1)

def article_body(s):
    return re.sub(r'<body class="inner(?: article)?"', '<body class="inner article"', s, count=1)

HOME_TABLE = ''
KARTA_BAND = ''
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
    kartochki — карточек домов; ryn_prim, ryn_oba, ryn_vtor, ryn_anons — кто продаёт (только застройщик, застройщик и собственники, только собственники, анонс); apart — домов с апартаментами (проверка 08); shkoly, shkoly_mark, shkoly_zam, pent, pent_base, pent_min, pent_max — из рейтингов (tools/reytingi.py)."""
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
    n['kamin'] = len({r['slug'] for r in rd(root / 'data/kaminy.csv')})
    # {ryn_prim}, {ryn_oba}, {ryn_vtor}, {ryn_anons} — кто продаёт (поле rynok): только застройщик / застройщик и собственники / только собственники / анонс
    ryn = Counter(r.get('rynok', '') for r in rows)
    n.update(ryn_prim=ryn['первичка'], ryn_oba=ryn['первичка и вторичка'], ryn_vtor=ryn['только вторичка'], ryn_anons=ryn['анонс'])
    n['apart'] = len({r['slug'] for r in rd(root / 'data/proverki.csv')
                      if r['check'] == '08' and 'апартамент' in (r['value'] or '').lower()})
    # {srez} — дата среза базы (когда data/doma.csv последний раз менялся)
    import datetime
    dp = root / 'data/doma.csv'
    n['srez'] = datetime.date.fromtimestamp(dp.stat().st_mtime).strftime('%d.%m.%Y') if dp.exists() else '—'
    # {dopusk} — допуск минусов для отметки словами, из data/itog.csv: «до одного в бизнесе и премиуме, ни одного в элите и делюксе»
    prep = {'бизнес': 'бизнесе', 'премиум': 'премиуме', 'элитный': 'элите', 'делюкс': 'делюксе'}
    word = {1: 'одного', 2: 'двух', 3: 'трёх', 4: 'четырёх'}
    groups = {}
    for t in rd(root / 'data/itog.csv'):
        groups.setdefault(int(t['otmetka_max_minus']), []).append(prep.get(t['class'], t['class']))
    parts = []
    for o, cl in sorted(groups.items(), key=lambda x: -x[0]):
        where = ', '.join(cl[:-1]) + ' и ' + cl[-1] if len(cl) > 1 else cl[0]
        parts.append(f'ни одного в {where}' if o == 0 else f'до {word.get(o, o)} в {where}')
    n['dopusk'] = ', '.join(parts) or '—'
    n.update(extra or {})
    return n

APART_PAGE = 'razbory/apartamenty-ili-kvartira/index.html'

def apart_list(root):
    """Дома с апартаментами по классам для разбора «Апартаменты или квартира» (между <!--apart-l--> и <!--/apart-l-->):
    проверка 08 в data/proverki.csv, в значении — «апартаменты». Ссылки ведут на дом на карте."""
    rd = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []
    ap = {r['slug'] for r in rd(root / 'data/proverki.csv') if r['check'] == '08' and 'апартамент' in (r['value'] or '').lower()}
    rows = [r for r in rd(root / 'data/doma.csv') if r['slug'] in ap]
    if not rows: return ''
    esc = lambda x: x.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
    out = []
    for c, title in (('бизнес', 'Бизнес'), ('премиум', 'Премиум'), ('элитный', 'Элит'), ('делюкс', 'Делюкс')):
        cr = sorted((r for r in rows if r['class'] == c), key=lambda r: (r.get('name_short') or r['name']).lower())
        if not cr: continue
        chips = ''.join(f'<a class="chip" href="../../karta.html#h-{r["slug"]}">{esc(r.get("name_short") or r["name"])}</a>' for r in cr)
        out.append(f'  <p class="ttl" style="margin:22px 0 12px">{title} · {len(cr)}</p>\n  <div class="chips">{chips}</div>')
    return '\n'.join(out)

APART_LIST = ''

KAMIN_PAGE = 'razbory/kamin-v-kvartire/index.html'

def kamin_list(root):
    """Дома с камином по проекту для разбора «Живой огонь в городе» (между <!--kamin-l--> и <!--/kamin-l-->):
    data/kaminy.csv + data/doma.csv. Список по общему образцу домов (reytingi.house_ri): строка раскрывается —
    какой камин и где он в доме, фото, «Дом на карте», «Паспорт дома», «Получить предложение» окном на странице."""
    import reytingi
    rd = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []
    doma = {r['slug']: r for r in rd(root / 'data/doma.csv')}
    rows = [k for k in rd(root / 'data/kaminy.csv') if k['slug'] in doma]
    if not rows: return ''
    esc = lambda x: (x or '').replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
    order = {'делюкс': 0, 'элитный': 1, 'премиум': 2, 'бизнес': 3}
    rows.sort(key=lambda k: (order.get(doma[k['slug']]['class'], 9), (doma[k['slug']].get('name_short') or doma[k['slug']]['name']).lower()))
    R = '../../'
    items = []
    for n, k in enumerate(rows, 1):
        h = doma[k['slug']]
        pf = (h.get('price_from_m2') or '').replace(' ', '')
        price = f'от {int(float(pf) / 1000):,} тыс ₽ за м²'.replace(',', ' ') if pf.replace('.', '').isdigit() else 'по запросу'
        src = k.get('source', '')
        host = re.sub(r'^https?://(www\.)?', '', src).split('/')[0] if src.startswith('http') else ''
        dl = [('Камин', esc(k['tip'])), ('Где в доме', esc(k['gde'])), ('Подробности', esc(k.get('detali', ''))),
              ('Адрес', esc(h['address'])), ('Цена', price),
              ('Источник', (f'<a href="{esc(src)}" rel="nofollow noopener">{esc(host)}</a>' + (f' · {esc(k["checked"])}' if k.get('checked') else '')) if host else '')]
        name = h['name'].split(' (')[0]
        items.append(reytingi.house_ri(root, R, h, n, esc(k['tip']), 'камин', dl, f'{name} · камин'))
    import karta
    ck = {'бизнес': 'biz', 'премиум': 'prem', 'элитный': 'elit', 'делюкс': 'dlx'}
    pts = [(doma[k['slug']]['lat'], doma[k['slug']]['lon'], ck.get(doma[k['slug']]['class'], 'biz'), f'#d-{k["slug"]}', n,
            doma[k['slug']]['name'].split(' (')[0]) for n, k in enumerate(rows, 1) if doma[k['slug']].get('lat') and doma[k['slug']].get('lon')]
    mm = karta.mini_map(pts, 'Дома с камином по проекту на карте Москвы')
    return (mm + '\n  <div class="ri-list" data-rlist data-lim="50">\n' + '\n'.join(items) + '\n  </div>'
            + reytingi.lead_modal('Разбор «Живой огонь в городе»'))

KAMIN_LIST = ''

def itog_table(root):
    """Таблица допуска минусов по классам для metod.html (между <!--itog-t--> и <!--/itog-t-->): data/itog.csv + итоги по базе."""
    rd = lambda p: list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []
    tol, rows = rd(root / 'data/itog.csv'), rd(root / 'data/doma.csv')
    if not tol: return ''
    gen = lambda k: 'минуса' if k % 10 == 1 and k % 100 != 11 else 'минусов'
    name = {'бизнес': 'Бизнес', 'премиум': 'Премиум', 'элитный': 'Элит', 'делюкс': 'Делюкс'}
    out = ['  <div class="tablewrap"><table class="cls-t it-t">',
           '   <tr><th>Класс</th><th><span class="tag mark">Отметка NOTA</span></th><th><span class="tag look">Присмотреться</span></th><th><span class="tag no">Без отметки</span></th><th>Сейчас в базе</th></tr>']
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

HOME_RAZBORY = ''
MES_I = {m: i for i, m in enumerate(['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'], 1)}

def home_razbory(root, n=3):
    """Три самых свежих разбора на главной (между <!--home-razbory--> и <!--/home-razbory-->).
    Берёт карточки из razbory.html (решения и районы; карточки домов — нет), дата — самая поздняя «Д месяц» в строке над заголовком
    («10 сентября · обновлено 23 сентября» → 23 сентября). Без даты карточка на главную не попадает.
    Новый разбор достаточно добавить в razbory.html — главная обновится при сборке."""
    import datetime
    s = (root / 'razbory.html').read_text()
    today = datetime.date.today()
    cards = []
    for i, m in enumerate(re.finditer(r'<a class="art" href="((?:razbory/|razbor-)[^"]*)">([\s\S]*?)</a>', s)):
        href, body = m.groups()
        img = re.search(r'<img [^>]*>', body)
        k = re.search(r'<div class="k">([\s\S]*?)</div>', body)
        h3 = re.search(r'<h3>([\s\S]*?)</h3>', body)
        txt = re.search(r'<p>([\s\S]*?)</p>', body)
        if not (img and k and h3 and txt): continue
        dates = []
        for d, mon in re.findall(r'(\d{1,2}) (' + '|'.join(MES_I) + r')', k.group(1)):
            y = today.year - (1 if MES_I[mon] > today.month + 1 else 0)
            dates.append((datetime.date(y, MES_I[mon], int(d)), f'{d} {mon}'))
        if not dates: continue
        dt, label = max(dates)
        kind = 'Район' if 0 <= s.find('id="rayony"') < m.start() else 'Разбор'  # раздел «Разбор района» в razbory.html
        cards.append((dt, -i, href, img.group(0), f'{kind} · сверка {label}', h3.group(1), txt.group(1)))
    cards.sort(reverse=True)
    out = []
    for dt, _, href, img, k, h3, txt in cards[:n]:
        out.append(f'   <a class="art" href="{href}">\n    <div class="ph has" data-ar="16x9">{img}</div>\n'
                   f'    <div class="k">{k}</div><h3>{h3}</h3>\n    <p>{txt}</p>\n   </a>')
    return '\n'.join(out)

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

# ---- адрес сайта для поисковиков (постоянный домен — site_url в site.json) ----
SITE_URL = site.get('site_url', '').rstrip('/')
NOINDEX_SITEMAP = {'scenarii.html'}   # не в карте сайта и закрыты на хостинге (deploy/.htaccess)
PREVIEW = '<meta name="robots" content="noindex" data-preview>'

def page_url(rel):
    if rel == 'index.html': return SITE_URL + '/'
    if rel.endswith('/index.html'): return SITE_URL + '/' + rel[:-len('index.html')]
    return SITE_URL + '/' + rel

# ---- версия статики: css/js и фото команды отдаёт nginx хостинга без правил кэша из .htaccess,
# поэтому к адресу дописываем ?v=<хеш содержимого> — браузер сам возьмёт новый файл после правки ----
import hashlib
_VER = {}
def ver(rel):
    if rel not in _VER:
        f = ROOT / rel
        _VER[rel] = hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.exists() else ''
    return _VER[rel]

# ---- Яндекс Метрика: номер счётчика — metrika_id в site.json; код в <head>, noscript — сразу после <body> ----
MK_A, MK_B = '<!-- Yandex.Metrika counter -->', '<!-- /Yandex.Metrika counter -->'
def metrika(s, rel):
    s = re.sub(r'\n?<!-- Yandex\.Metrika counter -->[\s\S]*?<!-- /Yandex\.Metrika counter -->', '', s)
    s = re.sub(r'\n?<!-- Yandex\.Metrika noscript -->[\s\S]*?<!-- /Yandex\.Metrika noscript -->', '', s)
    mid = str(site.get('metrika_id', '')).strip()
    if not mid or rel.startswith('test/') or 'http-equiv="refresh"' in s:
        return s
    js = (MK_A + '\n<script type="text/javascript">\n'
          '    (function(m,e,t,r,i,k,a){\n'
          '        m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};\n'
          '        m[i].l=1*new Date();\n'
          '        for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}\n'
          '        k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)\n'
          "    })(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=" + mid + "', 'ym');\n\n"
          "    ym(" + mid + ", 'init', {ssr:true, webvisor:true, clickmap:true, ecommerce:\"dataLayer\", referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true});\n"
          '</script>\n' + MK_B)
    ns = ('<!-- Yandex.Metrika noscript --><noscript><div><img src="https://mc.yandex.ru/watch/' + mid +
          '" style="position:absolute; left:-9999px;" alt="" /></div></noscript><!-- /Yandex.Metrika noscript -->')
    s = s.replace('</head>', js + '\n</head>', 1)
    s = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + '\n' + ns, s, count=1)
    return s

def bust(s, rel=''):
    def rep(m):
        v = ver(m.group(2))
        return m.group(1) + m.group(2) + ('?v=' + v if v else '') + '"'
    # свои стили и скрипты страницы рядом с ней (razbory/planirovki/planirovki.css) — тоже с версией
    d = rel.rsplit('/', 1)[0] + '/' if '/' in rel else ''
    def loc(m):
        v = ver(d + m.group(2))
        return m.group(1) + m.group(2) + ('?v=' + v if v else '') + '"'
    if d: s = re.sub(r'((?:src|href)=")([\w-]+\.(?:css|js))(?:\?v=[0-9a-f]*)?"', loc, s)
    return re.sub(r'((?:src|href)="(?:\.\./)*)((?:css/[\w-]+\.css|js/[\w-]+\.js|img/team/[\w-]+\.jpg))(?:\?v=[0-9a-f]*)?"', rep, s)

def seo(s, rel):
    """Канонический адрес, og:url и полные адреса картинок превью — на постоянный домен.
    Метка data-preview закрывает копию на GitHub Pages; deploy/deploy.sh вырезает её при выкладке на хостинг."""
    if not SITE_URL: return s
    from urllib.parse import urljoin
    url = page_url(rel)
    s = re.sub(r'\s*<link rel="canonical"[^>]*>', '', s)
    s = re.sub(r'\s*<meta property="og:url"[^>]*>', '', s)
    s = re.sub(r'\s*<meta name="(?:yandex|google-site)-verification"[^>]*>', '', s)
    s = s.replace('\n' + PREVIEW, '').replace(PREVIEW, '')
    def absimg(m):
        v = m.group(2)
        return m.group(1) + (v if v.startswith('http') else urljoin(url, v)) + '"'
    s = re.sub(r'(<meta (?:property="og:image"|name="twitter:image") content=")([^"]*)"', absimg, s)
    if 'property="og:image"' not in s:
        img = 'img/01-hero-maket-og.jpg'
        m = re.match(r'doma/([^/]+)/index\.html$', rel)
        if m and (ROOT / 'img/doma' / (m.group(1) + '.jpg')).exists():
            img = 'img/doma/' + m.group(1) + '.jpg'
        s = s.replace('</head>', f'<meta property="og:image" content="{SITE_URL}/{img}">\n</head>', 1)
    # адреса внутри JSON-LD — полные
    s = re.sub(r'("(?:url|image)":\s*")(?!https?:)([^"]*)"', lambda m: m.group(1) + urljoin(SITE_URL + '/', m.group(2)) + '"', s)
    add = [f'<link rel="canonical" href="{url}">', f'<meta property="og:url" content="{url}">']
    if 'name="robots"' not in s:
        add.append(PREVIEW)
    if rel == 'index.html':
        if site.get('yandex_verification'): add.append(f'<meta name="yandex-verification" content="{site["yandex_verification"]}">')
        if site.get('google_verification'): add.append(f'<meta name="google-site-verification" content="{site["google_verification"]}">')
    return s.replace('</head>', '\n'.join(add) + '\n</head>', 1)

def sitemap(pages):
    """sitemap.xml и robots.txt в корне. Дата — последнее изменение файла страницы."""
    import datetime
    rows = []
    for p in pages:
        rel = p.relative_to(ROOT).as_posix()
        if rel in NOINDEX_SITEMAP or 'name="robots"' in re.sub(re.escape(PREVIEW), '', p.read_text()): continue
        d = datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()
        rows.append(f' <url><loc>{page_url(rel)}</loc><lastmod>{d}</lastmod></url>')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(rows) + '\n</urlset>\n'
    robots = f'User-agent: *\nDisallow:\n\nSitemap: {SITE_URL}/sitemap.xml\n'
    for name, body in (('sitemap.xml', xml), ('robots.txt', robots)):
        f = ROOT / name
        if not f.exists() or f.read_text() != body: f.write_text(body)
    return len(rows)

if __name__ == '__main__':
    sys.path.insert(0, str(T))
    import baza, doma, karta, images, reytingi

    def all_pages():
        ps = [ROOT / p for p in SITE_PAGES if (ROOT / p).exists()]
        ps += sorted((ROOT / 'doma').glob('**/index.html'))
        ps += sorted((ROOT / 'razbory').glob('**/*.html'))  # и вторые страницы разбора: razbory/planirovki/podbor.html
        ps += sorted((ROOT / 'reytingi').glob('**/index.html'))
        ps += sorted((ROOT / 'test').glob('**/*.html'))
        return ps

    before = {p: p.read_bytes() for p in all_pages()}
    baza.export(ROOT)
    images.build(ROOT)
    doma.build(ROOT)
    karta.build(ROOT)
    rstats = reytingi.build(ROOT) or {}
    HOME_TABLE = doma.home_table(ROOT)
    KARTA_BAND = karta.BAND
    N = numbers(ROOT, rstats)
    ITOG_TABLE = itog_table(ROOT)
    APART_LIST = apart_list(ROOT)
    KAMIN_LIST = kamin_list(ROOT)
    HOME_RAZBORY = home_razbory(ROOT)
    for old, new in MOVED.items():
        (ROOT / old).write_text(stub(old, new))
    pages = all_pages()
    for p in pages:
        apply_shell(p)
    # считаем по итоговому содержимому: карточки и карта пересобираются каждый раз, но если текст тот же — это не изменение
    n = sum(1 for p in pages if before.get(p) != p.read_bytes())
    print(f'страницы: изменилось {n} из {len(pages)}')
    print(f'карта сайта: {sitemap(pages)} страниц · {SITE_URL}')
