"""Разбор «Школа как архитектура»: перенос страницы из чата школ (артефакт «Школа как архитектура») на сайт.
Запуск: python3 tools/import_arhitektura.py <путь к HTML артефакта>
Пишет razbory/shkola-kak-arhitektura/index.html (светлая страница в оформлении сайта) и фото в img/shkoly-arh/.
Фото — Wikimedia Commons, свободные лицензии: подпись с автором и лицензией остаётся под каждым кадром и в источниках.
Повторный запуск нужен, только если в чате школ обновили артефакт."""
import base64, html, io, json, pathlib, re, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = '../../'
e = html.escape
TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','sch','','y','','e','yu','ya']))

def slug(t):
    t = ''.join(TR.get(c, c) for c in t.lower())
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:48]

SEEN = {}

def save_img(b64, name):
    """Сохраняет кадр; один и тот же кадр (мозаика и карточка) пишется один раз."""
    if b64 in SEEN: return SEEN[b64]
    d = ROOT / 'img/shkoly-arh'; d.mkdir(parents=True, exist_ok=True)
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
    if im.width > 960:
        im = im.resize((960, round(im.height * 960 / im.width)), Image.LANCZOS)
    p = d / f'{name}.jpg'
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=80, progressive=True, optimize=True)
    if not p.exists() or p.read_bytes() != buf.getvalue():
        p.write_bytes(buf.getvalue())
    SEEN[b64] = (f'img/shkoly-arh/{name}.jpg', im.width, im.height)
    return SEEN[b64]

def txt(h):
    return html.unescape(re.sub(r'<[^>]+>', '', h)).strip()

def main(src):
    s = pathlib.Path(src).read_text(encoding='utf-8')
    sid = {}
    ap = ROOT / 'data/shkoly-arhitektura.json'
    if ap.exists():
        sid = {a['name']: a.get('sid', '') for a in json.loads(ap.read_text())}
    dek = txt(re.search(r'<p class="dek">([\s\S]*?)</p>', s).group(1))
    lead = [m for m in re.findall(r'<p>([\s\S]*?)</p>', re.search(r'<div class="lead">([\s\S]*?)</div>', s).group(1))]
    lead = [re.sub(r'<a href="[^"]*">([\s\S]*?)</a>', lambda m: f'<a href="{R}reytingi/shkoly-moskvy/">{m.group(1)}</a>', p) for p in lead]
    # разделы
    secs = []
    for sm in re.finditer(r'<section><div class="sec-head"><div class="eyebrow">([^<]*)</div><h2>([^<]*)</h2>\s*<p class="small muted">([^<]*)</p></div>\s*<div class="archlist">([\s\S]*?)</div></section>', s):
        eyebrow, h2, sub, body = sm.groups()
        cards = []
        for cm in re.finditer(r'<div class="arch-i">([\s\S]*?)</div></div>\s*(?=<div class="arch-i">|$)', body + '\n'):
            c = cm.group(1)
            name = txt(re.search(r'<div class="arch-h"><b>([\s\S]*?)</b>', c).group(1))
            tagm = re.search(r'<span class="tag">([^<]*)</span>', c)
            metas = [txt(x) for x in re.findall(r'<div class="arch-meta">([\s\S]*?)</div>', c)]
            note = txt(re.search(r'<div class="arch-n">([\s\S]*?)</div>', c).group(1))
            im = re.search(r'<img src="data:image/\w+;base64,([A-Za-z0-9+/=]+)" alt="([^"]*)"', c)
            if im:
                path, w, h = save_img(im.group(1), slug(name))
                cap = re.search(r'<figcaption>([\s\S]*?)</figcaption>', c).group(1)
                cap = re.sub(r'<a href="([^"]+)">', r'<a href="\1" rel="nofollow noopener">', cap)
                ph = (f'<figure class="arh-ph"><img src="{R}{path}" alt="{e(im.group(2))}" loading="lazy" width="{w}" height="{h}">'
                      f'<figcaption>{cap}</figcaption></figure>')
            else:
                yr = re.search(r'<div class="arch-ph none"[^>]*><span>([^<]*)</span>', c)
                ph = f'<div class="arh-ph none" aria-hidden="true"><span>{e(yr.group(1) if yr else "")}</span><em>свободного фото пока нет</em></div>'
            tag = ''
            if tagm:
                t = tagm.group(1); k = sid.get(name)
                tag = (f'<a class="tag mark" href="{R}reytingi/shkoly-moskvy/#s-{k}">{e(t)}</a>' if k else f'<span class="tag mark">{e(t)}</span>')
            cards.append(f'''  <article class="arh-i" id="a-{slug(name)}">
   {ph}
   <div class="arh-b"><h3>{e(name)}</h3>{tag}{''.join(f'<p class="arh-m">{e(m)}</p>' for m in metas)}<p class="arh-n">{e(note)}</p></div>
  </article>''')
        secs.append((eyebrow, h2, sub, cards))
    # мозаика
    mos = re.search(r'<figure class="mosaic"[^>]*>([\s\S]*?)</figure>', s).group(1)
    mimgs = []
    for i, (b64, alt) in enumerate(re.findall(r'<img src="data:image/\w+;base64,([A-Za-z0-9+/=]+)" alt="([^"]*)">', mos), 1):
        path, w, h = save_img(b64, f'm{i}-{slug(alt)}')
        mimgs.append(f'<img src="{R}{path}" alt="{e(alt)}" width="{w}" height="{h}">')
    mcap = txt(re.search(r'<p class="mosaic-cap">([\s\S]*?)</p>', s).group(1))
    n_all = sum(len(c) for *_, c in secs)
    foot = re.search(r'<footer>([\s\S]*?)</footer>', s).group(1)
    srcs = txt(re.findall(r'<p class="small">([\s\S]*?)</p>', foot)[0])
    lic = re.findall(r'<p class="tiny muted">([\s\S]*?)</p>', foot)[0]
    lic = re.sub(r'<a href="([^"]+)">', r'<a href="\1" rel="nofollow noopener">', lic)

    sec_html = []
    for i, (eyebrow, h2, sub, cards) in enumerate(secs):
        sec_html.append(f'''<section class="arh-sec{' method' if i % 2 == 0 else ''}" id="{slug(eyebrow)}"><div class="wrap">
 <div class="two">
  <div><p class="ttl">{e(eyebrow)} · {len(cards)}</p><h2 style="margin-top:20px">{e(h2)}</h2></div>
  <div><p class="lede">{e(sub)}</p></div>
 </div>
 <div class="arh-list">
{chr(10).join(cards)}
 </div>
</div></section>''')
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': 'Школа как архитектура: школьные здания Москвы, которые стоит увидеть',
          'dateModified': '2026-09-23', 'inLanguage': 'ru', 'author': {'@type': 'Organization', 'name': 'NOTA'}, 'publisher': {'@type': 'Organization', 'name': 'NOTA'}}
    desc = f'{n_all} школьных зданий Москвы и рядом с ней с известным автором — от конструктивизма 1930-х до новых кампусов: «Летово», гимназия Примакова, Пятьдесят седьмая школа, № 1535 и другие.'
    page = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<title>Школа как архитектура: {n_all} школьных зданий Москвы, которые стоит увидеть — NOTA</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light only">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{R}css/nota.css">
<link rel="icon" type="image/svg+xml" href="{R}favicon.svg">
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="Школа как архитектура — NOTA">
<meta property="og:image" content="../../img/22-shkola.jpg">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body class="inner">
<header class="top solid" id="top-bar"></header>
<main>
<section class="first tight-b"><div class="wrap">
 <p class="crumbs"><a href="{R}razbory.html">Разборы</a> <span>/</span> Школа как архитектура</p>
 <p class="ttl">Разбор · архитектура</p>
 <h1>Школа как архитектура</h1>
 <p class="lead">{e(dek)}</p>
</div></section>

<section style="padding-top:0"><div class="wrap">
 <figure class="arh-mosaic">{''.join(mimgs)}</figure>
 <p class="hint">{e(mcap)}</p>
</div></section>

<section class="tight"><div class="wrap two">
 <div><p class="ttl">На заметку:</p></div>
 <div>{''.join(f'<p class="lede" style="margin-bottom:16px">{p}</p>' for p in lead)}</div>
</div></section>

{chr(10).join(sec_html)}

<section><div class="wrap two">
 <div><p class="ttl">Источники</p><h2 style="margin-top:20px">Откуда здания<br>и фотографии</h2></div>
 <div>
  <p class="lede">{e(srcs)}</p>
  <p class="hint">{lic}</p>
  <div class="btns"><a class="btn" href="{R}reytingi/shkoly-moskvy/">Школы Москвы с нашей отметкой</a> <a class="btn btn-l" href="{R}podbor.html">Подобрать дом рядом со школой</a></div>
 </div>
</div></section>
</main>
<footer></footer>
<script src="{R}js/nota.js"></script>
</body>
</html>
'''
    out = ROOT / 'razbory/shkola-kak-arhitektura/index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print('архитектура школ:', n_all, 'зданий,', len(secs), 'раздела, мозаика', len(mimgs), '→', out.relative_to(ROOT))

if __name__ == '__main__':
    main(sys.argv[1])
