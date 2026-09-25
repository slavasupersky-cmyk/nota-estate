# Ищет свободные фото школьных зданий на Wikimedia Commons и складывает кандидатов
# в img/_src/shkoly-arh-kandidaty/<slug>/ + credits.tsv + obzor.html для просмотра.
import json, os, re, sys, time, html, urllib.parse, urllib.request

OUT = 'img/_src/shkoly-arh-kandidaty'
UA = {'User-Agent': 'NOTA-foto-shkol/1.0 (slavasupersky-cmyk.github.io)'}
MIN_W = 1000
PER_QUERY = 12

SCHOOLS = [
 ('shkola-letovo', 'Школа «Летово»', ['Letovo School', 'школа Летово Сосенское']),
 ('kurchatovskaya-shkola', 'Курчатовская школа', ['Курчатовская школа Москва', 'Kurchatov school Moscow', 'Сити Бэй школа']),
 ('shkola-548-tsaritsyno', 'Школа № 548 «Царицыно»', ['школа 548 Москва', 'Likhachova Prospekt school']),
 ('shkola-2070', 'Школа № 2070 им. Вартаняна', ['школа 2070 Коммунарка', 'Kommunarka school', 'школа Липовый парк Коммунарка']),
 ('oblastnaya-gimnaziya-im-e-m-primakova', 'Гимназия им. Примакова', ['гимназия Примакова', 'Primakov gymnasium Razdory']),
 ('horoshkola', 'Хорошкола', ['Хорошкола', 'Khoroshkola', 'Хорошевская гимназия Народного Ополчения']),
 ('mezhdunarodnaya-gimnaziya-skolkovo', 'Международная гимназия «Сколково»', ['International Gymnasium Skolkovo', 'гимназия Сколково']),
 ('wunderpark', 'Wunderpark International School', ['Wunderpark school', 'Вундерпарк школа']),
 ('skolka', 'Инновационная школа «Сколка»', ['школа Сколка', 'Skolkovo school Bolshoy boulevard', 'школа Сколково Большой бульвар']),
 ('pyatdesyat-sedmaya-shkola', 'Пятьдесят седьмая школа', ['Moscow school 57', 'школа 57 Малый Знаменский']),
 ('shkola-1535', 'Школа № 1535', ['школа 1535', 'Usacheva 50', 'образцовая школа Фрунзенского района']),
 ('shkola-1501', 'Школа № 1501', ['школа 1501', 'Тихвинский переулок 3']),
 ('shkola-pokrovskiy-kvartal', 'Покровский квартал', ['Bolshoy Kazenny 9', 'Елизаветинская гимназия Москва', 'Покровский квартал школа']),
 ('shkola-315', 'Школа № 315', ['Русаковская 10', 'школа 315 обсерватория', 'school 315 Moscow']),
 ('letovo-junior', 'Летово Джуниор', ['Летово Джуниор', 'Letovo Junior', 'школа проспект Вернадского 8Б']),
 ('horoshevskaya-progimnaziya', 'Хорошевская прогимназия', ['Хорошевская прогимназия', 'Маршала Тухачевского 45']),
 ('novyy-vzglyad', 'Школа «Новый взгляд»', ['Садовые кварталы школа', 'Sadovye Kvartaly school', 'Новый взгляд школа Хамовники']),
 ('tumo', 'TUMO Москва', ['TUMO Moscow', 'Мантулинская 7', 'Краснопресненский сахарорафинадный завод']),
 ('shkola-1249', 'Школа № 1249', ['School 1249', 'школа 1249 Чапаевский']),
 ('prokshino', 'Учебный центр в Прокшино', ['Прокшино школа', 'Prokshino school']),
 ('detsad-so-slonikami', 'Детский сад «со слониками»', ['детский сад Маршала Василевского', 'детский сад слоники Щукино']),
]

def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as e:
            err = e; time.sleep(2 + i * 3)
    raise err

def search(q):
    p = dict(action='query', format='json', generator='search', gsrnamespace=6,
             gsrsearch=q + ' filetype:bitmap', gsrlimit=PER_QUERY, prop='imageinfo',
             iiprop='url|size|extmetadata', iiurlwidth=1600)
    d = json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(p)))
    return list(d.get('query', {}).get('pages', {}).values())

def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()

os.makedirs(OUT, exist_ok=True)
rows, seen = [], set()
for slug, name, queries in SCHOOLS:
    d = os.path.join(OUT, slug); os.makedirs(d, exist_ok=True)
    n = 0
    for q in queries:
        try:
            pages = search(q)
        except Exception as e:
            print('  ! поиск не удался:', q, e); continue
        for pg in pages:
            ii = (pg.get('imageinfo') or [{}])[0]
            title = pg.get('title', '')
            if title in seen or ii.get('width', 0) < MIN_W:
                continue
            md = ii.get('extmetadata', {})
            lic = clean(md.get('LicenseShortName', {}).get('value'))
            if not lic or 'fair use' in lic.lower():
                continue
            seen.add(title); n += 1
            ext = '.png' if ii.get('thumburl', '').lower().endswith('.png') else '.jpg'
            fn = '%02d%s' % (n, ext)
            try:
                open(os.path.join(d, fn), 'wb').write(get(ii['thumburl']))
            except Exception as e:
                print('  ! не скачалось:', title, e); n -= 1; continue
            rows.append([slug, name, slug + '/' + fn, title.replace('File:', ''),
                         clean(md.get('Artist', {}).get('value')) or '—', lic,
                         ii.get('descriptionurl', ''), '%sx%s' % (ii.get('width'), ii.get('height'))])
            time.sleep(0.4)
    print('%-40s %d' % (name, n))

with open(os.path.join(OUT, 'credits.tsv'), 'w', encoding='utf-8') as f:
    f.write('slug\tшкола\tфайл\tфайл на Commons\tавтор\tлицензия\tстраница\tразмер оригинала\n')
    for r in rows: f.write('\t'.join(r) + '\n')

cards = ''.join(
    '<figure><img src="%s" loading="lazy"><figcaption><b>%s</b> · %s<br>%s · %s · <a href="%s">Commons</a></figcaption></figure>'
    % tuple(html.escape(x) for x in (r[2], r[1], r[2], r[4], r[5], r[6])) for r in rows)
open(os.path.join(OUT, 'obzor.html'), 'w', encoding='utf-8').write(
    '<!doctype html><meta charset="utf-8"><title>Кандидаты фото школ</title><style>'
    'body{font:14px -apple-system,Helvetica,Arial,sans-serif;margin:20px;background:#f2f3f4;color:#101317}'
    '@media(prefers-color-scheme:dark){body{background:#0d0f12;color:#e9ecef}a{color:#9bd}}'
    'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}'
    'img{width:100%;aspect-ratio:3/2;object-fit:cover;display:block}figure{margin:0}figcaption{font-size:12px;margin-top:4px}'
    '</style><h1>Кандидаты: ' + str(len(rows)) + ' фото</h1><main>' + cards + '</main>')
print('\nГотово:', len(rows), 'фото →', OUT + '/obzor.html')
