import pickle, json, re, csv, math
import numpy as np
from collections import Counter, defaultdict
from shapely import wkb
from shapely.geometry import Point
from shapely.strtree import STRtree
from pyproj import Transformer
TR=Transformer.from_crs('EPSG:4326','EPSG:32637',always_xy=True)

F=pickle.load(open('out/features.pkl','rb'))
BASE=json.load(open('schools-artifact-data.json',encoding='utf-8'))['__SCHOOLS__']
GEO={g['name']:g for g in csv.DictReader(open('/mnt/user-data/uploads/nota-estate/data/index-2026-09-shkoly-geo.csv',encoding='utf-8-sig'),delimiter=';')}

# ---------- районы ----------
districts=[]
for a in F['admin']:
    if a['level']=='8':
        g=wkb.loads(a['geom']); nm=a['name']
        nm=re.sub(r'^район\s+','',nm); nm=re.sub(r'\s+район$','',nm)
        districts.append((nm,g))
def norm_d(s):
    s=(s or '').lower().replace('ё','е')
    s=re.sub(r'^район\s+|\s+район$','',s)
    s=re.sub(r'ский$|ская$|ское$','',s)
    return s.strip()
DPOLY={norm_d(n):g for n,g in districts}
dtree=STRtree([g for _,g in districts])
def district_of(lon,lat):
    p=Point(lon,lat)
    for i in dtree.query(p):
        if districts[i][1].contains(p): return districts[i][0]
    return ''

# ---------- OSM-школы ----------
EXCL=re.compile(r'музык|художеств|искусств|автошкол|ДЮСШ|СДЮШОР|СШОР|спортивн|танц|балет|ДШИ|ДМШ|ДХШ|творчеств|досуг|языков|english|курс|колледж|техникум|училищ|детский сад|ясли|вожден|шахмат|плаван|воскресн|дошкол|Дошкол|раннего развития|бариста|барменов|семинари|институт|университет(?! ?[«"]?гимназ)|реабилитац|ЦПМСС|психолого|лечебной педагогики|детско-юношеск|юношеск|спорткомплекс|спортбаза|физкультурно|ФОК|Центр дополнительного|ЦВР|ЦДТ|ДДТ|хоров|Montessori|Playschool|Bambini|кружок|клуб|Лига Роботов|Школа Английского|игровая|лингвистический центр|Лингвистический центр', re.I)
NUMRE=[re.compile(r'(?:№|#|N°|No\.?)\s*(\d{1,4})\b'), re.compile(r'(?:школа|гимназия|лицей|цо|центр образования|спецшкола|интернат|школа-интернат)\s*(\d{2,4})\b', re.I)]
def fnames(t):
    return [t.get(k,'') for k in ('name','official_name','short_name','alt_name','old_name','operator','name:ru') if t.get(k)]
def orgnum(t):
    for s in fnames(t)[:3]:
        for rx in NUMRE:
            m=rx.search(s)
            if m: return int(m.group(1))
    if t.get('ref','').isdigit(): return int(t['ref'])
    return None

feats=[]
for f in F['feat']:
    t=f['tags']
    if not (f['amenity'] in ('school','college','university') or (f['building']=='school')): continue
    nm=' | '.join(fnames(t))
    x,y=TR.transform(f['lon'],f['lat'])
    feats.append(dict(osm=f['osm'], src=f['src'], amenity=f['amenity'], building=f['building'] or t.get('building',''), name=t.get('name',''), allnames=nm,
                      num=orgnum(t), lon=f['lon'], lat=f['lat'], x=x, y=y, geom=f['geom'], excl=bool(EXCL.search(nm)),
                      street=t.get('addr:street',''), hn=t.get('addr:housenumber','')))
print('osm school-ish features', len(feats), 'numbered', sum(1 for f in feats if f['num']), 'excluded', sum(1 for f in feats if f['excl']))
for f in feats: f['district']=district_of(f['lon'],f['lat'])

# ---------- адресный индекс ----------
ABBR={'ул':'улица','пр-т':'проспект','просп':'проспект','пр-кт':'проспект','пер':'переулок','ш':'шоссе','б-р':'бульвар','бул':'бульвар',
      'пр-д':'проезд','наб':'набережная','пл':'площадь','туп':'тупик','мкр':'микрорайон','кв-л':'квартал','стр':'строение'}
DROP={'г','москва','город','д'}
def norm_street(s):
    s=s.lower().replace('ё','е')
    toks=[]
    for t in re.findall(r'[\w-]+\.?', s):
        t=t.rstrip('.')
        t=ABBR.get(t,t)
        if t and t not in DROP: toks.append(t)
    return ' '.join(sorted(toks))
def norm_hn(s):
    s=s.lower().replace('ё','е').replace('c','с').replace('k','к')
    s=re.sub(r'корпус|корп\.?','к',s); s=re.sub(r'строение|стр\.?','с',s); s=re.sub(r'владение|вл\.?','',s); s=re.sub(r'^д\.?\s*','',s.strip())
    s=re.sub(r'[\s,]','',s)
    return s
AIDX=defaultdict(list)
for st,hn,lon,lat,oid in F['addr']:
    AIDX[(norm_street(st),norm_hn(hn))].append((lon,lat,oid))
def parse_addr(a):
    # 'ул. Фотиевой, д. 18' ; 'Олимпийский пр-т, д. 11, корп. 1'
    a=a.split(';')[0].split('+')[0].split('(')[0]
    parts=[p.strip() for p in a.split(',')]
    if len(parts)<2: return None
    st=parts[0]
    hn=''
    for p in parts[1:]:
        p2=p.lower()
        if p2.startswith('д.') or re.match(r'^\d',p2): hn+=re.sub(r'^д\.\s*','',p2)
        elif p2.startswith('корп'): hn+='к'+re.sub(r'^корп\.?\s*','',p2)
        elif p2.startswith('стр'): hn+='с'+re.sub(r'^стр\.?\s*','',p2)
    if not hn: return None
    return norm_street(st), norm_hn(hn)
def geocode(a):
    k=parse_addr(a or '')
    if not k: return None
    r=AIDX.get(k)
    if r: return r[0]
    # без строения/корпуса
    for alt in (k[1].replace('к','#').replace('с','к').replace('#','с'), re.sub(r'[кс].*$','',k[1])):
        r=AIDX.get((k[0],alt))
        if r: return r[0]
    return None

# ---------- база 488 ----------
def translit(s):
    tbl=dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','sch','','y','','e','yu','ya']))
    s=s.lower()
    out=''.join(tbl.get(c,c) for c in s)
    out=re.sub(r'[^a-z0-9]+','-',out).strip('-')
    return out[:60]
NAMED={
 'Лицей «Вторая школа» им. В.Ф. Овчинникова': r'Вторая\s+[Шш]кола',
 'Пятьдесят седьмая школа': r'Пятьдесят седьмая|(?:№|#)\s*57\b|Школа\s+57\b',
 'Лицей «Воробьёвы горы»': r'Воробь[её]вы\s+[Гг]оры',
 'Школа на Юго-Востоке им. В.И. Чуйкова': r'на Юго-Востоке',
 'Курчатовская школа': r'Курчатовская школа',
 'Школа «Интеллектуал»': r'Интеллектуал',
 'Школа «Покровский квартал»': r'Покровский квартал',
 'Школа «Марьина Роща» им. В.Ф. Орлова': r'Марьина Роща им',
 'Школа на проспекте Вернадского': r'на проспекте Вернадского',
 'Образовательный центр «Протон»': r'Протон',
 'Школа «Глория»': r'Глория',
 'Школа «Интеграл»': r'Интеграл\b',
 'Первый Московский кадетский корпус': r'Первый Московский кадетский',
 'Пансион воспитанниц Министерства обороны РФ': r'Пансион воспитанниц',
 'Пансион воспитанниц МО РФ': r'Пансион воспитанниц',
 'Школа «Свиблово»': r'Школа Свиблово|Школа «Свиблово»|Школа "Свиблово"',
 'Школа права и экономики': r'права и экономики',
 'Школа в Некрасовке': r'в Некрасовке',
 'Школа им. Артёма Боровика': r'Боровика',
 'Школа им. А. Боровика': r'Боровика',
 'Международная школа смешанного обучения': r'смешанного обучения',
 'Школа «Дмитровский»': r'Школа «Дмитровский»|Школа "Дмитровский"',
 'Школа «Технологии обучения»': r'Технологии обучения',
 'Школа им. В.В. Маяковского': r'Маяковского',
 'Школа имени Маяковского': r'Маяковского',
 'Школа «ШИК 16»': r'ШИК\s*-?\s*16',
 'Школа сотрудничества': r'[Сс]отрудничества',
 'Средняя школа «Знайка»': r'Знайка',
 'Школа «Знайка»': r'Знайка',
 'Школа в Капотне': r'в Капотне',
 'Школа «Бескудниково»': r'Бескудниково',
 'Школа им. И.С. Полбина': r'Полбина',
 'Школа им. Ф.М. Достоевского': r'Достоевского',
 'Медико-биологическая школа «Вита»': r'Вита\b',
 'Романовская школа': r'Романовская школа',
 'Школа «Содружество»': r'Содружество',
 'Школа «Южное Измайлово»': r'Южное Измайлово',
 'Школа Новокосино': r'Школа Новокосино|Школа «Новокосино»|Школа "Новокосино"',
 'Школа им. Е.Н. Чернышева': r'Чернышева',
 'Школа на Яузе': r'на Яузе',
 'Школа «Олимп-Плюс»': r'Олимп',
 'Центр образования и спорта «Москва-98»': r'Москва-98',
 'ЦОиС «Москва-98»': r'Москва-98',
 'Лицей РАНХиГС': r'РАНХиГС',
 'Лицей Президентской академии РАНХиГС': r'РАНХиГС',
 'Международная Ломоносовская гимназия': r'Ломоносовская гимназия',
 'Международная школа завтрашнего дня': r'завтрашнего дня',
 'Новая гуманитарная школа': r'Новая гуманитарная школа',
 'Первая Московская гимназия': r'Первая Московская гимназия',
 'Первая школа': r'Первая [Шш]кола',
 'Учебный центр «Наука-Сервис»': r'Наука-Сервис',
 'Школа «Лидер»': r'Школа «Лидер»|Школа "Лидер"',
 'Школа «Столичный - КИТ»': r'КИТ\b',
 'Школа «Столица-КИТ»': r'КИТ\b',
 'Инженерно-техническая школа им. П.Р. Поповича': r'Поповича',
 'Первый Московский образовательный комплекс': r'Первый Московский образовательный',
 'Школа «Марьино» им. А.Е. Голованова': r'Голованова',
 'Вешняковская школа': r'Вешняковская',
 'Школа им. В.В. Маяковского ': r'Маяковского',
 'Школа Центра педагогического мастерства (ЦПМ)': r'ЦПМ|Центр педагогического мастерства',
 'Школа «Летово»': r'Летово|Letovo',
 'Классический пансион МГУ': r'Классический пансион',
 'Ломоносовская школа': r'Ломоносовская школа',
 'Частная школа «Золотое сечение»': r'Золотое сечение',
 'Областная гимназия им. Е.М. Примакова': r'Примакова',
 'Ломоносовская школа «ИнТек»': r'ИнТек',
 'Хорошевская школа (Хорошкола)': r'Хорошкол|Хорош[её]вская школа',
 'Академическая гимназия': r'Академическая [Гг]имназия',
 'Павловская гимназия': r'Павловская гимназия',
 'Школа «НИКА»': r'Ника\b|НИКА\b',
 'Школа «Алгоритм»': r'Алгоритм\\b',
 'Международная школа «Интеграция XXI век»': r'Интеграция XXI',
 'Гимназия Святителя Василия Великого': r'Василия Великого',
 'Школа «Классика-М»': r'Классика-М',
 'Школа «Светлые горы»': r'Светлые горы',
 'Школа «Солнечный ветер»': r'Солнечный ветер',
 'Новая школа': r'^Новая школа',
 'Международная гимназия «Сколково»': r'Гимназия Сколково|гимназия «Сколково»|гимназия "Сколково"',
 'Cambridge International School (CIS)': r'Кембриджская международная школа|Cambridge International',
 'Британская международная школа (BIS)': r'Британская [Мм]еждународная|British International',
 'Международная школа Москвы (ISM)': r'International School of Moscow|Международная школа Москвы',
 'Школа «Президент»': r'Президент\b',
 'Heritage School': r'Heritage',
 'Wunderpark International School': r'Wunderpark',
 'Европейская гимназия': r'Европейская гимназия',
 'Инновационная школа «Сколка»': r'Сколка',
 'Russian International School (RIS)': r'Russian International|RIS\b',
 'Школа «Наследник»': r'Наследник',
 'Ломоносовская школа-пансион № 5': r'Ломоносовская школа\s*№\s*5|Ломоносовская школа-пансион',
 'Лицей НИУ ВШЭ': r'Лицей НИУ ВШЭ|Лицей ВШЭ|[Лл]ицей.*Высш(ая|ей) школ',
 'СУНЦ МГУ (школа-интернат им. А.Н. Колмогорова)': r'Специализированный учебно-научный центр МГУ|СУНЦ|Колмогорова|Школа-интернат МГУ',
 'Лицей Финансового университета': r'Финансового университета|Финуниверситет',
 'Университетская гимназия МГУ имени М.В. Ломоносова': r'Университетская гимназия',
 'Предуниверситарий МИФИ': r'Предуниверситари.*МИФИ|МИФИ.*[Пп]редуниверсит|Лицей МИФИ',
 'Экономический лицей РЭУ им. Г.В. Плеханова': r'Экономический лицей|Лицей РЭУ',
 'Медицинский Сеченовский Предуниверсарий': r'Сеченовский [Пп]редунив',
 'Предуниверситарий МГЛУ': r'Предуниверситари.*лингвистическ|Предуниверситарий МГЛУ',
 'Предуниверсарий МАИ': r'Предунивер.*МАИ',
 'Предуниверсарий РГГУ': r'Предунивер.*РГГУ',
 'ЦСиО «Самбо-70»': r'Самбо-70',
 'Спортивный интернат «Чертаново»': r'ЦСО\s*"?Чертаново|Интернат ЦСО',
 'ЦСиО «МЭШ» (Московская экспериментальная школа)': r'МЭШ|Экспериментальная школа',
 'Центр образования и спорта «Локомотив»': r'Локомотив',
}
SPORT_KEEP={'ЦСиО «Самбо-70»','Спортивный интернат «Чертаново»','ЦОиС «Москва-98»','ЦСиО «МЭШ» (Московская экспериментальная школа)','Центр образования и спорта «Локомотив»'}

base=[]
seen=set()
for s in BASE:
    sid=translit(s['name'])
    while sid in seen: sid+='-2'
    seen.add(sid)
    m=re.search(r'№\s*(\d+)', s['name'])
    num=int(m.group(1)) if m else None
    if s['name']=='Пятьдесят седьмая школа': num=57
    b=dict(sid=sid, name=s['name'], category=s['category'], district=s.get('district') or '', okrug=s.get('okrug') or '', address=s.get('address','') or '',
           index=s.get('index'), tier=s.get('tier',''), num=num, why=s.get('why',''), site=s.get('site',''), grant=s.get('grant',''))
    g=GEO.get(s['name'])
    if g and g.get('lat'):
        b['prev']=(float(g['lon']),float(g['lat']),g['geo_precision'])
    base.append(b)

def dist_m(lon1,lat1,lon2,lat2):
    x1,y1=TR.transform(lon1,lat1); x2,y2=TR.transform(lon2,lat2); return math.hypot(x1-x2,y1-y2)

bynum=defaultdict(list)
for f in feats:
    if f['num'] and not f['excl']: bynum[f['num']].append(f)

def anchor(b):
    """опорная точка для проверки: прежний геокод (дом/объект) или адрес из базы"""
    if 'prev' in b and b['prev'][2] in ('дом','объект (школа в OSM)','объект (отделение школы в OSM)'): return b['prev'][:2], 'prev:'+b['prev'][2]
    g=geocode(b['address'])
    if g: return (g[0],g[1]), 'addr'
    if 'prev' in b and b['prev'][2].startswith('здание'): return b['prev'][:2], 'prev:здание'
    return None, None

def in_district(f, b):
    d=norm_d(b['district'])
    if not d or d not in DPOLY: return None
    g=DPOLY[d]
    x=Point(f['lon'],f['lat'])
    if g.contains(x): return 0.0
    # расстояние до района в метрах (приблизительно)
    return g.distance(x)*80000

results={}
for b in base:
    if b['category']=='Спортивная' and b['name'] not in SPORT_KEEP:
        results[b['sid']]=dict(status='спортивная — не школа', cands=[]); continue
    cands=[]; how=''
    if b['num'] is not None:
        cands=list(bynum.get(b['num'],[])); how='номер'
    if b['name'] in NAMED:
        rx=re.compile(NAMED[b['name']])
        c2=[f for f in feats if rx.search(f['allnames']) and not (f['excl'] and b['category']!='Вузовская')]
        if b['num'] is None: cands=c2; how='название'
        else: cands+= [f for f in c2 if f not in cands]
    anc, anc_how = anchor(b)
    # фильтр по месту
    keep=[]
    for f in cands:
        dd=in_district(f,b)
        da=dist_m(f['lon'],f['lat'],anc[0],anc[1]) if anc else None
        ok=False
        if da is not None and da<=4500: ok=True
        elif da is None and dd is not None and dd<=1500: ok=True
        elif da is None and dd is None and b['category']!='Городская': ok=True   # частные без адреса: берём как есть, проверим руками
        f2=dict(f); f2['d_anchor']=da; f2['d_district']=dd
        (keep if ok else f2.setdefault('rej',1) and None)
        if ok: keep.append(f2)
    status = 'OSM' if keep else ('адрес' if anc else 'не найдено')
    results[b['sid']]=dict(status=status, how=how, anchor=anc, anchor_how=anc_how, cands=keep, n_all=len(cands))

cnt=Counter(r['status'] for r in results.values())
print(cnt)
pickle.dump(dict(base=base, results=results, feats=feats), open('out/match.pkl','wb'))
# диагностика
nf=[b for b in base if results[b['sid']]['status'] in ('не найдено','адрес')]
print('not matched to OSM:', len(nf))
for b in nf: print('  ', results[b['sid']]['status'], '|', b['name'], '|', b['category'], '|', b['district'], '|', b['address'][:50], '| cands', results[b['sid']]['n_all'], '|', b['tier'])
