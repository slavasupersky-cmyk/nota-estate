"""Карточки домов: data/doma.csv (выгрузка из nota-baza, см. tools/baza.py) + tools/doma.json → doma/<slug>/index.html
Паспорт дома — 9 проверок метода (data/kriterii.csv), ответы и факты — из data/proverki.csv.
Здесь же — таблица-пример для главной (home_table) и «пипсы» паспорта (pips), их берут build.py и karta.py."""
import csv, json, html, re, pathlib

DATE = '23 сентября 2026'
PARK_NORM = {'бизнес': 0.8, 'премиум': 1.5, 'элитный': 2.0, 'делюкс': 2.0}
UNITS_NORM = {'бизнес': (837, 'не больше типичного дома класса — 837'), 'премиум': (665, 'не больше типичного дома класса — 665'),
              'элитный': (100, 'до 100 квартир'), 'делюкс': (30, 'до 30 квартир')}
CLASS_RU = {'бизнес': 'Бизнес', 'премиум': 'Премиум', 'элитный': 'Элит', 'делюкс': 'Делюкс'}
CLASS_GEN = {'бизнес': 'бизнес-класса', 'премиум': 'премиум-класса', 'элитный': 'элит-класса', 'делюкс': 'делюкса'}
ADDR_RULE = {'бизнес': 'в старых границах Москвы', 'премиум': 'внутри Третьего кольца', 'элитный': 'в ЦАО', 'делюкс': 'в ЦАО'}
PASPORT = ['01', '02', '03', '04', '05', '06', '07', '08', '09']
HOME_SLUGS = ['forum', 'simonovskiy-val', 'scala', 'bolshaya-nikitskaya-16', 'republic']
e = html.escape

def num(x):
    try: return float(str(x).replace(' ', '').replace(',', '.'))
    except ValueError: return None

def fmt(n, d=0):
    return f'{n:,.{d}f}'.replace(',', ' ').replace('.', ',')

def plural(n, one, few, many):
    n = abs(int(n)); m10, m100 = n % 10, n % 100
    return one if m10 == 1 and m100 != 11 else few if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else many

def read(p):
    p = pathlib.Path(p)
    return list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []

_K = {}
def krit(root):
    """Проверки метода из data/kriterii.csv: id → dict(name, stop, level, group, porog)."""
    if not _K:
        for k in read(root / 'data/kriterii.csv'):
            _K[k['id']] = dict(name=k['proverka'], stop=k['stop'] == 'да', level=k['uroven'], group=k['gruppa'], porog=k['porog'])
    return _K

_P = {}
def facts(root):
    """Последний факт по каждой проверке: (slug, check) → строка proverki."""
    if not _P:
        for x in read(root / 'data/proverki.csv'):
            _P[(x['slug'], x['check'])] = x
    return _P

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
 <p class="hint">Пешком по улицам и дворам, 4,5 км/ч, до ближайшего корпуса школы.{approx} Все школы вокруг дома — на карте <a href="{R}shkoly-marshruty.html">«До школы пешком»</a>, сильные школы города — в <a href="{R}reytingi/shkoly-moskvy/">рейтинге школ</a>.</p></div>
</div></section>
'''

def district_label(d):
    return d if re.search(r'[.,~]|д\.|шоссе', d) else f'{d} район'

def load(root):
    rows = read(root / 'data/doma.csv')
    for r in rows:
        r['class_final'] = r['class']
    return rows

# ---------- паспорт ----------
ANS = {'да': ('y', 'да'), 'нет': ('n', 'нет'), 'не применяется': ('x', 'не применяется')}

def answer(r, c):
    a = r.get('p' + c) or ''
    return ANS.get(a, ('u', 'проверяем'))

def norm(r, c):
    cls = r['class_final']
    if c == '01':
        return 'не применяем за МКАД' if r['okrug'] in ('Рублёвка', 'Сколково') else f'{CLASS_RU[cls].lower()} — {ADDR_RULE[cls]}'
    if c == '02': return 'без ТЭЦ, мусорного завода и промзоны рядом, магистраль дальше 150 м'
    if c == '03': return 'метро до 15 минут пешком, школа с отметкой в километре'
    if c == '04': return UNITS_NORM[cls][1]
    if c == '05': return f'от {fmt(PARK_NORM[cls], 1)} места на квартиру'
    if c == '06': return 'рейтинг ЕРЗ.РФ от 3 из 5, без остановленных строек'
    if c == '07': return 'перенос срока не больше полугода'
    if c == '08': return 'продажа через эскроу'
    if c == '09': return 'не дороже медианы класса в районе больше чем на 30%'
    return ''

def value(root, r, c):
    """Как у дома: факт из proverki, иначе — из карточки дома."""
    f = facts(root).get((r['slug'], c), {})
    v = (f.get('value') or '').strip()
    u, pk = num(r['units_total']), num(r['parking'])
    if c == '01':
        return f'{r["address"]}, {district_label(r["district"])}'.strip(', ')
    if c == '03':
        if r.get('marked_min'): return f'школа с отметкой — {r["marked_min"]} мин пешком'
        if r.get('school_min'): return 'школ с отметкой в получасе пешком нет'
        return ''
    if c == '04' and u:
        return f'{fmt(u)} {plural(u, "квартира", "квартиры", "квартир")}' + (' и апартаментов' if 'апарт' in r['type'] else '')
    if c == '05' and u and pk:
        return f'{fmt(pk)} мест на {fmt(u)} {plural(u, "квартиру", "квартиры", "квартир")} — {fmt(pk / u, 2)}'
    if c == '06':
        return r['developer'] or ''
    if c == '07':
        return v or (r['stage'] + (f', {r["deadline"]}' if r['deadline'] else ''))
    if c == '08':
        return v or r['type']
    if c == '09':
        p = num(r['price_from_m2'])
        return f'от {fmt(p)} ₽/м²' if p else v
    return v

def pips(r, title=True):
    """Девять клеток паспорта: да — чёрная, нет — красная, проверяем — пустая."""
    out = []
    for c in PASPORT:
        k, t = answer(r, c)
        name = _K.get(c, {}).get('name', c)
        out.append(f'<i class="{k}"' + (f' title="{c} {e(name)} — {t}"' if title else '') + '></i>')
    closed = sum(1 for c in PASPORT if answer(r, c)[0] in ('y', 'n', 'x'))
    return f'<span class="pp" role="img" aria-label="Паспорт: {closed} из 9 проверок закрыты">' + ''.join(out) + '</span>', closed

VK = {'Отметка': 'mark', 'Присмотреться': 'look', 'Без отметки': 'no'}

def verdict(root, r):
    """Итог паспорта (считает baza.py) + объяснение человеческими словами."""
    K = krit(root); cls = r['class_final']
    vt = r.get('pasport') or 'Присмотреться'
    vk = VK.get(vt, 'look')
    if vk == 'no':
        why = []
        for c in PASPORT:
            if K.get(c, {}).get('stop') and (r.get('p' + c) == 'нет'):
                if c == '01': why.append(f'адрес не своего класса — {CLASS_RU[cls].lower()} {ADDR_RULE[cls].replace("в старых", "за старыми").replace("внутри Третьего кольца", "за Третьим кольцом").replace("в ЦАО", "за пределами ЦАО")}')
                elif c == '04':
                    u = num(r['units_total'])
                    why.append(f'{fmt(u)} {plural(u, "квартира", "квартиры", "квартир")} — больше, чем {"в типичном доме" if cls in ("бизнес", "премиум") else "допускает норма"} {CLASS_GEN[cls]} ({UNITS_NORM[cls][0]})' if u else 'слишком много соседей')
                elif c == '02': why.append('тяжёлое соседство')
                elif c == '06': why.append('застройщик срывает сроки')
                elif c == '08': why.append('продажа без эскроу')
        txt = 'Дом пересекает красную линию: ' + '; '.join(why) + '. Это не приговор дому — это то, что стоит знать до сделки.'
    elif vk == 'mark':
        txt = 'Стоп-факторов нет, и на большинство проверок паспорта ответ «да».'
    else:
        open_ = [K[c]['name'].lower() for c in PASPORT if answer(r, c)[0] == 'u' and c in K]
        no_ = [K[c]['name'].lower() for c in PASPORT if r.get('p' + c) == 'нет' and c in K]
        bits = []
        if no_: bits.append('не дотягивает: ' + ', '.join(no_))
        if open_: bits.append('ещё проверяем: ' + ', '.join(open_))
        txt = 'Стоп-факторов пока не нашли. ' + ('; '.join(bits).capitalize() + '.' if bits else '') + ' Закроем проверки — обновим итог.'
    return vk, vt, txt

def passport_html(root, r, R):
    K = krit(root)
    rows = []
    for c in PASPORT:
        k = K.get(c, {'name': c, 'stop': False})
        ak, at = answer(r, c)
        tag = {'y': 'mark', 'n': 'no', 'u': 'look', 'x': 'look'}[ak]
        f = facts(root).get((r['slug'], c), {})
        src = (f.get('source') or '').strip()
        when = (f.get('checked') or '').strip() if ak != 'u' else ''
        meta = ' · '.join(x for x in (src if src and not src.startswith('координаты базы') else '', when) if x)
        v = value(root, r, c)
        rows.append(f'''   <tr class="{ak}"><td><span class="pp-n">{c}</span><b>{e(k["name"])}</b>{'<em>стоп-фактор</em>' if k.get("stop") else ''}</td>
    <td>{e(v) if v else '<span class="muted">—</span>'}{f'<small>{e(meta)}</small>' if meta else ''}</td><td>{e(norm(r, c))}</td><td><span class="tag {tag}">{at}</span></td></tr>''')
    _, closed = pips(r)
    return f'''<section class="method" id="pasport"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Паспорт дома</p><h2 style="margin-top:20px">Девять проверок,<br>закрыто {closed} из 9</h2></div>
  <div><p class="lede">Паспорт собираем по открытым данным: проектная декларация, карты, рейтинг застройщика. «Проверяем» — значит, ответа с источником пока нет, и мы его не додумываем. Стоп-факторы отмечены красным: если хоть один из них «нет», отметки не будет.</p></div>
 </div>
 <div class="tablewrap">
  <table class="h-q pp-t">
   <tr><th>Проверка</th><th>Как у дома</th><th>Мерка класса</th><th>Ответ</th></tr>
{chr(10).join(rows)}
  </table>
 </div>
 <p class="hint">Ещё восемь проверок — архитектура, квартиры, двор, воздух, содержание, соседи, что построят рядом и ликвидность — делаем, когда дом попадает в вашу подборку. Как устроены все 17 — в <a href="{R}metod.html">методе</a>.</p>
</div></section>
'''

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

def card(root, slug, cfg, r):
    cls = r['class_final']; R = '../../'
    vk, vt, verdict_txt = verdict(root, r)
    u, pk = num(r['units_total']), num(r['parking'])
    ratio = pk / u if u and pk else None
    title = cfg['title']; dev = r['developer'] or 'застройщик не указан'
    price = num(r['price_from_m2'])
    stage = r['stage'] + (f', срок — {r["deadline"]}' if r['deadline'] and r['deadline'] != 'сдан' else '')
    kind = r['type']
    stats = [(fmt(u) if u else '—', 'апартаментов' if kind == 'апартаменты' else 'квартир в доме'),
             (fmt(ratio, 2) if ratio else '—', 'машиномест на квартиру'),
             ((fmt(price / 1e6, 2) + ' млн' if price >= 1e6 else fmt(price / 1000) + ' тыс') if price else '—', '₽ за м², от')]
    stat_html = '\n'.join(f'   <div><b>{a}</b><span>{b}</span></div>' for a, b in stats)
    checks = '\n'.join(f'   <li>{e(c)}</li>' for c in cfg.get('check', []))
    _, closed = pips(r)
    has_img = (root / 'img/doma' / f'{slug}.jpg').exists()
    img_html = (f'<figure class="h-img"><img src="{R}img/doma/{slug}.jpg" alt="{e(title)} — визуализация застройщика" width="960" height="600">'
                f'<figcaption>Визуализация застройщика</figcaption></figure>\n') if has_img else ''
    desc = f'{title} ({dev}) — {CLASS_RU[cls].lower()}, {r["district"]}. Паспорт NOTA: {closed} из 9 проверок закрыты, итог — {vt.lower()}. Адрес, плотность, машина, сроки, цена и школы рядом.'
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
 <div class="h-verdict"><span class="tag {vk}">{vt}</span><span>{e(verdict_txt)} <a href="#pasport">Паспорт дома</a></span></div>
 {img_html}<div class="h-stats">
{stat_html}
 </div>
</div></section>

<section class="tight"><div class="wrap two">
 <div><p class="ttl">На заметку:</p></div>
 <div><p class="lede h-note">{e(cfg["note"])}</p></div>
</div></section>

{passport_html(root, r, R)}
{schools_html(r, R)}<section class="tight"><div class="wrap two">
 <div><p class="ttl">Что проверить на месте</p><h2 style="margin-top:20px">Вопросы<br>для просмотра</h2></div>
 <div>
  <ul class="h-check">
{checks}
  </ul>
  <div class="btns"><a class="btn" href="{R}podbor.html">Подобрать под себя</a> <a class="btn btn-l" href="{R}karta.html#h-{slug}">Дом на карте</a></div>
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
    return HEAD.format(title=f'{title} ({dev}) — {CLASS_RU[cls].lower()}, {r["district"]}. Паспорт дома — NOTA', desc=e(desc), R=R, ld=ld_html) + body + TAIL.format(R=R), (title, CLASS_RU[cls], r['district'], vk, vt, u, r, dev)

def find(rows, slug, cfg):
    return next((x for x in rows if x['slug'] == slug), None) or next((x for x in rows if x['name'].startswith(cfg.get('match', '\0'))), None)

def home_table(root):
    """Строки таблицы «Каждый вывод — с цифрами» на главной (build.py вставляет между <!--baza-t--> и <!--/baza-t-->)."""
    rows = load(root); krit(root)
    cfgs = {k: v for k, v in json.loads((root / 'tools/doma.json').read_text()).items() if not k.startswith('_')}
    out = ['   <table class="pp-home">', '    <tr><th>Дом</th><th>Класс</th><th>Квартир</th><th>Паспорт</th><th>Итог</th></tr>']
    for slug in HOME_SLUGS:
        r = find(rows, slug, cfgs.get(slug, {}))
        if not r: continue
        cfg = cfgs.get(slug, {}); title = cfg.get('title') or r['name']
        u = num(r['units_total']); pp, closed = pips(r)
        vk, vt, _ = verdict(root, r)
        link = f'<a href="doma/{slug}/">{e(title)}</a>' if slug in cfgs else e(title)
        out.append(f'    <tr><td>{link} · {e(r["developer"])}</td><td>{CLASS_RU[r["class"]]}</td><td>{fmt(u) if u else "нет данных"}</td>'
                   f'<td>{pp}<span class="pp-c">{closed} из 9</span></td><td><span class="tag {vk}">{vt}</span></td></tr>')
    out.append('   </table>')
    return '\n'.join(out)

def build(root):
    rows = load(root); krit(root)
    cfgs = {k: v for k, v in json.loads((root / 'tools/doma.json').read_text()).items() if not k.startswith('_')}
    listing = []
    for slug, cfg in cfgs.items():
        r = find(rows, slug, cfg)
        if not r: print('нет в базе:', slug); continue
        page, meta = card(root, slug, cfg, r)
        d = root / 'doma' / slug; d.mkdir(parents=True, exist_ok=True)
        (d / 'index.html').write_text(page)
        listing.append((slug,) + meta)
    order = {'mark': 0, 'look': 1, 'no': 2}
    listing.sort(key=lambda x: (order[x[4]], x[1]))
    trs = '\n'.join(f'    <tr><td><a href="{s}/">{e(t)}</a></td><td>{e(dv)}</td><td><span class="tag {vk}">{vt}</span></td><td>{c}</td><td>{e(d)}</td><td>{fmt(u) if u else "—"}</td><td>{pips(r)[0]}</td></tr>'
                    for s, t, c, d, vk, vt, u, r, dv in listing)
    R = '../'
    idx = HEAD.format(title='Дома: паспорта новых домов Москвы — NOTA', R=R, ld='',
                      desc='Карточки новых домов Москвы от бизнес-класса и выше: паспорт NOTA из девяти проверок — адрес, соседство, плотность, машина, застройщик, сроки, договор, цена — и наш итог по каждому дому.') + f'''<section class="first tight-b"><div class="wrap">
 <p class="ttl">Дома</p>
 <h1>Карточки домов</h1>
 <p class="lead">По каждому дому — паспорт из девяти проверок, наш итог и что проверить на просмотре. Сначала дома с отметкой, потом те, к которым стоит присмотреться, в конце — без отметки, с причиной.</p>
</div></section>
<section style="padding-top:0"><div class="wrap">
 <div class="tablewrap">
  <table>
   <tr><th>Дом</th><th>Застройщик</th><th>Наш итог</th><th>Класс</th><th>Район</th><th>Квартир</th><th>Паспорт</th></tr>
{trs}
  </table>
 </div>
 <p class="hint"><span class="pp-key"><i class="y"></i> да <i class="n"></i> нет <i class="u"></i> проверяем</span> Карточек пока {len(listing)} из 288. Все дома базы — на <a href="../karta.html">карте объектов</a>, как устроена проверка — в <a href="../metod.html">методе</a>.</p>
</div></section>
''' + TAIL.format(R=R)
    (root / 'doma/index.html').write_text(idx)
    print('карточки домов:', len(listing))
