import pickle, math, re, json
import numpy as np
from collections import Counter, defaultdict
exec(open('match_schools.py',encoding='utf-8').read().split("results={}")[0])

def in_moscow_extract(f): return f['src']=='bbbike' or f['district']!=''
def cluster(fs, center=None, R=4500):
    if not fs: return fs
    xs=np.array([f['x'] for f in fs]); ys=np.array([f['y'] for f in fs])
    if center is None:
        best=None
        for i in range(len(fs)):
            n=((xs-xs[i])**2+(ys-ys[i])**2<=R*R).sum()
            if best is None or n>best[0]: best=(n,i)
        cx,cy=xs[best[1]],ys[best[1]]
    else: cx,cy=center
    return [f for f,x,y in zip(fs,xs,ys) if math.hypot(x-cx,y-cy)<=R]

GENERIC={'Образовательный центр «Протон»','Школа «Глория»','Школа «Интеграл»','Школа «Содружество»','Школа «Олимп-Плюс»','Медико-биологическая школа «Вита»','Школа «Президент»','Школа «Наследник»','Школа «Лидер»','Школа «Столичный - КИТ»','Школа «Столица-КИТ»','Средняя школа «Знайка»','Школа «Знайка»','Школа им. В.В. Маяковского','Школа имени Маяковского','Школа им. Ф.М. Достоевского','Школа им. И.С. Полбина','Школа им. Е.Н. Чернышева','Школа им. Артёма Боровика','Школа им. А. Боровика','Школа «НИКА»','Школа «Алгоритм»','Новая школа','Первая школа','Школа «Свиблово»','Школа «Дмитровский»','Школа «Светлые горы»','Школа «Классика-М»','Лицей РАНХиГС','Лицей Президентской академии РАНХиГС','Академическая гимназия'}
MANUAL_ADDR={'Школа «Дмитровский»':'Карельский б-р, д. 20'}
MANUAL_PT={'Школа «ШИК 16»':(37.64556,55.82578,'OSM w92162854 (social_facility)')}
HIGH=('дом','объект (школа в OSM)','объект (отделение школы в OSM)')
def get_anchor(b):
    if 'prev' in b and b['prev'][2] in HIGH: return (b['prev'][0],b['prev'][1]), 'дом'
    g=geocode(MANUAL_ADDR.get(b['name'], b['address']))
    if g: return (g[0],g[1]), 'адрес'
    if b['name'] in MANUAL_PT: return MANUAL_PT[b['name']][:2], 'дом'
    if 'prev' in b and b['prev'][2].startswith('здание'): return (b['prev'][0],b['prev'][1]), 'здание по номеру'
    if 'prev' in b and b['prev'][2].startswith('улица'): return (b['prev'][0],b['prev'][1]), 'улица'
    return None, None

out={}
for b in base:
    rec=dict(sid=b['sid'], status='', buildings=[], anchor=None, anchor_how=None, how='')
    out[b['sid']]=rec
    if b['category']=='Спортивная' and b['name'] not in SPORT_KEEP:
        rec['status']='спортивная академия — не школа'; continue
    cands=[]
    if b['num'] is not None and (b['category']!='Частная' or b['num']>=100):
        cands=list(bynum.get(b['num'],[])); rec['how']='номер'
    named_ids=set()
    if b['name'] in NAMED:
        rx=re.compile(NAMED[b['name']])
        c2=[f for f in feats if rx.search(f['allnames']) and not (f['excl'] and b['category']!='Вузовская')]
        cands+=[f for f in c2 if f not in cands]; rec['how']=(rec['how']+'+название').strip('+')
        if b['name'] not in GENERIC: named_ids={f['osm'] for f in c2}
    anc, anc_how = get_anchor(b)
    rec['anchor'], rec['anchor_how'] = anc, anc_how
    keep=[]
    if anc:
        ax,ay=TR.transform(*anc)
        R = 4500 if anc_how in ('дом','адрес') else 5500
        keep=[f for f in cands if math.hypot(f['x']-ax,f['y']-ay)<=(12000 if f['osm'] in named_ids else R)]
        # вузовские: если нашлись только университеты, а адрес есть — оставляем адрес
        if b['category']=='Вузовская' and keep and all(f['amenity']=='university' for f in keep): keep=[]
    else:
        d=norm_d(b['district'])
        if d and d in DPOLY:
            keep=[f for f in cands if (in_district(f,b) or 0)<=1500]
        if not keep and b['category'] in ('Городская','Вузовская') and ((b['num'] or 0)>=30 or b['name'] in NAMED):
            keep=cluster([f for f in cands if in_moscow_extract(f)])
        if not keep and b['category']=='Частная' and b['name'] in NAMED:
            keep=list(cands)
        if not keep and b['category']=='Спортивная' and b['name'] in NAMED:
            keep=cluster(cands)
    # дедуп корпусов (60 м)
    ded=[]
    for f in sorted(keep, key=lambda f:(f['geom'] is None, 'корпус' not in f['name'].lower())):
        if all(math.hypot(f['x']-g['x'],f['y']-g['y'])>60 for g in ded): ded.append(f)
    blds=[dict(osm=f['osm'], name=f['name'] or f['allnames'][:80], lon=f['lon'], lat=f['lat'], x=f['x'], y=f['y'], geom=f['geom'], src='OSM') for f in ded]
    # опорный адрес как отдельная точка, если далеко от найденных корпусов
    if anc and anc_how in ('дом','адрес'):
        ax,ay=TR.transform(*anc)
        if not blds or min(math.hypot(g['x']-ax,g['y']-ay) for g in blds)>300:
            blds.append(dict(osm='', name=('адрес: '+b['address'])[:80] if b['address'] else 'адрес из базы', lon=anc[0], lat=anc[1], x=ax, y=ay, geom=None, src='адрес'))
    elif anc and not blds:
        ax,ay=TR.transform(*anc)
        blds.append(dict(osm='', name='примерно: '+anc_how, lon=anc[0], lat=anc[1], x=ax, y=ay, geom=None, src=anc_how))
    rec['buildings']=blds
    if not blds: rec['status']='не найдено'
    elif all(g['src'] in ('здание по номеру','улица') for g in blds): rec['status']='примерно'
    elif any(g['src']=='OSM' for g in blds): rec['status']='корпуса OSM'
    else: rec['status']='адрес'

# дубли базы: одинаковые наборы корпусов
sig=defaultdict(list)
for b in base:
    r=out[b['sid']]
    if r['buildings']: sig[tuple(sorted((round(g['lon'],4),round(g['lat'],4)) for g in r['buildings']))].append(b)
for k,bs in sig.items():
    if len(bs)>1:
        bs=sorted(bs, key=lambda b:(b['tier']=='', b['district']=='', -(b['index'] or 0)))
        for d in bs[1:]:
            out[d['sid']]['status']='дубль'; out[d['sid']]['dup_of']=bs[0]['sid']
        print('DUP', [b['name'] for b in bs])
print(Counter(r['status'] for r in out.values()))
print('buildings', sum(len(r['buildings']) for r in out.values() if r['status'] not in ('дубль',)))
inext=lambda b: True
for b in base:
    r=out[b['sid']]
    if r['status'] in ('не найдено','примерно'):
        print('  ', r['status'],'|',b['name'],'|',b['category'],'|',b['district'],'|',b['tier'],'|',b['address'][:40])
pickle.dump(dict(base=base, out=out), open('out/match3.pkl','wb'))
