"""Рейтинг «Цена способа оплаты»: reytingi/tsena-sposoba-oplaty/index.html.
Данные: data/oplata-skhemy.csv (все схемы оплаты застройщиков со статусом сверки),
        data/oplata-raschet.csv (схемы, для которых известны обе цены, — посчитанная ставка в % годовых).
Цифры в «Шкале» считаются здесь же: тот же метод, что в методике на странице.
Запуск: python3 tools/oplata.py (потом build.py вставит шапку, подвал и живые цифры)."""
import pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from reytingi import read, e, fmt, plural, chips, cover, ld_list, write, lead_modal, HEAD, TAIL, R

SLUG = 'tsena-sposoba-oplaty'
SVERKA = '13 октября 2026'
IL2 = 'img/24-oplata-platezhi.jpg'  # иллюстрация «маленькие платежи и большой последний», после «Шкалы»
IL = 'img/24-oplata-klyuchi.jpg'   # иллюстрация «одна квартира — разные цены», между рейтингом и «Одной квартирой»
VKLAD, IPOTEKA = 13.06, 18.7          # пороги сравнения — источники в методике
NB = ' '

TIP = {  # tip → (ключ фильтра, подпись)
    'rassrochka_bez_udor': ('rassr', 'Рассрочка без процентов'),
    'rassrochka_s_udor': ('rassr', 'Рассрочка с удорожанием'),
    'otsrochka_pv': ('rassr', 'Отсрочка взноса'),
    'subsid_ipoteka': ('ipot', 'Ипотека от застройщика'),
    'ipoteka_krupnyi_chek': ('ipot', 'Ипотека на большую сумму'),
    'transh_ipoteka': ('transh', 'Траншевая ипотека'),
    'skidka_100': ('skid', 'Скидка за полную оплату'),
    'trade_in': ('trade', 'Trade-in'),
    'drugoe': ('drug', 'Другое'),
}
STATUS = {  # статус сверки → (ключ фильтра, подпись, класс метки)
    'новая': ('new', 'Новая в базе', 'look'),
    'продлена': ('same', 'Продлена', 'look'),
    'продлена с изменениями': ('chg', 'Изменилась', 'look'),
    'закончилась': ('off', 'Закончилась', 'no'),
    'вероятно закончилась': ('off', 'Вероятно закончилась', 'no'),
    'не подтверждена': ('off', 'Не подтверждена', 'no'),
}
OKT = {'s073', 's074', 's075', 's082', 's099', 's104', 's109', 's126'}   # запущены с 29 сентября по 12 октября

def ty(s):
    """Типографика из базы: 25% → 25 %, минус и неразрывный пробел."""
    s = (s or '').strip()
    s = re.sub(r'(\d)\s?%', r'\1' + NB + '%', s)
    s = re.sub(r'(?<![\w])-(\d)', '−\\1', s)
    return s

def e_ty(s):
    return e(ty(s))

def host(u):
    return re.sub(r'^https?://(www\.)?', '', u).split('/')[0]

def links(src):
    us = [u for u in (src or '').split() if u.startswith('http')]
    return ', '.join(f'<a href="{e(u)}" rel="nofollow noopener">{e(host(u))}</a>' for u in us)

def num(s):
    try: return float(str(s).replace(',', '.'))
    except ValueError: return None

# ------------------------------------------------------------------ расчёт
def irr(f0, flows):
    """Месячная ставка, при которой платежи flows [(месяц, сумма)] стоят f0 сегодня."""
    lo, hi = -0.99, 5.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if sum(a / (1 + mid) ** t for t, a in flows) > f0: lo = mid
        else: hi = mid
    return (lo + hi) / 2 * 12 * 100

def rassrochka(skidka, srok, pv=0.2):
    """Рассрочка по прайсу, когда за 100 % оплату дают скидку: остаток равными частями."""
    rest = 1 - pv
    return irr(1 - skidka - pv, [(k, rest / srok) for k in range(1, srok + 1)])

def subsidiya(nacenka, gody, stavka=0.125, srok=15, pv=0.2):
    """Субсидия на весь срок с наценкой к цене при 100 % оплате; кредит закрыт через `gody` лет."""
    p = 1 + nacenka; L = p * (1 - pv); n = srok * 12; r = stavka / 12
    pm = L * r / (1 - (1 + r) ** -n); h = min(n, gody * 12)
    bal = L * (1 + r) ** h - pm * ((1 + r) ** h - 1) / r
    flows = [(k, pm) for k in range(1, h + 1)]
    if h < n: flows[-1] = (h, pm + bal)
    return irr(1 - p * pv, flows)

KV = dict(  # студия № 424, 24,9 м², Шагал (Эталон): сайт Эталона, 13 октября 2026
    name='Студия 24,9 м² в Шагале у Эталона', prais=23_279_780, sto=17_459_835, pv=0.2, mes=50_000, n=17, konec=17.5,
    stavka_et=0.1299, stavka_ryn=0.187, srok=20, vyhod=5)

def kvartira(k=KV):
    """Сколько квартира стоит в сегодняшних деньгах при каждом способе: всё, что платите не сразу, лежит на вкладе (VKLAD)."""
    r = VKLAD / 100 / 12; d = lambda t: (1 + r) ** -t
    pv = round(k['prais'] * k['pv']); ost = k['prais'] - pv - k['mes'] * k['n']
    rassr = pv + sum(k['mes'] * d(t) for t in range(1, k['n'] + 1)) + ost * d(k['konec'])
    vklad = k['sto'] - pv                                   # остаток на вкладе, если деньги есть
    for _ in range(k['n']): vklad = vklad * (1 + r) - k['mes']
    vklad *= (1 + r) ** (k['konec'] - k['n'])
    L = k['prais'] - pv; n = k['srok'] * 12
    def ipot(st, h):
        q = st / 12; p = L * q / (1 - (1 + q) ** -n); h = min(h, n)
        bal = L * (1 + q) ** h - p * ((1 + q) ** h - 1) / q if h < n else 0
        return p, pv + sum(p * d(t) for t in range(1, h + 1)) + bal * d(h)
    p_et, et = ipot(k['stavka_et'], n)
    p_ryn, ryn = ipot(k['stavka_ryn'], k['vyhod'] * 12)
    return dict(pv=pv, ost=ost, rassr=rassr, vklad=vklad, nehvat=ost - vklad, p_et=p_et, et=et, p_ryn=p_ryn, ryn=ryn)

def mln(v, d=1):
    return fmt(v / 1e6, d) + NB + 'млн'

def tys(v):
    return fmt(round(v / 1e3)) + NB + 'тыс'

def cell(v):
    t = (fmt(v, 1).replace(',0', '') if v < 20 else fmt(round(v))) + NB + '%'
    return f'<b>{t}</b>' if v > IPOTEKA else t

# ------------------------------------------------------------------ страница
def raschet_ri(i, r):
    sub = ' · '.join(x for x in (r['zhk'], r['nazvanie']) if x)
    dl = [('Условия', e(ty(r['usloviya']))), ('Цена при 100 % оплате', e(ty(r['cena_100']))), ('Цена при этой схеме', e(ty(r['cena_shemy']))),
          ('Как посчитали', e(ty(r['raschet']))), ('Важно', e(ty(r['vazhno']))), ('Действует', e(ty(r['deystvuet']))),
          ('Источники', links(r['source']) + f' · проверено {SVERKA}')]
    dl_html = ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in dl if v)
    q = ' '.join([r['developer'], r['zhk'], r['nazvanie']]).lower().replace('ё', 'е')
    lead = f'Цена способа оплаты · {r["developer"]} · {r["zhk"]}'
    return f'''<article class="ri" id="{r['rid']}" data-s="{r['sposob']}" data-k="{r['kat']}" data-q="{e(q)}">
 <button class="ri-row" type="button" aria-expanded="false"><span class="ri-n">{i}</span><span class="ri-t"><b>{e(r['developer'])}</b><span>{e(ty(sub))}</span></span><span class="ri-c"><span class="tag {'no' if r['kat'] == 'dor' else 'look'}">{e(r['kat_text'])}</span></span><span class="ri-v">{e(ty(r['znachenie']))}<small>годовых</small></span></button>
 <div class="ri-body" hidden><div class="ri-main"><dl>{dl_html}</dl></div><div class="btns ri-btns"><button class="btn" type="button" data-lead="{e(lead)}">Посчитать мою квартиру</button></div></div>
</article>'''

def value(r):
    t = r['tip']; st = r['stavka']
    if t in ('subsid_ipoteka', 'ipoteka_krupnyi_chek', 'transh_ipoteka'):
        m = re.search(r'(\d+(?:,\d+)?)\s?%', st or '')
        if m: return ('платёж как при ' if 'платёж как' in st else ('от ' if st.strip().startswith('от') else '')) + m.group(1) + NB + '%', 'ставка'
        return '', ''
    if t == 'skidka_100':
        v = r['skidka_100'] if r['skidka_100'] not in ('', '—') else ''
        return (ty(v.split('(')[0].split(',')[0]).strip(), 'скидка') if v else ('', '')
    if t in ('rassrochka_bez_udor', 'rassrochka_s_udor', 'otsrochka_pv'):
        s = (r['srok'] or '').split(',')[0]
        return (ty(s), 'срок') if s and s not in ('нет данных', '—') else ('', '')
    return '', ''

def skhema_ri(i, r, houses, root):
    tk, tl = TIP.get(r['tip'], ('drug', 'Другое'))
    sk, sl, scl = STATUS.get(r['status'], ('off', r['status'] or '—', 'no'))
    if r['scheme_id'] in OKT: sl = 'С октября'
    kl = r['klass']
    ck = ' '.join(x for x, w in (('biz', 'бизнес'), ('prem', 'премиум'), ('elit', 'элит'), ('elit', 'делюкс')) if w in kl) or 'nd'
    zhk = r['zhk'] or ''
    sub = ' · '.join(x for x in (tl, zhk) if x)
    val, lab = value(r)
    now = r['izmeneniya'] if r['status'] == 'продлена с изменениями' else ''
    dl = [('Сейчас', e_ty(now)), ('Условия' if not now else 'Было 20 сентября', e_ty(r['opisanie'])),
          ('Ставка или удорожание', e_ty(r['stavka']) if r['stavka'] not in ('', '—', 'нет данных') and not now else ''),
          ('Срок', e_ty(r['srok']) if r['srok'] not in ('', '—', 'нет данных') and not now else ''),
          ('Взнос', e_ty(r['pv']) if r['pv'] not in ('', '—', 'нет данных') and not now else ''),
          ('Скидка', e_ty(r['skidka_100']) if r['skidka_100'] not in ('', '—', 'нет данных') and not now else ''),
          ('Ограничения', e_ty(r['ogranicheniya']) if r['ogranicheniya'] not in ('', '—') else ''),
          ('На 13 октября', e_ty(r['izmeneniya']) if r['izmeneniya'] and not now else ''),
          ('Действует', e_ty(r['deystvuet']) if r['deystvuet'] not in ('', 'нет данных') else 'срок не указан'),
          ('Источник', links(r['source']) + (f' · {e(r["kak_provereno"])}' if r.get('kak_provereno') else '') + f' · {r["checked"]}')]
    dl_html = ''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in dl if v)
    slug = r['slug']
    btns = ''
    if slug and slug in houses:
        btns += f'<a class="btn btn-l" href="{R}karta.html#h-{slug}">Дом на карте</a> '
        if (root / 'doma' / slug / 'index.html').exists():
            btns += f'<a class="btn btn-l" href="{R}doma/{slug}/">Паспорт дома</a> '
    lead = f'Схема оплаты · {r["developer"]}' + (f' · {zhk}' if zhk else '')
    btns += f'<button class="btn" type="button" data-lead="{e(lead)}">Узнать условия по квартире</button>'
    q = ' '.join([r['developer'], zhk, tl, r['opisanie']]).lower().replace('ё', 'е')
    return f'''<article class="ri" id="{r['scheme_id']}" data-t="{tk}" data-z="{sk}" data-c="{ck}" data-q="{e(q)}">
 <button class="ri-row" type="button" aria-expanded="false"><span class="ri-n">{i}</span><span class="ri-t"><b>{e(r['developer'])}</b><span>{e(ty(sub))}</span></span><span class="ri-c"><span class="tag {scl}">{e(sl)}</span></span><span class="ri-v">{e(val)}<small>{lab}</small></span></button>
 <div class="ri-body" hidden><div class="ri-main"><dl>{dl_html}</dl></div><div class="btns ri-btns">{btns}</div></div>
</article>'''

ODNA = [  # где разницу в цене видно на сайте · насколько дороже, чем при 100 % оплате · пояснение
    ('Эталон · Шагал', 'до +33 %', 'Скидка до 25 % — только при 100 % оплате. Рассрочка 0 % до марта 2028 года — по прайсу.'),
    ('Forma · Моментс', '+13 %', 'При 100 % оплате скидка до 24 %, при рассрочке — 14 %. Ипотека 11,9 % и 7,77 % — без скидки за полную оплату.'),
    ('ФСК · строящиеся дома', '11,9 % годовых', 'Рассрочка с открытыми процентами на остаток: при взносе 70 % на оставшиеся 30 % — 11,9 % годовых.'),
    ('Hutton · Lunar', '+4,5 %', 'При 100 % оплате скидка 12 %, при рассрочке 0 % — 8 %.'),
    ('ANT · Victory Park Residences', 'до +33 %', 'Скидка 25 % на часть готовых квартир — только при единовременной оплате. Рассрочка 0 % на 2 года — без неё.'),
    ('Остальные застройщики', 'по запросу', 'На сайтах — «скидка до…» и «рассрочка 0 %». Цену конкретной квартиры при каждой схеме мы запрашиваем в отделе продаж как брокеры, обычно в тот же день.'),
]

OKTYABR = [
    ('Короткие субсидии почти исчезли',
     'Сбер с 1 октября перестал доплачивать за низкую ставку на первые годы, и из каталогов застройщиков пропали шесть таких программ из нашей базы: от 0,3 % на первый год у Эталона до 8,1 % на три года у Донстроя. '
     'Короткие ставки остались у других банков: платёж «как при 4,4 %» на время стройки у ФСК с Совкомбанком, «Лёгкий старт» у ПИК и Forma — 8,99 % в первый год, у ПИК 19,49 % с четвёртого, — и 0,11 % на год или 0,22 % на два года у Центр-Инвеста при взносе от 50 и 70 %.'),
    ('Ставка «на весь срок» подорожала',
     'Эталон — 12,99 % вместо 11 %, ФСК с Альфа-Банком — 12,49 % вместо 12,39 % и кредит до 15 лет вместо 30. '
     'Почти все такие программы теперь в коридоре 12,4–13 %, чаще всего с Совкомбанком; у Эталона ставку дают только со страховкой и картой «Халва».'),
    ('Цену рассрочки стало видно',
     'Застройщики начали писать, какая скидка при какой схеме: Forma в Моментс — 24 % при полной оплате и 14 % при рассрочке, Lunar — 12 % и 8 %. У Эталона в Шагале и у ANT в Victory Park скидка только при полной оплате. '
     'Разница между этими ценами и есть цена рассрочки.'),
    ('Рассрочки длиннее, последний платёж больше',
     'Донстрой продлил рассрочку с полутора до трёх лет, у STONE она доходит до II квартала 2030 года, у TEKTA в Пыжевском — до лета 2029-го. Продают через месячный платёж: 50 тыс ₽ у Эталона, Гранели и ЛСР, 80–160 тыс ₽ у MR Group, 200–500 тыс ₽ у Донстроя. '
     'Остаток почти везде вносится одним платежом в конце.'),
    ('Скидки не уменьшились',
     'Гранель подняла выгоду до 27 %, Forma и MR Group в Мысе дают до 25 %, AFI и ANT — 25 % на готовые квартиры. Эталон в Шагале, наоборот, снизил максимум с 33 до 25 %. '
     'По всей Москве, по данным ЦИАН, со скидкой продаётся около 60 % квартир в новостройках, средняя скидка — 7,8 % (январь — июль).'),
]

PRAVILA = [
    ('Рассрочку после ключей разрешат не раньше осени 2027 года',
     'Минстрой вместе с ЦБ опубликовал для обсуждения законопроект: рассрочка — до трёх лет после плановой даты сдачи дома, квартира в залоге у застройщика до полной оплаты, данные — в бюро кредитных историй, без согласия банка в рассрочку можно продать не больше 25 % квартир в проекте. '
     'Вступление — 1 сентября 2027 года, только для новых договоров. Внести проект в Госдуму планировали осенью; на 13 октября подтверждений мы не нашли.'),
    ('ЦБ: субсидия всё равно заложена в цену',
     'Регулятор отмечает, что любая субсидия экономически всё равно заложена в цену квартиры (Т—Ж, 12 сентября). Поэтому сравнивать надо не ставки, а цену одной и той же квартиры при каждой схеме.'),
    ('Деньги не дешевеют',
     'Ключевая ставка — 14 %, 11 сентября ЦБ её не менял, следующее решение — 23 октября. Средняя максимальная ставка по вкладам в десяти крупнейших банках — 13,06 % (ЦБ, конец сентября), средняя ставка рыночной ипотеки — 18,7 % («Метриум», III квартал).'),
]

SPROSIT = [
    ('Сколько стоит эта квартира при 100 % оплате сегодня?', 'Это точка отсчёта: от неё считается цена любой схемы'),
    ('Какая скидка при моей схеме и суммируется ли она с другими?', 'Скидка за полную оплату часто не действует при рассрочке и субсидии'),
    ('Удорожание — это процент к цене или процент годовых на остаток?', '«7 %» часто значит 7 % годовых на остаток — это +2,1 % к цене за полгода, а не +7 %'),
    ('Сколько и когда последний платёж?', 'В Шагале на студию это 76 % цены через полтора года'),
    ('Что будет, если банк не одобрит ипотеку на остаток?', 'Расторжение, штраф или пересчёт цены — это написано в договоре'),
    ('Какая ставка после льготного периода и какая ПСК?', '«Лёгкий старт» у ПИК: 8,99 % в первый год и 19,49 % с четвёртого'),
    ('Какие страховки и карты обязательны для этой ставки?', 'У Эталона ставку Совкомбанка 12,99 % дают только со страховкой и картой «Халва»'),
    ('До какой даты действуют условия и фиксируется ли цена?', 'Половина действующих схем — до 31 октября: в ноябре их перепишут'),
]

ISTOCHNIKI = [
    ('Сайты застройщиков: ФСК, Эталон, Forma, Гранель, Донстрой, Hutton (Lunar), ANT (Victory Park), TEKTA, STONE, ЛСР, Центр-Инвест, РГ-Девелопмент, AFI, Брусника, ГК Основа, Level и другие — страницы акций и способов покупки, 13 октября 2026; если сайт не открывался — Новострой-М и Циан, ссылка в строке схемы', ''),
    ('Банк России: ключевая ставка, решение 11 сентября 2026', 'https://www.cbr.ru/press/keypr/'),
    ('Банк России: средняя максимальная ставка по вкладам десяти крупнейших банков, III декада сентября 2026', 'https://www.cbr.ru/statistics/avgprocstav/'),
    ('«Метриум» в пересказе «Финансов Mail»: итоги III квартала на первичном рынке бизнес-класса Москвы, средняя ставка рыночной ипотеки, 13 октября 2026', 'https://finance.mail.ru/article/itogi-iii-kvartala-2026-goda-na-pervichnom-rynke-biznes-klassa-moskvy-69232221/'),
    ('Т—Ж: банки отказываются от субсидированной ипотеки, ответ ЦБ, 12 сентября 2026', 'https://t-j.ru/ipoteka-developers/'),
    ('Chita.ru по материалам E1.RU: Сбер с 1 октября прекращает короткие субсидии застройщиков, 11 сентября 2026', 'https://www.chita.ru/text/realty/2026/09/11/76635775/'),
    ('РИА Недвижимость: Минстрой предложил рассрочку после ввода дома, 19 августа 2026', 'https://realty.ria.ru/20260819/minstroj-2111754431.html'),
    ('«Парламентская газета»: параметры законопроекта о рассрочке — три года после сдачи, 25 % квартир, 1 сентября 2027 года, 17 августа 2026', 'https://www.pnp.ru/economics/dolshhikam-mogut-razreshit-rassrochku-posle-novoselya.html'),
    ('ЦИАН в пересказе РИА Недвижимость: доля квартир со скидкой и средняя скидка в новостройках Москвы, январь — июль 2026, 24 августа 2026', 'https://realty.ria.ru/20260824/skidki-2112118345.html'),
]

def tsena_oplaty(root):
    sh = read(root / 'data/oplata-skhemy.csv')
    rs = read(root / 'data/oplata-raschet.csv')
    if not sh or not rs: return None
    houses = {h['slug'] for h in read(root / 'data/doma.csv')}
    rs.sort(key=lambda r: num(r['stavka_sort']))
    act = [r for r in sh if r['status'] in ('новая', 'продлена', 'продлена с изменениями')]
    devs = {r['developer'] for r in sh}
    n31 = sum('31.10' in r['deystvuet'] for r in act)
    both = {'Level Group', 'Hutton', 'Эталон', 'ANT Development', 'Forma'}

    title = 'Цена способа оплаты: рассрочки, скидки и субсидии застройщиков, октябрь 2026 — NOTA'
    desc = (f'{len(sh)} {plural(len(sh), "схема", "схемы", "схем")} оплаты у {len(devs)} застройщиков Москвы на {SVERKA}. Сколько на самом деле стоит рассрочка в % годовых: '
            'студия в Шагале стоит 17,5 млн ₽ сразу и 20,1 млн ₽ в рассрочку «0 %» даже с остатком на вкладе. Что изменилось с 1 октября и что спросить до брони.')
    ld = ld_list('Цена способа оплаты', desc, f'https://nota.expert/reytingi/{SLUG}/', [f'{r["developer"]} · {r["zhk"]}: {r["nazvanie"]}' for r in rs])
    page = HEAD.format(title=e(title), desc=e(desc), R=R, img='img/ix-2026-10-oplata-og.jpg', ld=ld)
    page += cover('img/ix-2026-10-oplata.jpg', 'План квартиры, договор и ключи на столе',
                  f'<b>Рейтинг</b><span>Способы оплаты</span><span>Октябрь 2026</span><span>{len(sh)} {plural(len(sh), "схема", "схемы", "схем")}</span>',
                  'Цена способа оплаты',
                  f'Одна и та же квартира стоит по-разному — смотря как за неё платить. Показываем на одной студии, а ниже — {len(sh)} {plural(len(sh), "схема", "схемы", "схем")} оплаты у {len(devs)} застройщиков на {SVERKA} и сколько на самом деле стоит каждая рассрочка.')
    kv = kvartira()
    page += f'''<section><div class="wrap jr-ed">
 <div><p class="ttl">На заметку:</p></div>
 <div>
  <div class="jr-ed-t">
   <p>Рассрочка «0 %» бесплатной не бывает. Студия в Шагале при полной оплате стоит {mln(KV['sto'])} ₽, а в рассрочку — {mln(KV['prais'])} ₽: скидку 25 % дают только тем, кто платит сразу. Даже если остаток держать на вкладе под 13 %, рассрочка обойдётся дороже: к последнему платежу не хватит {mln(kv['nehvat'])} ₽.</p>
   <p>С 1 октября почти закончились короткие субсидии. Их место заняли рассрочки на два–четыре года и ипотека «на весь срок» под 12,4–13 %. Скидки за полную оплату застройщики не уменьшают, а половина условий действует до 31 октября.</p>
   <p>Правило одно: до брони узнайте цену квартиры при 100 % оплате и при вашей схеме. По любой квартире мы как брокеры запрашиваем обе цены у застройщика — пришлите дом.</p>
  </div>
 </div>
</div></section>
<section class="method" id="kvartira"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Одна квартира</p><h2 style="margin-top:20px">Одна студия —<br>четыре цены</h2></div>
  <div><p class="lede">{KV['name']}, прайс — {mln(KV['prais'], 2)} ₽. Считаем, сколько она стоит в сегодняшних деньгах: всё, что вы платите не сразу, пока лежит на вкладе под 13 % и приносит проценты.</p></div>
 </div>
 <div class="strip">
  <div><b>{mln(KV['sto'])}</b><small>сразу: скидка 25 % — только при 100 % оплате</small></div>
  <div><b>{mln(kv['rassr'])}</b><small>рассрочка 0 % до марта 2028: {mln(kv['pv'], 2)} сейчас, {tys(KV['mes'])} в месяц и {mln(kv['ost'])} в конце</small></div>
  <div><b>{mln(kv['et'])}</b><small>ипотека Эталона 12,99 %: скидки нет, {tys(kv['p_et'])} ₽ в месяц на 20 лет</small></div>
  <div><b>{mln(kv['ryn'])}</b><small>рыночная ипотека 18,7 %: {tys(kv['p_ryn'])} ₽ в месяц, если закрыть кредит через 5 лет</small></div>
 </div>
 <div class="two" style="margin-top:34px;align-items:start">
  <div class="claim"><h3>Если деньги есть</h3><p>Платите сразу. Положите остаток на вклад вместо рассрочки — к марту 2028 года на нём будет {mln(kv['vklad'])} ₽, а последний платёж — {mln(kv['ost'])} ₽. Скидка 25 % больше, чем вклад заработает за полтора года.</p></div>
  <div class="claim"><h3>Если денег сразу нет</h3><p>Рассрочка дешевле ипотеки на {mln(kv['et'] - kv['rassr'])} ₽ в сегодняшних деньгах. Но к марту 2028 года нужно найти {mln(kv['ost'])} ₽ — своими деньгами или ипотекой по ставке того времени.</p></div>
 </div>
 <p class="hint">Цены — сайт Эталона, студия № 424, {SVERKA}. Вклад — 13 %: средняя максимальная ставка десяти крупнейших банков (ЦБ), налог на проценты не учтён. Ипотека — на цену по прайсу с взносом 20 %. Если ставки по вкладам снизятся, оплата сразу станет ещё выгоднее рассрочки.</p>
</div></section>
'''
    page += f'''<section class="method" id="spisok"><div class="wrap" data-rlist data-lim="20">
 <div class="two">
  <div><p class="ttl">Рейтинг</p><h2 style="margin-top:20px">Сколько на самом деле стоит рассрочка —<br>от дешёвой к дорогой</h2></div>
  <div><p class="lede">Точка отсчёта — цена той же квартиры при 100 % оплате сегодня. Всё, что вы платите сверх неё позже, — плата за отсрочку. Мы перевели её в проценты годовых и сравнили с вкладом ({fmt(VKLAD, 2)} %) и рыночной ипотекой ({fmt(IPOTEKA, 1)} %). Здесь — схемы, где обе цены видны на сайте застройщика: любую цифру можно проверить по ссылке. Для вашей квартиры обе цены мы запрашиваем у застройщика сами.</p></div>
 </div>
 <div class="ri-filters">
  {chips('s', 'Способ', [('rassr', 'Рассрочка'), ('ipot', 'Ипотека от застройщика')])}
  {chips('k', 'Сравнение', [('vklad', 'Дешевле вклада'), ('ipot', 'Дешевле ипотеки'), ('dor', 'Дороже ипотеки')])}
 </div>
 <div class="hs-bar"><span class="ri-cnt"></span><button class="linkbtn" type="button" data-reset>Сбросить фильтры</button></div>
 <div class="ri-list">
{chr(10).join(raschet_ri(i + 1, r) for i, r in enumerate(rs))}
 </div>
 <div class="hs-more"><button class="btn btn-l ri-more" type="button" hidden>Показать ещё</button></div>
 <p class="hint">Ставка — месячная, умноженная на 12, как в ипотеке. Вклад — средняя максимальная ставка десяти крупнейших банков, III декада сентября 2026 (ЦБ). Рыночная ипотека — средняя ставка, III квартал 2026 («Метриум»). Если ставка дана диапазоном, она зависит от скидки на конкретную квартиру или от графика платежей. Как считали — в методике ниже.</p>
</div></section>
'''
    if (root / IL).exists():
        page += f'''<section class="tight"><div class="wrap">
 <div class="phwrap" style="margin:0"><div class="ph has" data-ar="21x9"><img src="{R}{IL}" alt="Три одинаковых ключа с бирками разного размера на тёмном каменном столе" loading="lazy"></div></div>
</div></section>
'''
    cards = ''.join(f'<div class="lv"><span class="ttl">{e(a)}</span><b>{e(ty(b))}</b><p>{e(ty(c))}</p></div>' for a, b, c in ODNA)
    page += f'''<section id="dve-tseny"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Две цены</p><h2 style="margin-top:20px">Где разницу видно<br>прямо на сайте</h2></div>
  <div><p class="lede">Чаще застройщики пишут «скидка до…» и «рассрочка 0 %», а цену при рассрочке называют в отделе продаж. Вот где на сайте видно, насколько та же квартира дороже при другом способе оплаты, чем при 100 % оплате.</p></div>
 </div>
 <div class="levels">{cards}</div>
 <p class="hint">Наценка — цена при схеме, делённая на цену при полной оплате. «До» — максимальная скидка, на большинстве квартир она меньше. Сайты застройщиков, {SVERKA}.</p>
</div></section>
'''
    srok = (6, 12, 24, 36); disc = (5, 10, 15, 20, 25)
    m1 = ''.join('<tr><td><b>' + f'{d}{NB}%' + '</b></td>' + ''.join(f'<td>{cell(rassrochka(d / 100, t))}</td>' for t in srok) + '</tr>' for d in disc)
    gody = (3, 5, 10, 15); nac = (0, 5, 10, 15, 20)
    m2 = ''.join('<tr><td><b>' + (f'+{n}{NB}%' if n else 'нет') + '</b></td>' + ''.join(f'<td>{cell(subsidiya(n / 100, g))}</td>' for g in gody) + '</tr>' for n in nac)
    page += f'''<section class="method" id="shkala"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Шкала</p><h2 style="margin-top:20px">Посчитайте свою схему<br>по двум таблицам</h2></div>
  <div><p class="lede">Найдите в первой таблице скидку, которую вы теряете, и срок рассрочки — получите её цену в процентах годовых. Во второй — наценку за субсидированную ставку и через сколько лет вы закроете кредит. Жирным — дороже рыночной ипотеки ({fmt(IPOTEKA, 1)} %).</p></div>
 </div>
 <h3 style="margin-top:34px">Рассрочка 0 % без скидки за полную оплату</h3>
 <div class="tablewrap" style="margin-top:16px"><table style="min-width:0">
  <tr><th>Скидка</th><th>6 мес</th><th>12 мес</th><th>24 мес</th><th>36 мес</th></tr>
  {m1}
 </table></div>
 <p class="hint">Слева — скидка за 100 % оплату, которую вы теряете, сверху — за сколько месяцев выплачивается остаток. Взнос 20 %, остаток равными ежемесячными платежами. Чем короче рассрочка и больше скидка за полную оплату, тем дороже рассрочка: полгода вместо скидки 10 % — это 47 % годовых, три года вместо скидки 5 % — 4 %. При взносе 30 % ставки чуть выше.</p>
 <h3 style="margin-top:40px">Ипотека 12,5 % на весь срок с наценкой к цене</h3>
 <div class="tablewrap" style="margin-top:16px"><table style="min-width:0">
  <tr><th>Наценка</th><th>3 года</th><th>5 лет</th><th>10 лет</th><th>15 лет</th></tr>
  {m2}
 </table></div>
 <p class="hint">Слева — насколько квартира с субсидией дороже, чем при 100 % оплате, сверху — через сколько лет кредит закрыт: продажей, рефинансированием или последним платежом. Кредит на 15 лет, взнос 20 %, аннуитет; если продать квартиру или рефинансировать раньше, остаток долга гасится в этот месяц. При наценке до 10 % субсидия дешевле рыночной ипотеки при любом сроке, при 15 % — если не закрывать кредит в первые три года, при 20 % — если держать его дольше пяти лет. Страховки и комиссии не учтены.</p>
</div></section>
'''
    if (root / IL2).exists():
        page += f'''<section class="tight"><div class="wrap">
 <div class="phwrap" style="margin:0"><div class="ph has" data-ar="21x9"><img src="{R}{IL2}" alt="Четыре маленьких конверта и один большой с красной сургучной печатью на тёмном каменном столе" loading="lazy"></div></div>
</div></section>
'''
    claims = lambda L: ''.join(f'<div class="claim"><h3>{e(h)}</h3><p>{e(ty(p))}</p></div>' for h, p in L)
    page += f'''<section id="oktyabr"><div class="wrap two">
 <div><p class="ttl">С 1 октября</p><h2 style="margin-top:20px">Что изменилось<br>за месяц</h2></div>
 <div class="claims">{claims(OKTYABR)}</div>
</div></section>
'''
    order = list(TIP)
    sh_sorted = sorted(sh, key=lambda r: (STATUS.get(r['status'], ('off',))[0] == 'off', r['developer'].lower().replace('ё', 'е'), order.index(r['tip']) if r['tip'] in order else 99, r['scheme_id']))
    page += f'''<section class="method" id="vse"><div class="wrap" data-rlist data-lim="20">
 <div class="two">
  <div><p class="ttl">Все схемы</p><h2 style="margin-top:20px">{len(sh)} {plural(len(sh), "схема", "схемы", "схем")} на {SVERKA}</h2></div>
  <div><p class="lede">Каждую схему мы открыли на сайте застройщика. Схемы из прошлой сверки, 20 сентября, помечены: продлена, изменилась, закончилась или не подтвердилась. «Новая в базе» — схема, которой у нас ещё не было, «С октября» — запущена в последние две недели. Закончившиеся — в конце списка.</p></div>
 </div>
 <div class="ri-filters">
  {chips('t', 'Способ', [('rassr', 'Рассрочка'), ('ipot', 'Ипотека'), ('transh', 'Транши'), ('skid', 'Скидка за 100 %'), ('trade', 'Trade-in'), ('drug', 'Другое')])}
  {chips('z', 'Статус', [('new', 'Новые'), ('same', 'Продлены'), ('chg', 'Изменились'), ('off', 'Закончились или не подтверждены')])}
  {chips('c', 'Класс', [('biz', 'Бизнес'), ('prem', 'Премиум'), ('elit', 'Элит и делюкс')])}
  <label class="ri-q"><span class="cg-l">Поиск</span><input type="search" placeholder="Застройщик или дом" autocomplete="off"></label>
 </div>
 <div class="hs-bar"><span class="ri-cnt"></span><button class="linkbtn" type="button" data-reset>Сбросить фильтры</button></div>
 <div class="ri-list">
{chr(10).join(skhema_ri(i + 1, r, houses, root) for i, r in enumerate(sh_sorted))}
 </div>
 <div class="hs-more"><button class="btn btn-l ri-more" type="button" hidden>Показать ещё</button></div>
 <p class="hint">Справа — главная цифра схемы: ставка, скидка или срок. «Нет данных» значит, что застройщик не опубликовал условие. Если на сайте застройщика и на агрегаторе условия расходятся, мы указываем оба.</p>
</div></section>
'''
    page += f'''<section id="pravila"><div class="wrap two">
 <div><p class="ttl">Правила и рынок</p><h2 style="margin-top:20px">Что меняется<br>вокруг рассрочек</h2></div>
 <div class="claims">{claims(PRAVILA)}</div>
</div></section>
'''
    qs = ''.join(f'<details><summary>{i + 1}. {e(ty(a))}</summary><p>{e(ty(b))}</p></details>' for i, (a, b) in enumerate(SPROSIT))
    page += f'''<section class="method" id="sprosit"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Перед бронью</p><h2 style="margin-top:20px">Восемь вопросов застройщику</h2></div>
  <div><p class="lede">Ответы на первые два вопроса дают цену рассрочки. Остальные — про риск: что будет с последним платежом и со ставкой после льготного периода. Откройте вопрос — там, зачем его задавать.</p>
  <div class="btns"><button class="btn" type="button" data-lead="Цена способа оплаты · свой дом">Сверим условия по вашему дому</button></div></div>
 </div>
 <div class="faq ri-w">{qs}</div>
</div></section>
'''
    met = [
        ('Что считаем', 'Сколько на самом деле стоит рассрочка или субсидия: под какую ставку вы, по сути, берёте у застройщика кредит. Точка отсчёта — цена той же квартиры при 100 % оплате сегодня. Всё, что вы платите сверх неё позже, — плата за отсрочку. Переводим её в проценты годовых так же, как считают ипотеку: находим месячную ставку, при которой ваши будущие платежи стоят сегодня ровно столько, сколько вы не доплатили, и умножаем на 12.'),
        ('С чем сравниваем', f'С вкладом: {fmt(VKLAD, 2)} % — средняя максимальная ставка десяти крупнейших банков, III декада сентября 2026 (ЦБ). Если рассрочка дешевле, выгоднее держать деньги на вкладе и платить застройщику частями. С рыночной ипотекой: {fmt(IPOTEKA, 1)} % — средняя ставка, III квартал 2026 («Метриум»). Налог на проценты по вкладу и страховки по ипотеке не учитываем.'),
        ('Допущения', 'Если график не расписан, считаем остаток равными ежемесячными платежами. Платёж «до марта 2028 года» ставим в последний месяц. Для ипотеки — аннуитет; если квартиру продают или кредит рефинансируют раньше, остаток долга гасится в этот месяц. Скидку «до» берём максимальной и показываем, как меняется ставка при меньшей.'),
        ('Почему в рейтинге восемь схем', f'В рейтинг попали схемы, где обе цены — при 100 % оплате и при схеме — открыто видны на сайте застройщика: так любую цифру можно проверить по ссылке. Цену конкретной квартиры при каждой схеме мы как брокеры запрашиваем в отделе продаж — по любому дому из {len(sh)} схем в списке.'),
        ('Как проверяли', f'Каждую схему открыли на сайте застройщика {SVERKA}. Если сайт не открывался, брали Новострой-М или Циан — так и помечено в строке. Схемы из сверки 20 сентября помечены: продлена, изменилась, закончилась или не подтвердилась.'),
        ('Когда обновим', f'{n31} из {len(act)} действующих схем — до 31 октября. Пересверим в первых числах ноября и после решения ЦБ по ставке 23 октября.'),
    ]
    page += f'''<section id="metodika"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Методика</p><h2 style="margin-top:20px">Как мы считали</h2></div>
  <div><p class="lede">Один метод для всех схем: сравниваем, сколько вы заплатите и когда, с ценой той же квартиры при полной оплате сегодня.</p></div>
 </div>
 <div class="faq ri-w">{''.join(f'<details><summary>{e(a)}</summary><p>{e(ty(b))}</p></details>' for a, b in met)}</div>
 <div class="btns" style="margin-top:34px"><a class="btn" href="{R}podbor.html">Посчитаем под ваш случай</a> <a class="btn btn-l" href="{R}razbory/ipoteka-s-1-oktyabrya/">Ипотека с 1 октября</a> <a class="btn btn-l" href="{R}reytingi.html">Все рейтинги</a></div>
</div></section>
'''
    src = ''.join(f'<li>' + (f'<a href="{e(u)}" rel="nofollow noopener">{e(t)}</a>' if u else e(t)) + '</li>' for t, u in ISTOCHNIKI)
    page += f'''<section class="method"><div class="wrap two">
 <div><p class="ttl">Источники</p><h2 style="margin-top:20px">Откуда цифры</h2></div>
 <div>
  <ul class="h-src">{src}</ul>
  <p class="hint">{'Обложка и иллюстрации сгенерированы' if (root / IL).exists() and (root / IL2).exists() else 'Обложка и иллюстрация сгенерированы' if (root / IL).exists() or (root / IL2).exists() else 'Обложка сгенерирована'} для NOTA. Рейтинг собран {SVERKA}. Условия застройщиков меняются каждый месяц — в начале ноября пересверим все схемы и поставим новую дату.</p>
 </div>
</div></section>
'''
    page += lead_modal('Рейтинг «Цена способа оплаты»', ttl='Расчёт схемы', text='Напишите, какой дом и какую схему оплаты смотрите. Запросим у застройщика обе цены и посчитаем, сколько на самом деле стоит рассрочка. Обычно в тот же день.',
                       btn='Получить расчёт', note_ph='Дом, квартира, схема оплаты')
    page += TAIL.format(R=R)
    p = write(root, SLUG, page)
    return p, len(sh), {'oplata_shem': len(sh), 'oplata_dev': len(devs), 'oplata_act': len(act)}

if __name__ == '__main__':
    root = pathlib.Path(__file__).resolve().parent.parent
    res = tsena_oplaty(root)
    print('цена способа оплаты:', res[1] if res else 'нет данных', res[2] if res else '')
