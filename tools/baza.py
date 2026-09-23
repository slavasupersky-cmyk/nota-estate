"""Выгрузка из мастер-базы ../nota-baza в data/ сайта — только публичные поля.
Запускается из build.py первым шагом; можно отдельно: python3 tools/baza.py
Путь к базе — переменная окружения NOTA_BAZA или папка nota-baza рядом с репозиторием.
Руками data/*.csv из этого списка не править: перезапишутся при сборке."""
import csv, io, os, pathlib, re, shutil
from collections import defaultdict

# рынок по стадии: где сейчас можно купить квартиру в доме
RYNOK = {'анонс': 'анонс', 'старт продаж': 'первичка', 'строится': 'первичка',
         'строится, есть сданные': 'первичка и вторичка', 'сдан, есть остатки': 'первичка и вторичка',
         'распродан': 'только вторичка'}
HIDE_STAGES = {'дубль'}  # строки-дубли держатся в базе ради связей, на сайт не идут
HIDE_TYPES = {'коттеджи', 'таунхаусы'}  # посёлки — отдельный рынок, на сайт не идут (решение Supersky 24.09); в базе остаются

CHECKS_PASPORT = ['01', '02', '03', '04', '05', '06', '07', '08', '09']

DOMA_COLS = ['slug', 'name', 'name_short', 'dev_id', 'developer', 'class', 'class_zayavlen', 'class_why', 'class_declared', 'class_disputed', 'okrug', 'district',
             'address', 'lat', 'lon', 'geo_precision', 'type', 'units_total', 'units_per_floor', 'floors', 'ceilings_m', 'parking',
             'stage', 'deadline_initial', 'deadline', 'price_from_m2', 'price_median_m2', 'price_check', 'penthouses', 'penthouse_flag',
             'architect', 'facade', 'energy_class', 'escrow', 'maintenance_rub_m2', 'website', 'sources', 'updated']
# вычисляемые колонки, которые добавляет выгрузка
CALC_COLS = ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'pasport', 'pasport_why',
             'school_min', 'school_name', 'nota_school_min', 'nota_school_name', 'nota_15', 'marked_min', 'marked_name', 'marked_20',
             'lots', 'lot_min_m2', 'lot_min_price', 'lots_median_m2', 'lots_date', 'has_foto', 'rynok']
PUBLIC = {
    'proverki.csv': ['slug', 'check', 'answer', 'value', 'source', 'checked'],
    'zastroyshchiki.csv': ['dev_id', 'name', 'erz_rating', 'erz_checked', 'sdano_3_goda', 'ostanovleno', 'bankrotstvo', 'sayt'],
    'shkoly.csv': ['school_id', 'name', 'official_name', 'category', 'tier', 'marked', 'index', 'grant', 'raex_msk_compete', 'raex_rf', 'vsosh_w', 'vsosh_p',
                   'price', 'why', 'zone', 'okrug', 'district', 'address', 'site', 'korpusov', 'lat', 'lon', 'geo_precision'],
    'kriterii.csv': None,
    'penthausy.csv': ['pent_id', 'slug', 'zhk', 'developer', 'okrug', 'district', 'address', 'count', 'area_m2', 'floor', 'price_total', 'price_m2', 'features', 'status', 'source', 'checked'],
    'oplata-skhemy.csv': ['scheme_id', 'dev_id', 'developer', 'slug', 'zhk', 'klass', 'tip', 'opisanie', 'stavka', 'srok', 'pv', 'vvod', 'skidka_100', 'ogranicheniya', 'source', 'deystvuet', 'checked'],
    'oplata-banki.csv': None,
    'oplata-tipy.csv': None,
    'itog.csv': None,
    'otkrytost-cen.csv': None,
}


def baza_path(root):
    return pathlib.Path(os.environ.get('NOTA_BAZA') or root.parent / 'nota-baza')


def read(p):
    if not p.exists():
        return []
    return list(csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';'))


def write(p, rows, cols):
    """Пишет CSV (UTF-8 с BOM, «;»), только если содержимое поменялось. Возвращает True, если записал."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, delimiter=';', extrasaction='ignore', lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    new = '﻿' + buf.getvalue()
    if p.exists() and p.read_text(encoding='utf-8') == new:
        return False
    p.write_text(new, encoding='utf-8')
    return True


def date_key(d):
    m = re.match(r'(\d\d)\.(\d\d)\.(\d{4})', d or '')
    return (m.group(3), m.group(2), m.group(1)) if m else ('', '', '')


def num(v):
    try:
        return float(str(v).replace(' ', '').replace(',', '.'))
    except ValueError:
        return None


RED = set()  # красная линия только по пометке «красная линия» в note
RED_MARKED = {'02', '06', '08'}  # 06 «нет» без пометки = рейтинг ЕРЗ ниже 3,0 → обычный минус
CHECK_NAMES = {}


def pasport(ans, notes, cls, tol):
    """Итог паспорта (метод 23.09): красная линия → «Без отметки»; иначе считаем минусы («нет»)
    среди проверок с данными и сравниваем с допуском класса из nota-baza/itog.csv."""
    red = [c for c in CHECKS_PASPORT if ans.get(c) == 'нет' and (c in RED or (c in RED_MARKED and 'красная линия' in notes.get(c, '')))]
    if red:
        return 'Без отметки', 'красная линия: ' + ', '.join(CHECK_NAMES.get(c, c) for c in red)
    known = [c for c in CHECKS_PASPORT if ans.get(c) in ('да', 'нет')]
    minus = [c for c in known if ans[c] == 'нет']
    t = tol.get(cls, {'otmetka_max_minus': '1', 'bez_otmetki_from_minus': '3', 'min_known': '4'})
    why = ('минусы: ' + ', '.join(CHECK_NAMES.get(c, c) for c in minus)) if minus else ''
    if len(known) < int(t['min_known']):
        return 'Присмотреться', 'мало данных: известно ' + str(len(known)) + ' из ' + str(len(CHECKS_PASPORT)) + (' · ' + why if why else '')
    if len(minus) >= int(t['bez_otmetki_from_minus']):
        return 'Без отметки', why
    if len(minus) <= int(t['otmetka_max_minus']):
        return 'Отметка', why
    return 'Присмотреться', why


def export(root, verbose=True):
    B = baza_path(root)
    if not (B / 'doma.csv').exists():
        print('база не найдена:', B, '— беру data/ как есть')
        return False
    D = root / 'data'
    changed = []

    doma = [d for d in read(B / 'doma.csv') if d.get('stage') not in HIDE_STAGES and d.get('type') not in HIDE_TYPES]
    krit = read(B / 'kriterii.csv')
    CHECK_NAMES.update({k['id']: k['proverka'].lower() for k in krit})
    tol = {x['class']: x for x in read(B / 'itog.csv')}

    # свежий ответ по каждой проверке
    latest = {}
    prov = read(B / 'proverki.csv')
    for x in prov:
        k = (x['slug'], x['check'])
        if k not in latest or date_key(x['checked']) >= date_key(latest[k]['checked']):
            latest[k] = x
    live = {d['slug'] for d in doma}
    prov_pub = sorted((v for v in latest.values() if v['slug'] in live), key=lambda x: (x['slug'], x['check']))

    # школы и маршруты
    shk = {s['school_id']: s for s in read(B / 'shkoly.csv')}
    korp = {k['school_id']: k for k in read(B / 'shkoly-korpusa.csv')}
    routes = defaultdict(list)
    for m in read(B / 'marshruty.csv'):
        routes[m['slug']].append(m)

    # последний срез лотов
    loty_files = sorted((B / 'loty').glob('*.csv')) if (B / 'loty').exists() else []
    loty, loty_date = {}, ''
    if loty_files:
        f = loty_files[-1]
        loty_date = '.'.join(reversed(f.stem.split('-')))
        loty = {x['slug']: x for x in read(f)}

    # картинки: foto/<slug>/cover.* → img/_src/doma/<slug>.<ext> (дальше ужимает images.py)
    src = root / 'img/_src/doma'
    src.mkdir(parents=True, exist_ok=True)
    foto = set()
    for d in sorted((B / 'foto').glob('*/')) if (B / 'foto').exists() else []:
        if not d.is_dir():
            continue
        cov = next((p for p in d.iterdir() if p.stem.lower() == 'cover' and p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')), None)
        if not cov:
            continue
        foto.add(d.name)
        dst = src / (d.name + cov.suffix.lower())
        if not dst.exists() or dst.stat().st_mtime < cov.stat().st_mtime:
            shutil.copy2(cov, dst)
            changed.append('img/_src/doma/' + dst.name)

    out = []
    for d in doma:
        r = {c: d.get(c, '') for c in DOMA_COLS}
        s = d['slug']
        ans = {c: latest[(s, c)]['answer'] for c in CHECKS_PASPORT if (s, c) in latest}
        for c in CHECKS_PASPORT:
            r['p' + c] = ans.get(c, '')
        notes = {c: latest[(s, c)].get('note', '') for c in CHECKS_PASPORT if (s, c) in latest}
        r['pasport'], r['pasport_why'] = pasport(ans, notes, d.get('class', ''), tol)

        rs = sorted(routes.get(s, []), key=lambda m: float(m['walk_min'] or 999))
        def nm(m):
            return shk[m['school_id']]['name'] if m['school_id'] in shk else korp.get(m['school_id'], {}).get('school', '')
        if rs:
            r['school_min'], r['school_name'] = rs[0]['walk_min'], nm(rs[0])
        nota = [m for m in rs if m['school_id'] in shk]
        if nota:
            r['nota_school_min'], r['nota_school_name'] = nota[0]['walk_min'], nm(nota[0])
        r['nota_15'] = sum(1 for m in nota if float(m['walk_min']) <= 15) if rs else ''
        marked = [m for m in nota if shk[m['school_id']]['marked'] == 'да']
        if marked:
            r['marked_min'], r['marked_name'] = marked[0]['walk_min'], nm(marked[0])
        r['marked_20'] = sum(1 for m in marked if float(m['walk_min']) <= 20) if rs else ''

        l = loty.get(s)
        if l:
            r.update(lots=l.get('lots', ''), lot_min_m2=l.get('lot_min_m2', ''), lot_min_price=l.get('lot_min_price', ''),
                     lots_median_m2=l.get('price_median_m2', ''), lots_date=loty_date)
        r['has_foto'] = 'да' if s in foto else ''
        r['rynok'] = RYNOK.get(d.get('stage', ''), 'первичка')
        out.append(r)

    if write(D / 'doma.csv', out, DOMA_COLS + CALC_COLS): changed.append('data/doma.csv')
    if write(D / 'proverki.csv', prov_pub, PUBLIC['proverki.csv']): changed.append('data/proverki.csv')
    for name, cols in PUBLIC.items():
        if name == 'proverki.csv':
            continue
        rows = read(B / name)
        if not rows:
            continue
        if write(D / name, rows, cols or list(rows[0])): changed.append('data/' + name)
    lpt = sorted((B / 'loty-po-tipam').glob('*.csv')) if (B / 'loty-po-tipam').exists() else []
    if lpt:
        rows = [x for x in read(lpt[-1]) if x.get('slug') in {d['slug'] for d in doma}]
        cols = [c for c in rows[0] if c not in ('primechanie',)] if rows else []
        if rows and write(D / 'loty-po-tipam.csv', rows, cols): changed.append('data/loty-po-tipam.csv')
    pub_routes = [dict(slug=m['slug'], school_id=m['school_id'], korpus_id=m['korpus_id'], walk_min=m['walk_min'], walk_m=m['walk_m'])
                  for s in sorted(routes) for m in sorted(routes[s], key=lambda m: float(m['walk_min']))]
    if write(D / 'marshruty.csv', pub_routes, ['slug', 'school_id', 'korpus_id', 'walk_min', 'walk_m']): changed.append('data/marshruty.csv')

    if verbose:
        cnt = defaultdict(int)
        for r in out:
            cnt[r['pasport']] += 1
        print(f'база → сайт: домов {len(out)}, проверок {len(prov_pub)}, паспорт ' +
              ', '.join(f'{k} {v}' for k, v in sorted(cnt.items())) +
              (f'; обновлено: {", ".join(changed)}' if changed else '; без изменений'))
    return True


if __name__ == '__main__':
    export(pathlib.Path(__file__).resolve().parent.parent)
