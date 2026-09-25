#!/usr/bin/env python3
"""Сборка прототипа «Прохорова Select»: карта из геометрии NOTA, объекты на реальных домах,
векторный логотип, демо-планировки. Запуск: python3 build_ps.py"""
import csv, json, re, base64, random, io, glob, os
from pathlib import Path
from PIL import Image

H = Path('.')
random.seed(314)

# ---------- геометрия карты (км от Кремля: x — восток, y — юг) ----------
src = (H / 'nota/nota-karta-zhk.html').read_text()
def grab(s, name):
    i = s.index(name + '=') + len(name) + 1
    op = s[i]; cl = {'[': ']', '{': '}'}[op]; dep = 0
    for j in range(i, len(s)):
        if s[j] == op: dep += 1
        elif s[j] == cl:
            dep -= 1
            if dep == 0: return json.loads(s[i:j + 1])
D, M, W = grab(src, 'DISTRICTS'), grab(src, 'MKAD'), grab(src, 'W')
LAT0, LON0, KX, KY = 55.75297, 37.61758, 62.65, 111.2
def proj(lat, lon): return ((lon - LON0) * KX, (LAT0 - lat) * KY)

# ---------- объекты ----------
rows = list(csv.DictReader((H / 'nota/pick.csv').open(encoding='utf-8'), delimiter=';'))
RATE = {'премиум': (1.15, 1.9), 'элитный': (1.9, 3.0), 'делюкс': (3.0, 4.6)}   # млн ₽ за м²
CLS = {'премиум': 'Премиум', 'элитный': 'Элит', 'делюкс': 'Делюкс'}
ST = ['без отделки', 'white box', 'с отделкой от застройщика', 'дизайнерский ремонт', 'с мебелью']
objs = []
for r in rows:
    x, y = proj(float(r['lat']), float(r['lon']))
    lo, hi = RATE[r['class']]
    m = random.choice([88, 96, 104, 112, 118, 126, 134, 142, 150, 158, 168, 176, 188, 204, 218, 236, 260])
    p = max(50, round(m * random.uniform(lo, hi) / 0.5) * 0.5)
    ff = int(r['floors'] or random.choice([7, 9, 12, 14, 18]))
    objs.append(dict(slug=r['slug'], n=r['name'], d=r['district'], a=r['address'], c=CLS[r['class']],
                     h=(r['ceilings_m'] + ' м') if r['ceilings_m'] else '', m=m, r=1 if m < 100 else 2 if m < 140 else 3 if m < 200 else 4,
                     f=random.randint(2, max(2, ff - 1)), ff=ff, p=p, s=random.choices('wng', [6, 3, 2])[0], st=random.choice(ST), kx=x, ky=y))

# два «полных» объекта — первые в порядке: новый и подешевле
objs.sort(key=lambda o: ({'n': 0, 'w': 1, 'g': 2}[o['s']], o['p']))
objs[0].update(t='Гостиная с камином, спальни окнами во двор. Дом после реставрации, 4 квартиры на этаже, лифт и консьерж. Документы проверены, перепланировка узаконена.')
objs[1].update(t='Кухня-гостиная 48 м² с выходом на террасу, две спальни с гардеробными, окна на закрытый двор. Паркинг на два места входит в цену.')

# ---------- масштаб и SVG ----------
xs = [o['kx'] for o in objs]; ys = [o['ky'] for o in objs]
x0, x1 = min(xs) - 2.5, max(xs) + 2.5
y0, y1 = min(ys) - 2.0, max(ys) + 2.0
Wd = 800; S = Wd / (x1 - x0); Hd = round((y1 - y0) * S)
def P(p): return (round((p[0] - x0) * S, 1), round((p[1] - y0) * S, 1))
def smooth(pts, closed):
    n = len(pts)
    g = (lambda i: pts[i % n]) if closed else (lambda i: pts[max(0, min(n - 1, i))])
    d = 'M%.1f %.1f' % P(g(0))
    for i in range(n if closed else n - 1):
        p0, p1, p2, p3 = g(i - 1), g(i), g(i + 1), g(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += 'C%.1f %.1f %.1f %.1f %.1f %.1f' % (P(c1) + P(c2) + P(p2))
    return d + ('Z' if closed else '')
svg = [f'<svg id="map" viewBox="0 0 {Wd} {Hd}" role="img" aria-label="Схема Москвы с объектами">',
       f'<rect width="{Wd}" height="{Hd}" class="k-bg"/>']
for d in D:
    for ring in d['r']:
        svg.append('<path d="M' + 'L'.join('%.1f %.1f' % P(p) for p in ring) + 'Z" class="k-d"/>')
for p in W['parks'].values(): svg.append(f'<path d="{smooth(p, True)}" class="k-park"/>')
svg.append(f'<path d="{smooth(W["moskva"], False)}" class="k-river"/>')
svg.append(f'<path d="{smooth(W["yauza"], False)}" class="k-river k-yauza"/>')
for k, v in W['rings'].items(): svg.append(f'<path d="{smooth(v, k != "Бульварное")}" class="k-ring"/>')
svg.append(f'<path d="{smooth(M, True)}" class="k-ring k-mkad"/>')
# подписи районов — только тех, где есть объекты, в центре их полигона
have = {o['d'] for o in objs}
for d in D:
    if d['n'] in have:
        ring = max(d['r'], key=len)
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        px, py = P((cx, cy))
        if 0 < px < Wd and 0 < py < Hd:
            svg.append(f'<text class="label" x="{px:.0f}" y="{py:.0f}" text-anchor="middle">{d["n"]}</text>')
t = P((max(p[0] for p in W['rings']['ТТК']) + .3, 0.2)); svg.append(f'<text class="label" x="{t[0]:.0f}" y="{t[1]:.0f}">ТТК</text>')
t = P((max(p[0] for p in W['rings']['Садовое']) + .3, -1.2)); svg.append(f'<text class="label" x="{t[0]:.0f}" y="{t[1]:.0f}">Садовое</text>')
svg.append('<g id="pts"></g></svg>')
MAP_SVG = ''.join(svg)

# ---------- картинки ----------
def b64img(path, w=640, q=70):
    im = Image.open(path).convert('RGB'); im.thumbnail((w, w))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
for i, o in enumerate(objs):
    o['id'] = i; o['x'], o['y'] = P((o['kx'], o['ky']))
    o['img'] = b64img(H / 'nota/doma' / f"{o['slug']}.jpg")
    del o['kx'], o['ky']
def g(pat):
    f = glob.glob(f'gen/*{pat}*'); return b64img(f[0], 900, 68) if f else None
gen = glob.glob('gen/*')
objs[0]['pic1'], objs[0]['pic2'] = g('interior-photograph-of-a.'), g('wide-interior'); objs[0]['cap2'] = 'Спальня'
objs[1]['pic1'], objs[1]['pic2'] = g('interior-photograph-of-a34'), g('exterior'); objs[1]['cap2'] = 'Двор'
KEYS = g('detail') or ''
FIRE = g('interior-photograph-of-a.') or ''
BED = g('wide-interior') or ''

# ---------- планировки (вымышленные) ----------
def plan(rooms, W_, H_):
    out = [f'<svg viewBox="-6 -6 {W_ + 12} {H_ + 12}" class="plansvg" role="img" aria-label="Планировка">',
           f'<rect x="0" y="0" width="{W_}" height="{H_}" class="pl-out"/>']
    for x, y, w, h, name, area in rooms:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="pl-room"/>')
        out.append(f'<text x="{x + w / 2}" y="{y + h / 2 - 3}" class="pl-t" text-anchor="middle">{name}</text>')
        out.append(f'<text x="{x + w / 2}" y="{y + h / 2 + 10}" class="pl-a" text-anchor="middle">{area} м²</text>')
    return ''.join(out) + '</svg>'
objs[0]['plan'] = plan([(0, 0, 150, 90, 'Гостиная с камином', 42), (150, 0, 90, 90, 'Кухня-столовая', 24), (240, 0, 60, 90, 'Прихожая', 14),
                        (0, 90, 100, 70, 'Спальня', 22), (100, 90, 70, 70, 'Спальня', 16), (170, 90, 70, 70, 'Спальня', 16),
                        (240, 90, 60, 35, 'Ванная', 8), (240, 125, 60, 35, 'Ванная', 8)], 300, 160) if objs[0]['m'] >= 150 else \
    plan([(0, 0, 160, 90, 'Кухня-гостиная', 38), (160, 0, 80, 90, 'Спальня', 19), (240, 0, 60, 90, 'Прихожая', 12),
          (0, 90, 110, 60, 'Спальня', 18), (110, 90, 90, 60, 'Кабинет', 14), (200, 90, 50, 60, 'Ванная', 8), (250, 90, 50, 60, 'С/у', 6)], 300, 150)
objs[1]['plan'] = plan([(0, 0, 170, 100, 'Кухня-гостиная', 48), (170, 0, 70, 100, 'Терраса', 12), (240, 0, 60, 100, 'Прихожая', 12),
                        (0, 100, 110, 60, 'Спальня', 20), (110, 100, 40, 60, 'Гард.', 6), (150, 100, 100, 60, 'Спальня', 18), (250, 100, 50, 60, 'Ванная', 9)], 300, 160)

# ---------- логотип: вектор, цвета через CSS ----------
def logo_inline(cls):
    s = (H / 'logo-svg/prokhorova-select-light.svg').read_text()
    body = s[s.index('</defs>') + 7:s.rindex('</svg>')]
    body = body.replace('fill="#1F1B17"', 'class="lg-ink"').replace('fill="url(#bronze)"', 'class="lg-br"')
    vb = re.search(r'viewBox="([^"]+)"', s).group(1)
    return f'<svg class="{cls}" viewBox="{vb}" role="img" aria-label="Прохорова Select — private real estate">{body}</svg>'
def mark_inline(cls):
    s = (H / 'logo-svg/mark-light.svg').read_text()
    body = s[s.index('</defs>') + 7:s.rindex('</svg>')].replace('fill="url(#bronze)"', 'class="lg-br"')
    vb = re.search(r'viewBox="([^"]+)"', s).group(1)
    grad = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><linearGradient id="lg-grad" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" class="lg-s1"/><stop offset=".45" class="lg-s2"/><stop offset="1" class="lg-s3"/></linearGradient></defs></svg>')
    return grad + f'<svg class="{cls}" viewBox="{vb}" aria-hidden="true">{body}</svg>'

# ---------- сборка ----------
html = (H / 'site_src.html').read_text()
a, b = html.index('<!-- ============ КАРТА ============ -->'), html.index('<!-- ============ КОНТАКТЫ ============ -->')
html = html[:a] + (H / 'karta_section.html').read_text().replace('{{MAP_SVG}}', MAP_SVG) + html[b:]
a, b = html.index('/* ---------- объекты'), html.index('/* модалка */')
html = html[:a] + (H / 'karta_script.js').read_text().replace('{{OBJ_JSON}}', json.dumps(objs, ensure_ascii=False)) + '\n' + html[b:]
html = html.replace('{{KEYS}}', KEYS).replace('{{PHOTO_FIRE}}', FIRE).replace('{{PHOTO_BED}}', BED).replace('{{LOGO_INLINE}}', logo_inline('logo')).replace('{{MARK_INLINE}}', mark_inline('mark'))
(H / 'prokhorova-select.html').write_text(html)
print('ok', len(html) // 1024, 'KB;', len(objs), 'объектов;', 'gen:', len(gen))
