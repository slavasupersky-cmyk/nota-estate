"""Карточки домов: data/doma.csv (выгрузка из nota-baza, см. tools/baza.py) + tools/doma.json → doma/<slug>/index.html"""
import csv, json, html, re, pathlib

DATE = '21 сентября 2026'
OLD_MOSCOW = {'ЦАО','САО','СВАО','ВАО','ЮВАО','ЮАО','ЮЗАО','ЗАО','СЗАО'}
PARK_NORM = {'бизнес': 0.8, 'премиум': 1.5, 'элитный': 2.0, 'делюкс': 2.0}
UNITS_NORM = {'бизнес': (837, 'типичный дом класса — 837 квартир'), 'премиум': (665, 'типичный дом класса — 665 квартир'),
              'элитный': (100, 'норма класса — до 100 квартир'), 'делюкс': (30, 'норма класса — до 30 квартир')}
CLASS_RU = {'бизнес': 'Бизнес', 'премиум': 'Премиум', 'элитный': 'Элит', 'делюкс': 'Делюкс'}
ADDR_RULE = {'бизнес': 'в старых границах Москвы', 'премиум': 'внутри Третьего кольца', 'элитный': 'в ЦАО', 'делюкс': 'в ЦАО'}
e = html.escape

def num(x):
    try: return float(str(x).replace(' ', '').replace(',', '.'))
    except ValueError: return None

def fmt(n, d=0):
    s = f'{n:,.{d}f}'.replace(',', ' ').replace('.', ',')
    return s

def plural(n, one, few, many):
    n = abs(int(n)); m10, m100 = n % 10, n % 100
    return one if m10 == 1 and m100 != 11 else few if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else many

def schools_html(r, R):
    """Блок «Школы рядом»: минуты пешком по улицам из маршрутов базы. Пусто, если маршрутов нет (Рублёвка)."""
    if not r.get('school_min'):
        return ''
    bits = [f'Ближайшая школа — {e(r["school_name"])}, {r["school_min"]} мин пешком.']
    if r.get('nota_school_min') and r['nota_school_name'] != r['school_name']:
        bits.append(f'Ближайшая из нашей базы школ — {e(r["nota_school_name"])}, {r["nota_school_min"]} мин.')
    n15 = int(r['nota_15'] or 0)
    if n15:
        bits.append(f'В 15 минутах — {n15} {plural(n15, "школа", "школы", "школ")} из базы.')
    if r.get('marked_min'):
        bits.append(f'С отметкой NOTA — {e(r["marked_name"])}, {r["marked_min"]} мин.')
    else:
        bits.append('Школ с отметкой NOTA в получасе пешком нет.')
    approx = '' if r.get('geo_precision') == 'адрес' else ' Координаты дома примерные, минуты — плюс-минус пять.'
    return f'''<section class="tight"><div class="wrap two">
 <div><p class="ttl">Школы рядом</p></div>
 <div><p class="lede">{' '.join(bits)}</p>
 <p class="hint">Пешком по улицам и дворам, 4,5 км/ч, до ближайшего корпуса школы.{approx} Все школы вокруг дома — на карте <a href="{R}shkoly-marshruty.html">«До школы пешком»</a>.</p></div>
</div></section>
'''

def district_label(d):
    return d if re.search(r'[.,~]|д\.|шоссе', d) else f'{d} район'

def load(root):
    p = root / 'data/doma.csv'
    rows = list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';'))
    for r in rows:
        r['class_final'] = r['class']
    return rows

def evaluate(r, cfg):
    cls = r['class_final']
    if cls == 'премиум': a = 'да' if cfg.get('in_ttk') else ('нет' if cfg.get('in_ttk') is False else 'нет данных')
    elif cls == 'бизнес': a = 'да' if r['okrug'] in OLD_MOSCOW else 'нет'
    else: a = 'да' if r['okrug'] == 'ЦАО' else 'нет'
    u, pk = num(r['units_total']), num(r['parking'])
    ratio = pk / u if u and pk else None
    p = 'нет данных' if ratio is None else ('да' if ratio >= PARK_NORM[cls] else 'нет')
    q = 'нет данных' if u is None else ('да' if u <= UNITS_NORM[cls][0] else 'нет')
    ans = [a, p, q]
    # ответы из базы (proverki: 01 адрес, 05 машина, 04 плотность) главнее расчёта на месте
    for i, c in enumerate(('p01', 'p05', 'p04')):
        if r.get(c) in ('да', 'нет', 'нет данных'):
            ans[i] = r[c]
    if 'нет' in ans: v = ('no', 'Без отметки')
    elif all(x == 'да' for x in ans): v = ('mark', 'Отметка')
    else: v = ('look', 'Присмотреться')
    return ans, v, u, pk, ratio

def sources_html(s):
    out = []
    for t in re.split(r'\s*\|\s*|\s+', s.strip()):
        if not t or t in ('coords', 'approx', 'approx-coords') or t.startswith('coords'): continue
        if t.startswith('http'):
            host = re.sub(r'^https?://(www\.)?', '', t).split('/')[0]
            out.append(f'<li><a href="{e(t)}" rel="nofollow noopener">{e(host)}</a></li>')
        elif '.' in t:
            out.append(f'<li>{e(t.rstrip(","))}</li>')
    seen, res = set(), []
    for o in out:
        if o not in seen: seen.add(o); res.append(o)
    return '\n'.join(res) or '<li>каталоги новостроек</li>'

HEAD = '''<!DOCTYPE html>
<html lang="ru">
<head>
<title>{title}</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light only">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{R}css/nota.css">
<link rel="icon" type="image/svg+xml" href="{R}favicon.svg">
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
{ld}</head>
<body class="inner">
<header class="top solid" id="top-bar"></header>
<main>
'''
TAIL = '''</main>
<footer></footer>
<script src="{R}js/nota.js"></script>
</body>
</html>
'''

def card(slug, cfg, r):
    cls = r['class_final']; R = '../../'
    ans, (vk, vt), u, pk, ratio = evaluate(r, cfg)
    title = cfg['title']; dev = r['developer'] or 'застройщик не указан'
    import pathlib
    root_ = pathlib.Path(__file__).resolve().parent.parent
    has_img = (root_ / 'img/doma' / f'{slug}.jpg').exists()
    img_html = (f'<figure class="h-img"><img src="{R}img/doma/{slug}.jpg" alt="{e(title)} — визуализация застройщика" width="960" height="600">'
                f'<figcaption>Визуализация застройщика</figcaption></figure>\n') if has_img else ''
    price = num(r['price_from_m2'])
    stage = r['stage'] + (f', срок — {r["deadline"]}' if r['deadline'] and r['deadline'] != 'сдан' else '')
    kind = r['type']
    # цифры
    stats = [(fmt(u) if u else '—', 'апартаментов' if kind == 'апартаменты' else 'квартир в доме'),
             (fmt(ratio, 2) if ratio else '—', 'машиномест на квартиру'),
             ((fmt(price / 1e6, 2) + ' млн' if price >= 1e6 else fmt(price / 1000) + ' тыс') if price else '—', '₽ за м², от')]
    stat_html = '\n'.join(f'   <div><b>{a}</b><span>{b}</span></div>' for a, b in stats)
    unit_word = 'лотов' if kind == 'апартаменты' else 'квартир'
    rows = [
        ('Где стоит дом?', f'{r["address"]}, {district_label(r["district"])}', f'{CLASS_RU[cls]} — {ADDR_RULE[cls]}', ans[0]),
        ('Сколько машиномест на квартиру?', (f'{fmt(pk)} мест на {fmt(u)} {unit_word} — {fmt(ratio, 2)}' if ratio else 'застройщик не раскрыл'),
         f'не меньше {fmt(PARK_NORM[cls], 1)}', ans[1]),
        ('Сколько в доме квартир?', (f'{fmt(u)}' if u else 'застройщик не раскрыл'), UNITS_NORM[cls][1], ans[2]),
    ]
    tagk = {'да': 'mark', 'нет': 'no', 'нет данных': 'look'}
    rows_html = '\n'.join(f'    <tr><td><b>{q}</b></td><td>{e(h)}</td><td>{e(n)}</td><td><span class="tag {tagk[a]}">{a}</span></td></tr>' for q, h, n, a in rows)
    checks = '\n'.join(f'   <li>{e(c)}</li>' for c in cfg.get('check', []))
    verdict_txt = {'mark': 'Дом прошёл все три проверки.',
                   'look': 'По одному из вопросов застройщик пока не раскрыл данные. Проверяем и возвращаемся с ответом.',
                   'no': 'Дом не проходит проверку своего класса. Причина — в таблице ниже.'}[vk]
    desc = f'{title} ({dev}) — {CLASS_RU[cls].lower()}, {r["district"]}. Наш итог: {vt.lower()}. Три проверки NOTA: адрес, паркинг, число квартир.'
    ld = {'@context': 'https://schema.org', '@type': 'ApartmentComplex', 'name': title,
          'address': {'@type': 'PostalAddress', 'streetAddress': r['address'], 'addressLocality': 'Москва', 'addressRegion': r['district']},
          'geo': {'@type': 'GeoCoordinates', 'latitude': r['lat'], 'longitude': r['lon']}}
    if u: ld['numberOfAccommodationUnits'] = int(u)
    ld_html = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n'
    body = f'''<section class="first tight-b"><div class="wrap">
 <p class="crumbs"><a href="{R}doma/">Дома</a> <span>/</span> {e(title)}</p>
 <p class="ttl">{CLASS_RU[cls]} · {e(district_label(r["district"]))}</p>
 <h1>{e(title)} <span class="h-dev">{e(dev)}</span></h1>
 <p class="lead">{e(r["address"])} · {e(stage)}</p>
 <div class="h-verdict"><span class="tag {vk}">{vt}</span><span>{verdict_txt}</span></div>
 {img_html}<div class="h-stats">
{stat_html}
 </div>
</div></section>

<section class="tight"><div class="wrap two">
 <div><p class="ttl">На заметку:</p></div>
 <div><p class="lede h-note">{e(cfg["note"])}</p></div>
</div></section>

{schools_html(r, R)}<section class="method"><div class="wrap">
 <p class="ttl">Три вопроса к дому</p>
 <div class="tablewrap">
  <table class="h-q">
   <tr><th>Вопрос</th><th>Как у дома</th><th>Мерка класса</th><th>Ответ</th></tr>
{rows_html}
  </table>
 </div>
 <p class="hint">Цену за метр в проверку не включаем — только сверяем с классом. Как устроена проверка — в <a href="{R}metod.html">методе</a>.</p>
</div></section>

<section class="tight"><div class="wrap two">
 <div><p class="ttl">Что проверить на месте</p><h2 style="margin-top:20px">Вопросы<br>для просмотра</h2></div>
 <div>
  <ul class="h-check">
{checks}
  </ul>
  <div class="btns"><a class="btn" href="{R}podbor.html">Подобрать под себя</a> <a class="btn btn-l" href="{R}karta.html">Дом на карте</a></div>
 </div>
</div></section>

<section class="tight"><div class="wrap">
 <p class="ttl">Источники</p>
 <ul class="h-src">
{sources_html(r["sources"])}
 </ul>
 <p class="hint">Данные базы NOTA на {DATE}. Если застройщик раскроет новые цифры, итог пересчитаем.</p>
</div></section>
'''
    return HEAD.format(title=f'{title} ({dev}) — {CLASS_RU[cls].lower()}, {r["district"]}. Разбор дома — NOTA', desc=e(desc), R=R, ld=ld_html) + body + TAIL.format(R=R), (title, CLASS_RU[cls], r['district'], vk, vt, u, ratio, dev)

def build(root):
    rows = load(root)
    cfgs = {k: v for k, v in json.loads((root / 'tools/doma.json').read_text()).items() if not k.startswith('_')}
    listing = []
    for slug, cfg in cfgs.items():
        r = next((x for x in rows if x['slug'] == slug), None) or next((x for x in rows if x['name'].startswith(cfg.get('match', '\0'))), None)
        if not r: print('нет в базе:', slug); continue
        page, meta = card(slug, cfg, r)
        d = root / 'doma' / slug; d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(page)
        listing.append((slug,) + meta)
    order = {'mark': 0, 'look': 1, 'no': 2}
    listing.sort(key=lambda x: (order[x[4]], x[1]))
    trs = '\n'.join(f'    <tr><td><a href="{s}/">{e(t)}</a></td><td>{e(dv)}</td><td><span class="tag {vk}">{vt}</span></td><td>{c}</td><td>{e(d)}</td><td>{fmt(u) if u else "—"}</td><td>{fmt(ra,2) if ra else "—"}</td></tr>'
                    for s, t, c, d, vk, vt, u, ra, dv in listing)
    R = '../'
    idx = HEAD.format(title='Дома: разборы новых домов Москвы — NOTA', R=R, ld='',
                      desc='Карточки новых домов Москвы от бизнес-класса и выше: три проверки NOTA — адрес, паркинг, число квартир — и наш итог по каждому дому.') + f'''<section class="first tight-b"><div class="wrap">
 <p class="ttl">Дома</p>
 <h1>Карточки домов</h1>
 <p class="lead">По каждому дому — три вопроса, ответы на них и что проверить на просмотре. Сначала те, что получили отметку, потом те, к которым стоит присмотреться, и в конце — без отметки, с причиной.</p>
</div></section>
<section style="padding-top:0"><div class="wrap">
 <div class="tablewrap">
  <table>
   <tr><th>Дом</th><th>Застройщик</th><th>Наш итог</th><th>Класс</th><th>Район</th><th>Квартир</th><th>М/м на кв.</th></tr>
{trs}
  </table>
 </div>
 <p class="hint">Карточек пока {len(listing)} из 288. Все дома базы — на <a href="../karta.html">карте объектов</a>.</p>
</div></section>
''' + TAIL.format(R=R)
    (root / 'doma/index.html').write_text(idx)
    print('карточки домов:', len(listing))
