"""Карта объектов: data/doma.csv (выгрузка из nota-baza, см. tools/baza.py) + img/doma/<slug>.jpg
→ <main> страницы karta.html: карта с точками по реальным координатам, фильтры, список «по вашим фильтрам»."""
import csv, json, re, html

e = html.escape
LAT0, LON0, KX, KY = 55.75297, 37.61758, 62.65, 111.2      # локальная проекция, 1 = 1 км, центр — Кремль
S = 15.0                                                    # px на км
CLS = {'бизнес': 'Бизнес', 'премиум': 'Премиум', 'элитный': 'Элит', 'делюкс': 'Делюкс'}
CKEY = {'бизнес': 'biz', 'премиум': 'prem', 'элитный': 'elit', 'делюкс': 'dlx'}
R_DOT = {'biz': 3.4, 'prem': 4.0, 'elit': 4.6, 'dlx': 5.2}
SIZES = {'biz': (45, 70, 100), 'prem': (60, 90, 130), 'elit': (90, 140, 200), 'dlx': (120, 180, 250)}
OUT = {'Сколково', 'Рублёвка'}
TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
              ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u',
               'f', 'kh', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e', 'yu', 'ya']))
OKR = ['ЦАО', 'САО', 'СВАО', 'ВАО', 'ЮВАО', 'ЮАО', 'ЮЗАО', 'ЗАО', 'СЗАО', 'Сколково', 'Рублёвка']
YB = {'now': 'Сдан или в 2026', 'y27': '2027', 'y28': '2028 и позже', 'ann': 'Анонс'}


def slugify(name):
    base = name.split(' (')[0].lower()
    base = ''.join(TR.get(ch, ch) for ch in base)
    return re.sub(r'[^a-z0-9]+', '-', base).strip('-') or 'dom'


def num(v):
    try:
        return float(str(v).replace(' ', '').replace(',', '.'))
    except ValueError:
        return None


def fmt(n, d=0):
    return f'{n:,.{d}f}'.replace(',', ' ').replace('.', ',')


def grab(s, name):
    i = s.index(name + '=') + len(name) + 1
    op = s[i]
    cl = {'[': ']', '{': '}'}[op]
    dep = 0
    for j in range(i, len(s)):
        if s[j] == op:
            dep += 1
        elif s[j] == cl:
            dep -= 1
            if dep == 0:
                return json.loads(s[i:j + 1])


def proj(lat, lon):
    return ((lon - LON0) * KX, (LAT0 - lat) * KY)


def smooth_path(pts, closed, P):
    n = len(pts)
    g = (lambda i: pts[i % n]) if closed else (lambda i: pts[max(0, min(n - 1, i))])
    d = 'M%.1f %.1f' % P(g(0))
    last = n if closed else n - 1
    for i in range(last):
        p0, p1, p2, p3 = g(i - 1), g(i), g(i + 1), g(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += 'C%.1f %.1f %.1f %.1f %.1f %.1f' % (P(c1) + P(c2) + P(p2))
    return d + ('Z' if closed else '')


def year_bucket(r):
    dl, st = r['deadline'], r['stage']
    if 'сдан' in dl or st.startswith('сдан'):
        return 'now'
    ys = [int(y) for y in re.findall(r'20\d\d', dl)]
    if not ys:
        return 'ann'
    y = min(ys)
    return 'now' if y <= 2026 else ('y27' if y == 2027 else 'y28')


def when_text(r):
    if 'сдан' in r['deadline'] or r['stage'].startswith('сдан'):
        return 'сдан'
    if r['deadline']:
        return r['deadline']
    return 'анонс' if 'анонс' in r['stage'] else 'уточняется'


def build(root):
    rows = list(csv.DictReader((root / 'data/doma.csv').open(encoding='utf-8-sig'), delimiter=';'))
    extra = {}
    for r in rows:
        r['class_final'] = r['class']
        lp = num(r['lot_min_price'])
        extra[r['slug']] = {'price_median_m2': r['lots_median_m2'] or r['price_median_m2'], 'lots_count': r['lots'],
                            'lot_min_area': r['lot_min_m2'], 'lot_min_price_mln': fmt(lp / 1e6, 1) if lp else '',
                            'checked': r['lots_date']}
    notes = {k: v for k, v in json.loads((root / 'tools/doma.json').read_text()).items() if not k.startswith('_')}
    geo_src = (root / 'nota-karta-zhk.html').read_text()
    D, M, W = grab(geo_src, 'DISTRICTS'), grab(geo_src, 'MKAD'), grab(geo_src, 'W')

    # --- геометрия и масштаб
    xs = [p[0] for p in M]
    ys = [p[1] for p in M]
    x0, x1, y0, y1 = min(xs) - 1.5, max(xs) + 1.5, min(ys) - 1.2, max(ys) + 1.2
    INSET = 250

    def P(p):
        return (INSET + (p[0] - x0) * S, (p[1] - y0) * S)

    Wd, Hd = INSET + (x1 - x0) * S, (y1 - y0) * S

    # --- дома и слаги
    items, used = [], {}
    for r in rows:
        items.append((r['slug'], r))  # слаг — из базы, одинаковый везде
    doma_slug = {}
    for s_, cfg in notes.items():
        if any(slug == s_ for slug, _ in items):
            doma_slug[s_] = s_

    # --- врезка для Рублёвки и Сколково
    outs = [proj(num(r['lat']), num(r['lon'])) for _, r in items if r['okrug'] in OUT]
    bx0, bx1 = min(p[0] for p in outs), max(p[0] for p in outs)
    by0, by1 = min(p[1] for p in outs), max(p[1] for p in outs)
    IN_X, IN_Y, IN_W, IN_H = 14, 40, INSET - 40, 200
    kin = min((IN_W - 30) / max(bx1 - bx0, .1), (IN_H - 30) / max(by1 - by0, .1))

    def Pin(p):
        return (IN_X + 15 + (p[0] - bx0) * kin, IN_Y + 15 + (p[1] - by0) * kin)

    svg = [f'<svg viewBox="0 0 {Wd:.0f} {Hd:.0f}" role="img" aria-label="Карта Москвы: {len(items)} новых домов базы NOTA">',
           f'<rect width="{Wd:.0f}" height="{Hd:.0f}" class="k-bg"/>']
    for d in D:
        for ring in d['r']:
            svg.append('<path d="M' + 'L'.join('%.1f %.1f' % P(p) for p in ring) + 'Z" class="k-d"/>')
    for p in W['parks'].values():
        svg.append(f'<path d="{smooth_path(p, True, P)}" class="k-park"/>')
    svg.append(f'<path d="{smooth_path(W["moskva"], False, P)}" class="k-river"/>')
    svg.append(f'<path d="{smooth_path(W["yauza"], False, P)}" class="k-river k-yauza"/>')
    for k, v in W['rings'].items():
        svg.append(f'<path d="{smooth_path(v, k != "Бульварное", P)}" class="k-ring"/>')
    svg.append(f'<path d="{smooth_path(M, True, P)}" class="k-ring k-mkad"/>')
    t = P((max(p[0] for p in W['rings']['ТТК']) + .4, 0.2))
    svg.append(f'<text x="{t[0]:.0f}" y="{t[1]:.0f}" class="k-lbl">ТТК</text>')
    t = P((max(xs) + .3, 3))
    svg.append(f'<text x="{t[0]:.0f}" y="{t[1]:.0f}" class="k-lbl">МКАД</text>')
    svg.append(f'<rect x="{IN_X}" y="{IN_Y}" width="{IN_W}" height="{IN_H}" class="k-inset"/>')
    svg.append(f'<text x="{IN_X}" y="{IN_Y - 10}" class="k-lbl">РУБЛЁВКА · СКОЛКОВО</text>')

    dots, data, lis = [], [], []
    for i, (slug, r) in enumerate(items):
        ck = CKEY[r['class_final']]
        u, pk, pf = num(r['units_total']), num(r['parking']), num(r['price_from_m2'])
        yb = year_bucket(r)
        form = ' '.join(x for x in (('pent' if r['penthouse_flag'] == 'да' else ''), ('club' if (u or 999) <= 100 else '')) if x)
        p = Pin(proj(num(r['lat']), num(r['lon']))) if r['okrug'] in OUT else P(proj(num(r['lat']), num(r['lon'])))
        name = r['name'].split(' (')[0]
        ok_, rk = slugify(r['okrug']), ('' if r['okrug'] in OUT else slugify(r['district']))
        geo_attr = f' data-o="{ok_}" data-r="{rk}"'
        dots.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{R_DOT[ck]}" class="kd {ck}" data-i="{i}" data-c="{ck}" data-y="{yb}" data-f="{form}"{geo_attr}><title>{e(name)}</title></circle>')

        x = extra.get(slug, {})
        pmed = num(x.get('price_median_m2', '') or '')
        img = (root / 'img/doma' / f'{slug}.jpg').exists()
        dev = r['developer'] or 'застройщик не указан'
        stage = r['stage'] + (f', срок — {r["deadline"]}' if r['deadline'] and r['deadline'] != 'сдан' else '')
        if x.get('summary'):
            summ = x['summary']
        elif slug in doma_slug:
            summ = notes[doma_slug[slug]]['note']
        else:
            bits = [f'{CLS[r["class_final"]]} от {dev}, {r["district"]}.']
            if u:
                word = 'лотов' if r['type'] == 'апартаменты' else 'квартир'
                bits.append(f'{fmt(u)} {word}' + (f', {fmt(pk)} машиномест — {fmt(pk / u, 2)} на квартиру.' if pk else ', число машиномест застройщик не раскрыл.'))
            if r['type'] and r['type'] != 'квартиры':
                bits.append(f'Формат: {r["type"]}.')
            if r['penthouse_flag'] == 'да':
                bits.append('Есть пентхаусы.')
            summ = ' '.join(bits)
        facts = [('Адрес', r['address']), ('Застройщик', dev), ('Класс', CLS[r['class_final']]), ('Стадия', stage),
                 ('Квартир', fmt(u) if u else 'нет данных'),
                 ('Машиномест на квартиру', fmt(pk / u, 2) if (u and pk) else 'нет данных')]
        if r.get('school_min'):
            t = f'ближайшая школа — {r["school_min"]} мин'
            t += f', с отметкой NOTA — {r["marked_min"]} мин' if r.get('marked_min') else ', с отметкой NOTA в получасе нет'
            facts.append(('До школы пешком', t))
        if pf:
            facts.append(('Цена от', f'{fmt(pf / 1000)} тыс ₽ за м²'))
        if pmed:
            facts.append(('Медиана', f'{fmt(pmed / 1000)} тыс ₽ за м²'))
        fact_html = ''.join(f'<div><dt>{a}</dt><dd>{e(b)}</dd></div>' for a, b in facts)
        pic = f'<div class="hs-img"><img src="img/doma/{slug}.jpg" alt="{e(name)}" loading="lazy"></div>' if img else ''
        price_cell = f'от {fmt(pf / 1000)} тыс/м²' if pf else 'по запросу'
        lis.append(
            f'<article class="hs" id="h-{slug}" data-i="{i}" data-c="{ck}" data-y="{yb}" data-f="{form}"{geo_attr}>'
            f'<button class="hs-row" type="button" aria-expanded="false"><span class="hs-n"><b>{e(name)}</b><small>{e(dev)}</small></span>'
            f'<span class="hs-c">{CLS[r["class_final"]]}</span><span class="hs-d">{e(r["district"])}</span>'
            f'<span class="hs-p">{price_cell}</span><span class="hs-w">{e(when_text(r))}</span></button>'
            f'<div class="hs-body" hidden>{pic}<div class="hs-main"><p class="hs-sum">{e(summ)}</p><dl class="hs-facts">{fact_html}</dl></div>'
            f'<div class="hs-side"></div></div></article>')
        rec = {'n': name, 'd': dev, 'c': CLS[r['class_final']], 'k': ck, 'ds': r['district'],
               'p': round(pf / 1000) if pf else None, 'w': when_text(r), 's': slug}
        if img: rec['img'] = 1
        if slug in doma_slug: rec['dm'] = doma_slug[slug]
        if x.get('lots_count') or x.get('lot_min_price_mln'):
            rec['x'] = [x.get('lots_count') or '', x.get('lot_min_area') or '', x.get('lot_min_price_mln') or '', x.get('checked') or '']
        data.append(rec)
    svg.append('<g id="kdots">' + ''.join(dots) + '</g></svg>')

    counts = {k: sum(1 for _, r in items if CKEY[r['class_final']] == k) for k in R_DOT}
    yc = {k: sum(1 for _, r in items if year_bucket(r) == k) for k in YB}
    pent = sum(1 for _, r in items if r['penthouse_flag'] == 'да')
    club = sum(1 for _, r in items if (num(r['units_total']) or 999) <= 100)

    def chip(g, k, t, on=False, extra=''):
        lab, _, cnt = t.partition(' · ')
        c = f' <span class="cn">{cnt}</span>' if cnt else ' <span class="cn"></span>'
        return f'<button class="chip" type="button" data-g="{g}" data-k="{k}"{extra} aria-pressed="{"true" if on else "false"}"><span class="cl">{lab}</span>{c}</button>'

    oc = {o: sum(1 for _, r in items if r['okrug'] == o) for o in OKR}
    dist = {}
    for _, r in items:
        if r['okrug'] not in OUT:
            dist.setdefault(r['okrug'], {}).setdefault(r['district'], 0)
            dist[r['okrug']][r['district']] += 1
    rgrp = ''.join(
        f'<div class="chips kr" data-for="{slugify(o)}" hidden>' + chip('r', 'all', 'Все районы', True, f' data-o="{slugify(o)}"')
        + ''.join(chip('r', slugify(d), f'{d} · {n}', False, f' data-o="{slugify(o)}"') for d, n in sorted(dist[o].items()))
        + '</div>' for o in OKR if o in dist)
    geo_filters = ('<div class="chipgrp"><span class="lb">Округ и район</span><div class="chips">' + chip('o', 'all', 'Вся карта', True)
                   + ''.join(chip('o', slugify(o), f'{o} · {oc[o]}') for o in OKR if oc[o]) + '</div>' + rgrp + '</div>')

    filters = ('<div class="chipgrp"><span class="lb">Класс дома</span><div class="chips">' + chip('c', 'all', 'Все классы', True)
               + ''.join(chip('c', k, f'{t} · {counts[k]}') for k, t in [('biz', 'Бизнес'), ('prem', 'Премиум'), ('elit', 'Элит'), ('dlx', 'Делюкс')])
               + '</div></div><div class="chipgrp"><span class="lb">Когда ключи</span><div class="chips">' + chip('y', 'all', 'Любой срок', True)
               + ''.join(chip('y', k, f'{YB[k]} · {yc[k]}') for k in YB if yc[k])
               + '</div></div><div class="chipgrp"><span class="lb">Формат</span><div class="chips">' + chip('f', 'all', 'Любой формат', True)
               + chip('f', 'pent', f'С пентхаусами · {pent}') + chip('f', 'club', f'До 100 квартир · {club}') + '</div></div>' + geo_filters)
    n = len(items)
    main = f'''<main>
<section class="first tight-b"><div class="wrap">
 <p class="ttl">Карта объектов</p>
 <h1>{n} новых домов на одной карте</h1>
 <p class="lead">Новые дома от бизнес-класса и выше: старая Москва, Сколково и Рублёвка. Наведите на точку, чтобы увидеть дом, нажмите — откроется его карточка в списке ниже. Фильтры меняют и карту, и список.</p>
</div></section>

<section class="tight first-content kscreen"><div class="wrap kmap">
 <div class="kmap-l">
  {filters}
  <p class="hint"><a href="#spisok">К списку домов</a> · <button class="linkbtn" type="button" data-reset>Сбросить фильтры</button></p>
 </div>
 <div class="kmap-r">
  <div class="map" id="kmap">{"".join(svg)}<div class="kt" id="kt" hidden></div></div>
  <div class="legend"><span><i class="biz"></i>Бизнес</span><span><i class="prem"></i>Премиум</span><span><i class="elit"></i>Элит</span><span><i class="dlx"></i>Делюкс</span><span class="lg-note">Точки стоят по адресам из базы.</span></div>
 </div>
</div></section>

<section class="tight" id="spisok"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Список домов</p><h2 style="margin-top:20px">Дома по вашим фильтрам</h2></div>
  <div><p class="lede">Нажмите на дом, чтобы раскрыть карточку: коротко о доме, примеры стоимости и что сейчас в продаже. Актуальные лоты пришлём по запросу — прайсы меняются каждую неделю.</p></div>
 </div>
 <div class="hs-bar"><span id="kcnt">Показано {n} из {n}</span><button class="linkbtn" type="button" data-reset>Сбросить фильтры</button></div>
 <div class="hs-head"><span>Дом и застройщик</span><span>Класс</span><span>Район</span><span>Цена</span><span>Ключи</span></div>
 <div class="hs-list" id="klist">
{chr(10).join(lis)}
 </div>
 <p class="hint">Данные базы NOTA на сентябрь 2026: классы, адреса, число квартир и машиномест, стадии и цены «от» — из каталогов и проектных деклараций. Если чего-то нет, застройщик это не раскрыл.</p>
</div></section>

<div class="modal" id="kmdl" hidden>
 <div class="modal-bg" data-close></div>
 <div class="modal-in" role="dialog" aria-modal="true" aria-labelledby="kmdl-h">
  <button class="modal-x" type="button" data-close aria-label="Закрыть">×</button>
  <p class="ttl">Актуальное предложение</p>
  <h3 id="kmdl-h">Дом</h3>
  <p style="margin-top:12px;color:var(--ink-2);font-size:15px">Пришлём, что в продаже сейчас: минимальный лот, планировки, цены и условия оплаты. Обычно в тот же день.</p>
  <form novalidate class="cform" style="margin-top:14px;box-shadow:none">
   <label class="fl-l">Как к вам обращаться<input type="text" autocomplete="name" placeholder="Имя"></label>
   <label class="fl-l">Телефон или ник в Telegram / MAX<input type="text" placeholder="+7 … или @ник"></label>
   <label class="fl-l">Что важно<textarea placeholder="Площадь, этаж, бюджет — если хотите уточнить"></textarea></label>
   <label class="consent"><input type="checkbox"><span>Согласен на обработку персональных данных и прочитал <a href="politika.html">политику конфиденциальности</a>.</span></label>
   <div class="send"><button class="btn" type="button">Получить предложение</button></div>
  </form>
 </div>
</div>
<script type="application/json" id="kdata">{json.dumps(data, ensure_ascii=False)}</script>
</main>'''
    kp = root / 'karta.html'
    s = kp.read_text()
    a = s.index('<main>')
    b = s.index('</main>') + len('</main>')
    kp.write_text(s[:a] + main + s[b:])
    print('карта: домов', n, '· с картинкой', sum(1 for d in data if d.get('img')), '· со срезом лотов', sum(1 for v in extra.values() if v['lots_count']))
