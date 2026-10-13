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

ODNA = [  # дом · насколько дороже, чем при 100 % оплате · пояснение
    ('Level · Мечникова', '+13 % и +20 %', 'При 100 % оплате скидка 25 %, с ипотекой 12,49 % на весь срок — 15 %, с траншевой ипотекой — 10 %.'),
    ('Level · Войковская', '+5 %', 'При 100 % оплате скидка 20 %, при долгой рассрочке — 16 %.'),
    ('Level · Лесной, Южнопортовая, Селигерская, Нижегородская', '+4,6 %', 'При 100 % оплате скидка 35 %, при долгой рассрочке — 32 %.'),
    ('Level · остальные проекты', '0', 'Скидка 35 % и при 100 % оплате, и с ипотекой 12,49 %, и при рассрочке до 6 месяцев.'),
    ('Hutton · Lunar', '+4,5 %', 'При 100 % оплате скидка 12 %, при рассрочке 0 % на 12 месяцев — 8 %.'),
    ('Эталон · Шагал', 'до +33 %', 'Скидка до 25 % — только при 100 % оплате. Рассрочка 0 % до марта 2028 года — по прайсу.'),
    ('ANT · Victory Park Residences', 'до +33 %', 'Скидка 25 % на часть готовых квартир — только при единовременной оплате. Рассрочка 0 % на 2 года — без неё.'),
    ('Forma · все проекты', 'до +33 % и +13 %', 'Скидка до 25 % — при 100 % оплате или ипотеке без субсидии, ипотека 11,9 % и 7,77 % — без неё. В Моментс при рассрочке скидка 14 % вместо 24 %.'),
    ('Ещё {n} застройщика', 'нет данных', 'Скидку публикуют как «до…», а цену той же квартиры при рассрочке называют только в офисе продаж. Спросите обе цены до брони.'),
]

OKTYABR = [
    ('Короткие субсидии почти исчезли',
     'Сбер с 1 октября перестал доплачивать за низкую ставку на первые годы, и из каталогов застройщиков пропали шесть таких программ из нашей базы: от 0,3 % на первый год у Эталона до 8,1 % на три года у Донстроя. '
     'Короткие ставки остались у других банков: платёж «как при 4,4 %» на время стройки у ФСК с Совкомбанком, «Лёгкий старт» у ПИК и Forma — 8,99 % в первый год, у ПИК 19,49 % с четвёртого, — и 0,11 % на год или 0,22 % на два года у Центр-Инвеста при взносе от 50 и 70 %.'),
    ('Ставка «на весь срок» подорожала',
     'Level — 12,49 % вместо 11,89 %, Эталон — 12,99 % вместо 11 %, ФСК с Альфа-Банком — 12,49 % вместо 12,39 % и кредит до 15 лет вместо 30. '
     'Почти все такие программы теперь в коридоре 12,4–13 %, чаще всего с Совкомбанком; у Level и Эталона ставку дают только со страховкой и картой «Халва».'),
    ('Цену рассрочки стало видно',
     'Застройщики начали писать, какая скидка при какой схеме: Lunar — 12 % при полной оплате и 8 % при рассрочке, Level — 35 % и 32 %, Forma в Моментс — 24 % и 14 %. У Эталона в Шагале и у ANT в Victory Park скидка только при полной оплате. '
     'Разница между этими ценами и есть цена рассрочки.'),
    ('Рассрочки длиннее, последний платёж больше',
     'Донстрой продлил рассрочку с полутора до трёх лет, у STONE она доходит до II квартала 2030 года, у TEKTA в Пыжевском — до лета 2029-го. Продают через месячный платёж: 50 тыс ₽ у Эталона, Гранели и ЛСР, 80–160 тыс ₽ у MR Group, 200–500 тыс ₽ у Донстроя. '
     'Остаток почти везде вносится одним платежом в конце.'),
    ('Скидки не уменьшились',
     'Level держит до 35 %, Гранель подняла выгоду до 27 %, MR Group в Мысе даёт до 25 %, AFI и ANT — 25 % на готовые квартиры. Эталон в Шагале, наоборот, снизил максимум с 33 до 25 %. '
     'По всей Москве, по данным ЦИАН, со скидкой продаётся около 60 % квартир в новостройках, средняя скидка — 7,8 % (январь — июль).'),
    ('Рассрочка до рождения ребёнка',
     'Под новые правила семейной ипотеки Гранель даёт будущим родителям рассрочку на 9 месяцев по 50 тыс ₽ в месяц, а после рождения ребёнка остаток можно закрыть семейной ипотекой. У ФСК такая рассрочка действовала в сентябре. '
     'В октябре ФСК доплачивает банку, чтобы семейная ставка была 8,5 % на 15 лет при кредите до 12 млн ₽.'),
]

PRAVILA = [
    ('Рассрочку после ключей разрешат не раньше осени 2027 года',
     'Минстрой вместе с ЦБ опубликовал для обсуждения законопроект: рассрочка — до трёх лет после плановой даты сдачи дома, квартира в залоге у застройщика до полной оплаты, данные — в бюро кредитных историй, без согласия банка в рассрочку можно продать не больше 25 % квартир в проекте. '
     'Вступление — 1 сентября 2027 года, только для новых договоров. Внести проект в Госдуму планировали осенью; на 13 октября подтверждений мы не нашли.'),
    ('ЦБ: субсидия всё равно заложена в цену',
     'Регулятор отмечает, что любая субсидия экономически всё равно заложена в цену квартиры (Т—Ж, 12 сентября). Поэтому сравнивать надо не ставки, а цену одной и той же квартиры при каждой схеме.'),
    ('Деньги не дешевеют',
     'Ключевая ставка — 14 %, 11 сентября ЦБ её не менял, следующее решение — 23 октября. Средняя максимальная ставка по вкладам в десяти крупнейших банках — 13,06 % (ЦБ, конец сентября), средняя ставка рыночной ипотеки — 18,7 % («Метриум», III квартал).'),
    ('Рассрочкой платят всё чаще',
     'Во II квартале 2026 года в рассрочку прошла каждая четвёртая сделка по договорам долевого участия; на 1 сентября покупатели не оплатили 17 % стоимости таких договоров (ДОМ.РФ). В высокобюджетном сегменте старой Москвы на рассрочку приходится 53 % сделок (НДВ и Media Instinct, май 2026).'),
]

SPROSIT = [
    ('Сколько стоит эта квартира при 100 % оплате сегодня?', 'Это точка отсчёта: от неё считается цена любой схемы'),
    ('Какая скидка при моей схеме и суммируется ли она с другими?', 'Скидка за полную оплату часто не действует при рассрочке и субсидии'),
    ('Удорожание — это процент к цене или процент годовых на остаток?', '«7 %» у Level — это 7 % годовых, то есть +2,1 % к цене за полгода'),
    ('Сколько и когда последний платёж?', 'В Шагале на студию это 76 % цены через полтора года'),
    ('Что будет, если банк не одобрит ипотеку на остаток?', 'Расторжение, штраф или пересчёт цены — это написано в договоре'),
    ('Какая ставка после льготного периода и какая ПСК?', '«Лёгкий старт» у ПИК: 8,99 % в первый год и 19,49 % с четвёртого'),
    ('Какие страховки и карты обязательны для этой ставки?', 'У Level и Эталона ставку Совкомбанка дают только со страховкой и картой «Халва»'),
    ('До какой даты действуют условия и фиксируется ли цена?', 'Половина действующих схем — до 31 октября: в ноябре их перепишут'),
]

ISTOCHNIKI = [
    ('Сайты застройщиков: Level, ФСК, Эталон, Forma, Гранель, Донстрой, Hutton (Lunar), ANT (Victory Park), TEKTA, STONE, ЛСР, Центр-Инвест, РГ-Девелопмент, AFI, Брусника, ГК Основа — страницы акций и способов покупки, 13 октября 2026; если сайт не открывался — Новострой-М и Циан, ссылка в строке схемы', ''),
    ('Банк России: ключевая ставка, решение 11 сентября 2026', 'https://www.cbr.ru/press/keypr/'),
    ('Банк России: средняя максимальная ставка по вкладам десяти крупнейших банков, III декада сентября 2026', 'https://www.cbr.ru/statistics/avgprocstav/'),
    ('«Метриум» в пересказе «Финансов Mail»: итоги III квартала на первичном рынке бизнес-класса Москвы, средняя ставка рыночной ипотеки, 13 октября 2026', 'https://finance.mail.ru/article/itogi-iii-kvartala-2026-goda-na-pervichnom-rynke-biznes-klassa-moskvy-69232221/'),
    ('Т—Ж: банки отказываются от субсидированной ипотеки, ответ ЦБ, 12 сентября 2026', 'https://t-j.ru/ipoteka-developers/'),
    ('Chita.ru по материалам E1.RU: Сбер с 1 октября прекращает короткие субсидии застройщиков, 11 сентября 2026', 'https://www.chita.ru/text/realty/2026/09/11/76635775/'),
    ('РИА Недвижимость: Минстрой предложил рассрочку после ввода дома, 19 августа 2026', 'https://realty.ria.ru/20260819/minstroj-2111754431.html'),
    ('«Парламентская газета»: параметры законопроекта о рассрочке — три года после сдачи, 25 % квартир, 1 сентября 2027 года, 17 августа 2026', 'https://www.pnp.ru/economics/dolshhikam-mogut-razreshit-rassrochku-posle-novoselya.html'),
    ('ДОМ.РФ в пересказе ABN: каждая четвёртая сделка по ДДУ во II квартале — в рассрочку, 29 сентября 2026', 'https://abn.agency/2026/09/29/kazhdaya-chetvertaya-sdelka-po-ddu-vo-ii-kvartale-proshla-v-rassrochku/'),
    ('НДВ и Media Instinct в пересказе «Портал Воронеж»: длинные рассрочки в Москве, 20 мая 2026', 'https://portalvoronezh.ru/news/ekonomika/kvazi-ipoteka-kak-dlinnye-rassrochki-ot-developerov-stali-osnovnym-draiverom-sprosa-v-2026.html'),
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
            'рассрочка Level — 5 %, «0 %» в Шагале — до 27 %. Что изменилось с 1 октября и что спросить до брони.')
    ld = ld_list('Цена способа оплаты', desc, f'https://nota.expert/reytingi/{SLUG}/', [f'{r["developer"]} · {r["zhk"]}: {r["nazvanie"]}' for r in rs])
    page = HEAD.format(title=e(title), desc=e(desc), R=R, img='img/ix-2026-10-oplata-og.jpg', ld=ld)
    page += cover('img/ix-2026-10-oplata.jpg', 'План квартиры, договор и ключи на столе',
                  f'<b>Рейтинг</b><span>Способы оплаты</span><span>Октябрь 2026</span><span>{len(sh)} {plural(len(sh), "схема", "схемы", "схем")}</span>',
                  'Цена способа оплаты',
                  f'Одна и та же квартира стоит по-разному в зависимости от того, как вы за неё платите. Мы сверили {len(sh)} {plural(len(sh), "схему", "схемы", "схем")} оплаты у {len(devs)} застройщиков на {SVERKA} и посчитали, сколько на самом деле стоит рассрочка или субсидия — в процентах годовых, как ипотека.')
    page += f'''<section><div class="wrap jr-ed">
 <div><p class="ttl">На заметку:</p></div>
 <div>
  <div class="jr-ed-t">
   <p>Рассрочка — это кредит от застройщика, и бесплатной она не бывает: её цена — скидка, которую дают только за полную оплату. Мы посчитали это там, где застройщик назвал обе цены. У Level рассрочка на полгода стоит 5–7 % годовых — дешевле вклада. В Шагале у Эталона рассрочка до марта 2028 года на студии со скидкой 25 % обходится в 27 % годовых — дороже рыночной ипотеки.</p>
   <p>С 1 октября почти закончились короткие субсидии: ставки от 0,3 до 8,1 % на первые годы пропали из каталогов шести застройщиков нашей базы. Их место заняли рассрочки на два–четыре года и ипотека «на весь срок» под 12,4–13 %. Скидки за полную оплату застройщики не уменьшают: Level держит до 35 %, Гранель подняла выгоду до 27 %. Половина действующих условий — до 31 октября.</p>
   <p>Правило одно: до брони спросите цену квартиры при 100 % оплате и при вашей схеме. Разница — это цена рассрочки. Сравните её с вкладом и ипотекой по шкале ниже.</p>
  </div>
 </div>
</div></section>
<section style="padding-top:0"><div class="wrap">
 <div class="strip" style="margin-top:0">
  <div><b>{len(sh)}</b><small>{plural(len(sh), "схема", "схемы", "схем")} у {len(devs)} застройщиков сверили {SVERKA}, {len(act)} действуют</small></div>
  <div><b>5{NB}%</b><small>годовых — самая дешёвая рассрочка: Level, полгода, скидка сохраняется</small></div>
  <div><b>27{NB}%</b><small>годовых — рассрочка «0 %» в Шагале, если за полную оплату на студию дают скидку 25 %</small></div>
  <div><b>{len(both)} из {len(devs)}</b><small>застройщиков называют цену одной квартиры и при 100 % оплате, и при другой схеме</small></div>
 </div>
</div></section>
'''
    page += f'''<section class="method" id="spisok"><div class="wrap" data-rlist data-lim="20">
 <div class="two">
  <div><p class="ttl">Рейтинг</p><h2 style="margin-top:20px">Сколько на самом деле стоит рассрочка —<br>от дешёвой к дорогой</h2></div>
  <div><p class="lede">Точка отсчёта — цена той же квартиры при 100 % оплате сегодня. Всё, что вы платите сверх неё позже, — плата за отсрочку. Мы перевели её в проценты годовых и сравнили с вкладом ({fmt(VKLAD, 2)} %) и рыночной ипотекой ({fmt(IPOTEKA, 1)} %). Откройте строку: там условия, пример в рублях и что важно знать.</p></div>
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
    cards = ''.join(f'<div class="lv"><span class="ttl">{e(a.format(n=len(devs) - len(both)))}</span><b>{e(ty(b))}</b><p>{e(ty(c))}</p></div>' for a, b, c in ODNA)
    page += f'''<section id="odna-kvartira"><div class="wrap">
 <div class="two">
  <div><p class="ttl">Одна квартира</p><h2 style="margin-top:20px">Цену при каждой схеме называют {len(both)} застройщиков из {len(devs)}</h2></div>
  <div><p class="lede">Остальные пишут «скидка до…» и «рассрочка 0 %», а цену при рассрочке называют в офисе продаж. Вот где застройщик сам сказал, насколько та же квартира дороже при другом способе оплаты, чем при 100 % оплате.</p></div>
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
        ('Почему посчитали не всё', f'Из {len(devs)} застройщиков цену одной квартиры и при 100 % оплате, и при другой схеме называют {len(both)}. Остальные пишут «скидка до…» и «рассрочка 0 %», а цену при рассрочке называют в офисе продаж. Их схемы — в списке «Все схемы» со статусом на {SVERKA}.'),
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
