"""Рейтинги NOTA: страницы reytingi/<slug>/index.html из выгрузки базы (data/).
- reytingi/shkoly-moskvy/   — школы Москвы с нашей отметкой: data/shkoly.csv + снимок data/shkoly-baza-2026-09-23.json (описания, цены,
                               архитектура) + data/marshruty.csv (минуты пешком до домов) + data/doma.csv
- reytingi/penthausy-moskvy/ — пентхаусы в продаже: data/penthausy.csv
Хаб reytingi.html — статичный, правится руками. Фильтры, счётчики и «Показать ещё» — общий модуль [data-rlist] в js/nota.js."""
import csv, json, html, re, pathlib, statistics as st
from collections import defaultdict, Counter

e = html.escape
R = '../../'

def read(p):
    p = pathlib.Path(p)
    return list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';')) if p.exists() else []

def num(x):
    try: return float(str(x).replace(' ', '').replace(',', '.'))
    except ValueError: return None

def fmt(n, d=0):
    return f'{n:,.{d}f}'.replace(',', ' ').replace('.', ',')

def plural(n, one, few, many):
    n = abs(int(n)); m10, m100 = n % 10, n % 100
    return one if m10 == 1 and m100 != 11 else few if 2 <= m10 <= 4 and not 12 <= m100 <= 14 else many

def rub(v):
    """Рубли человеческими словами: 640 тыс, 1,9 млн, 4,3 млрд."""
    if v >= 1e9: return fmt(v / 1e9, 1).replace(',0', '') + ' млрд'
    if v >= 1e6: return fmt(v / 1e6, 1).replace(',0', '') + ' млн'
    return fmt(round(v / 1e3)) + ' тыс'

def rng(s):
    """«3231970000-8300000000» → (3.2e9, 8.3e9); «от 9000000000» → (9e9, None); «свыше 900» → (900, None)."""
    s = (s or '').replace(' ', '').replace(',', '.')
    xs = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', s)]
    if not xs: return None, None
    if len(xs) == 1: return xs[0], (None if re.search(r'от|свыше', s) else xs[0])
    return xs[0], xs[1]

def chip(g, k, label, on=False):
    return (f'<button class="chip" type="button" data-g="{g}" data-k="{k}" aria-pressed="{"true" if on else "false"}">'
            f'<span class="cl">{label}</span> <span class="cn"></span></button>')

def chips(g, title, opts):
    return (f'<div class="chipgrp" title="Можно выбрать несколько"><span class="cg-l">{title}</span><div class="chips">' + chip(g, 'all', 'Все', True) +
            ''.join(chip(g, k, l) for k, l in opts) + '</div></div>')

HEAD = '''<!DOCTYPE html>
<html lang="ru">
<head>
<title>{title}</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{R}css/nota.css">
<link rel="icon" type="image/svg+xml" href="{R}favicon.svg">
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{R}{img}">
<script type="application/ld+json">{ld}</script>
</head>
<body class="inner dark">
<header class="top solid" id="top-bar"></header>
<main>
'''
TAIL = '''</main>
<footer></footer>
<script src="{R}js/nota.js"></script>
</body>
</html>
'''

def cover(img, alt, kicker, h1, lead):
    return f'''<section class="jr-cover">
 <div class="jr-cover-img" style="background-image:url({R}{img})" role="img" aria-label="{e(alt)}"></div>
 <div class="wrap jr-cover-in">
  <p class="ix-back"><a href="{R}reytingi.html">← Все рейтинги</a></p>
  <p class="jr-issue">{kicker}</p>
  <h1>{h1}</h1>
  <p class="lead">{lead}</p>
 </div>
</section>
'''

def ld_list(name, desc, url, items):
    return json.dumps({'@context': 'https://schema.org', '@type': 'ItemList', 'name': name, 'description': desc, 'url': url,
                       'numberOfItems': len(items),
                       'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n} for i, n in enumerate(items[:50])]},
                      ensure_ascii=False)

def write(root, slug, page):
    d = root / 'reytingi' / slug
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'index.html'
    old = p.read_text() if p.exists() else ''
    # шапку и подвал потом вставит build.py — сравниваем без них, чтобы не переписывать файл зря
    strip = lambda s: re.sub(r'<header class="top[\s\S]*?</header>|<footer[\s\S]*?</footer>', '', s)
    if strip(old) != strip(page):
        p.write_text(page)
    return p

# ---------------------------------------------------------------- школы
ZONES = [('cao', 'ЦАО', ['ЦАО']), ('sao', 'САО', ['САО']), ('svao', 'СВАО', ['СВАО']), ('vao', 'ВАО', ['ВАО']), ('yuvao', 'ЮВАО', ['ЮВАО']),
         ('yuao', 'ЮАО', ['ЮАО']), ('yuzao', 'ЮЗАО', ['ЮЗАО']), ('zao', 'ЗАО', ['ЗАО']), ('szao', 'СЗАО', ['СЗАО']),
         ('new', 'Новая Москва и Зеленоград', ['НАО', 'ТАО', 'ЗелАО']), ('mo', 'За МКАД', ['За МКАД'])]
TYPES = [('gor', 'Городские', 'Городская'), ('chast', 'Частные', 'Частная'), ('sport', 'Спортивные', 'Спортивная'), ('vuz', 'При вузах', 'Вузовская')]
TIERS = [('mark', 'Отметка', 'Отметка'), ('zam', 'На заметку', 'На заметку'), ('best', 'Лучшая в районе', 'Лучшая в районе')]
TIER_TAG = {'Отметка': 'mark', 'На заметку': 'look', 'Лучшая в районе': 'no'}
CLS = {'бизнес': 'бизнес', 'премиум': 'премиум', 'элитный': 'элит', 'делюкс': 'делюкс'}
HK = {'бизнес': 'biz', 'премиум': 'prem', 'элитный': 'elit', 'делюкс': 'dlx'}

WEIGHTS = [
    ('Всероссийская олимпиада, финал 2026 года', 'Результаты школ Москвы: 3 балла за каждого победителя, 0,7 — за призёра. Ещё 3 балла, если школа брала дипломы и в 2025 году', 'до 25'),
    ('Грант Мэра Москвы 2025/26', 'Городской рейтинг вклада школ: экзамены, олимпиады, работа с малышами и детьми с особенностями, массовый спорт. От 35 баллов за первую двадцатку до 4 за места с 301-го по 400-е', 'до 35'),
    ('RAEX, рейтинг частных школ России', 'Для частных школ это замена городского гранта: город их по своей шкале не оценивает', 'до 40'),
    ('RAEX, поступление в ведущие вузы (Москва)', 'Какая доля выпускников поступает в 49 сильнейших вузов страны', 'до 20'),
    ('RAEX, отраслевые рейтинги', 'Медицина, экономика, точные и технические науки, гуманитарные направления', 'до 14'),
    ('RAEX, масштаб подготовки и топ-100 России', 'Сколько всего выпускников поступает в сильные вузы и место школы среди лучших в стране', 'до 18'),
    ('Городские профильные проекты', 'Только самые узкие: ресурсный центр «Математической вертикали» (11 школ), академический класс (14 школ), медиакласс (66 школ). Проекты, в которых участвуют почти все, не учитываются', 'до 14'),
    ('Forbes Education, частные школы', 'Высокая ценовая категория — 6 баллов, средняя — 4', 'до 6'),
]
SOURCES_SH = [
    'Сборная Москвы на Всероссийской олимпиаде: результаты школ, 2026 и 2025 (Центр педагогического мастерства)',
    'Рейтинг вклада школ в качественное образование московских школьников, ДОНМ, 2025/26',
    'RAEX: школы Москвы — конкурентоспособность выпускников и масштаб подготовки, 2026; топ-100 школ России, 2026; отраслевые рейтинги школ 2026; рейтинг частных школ России, 2026',
    'Портал предпрофессионального образования Москвы: академические классы, медиаклассы, ресурсные центры «Математической вертикали»',
    'Forbes Education: частные школы Москвы и области, 2026',
    'Реестр организаций Москомспорта',
    'Корпуса школ и пешеходные дорожки — OpenStreetMap (выгрузка BBBike 19.09.2026, Overpass 23.09.2026)',
    'По зданиям: archi.ru, «Проект Россия», EdDesign Mag, «Узнай Москву», mos.ru',
]

def shkoly(root):
    base = read(root / 'data/shkoly.csv')
    if not base: return None
    snap_p = sorted((root / 'data').glob('shkoly-baza-*.json'))
    snap = {r['name']: r for r in json.loads(snap_p[-1].read_text())['__SCHOOLS__']} if snap_p else {}
    doma = {r['slug']: r for r in read(root / 'data/doma.csv')}
    near = defaultdict(list)
    for m in read(root / 'data/marshruty.csv'):
        near[m['school_id']].append((float(m['walk_min']), m['slug']))
    zone_of = {z: k for k, _, zs in ZONES for z in zs}
    type_of = {v: k for k, _, v in TYPES}
    tier_of = {v: k for k, _, v in TIERS}

    rows = []
    for s in base:
        x = snap.get(s['name'], {})
        idx = int(num(s['index']) or 0)
        rows.append((s, x, idx))
    rows.sort(key=lambda t: (-t[2], t[0]['category'] == 'Спортивная', t[0]['name']))

    items, names, near_json, used = [], [], {}, {}
    for s, x, idx in rows:
        sid = s['school_id']; names.append(s['name'])
        z = zone_of.get(s['zone'], '')
        t = type_of.get(s['category'], '')
        tr = tier_of.get(s['tier'], 'rest')
        hs = sorted(near.get(sid, []))
        h15 = sum(1 for m, _ in hs if m <= 15)
        place = s['district'] or s['okrug'] or s['zone']
        sub = ' · '.join(v for v in (s['category'], place if place not in ('Уточнить',) else '') if v)
        tag = f'<span class="tag {TIER_TAG[s["tier"]]}">{e(s["tier"])}</span>' if s['tier'] else ''
        score = str(idx) if idx else '—'
        near_txt = (f'{h15} {plural(h15, "дом", "дома", "домов")} за 15 мин' if h15 else
                    (f'ближайший дом — {int(hs[0][0])} мин' if hs else ''))
        # раскрытая часть
        about = (x.get('about') or '').strip()
        dl = []
        if s['why'] and s['category'] != 'Спортивная': dl.append(('Почему здесь', s['why']))
        if x.get('sport_type'): dl.append(('Что это', x['sport_type']))
        if x.get('features'): dl.append(('Особенности', x['features']))
        pr = (x.get('price') or s.get('price') or '').strip()
        if pr and '₽' not in about:
            a, b = rng(pr)
            if a: dl.append(('Стоимость', (f'{rub(a)} — {rub(b)} ₽ в год' if b and b != a else f'{rub(a)} ₽ в год')))
        if s['address']: dl.append(('Адрес', s['address']))
        site = s['site'] or x.get('site') or ''
        dl_html = ''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k, v in dl)
        if site:
            host = re.sub(r'^https?://(www\.)?', '', site).split('/')[0]
            dl_html += f'<dt>Сайт</dt><dd><a href="{e(site)}" rel="nofollow noopener">{e(host)}</a></dd>'
        hcls = sorted({HK.get(doma[sl]['class'], '') for m, sl in hs if m <= 20 and sl in doma} - {''})
        if hs:
            near_html = f'<div class="ri-near" data-sid="{sid}"></div>'
            near_json[sid] = [[slug, int(m)] for m, slug in hs if slug in doma]
            for m, slug in hs:
                if slug in doma:
                    h = doma[slug]
                    used[slug] = [h['name'].split(' (')[0], CLS.get(h['class'], h['class']), int(num(h['price_from_m2']) or 0)]
        elif s['category'] != 'Спортивная':
            near_html = '<div class="ri-near"><p class="k">Новые дома рядом</p><p class="hint" style="margin:0">В получасе пешком домов из нашей базы нет.</p></div>'
        else:
            near_html = ''
        pick = (f'<div class="ri-pickbox"><button class="btn btn-l ri-pick" type="button" data-pick="{sid}">В подборку</button>'
                f'<span class="hint">Отметьте несколько школ — соберём дома рядом с ними в одну подборку.</span></div>') if hs else ''
        body = (f'<div class="ri-main">{f"<p>{e(about)}</p>" if about else ""}<dl>{dl_html}</dl>{pick}</div>{near_html}')
        q = ' '.join([s['name'], s['district'], s['address']]).lower().replace('ё', 'е')
        items.append(f'''<article class="ri" id="s-{sid}" data-t="{t}" data-l="{tr}" data-z="{z}" data-h="{' '.join(hcls)}" data-q="{e(q)}" data-name="{e(s["name"])}">
 <button class="ri-row" type="button" aria-expanded="false"><span class="ri-n">{score}</span><span class="ri-t"><b>{e(s["name"])}</b><span>{e(sub)}</span></span><span class="ri-c">{tag}</span><span class="ri-v">{near_txt}</span></button>
 <div class="ri-body" hidden>{body}</div>
</article>''')

    cnt = Counter(r[0]['category'] for r in rows)
    tiers = Counter(r[0]['tier'] for r in rows)
    n_all = len(rows)
    # дома: школа с отметкой в 20 минутах
    hr = [r for r in doma.values() if r.get('school_min')]
    k20 = sum(1 for r in hr if r.get('marked_min') and float(r['marked_min']) <= 20)
    share20 = round(k20 / len(hr) * 100) if hr else 0

    type_desc = {
        'Городская': 'Бесплатная школа с аттестатом. В начальную школу берут по месту жительства, в сильные профильные классы — по экзаменам с 7–8 класса. Единственный тип, где адрес квартиры прямо влияет на шансы поступить.',
        'Вузовская': 'Лицеи и предуниверситарии при вузах: МИФИ, ВШЭ, Финансовом университете, РЭУ, МГЛУ, Сеченовском, РАНХиГС, МГУ. Берут со всего города по экзамену, обычно с 8–10 класса. Здесь важна дорога, а не прописка.',
        'Частная': 'От 640 тысяч до 3,7 млн рублей в год. Четыре школы с пансионом: «Летово», Классический пансион МГУ, гимназия Примакова, Ломоносовская. Многие сильные частные школы стоят за МКАД — это другой сценарий жизни: выбирают не район, а шоссе.',
        'Спортивная': 'Аттестат дают пять: «Самбо-70», интернат «Чертаново», «Москва-98», «МЭШ», ЦОиС «Локомотив». Остальные — спортшколы олимпийского резерва и академии: ребёнок учится в обычной школе, а сюда ездит на тренировки. Это два адреса и дорога между ними. Отметку им не считаем — их измеряют разряды.',
    }
    types_html = '\n'.join(f'''  <div class="lv"><span class="ttl">{c}</span><b>{cnt.get(c, 0)} в базе</b><p>{type_desc[c]}</p></div>'''
                           for c in ('Городская', 'Частная', 'Вузовская', 'Спортивная'))

    desc = (f'{n_all} школ Москвы — городские, частные, спортивные и при вузах — по восьми открытым рейтингам: '
            f'{tiers["Отметка"]} с отметкой NOTA, {tiers["На заметку"]} на заметку. Фильтры по типу, уровню и округу, новые дома рядом пешком.')
    body = cover('img/ix-2026-09-shkola.jpg', 'Кампус современной школы',
                 f'<b>Рейтинг</b><span>Школы Москвы</span><span>Сентябрь 2026</span><span>{n_all} школ</span>',
                 'Школы Москвы с&nbsp;нашей отметкой',
                 f'{n_all} московских школ — городских, частных, спортивных и при вузах — по восьми открытым рейтингам. {tiers["Отметка"]} получили отметку NOTA, ещё {tiers["На заметку"]} — на заметку. И сколько минут пешком до них от новых домов.') + f'''
<section><div class="wrap jr-ed">
 <div><p class="ttl">На заметку:</p></div>
 <div>
  <div class="jr-ed-t">
   <p>Школу выбирают один раз, а живут рядом с ней одиннадцать лет — дольше, чем обычно выплачивают ипотеку. Поэтому у многих семей вопрос «где покупать квартиру» начинается не с метро и не с вида из окна, а со школы. Эта страница для такого разговора: здесь школы, в которые стоит целиться, и дома, которые стоят рядом с ними.</p>
   <p>Обычные рейтинги показывают два десятка знаменитых школ в центре и молчат про остальной город. Здесь по-другому: в каждом районе, где сейчас продаётся жильё бизнес-класса и выше, есть хотя бы одна школа с понятным объяснением, почему она здесь. {tiers["Отметка"]} школ получили отметку, ещё {tiers["На заметку"]} — на заметку, а там, где в районе нет школ такого уровня, показана сильнейшая из тех, что есть, — с пометкой «лучшая в районе».</p>
   <p>Про школы с отметкой написано по-человечески: как устроен день, что там кроме уроков, как поступить и о чём лучше знать заранее — про шестидневку, отсев или конкурс в тридцать человек на место. А у каждой школы — новые дома, до которых можно дойти пешком, в минутах по улицам, а не «в том же районе»: из таких пар почти половина оказывается дальше получаса пешком.</p>
  </div>
 </div>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="strip" style="margin-top:0">
  <div><b>{n_all}</b><small>школ в базе: {cnt["Городская"]} городских, {cnt["Частная"]} частных, {cnt["Спортивная"]} спортивных, {cnt["Вузовская"]} при вузах</small></div>
  <div><b>{tiers["Отметка"]}</b><small>получили отметку NOTA — 40 баллов и выше</small></div>
  <div><b>{tiers["На заметку"]}</b><small>на заметку — от 25 до 39 баллов</small></div>
  <div><b>{share20}%</b><small>новых домов — со школой с отметкой в 20 минутах пешком</small></div>
 </div>
</div></section>

<section class="method" id="spisok"><div class="wrap" data-rlist data-lim="20">
 <div class="two">
  <div><p class="ttl">Все школы</p><h2 style="margin-top:20px">{n_all} школ:<br>выберите свои</h2></div>
  <div><p class="lede">Выберите тип школы, уровень и округ, а в «Домах рядом» — классы жилья, которые рассматриваете: останутся школы, до которых от таких домов 20 минут пешком. В каждой строке фильтра можно выбрать несколько вариантов. Откройте школу, чтобы прочитать о ней и добавить в подборку.</p></div>
 </div>
 <div class="ri-filters">
  {chips('t', 'Тип', [(k, l) for k, l, _ in TYPES])}
  {chips('l', 'Уровень', [(k, l) for k, l, _ in TIERS] + [('rest', 'Остальные')])}
  {chips('h', 'Дома рядом', [('biz', 'бизнес'), ('prem', 'премиум'), ('elit', 'элит'), ('dlx', 'делюкс')])}
  {chips('z', 'Округ', [(k, l) for k, l, _ in ZONES])}
  <label class="ri-q"><span class="cg-l">Поиск</span><input type="search" placeholder="Номер, название или район" autocomplete="off"></label>
 </div>
 <div class="hs-bar"><span class="ri-cnt"></span><button class="linkbtn" type="button" data-reset>Сбросить фильтры</button></div>
 <div class="ri-list">
{chr(10).join(items)}
 </div>
 <div class="hs-more"><button class="btn btn-l ri-more" type="button" hidden>Показать ещё</button></div>
 <script type="application/json" class="ri-data">{json.dumps({'h': used, 'n': near_json, 'R': R}, ensure_ascii=False, separators=(',', ':'))}</script>
 <div class="pickbar" hidden><span class="pb-t"></span><button class="btn pb-go" type="button">Подобрать дома рядом</button><button class="linkbtn pb-clr" type="button">сбросить</button></div>
 <div class="modal" id="pickmdl" hidden>
  <div class="modal-bg" data-close></div>
  <div class="modal-in pk-in" role="dialog" aria-modal="true" aria-labelledby="pk-h">
   <button class="modal-x" type="button" data-close aria-label="Закрыть">×</button>
   <p class="ttl">Подборка NOTA</p>
   <h3 id="pk-h">Дома рядом с выбранными школами</h3>
   <div class="pk-sel"></div>
   <div class="pk-list"></div>
   <p class="hint pk-note">Пришлите этот список нам — ответим сегодня и пришлём, что продаётся в этих домах: планировки, цены и условия. Для покупателя подбор бесплатный.</p>
   <div class="btns"><a class="btn" href="https://t.me/nota_estate" target="_blank" rel="noopener">Написать в Telegram</a> <button class="btn btn-l pk-copy" type="button">Скопировать список</button></div>
  </div>
 </div>
 <p class="hint">Число слева — отметка NOTA от 0 до 100. Справа — сколько новых домов из нашей базы в 15 минутах пешком по улицам до ближайшего корпуса школы. Все маршруты — на карте <a href="{R}shkoly-marshruty.html">«До школы пешком»</a>.</p>
</div></section>

<section id="metodika"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Методика</p><h2 style="margin-top:20px">Из чего складывается<br>отметка</h2></div>
  <div><p class="lede">Баллы из восьми источников складываются и приводятся к шкале от 0 до 100: сильнейшая школа получает 100. От 40 и выше — отметка, от 25 до 39 — на заметку. Ни один источник не даёт больше трети итога.</p></div>
 </div>
 <div class="faq ri-w">
{chr(10).join(f'  <details><summary>{e(a)}<span class="ri-wb">{c} баллов</span></summary><p>{e(b)}.</p></details>' for a, b, c in WEIGHTS)}
 </div>
 <div class="claims ri-notes">
  <div class="claim"><h3>Чего в отметке нет</h3><p>Отзывов, конкурса на место, состояния здания и, главное, того, какой учитель достанется вашему ребёнку. Отметка говорит, что школа из года в год выводит детей на высокий уровень, и ничего не говорит о том, как в ней живётся в пятом классе. Средние баллы ЕГЭ по школам официально не публикуют, поэтому их здесь нет.</p></div>
  <div class="claim"><h3>Где цифры спорят с репутацией</h3><p>Хорошкола — сильная и известная школа, но по цифрам 2026 года у неё грант Мэра III степени, 40-е место по Москве в рейтинге поступлений и четыре диплома Всероса. Итог — 38, то есть «на заметку». Это не оценка школы в целом, а срез за один год.</p></div>
  <div class="claim"><h3>Ограничения</h3><p>В первый класс берут по месту жительства, и ближайшая школа не всегда «своя»: закрепление домов за школами мы ещё не учитываем. Цены частных школ меняются каждый год — уточняйте их в приёмной комиссии.</p></div>
 </div>
</div></section>

<section class="method" id="tipy"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Типы</p><h2 style="margin-top:20px">Четыре разные вещи,<br>которые называют школой</h2></div>
  <div><p class="lede">Городская школа, частная, при вузе и спортивная — это разные сценарии жизни. От типа зависит, важен ли адрес квартиры или дорога до школы.</p></div>
 </div>
 <div class="levels ri-types">
{types_html}
 </div>
</div></section>

<section id="stoit-znat"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Стоит знать</p><h2 style="margin-top:20px">Что изменилось<br>в частных школах</h2></div>
  <div class="claims">
   <div class="claim"><h3>Международного бакалавриата больше нет</h3><p>В августе 2025 года фонд International Baccalaureate признали в России нежелательной организацией. Школы, которые работали по программам IB, от них отказались, и международный диплом IB в России больше не получить. Если на сайте школы до сих пор висит страница про IB, это старый текст, а не преимущество.</p></div>
   <div class="claim"><h3>Проверяйте, кому платите</h3><p>В марте 2026 года одна из самых дорогих школ Москвы, Brookes Moscow, закрылась посреди учебного года. Прежде чем платить за год вперёд, стоит посмотреть, сколько лет работает юрлицо школы и кто её владелец.</p></div>
  </div>
 </div>
</div></section>

<section class="method" id="arhitektura"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Отдельный разбор</p><h2 style="margin-top:20px">Школа как<br>архитектура</h2></div>
  <div><p class="lede">Школу выбирают по цифрам, а ребёнок проводит в ней одиннадцать лет — в конкретных коридорах, с конкретным светом и потолками. Двадцать одно школьное здание с известным автором: от конструктивизма 1930-х до кампусов последних лет.</p>
   <div class="btns"><a class="btn btn-l" href="{R}razbory/shkola-kak-arhitektura/">Смотреть 21 здание</a></div></div>
 </div>
</div></section>

<section><div class="wrap two">
 <div><p class="ttl">Источники</p><h2 style="margin-top:20px">Откуда цифры</h2></div>
 <div>
  <ul class="h-src">
{chr(10).join(f'   <li>{e(x)}</li>' for x in SOURCES_SH)}
   <li>О запрете International Baccalaureate — сообщения Генпрокуратуры от 25 августа 2025 года в изложении <a href="https://www.forbes.ru/education/544513-deatel-nost-international-baccalaureate-priznali-nezelatel-noj-v-rossii" rel="nofollow noopener">Forbes Education</a> и <a href="https://skillbox.ru/media/education/deyatelnost-organizacii-mezhdunarodnogo-bakalavriata-priznana-nezhelatelnoy-v-rossii/" rel="nofollow noopener">Skillbox Media</a>; о закрытии Brookes Moscow — <a href="https://www.m24.ru/news/17032026/883274" rel="nofollow noopener">Москва 24</a> и <a href="https://www.dp.ru/a/2026/03/16/jelitnaja-chastnaja-shkola-v-moskve" rel="nofollow noopener">«Деловой Петербург»</a>, 16–17 марта 2026 года</li>
  </ul>
  <p class="hint">База школ NOTA, редакция 5, на 23 сентября 2026. Минуты — пешком по улицам и дворам, 4,5 км/ч, без светофоров, до ближайшего корпуса школы.</p>
  <div class="btns"><a class="btn" href="{R}podbor.html">Подобрать дом рядом со школой</a> <a class="btn btn-l" href="{R}shkoly-marshruty.html">Карта «До школы пешком»</a></div>
 </div>
</div></section>
'''
    page = HEAD.format(title=f'Школы Москвы с нашей отметкой: рейтинг {n_all} школ 2026 — NOTA', R=R, desc=e(desc), img='img/ix-2026-09-shkola.jpg',
                       ld=ld_list('Школы Москвы с нашей отметкой', desc, 'reytingi/shkoly-moskvy/', names)) + body + TAIL.format(R=R)
    stats = {'shkoly': n_all, 'shkoly_mark': tiers.get('Отметка', 0), 'shkoly_zam': tiers.get('На заметку', 0)}
    return write(root, 'shkoly-moskvy', page), n_all, stats

# ---------------------------------------------------------------- пентхаусы
PDIST = [('hamovniki', 'Хамовники', ['Хамовники']), ('yakimanka', 'Якиманка и Замоскворечье', ['Якиманка', 'Замоскворечье']),
         ('tverskoy', 'Тверской и Арбат', ['Тверской', 'Арбат', 'Красносельский']), ('presnya', 'Пресня', ['Пресненский']),
         ('zapad', 'Запад', ['Раменки', 'Дорогомилово', 'Очаково-Матвеевское', 'Гагаринский']),
         ('sever', 'Север и северо-запад', ['Хорошёвский', 'Хорошёво-Мнёвники', 'Беговой', 'Марфино', 'Войковский', 'Тимирязевский', 'Щукино'])]

def host(u):
    return re.sub(r'^https?://(www\.)?', '', u).split('/')[0]

def v_dome(name):
    """«в доме «Долина Сетунь»», «в клубном доме в Брюсовом переулке»."""
    n = name.split(' (')[0]
    return e('в клубном доме' + n[len('Клубный дом'):]) if n.startswith('Клубный дом') else e(f'доме «{n}»')

def penthausy(root):
    rows = read(root / 'data/penthausy.csv')
    if not rows: return None
    doma = {r['slug']: r for r in read(root / 'data/doma.csv')}
    dist_of = {d: k for k, _, ds in PDIST for d in ds}
    def district(r):
        d = r['district']
        return next((k for k, _, ds in PDIST for x in ds if d.startswith(x) or x.startswith(d)), 'other')
    data = []
    for r in rows:
        pm_lo, pm_hi = rng(r['price_m2']); pt_lo, pt_hi = rng(r['price_total']); a_lo, a_hi = rng(r['area_m2'])
        key = pm_hi or pm_lo or 0
        data.append(dict(r=r, pm=(pm_lo, pm_hi), pt=(pt_lo, pt_hi), area=(a_lo, a_hi), key=key, dk=district(r)))
    sale = [x for x in data if x['r']['status'] == 'в продаже']
    data.sort(key=lambda x: (x['r']['status'] != 'в продаже', -x['key'], x['r']['zhk']))
    priced = [x for x in data if x['key']]
    top = sorted(priced, key=lambda x: -x['key'])
    top10 = [x for x in top if x['r']['status'] == 'в продаже'][:10]
    n_ham = sum(1 for x in top10 if x['r']['district'].startswith('Хамовники'))
    all_cao = all(x['r']['okrug'] == 'ЦАО' for x in top10)
    words = ['ни один', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять', 'десять']
    geo_txt = (f'{words[n_ham]} из десяти самых дорогих — в Хамовниках' + (', и все десять — в центре' if all_cao else '')) if n_ham else 'самые дорогие — в центре'
    cheapest = min(priced, key=lambda x: x['pm'][0] or x['key'])
    biggest = max([x for x in sale if x['area'][0]], key=lambda x: x['area'][1] or x['area'][0])
    lots = sum(int(num(x['r']['count']) or 1) for x in sale)
    in_base = sum(1 for x in data if x['r']['slug'] and x['r']['slug'] in doma)

    def band(x):
        v = x['key']
        return 'b1' if v and v < 2e6 else 'b2' if v and v < 5e6 else 'b3' if v else 'b0'
    def m2(v): return f'{fmt(v / 1e6, 1).replace(",0", "")} млн'
    items = []
    for i, x in enumerate(data, 1):
        r = x['r']
        name = r['zhk'].split(' (')[0]
        pm = (f'{m2(x["pm"][0])} — {m2(x["pm"][1])}' if x['pm'][1] and x['pm'][1] != x['pm'][0] else
              (f'{"от " if not x["pm"][1] else ""}{m2(x["pm"][0])}' if x['pm'][0] else 'по запросу'))
        pt = (f'{rub(x["pt"][0])} — {rub(x["pt"][1])} ₽' if x['pt'][1] and x['pt'][1] != x['pt'][0] else
              (f'{"от " if not x["pt"][1] else ""}{rub(x["pt"][0])} ₽' if x['pt'][0] else 'по запросу'))
        area = r['area_m2'].replace('-', '–').replace(' ', ' ')
        area = (area + ' м²') if area else 'не раскрыта'
        cnt = int(num(r['count']) or 0)
        status = {'в продаже': '', 'продан 2026': 'продан в 2026', 'выйдет в продажу': 'выйдет в продажу'}.get(r['status'], r['status'])
        sub = ' · '.join(v for v in (r['developer'], r['district'], (f'{cnt} {plural(cnt, "пентхаус", "пентхауса", "пентхаусов")}' if cnt > 1 else '')) if v)
        dl = [('Площадь', area), ('Этаж', r['floor'] or '—'), ('Цена лота', pt), ('Цена метра', pm)]
        if r['features']: dl.append(('Что внутри', r['features']))
        srcs = [u for u in re.split(r'\s*\|\s*', r['source']) if u.startswith('http')]
        src_html = ', '.join(f'<a href="{e(u)}" rel="nofollow noopener">{e(host(u))}</a>' for u in srcs)
        dl_html = ''.join(f'<dt>{k}</dt><dd>{e(v)}</dd>' for k, v in dl) + (f'<dt>Источники</dt><dd>{src_html} · {e(r["checked"])}</dd>' if src_html else '')
        link = ''
        if r['slug'] and r['slug'] in doma:
            h = doma[r['slug']]
            card = root / 'doma' / r['slug'] / 'index.html'
            href = f'{R}doma/{r["slug"]}/' if card.exists() else f'{R}karta.html#h-{r["slug"]}'
            link = f'<div class="ri-near"><p class="k">Дом в нашей базе</p><p style="margin:0"><a href="{href}">{e(h["name"].split(" (")[0])}</a> — {e(h["class"].replace("элитный", "элит"))}, {e(h["stage"])}{", срок — " + e(h["deadline"]) if h["deadline"] and h["deadline"] != "сдан" else ""}</p></div>'
        q = ' '.join([r['zhk'], r['developer'], r['district'], r['features']]).lower().replace('ё', 'е')
        st_tag = f'<span class="tag look">{status}</span>' if status else ''
        items.append(f'''<article class="ri" id="p-{r["pent_id"]}" data-d="{x["dk"]}" data-b="{band(x)}" data-s="{"sale" if not status else "other"}" data-q="{e(q)}">
 <button class="ri-row" type="button" aria-expanded="false"><span class="ri-n">{i}</span><span class="ri-t"><b>{e(name)}</b><span>{e(sub)}</span></span><span class="ri-c">{st_tag}</span><span class="ri-v">{pm}<small>за м²</small></span></button>
 <div class="ri-body" hidden><div class="ri-main"><dl>{dl_html}</dl></div>{link}</div>
</article>''')
    n = len(data)
    desc = (f'{n} пентхаусов в новых домах Москвы: {len(sale)} в продаже, цены от {m2(cheapest["pm"][0] or cheapest["key"])} до {m2(top[0]["key"])} рублей за метр. '
            'Площадь, этаж, цена лота и что внутри — с источниками.')
    body = cover('img/18-penthaus.jpg', 'Терраса пентхауса с видом на Москву',
                 f'<b>Рейтинг</b><span>Пентхаусы</span><span>Сентябрь 2026</span><span>{n} объектов</span>',
                 'Пентхаусы Москвы',
                 f'{n} пентхаусов в новых домах Москвы: где они, сколько стоят и за что просят сверху — от {m2(cheapest["pm"][0] or cheapest["key"])} до {m2(top[0]["key"])} рублей за метр.') + f'''
<section><div class="wrap jr-ed">
 <div><p class="ttl">От редактора</p></div>
 <div>
  <div class="jr-ed-t">
   <p>Пентхаус — самый заметный лот в доме, и цены на них живут по своим законам. Метр под крышей стоит от {m2(cheapest["pm"][0] or cheapest["key"])} рублей в {v_dome(cheapest["r"]["zhk"])} до {m2(top[0]["key"])} в {v_dome(top[0]["r"]["zhk"])}. Разница — в {round(top[0]["key"] / (cheapest["pm"][0] or cheapest["key"]))} раз, и объясняет её не площадь, а адрес: {geo_txt}.</p>
   <p>Мы собрали пентхаусы, которые сейчас продаются в новых домах, с площадью, этажом и ценой, и расставили их по цене метра. Цены — из открытых источников на {e(rows[0]["checked"])}: итоговая цена в пентхаусах почти всегда договорная, поэтому это ориентир, а не прайс.</p>
  </div>
  <p class="jr-sign"><span><b>Елена</b>, редактор NOTA</span></p>
 </div>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <div class="strip" style="margin-top:0">
  <div><b>{len(sale)}</b><small>в продаже — всего около {lots} лотов под крышей</small></div>
  <div><b>{m2(top[0]["key"])}</b><small>за метр — самый дорогой: {e(top[0]["r"]["zhk"])}</small></div>
  <div><b>{fmt(biggest["area"][1] or biggest["area"][0])} м²</b><small>самый большой лот в продаже — {e(biggest["r"]["zhk"])}</small></div>
  <div><b>{in_base}</b><small>{plural(in_base, "пентхаус", "пентхауса", "пентхаусов")} — в домах нашей базы, с паспортом дома</small></div>
 </div>
</div></section>

<section class="method" id="spisok"><div class="wrap" data-rlist data-lim="20">
 <div class="two">
  <div><p class="ttl">Рейтинг</p><h2 style="margin-top:20px">По цене метра —<br>от дорогих к доступным</h2></div>
  <div><p class="lede">В строке — верхняя граница цены метра в доме. Откройте пентхаус: площадь, этаж, цена лота, что внутри и откуда цифры.</p></div>
 </div>
 <div class="ri-filters">
  {chips('d', 'Где', [(k, l) for k, l, _ in PDIST])}
  {chips('b', 'Цена метра', [('b1', 'до 2 млн'), ('b2', '2–5 млн'), ('b3', 'от 5 млн')])}
  <label class="ri-q"><span class="cg-l">Поиск</span><input type="search" placeholder="Дом, застройщик или терраса" autocomplete="off"></label>
 </div>
 <div class="hs-bar"><span class="ri-cnt"></span><button class="linkbtn" type="button" data-reset>Сбросить фильтры</button></div>
 <div class="ri-list">
{chr(10).join(items)}
 </div>
 <div class="hs-more"><button class="btn btn-l ri-more" type="button" hidden>Показать ещё</button></div>
</div></section>

<section><div class="wrap two">
 <div><p class="ttl">Как считали</p><h2 style="margin-top:20px">Ориентир,<br>а не прайс</h2></div>
 <div>
  <p class="lede">Цены и площади — из открытых источников: каталоги пентхаусов, обзоры РИА Недвижимость, «Прайма», «Мира квартир» и «Ленты» на {e(rows[0]["checked"])}. У каждого пентхауса ссылки на источник. Проданные в 2026 году и готовящиеся к продаже лоты стоят в конце списка.</p>
  <p class="hint">Цена метра в строке — верхняя граница по дому. Если цену не публикуют, пишем «по запросу». Пентхаус в доме из нашей базы ведёт на паспорт дома — адрес, плотность, сроки и школы рядом.</p>
  <div class="btns"><a class="btn" href="{R}podbor.html">Подобрать пентхаус</a> <a class="btn btn-l" href="{R}karta.html">Дома на карте</a></div>
 </div>
</div></section>
'''
    names = [x['r']['zhk'] for x in data]
    page = HEAD.format(title=f'Пентхаусы Москвы: {n} пентхаусов в новых домах, цены 2026 — NOTA', R=R, desc=e(desc), img='img/18-penthaus.jpg',
                       ld=ld_list('Пентхаусы Москвы', desc, 'reytingi/penthausy-moskvy/', names)) + body + TAIL.format(R=R)
    stats = {'pent': n, 'pent_sale': len(sale), 'pent_base': in_base,
             'pent_min': m2(cheapest['pm'][0] or cheapest['key']), 'pent_max': m2(top[0]['key'])}
    return write(root, 'penthausy-moskvy', page), n, stats

def build(root):
    """Собирает страницы рейтингов и отдаёт их цифры для хаба reytingi.html (живые цифры build.py)."""
    out, stats = [], {}
    a = shkoly(root)
    if a: out.append(f'школы {a[1]}'); stats.update(a[2])
    b = penthausy(root)
    if b: out.append(f'пентхаусы {b[1]}'); stats.update(b[2])
    print('рейтинги:', ', '.join(out) or 'нет данных')
    return stats
