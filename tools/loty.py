"""Что в продаже по комнатности: data/loty-po-tipam.csv (выгрузка baza.py из nota-baza/loty-po-tipam/<дата>.csv, берётся самый свежий файл).
Готовит строки для раскрытой карточки дома на карте (karta.py) и для карточек домов doma/<slug>/ (doma.py).
Площадь — в м², цена — в млн ₽ без единиц в ячейке: единицы стоят в заголовке таблицы.
cena_ot — цена со скидкой застройщика, если он её показывает; cena_ot_bez_skidki — зачёркнутая."""
import csv, pathlib
from collections import defaultdict

ORDER = ['студия', '1', '2', '3', '4+', 'таунхаус', 'дом', 'участок']
LABEL = {'студия': 'Студии', '1': '1 комната', '2': '2 комнаты', '3': '3 комнаты', '4+': '4+ комнаты',
         'таунхаус': 'Таунхаусы', 'дом': 'Дома', 'участок': 'Участки'}
SRC = {'застройщик': 'сайт застройщика', 'застройщик/офиц.сайт': 'сайт застройщика', 'novostroev': 'novostroev.ru',
       'новострой-м': 'novostroy-m.ru', 'mskguru': 'mskguru.ru'}


def num(x):
    try:
        v = float(str(x).replace(' ', '').replace(',', '.'))
        return v if v > 0 else None
    except ValueError:
        return None


def fmt(n, d=0):
    s = f'{n:,.{d}f}'.replace(',', ' ').replace('.', ',')
    return s[:-2] if d == 1 and s.endswith(',0') else s


def money(v):
    """17 900 143 → («17,9», «млн»); 453 802 900 → («454», «млн»); 1 200 000 000 → («1,2», «млрд»)."""
    if v >= 1e9:
        return fmt(v / 1e9, 1), 'млрд'
    if v >= 1e8:
        return fmt(v / 1e6), 'млн'
    return fmt(v / 1e6, 1), 'млн'


def mln(v):
    """Цена в млн ₽ для ячейки: 17 900 143 → «17,9»; 453 802 900 → «454»; 9 436 581 085 → «9 437»."""
    return fmt(v / 1e6, 1) if v < 1e8 else fmt(v / 1e6).replace(' ', '\u00a0')


def price(lo, hi):
    if lo and hi and abs(hi - lo) >= 1e5:
        return f'{mln(lo)}–{mln(hi)}'
    if lo:
        return mln(lo) if hi else f'от {mln(lo)}'
    if hi:
        return f'до {mln(hi)}'
    return ''


def area(lo, hi):
    if lo and hi and hi - lo >= 0.1:
        return f'{fmt(lo, 1)}–{fmt(hi, 1)}'
    if lo:
        return fmt(lo, 1) if hi else f'от {fmt(lo, 1)}'
    if hi:
        return f'до {fmt(hi, 1)}'
    return ''


def source(s):
    s = (s or '').strip()
    if s.lower().startswith('cian'):
        return 'ЦИАН' + s[4:]
    return SRC.get(s, s)


def load(root):
    """slug → строки по типам в порядке студии → 4+ → дома и участки."""
    p = pathlib.Path(root) / 'data/loty-po-tipam.csv'
    by = defaultdict(list)
    if p.exists():
        for x in csv.DictReader(p.open(encoding='utf-8-sig'), delimiter=';'):
            by[x['slug']].append(x)
    out = {}
    for slug, xs in by.items():
        xs.sort(key=lambda x: ORDER.index(x['tip']) if x['tip'] in ORDER else 99)
        rows = []
        for x in xs:
            lo, hi, lc, la = num(x['cena_ot']), num(x['cena_do']), num(x['lot_cena']), num(x['lot_ploshchad'])
            pr = price(lo, hi)
            lot = ''
            if lc and la:
                lot = f'{fmt(la, 1)} м² за {" ".join(money(lc))} ₽'
                if x['lot_etazh']:
                    lot += f', {x["lot_etazh"]} этаж'
                k = (x['lot_korpus'] or '').strip()
                if k:
                    w = k.split()[0].lower().rstrip(',')
                    lot += (f', корпус {k}' if k[0].isdigit() else
                            f', {k[0].lower() + k[1:]}' if w in ('корпус', 'корпуса', 'корп.', 'очередь', 'башня', 'секция', 'квартал', 'дом', 'парадный') else f', {k}')
            n = num(x['lotov'])
            rows.append(dict(tip=x['tip'], label=LABEL.get(x['tip'], x['tip']), lots=int(n) if n else None,
                             area=area(num(x['ploshchad_ot']), num(x['ploshchad_do'])), price=pr, lot=lot,
                             otdelka=(x['otdelka'] or '').strip().lower(), skidka=bool(num(x['cena_ot_bez_skidki'])),
                             src=source(x['istochnik']), date=x['provereno']))
        if any(r['area'] or r['price'] for r in rows):
            out[slug] = rows
    return out


def when(rows):
    """Самая свежая дата сверки: 2026-09-17 → 17.09.2026."""
    d = max((r['date'] for r in rows if r['date']), default='')
    return '.'.join(reversed(d.split('-'))) if d else ''


def sources(rows):
    seen = []
    for r in rows:
        if r['src'] and r['src'] not in seen:
            seen.append(r['src'])
    return seen
