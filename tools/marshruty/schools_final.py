import pickle, math, re, json
import numpy as np
from collections import defaultdict, Counter
exec(open('match_schools.py',encoding='utf-8').read().split("# ---------- база 488")[0])
M=pickle.load(open('out/match3.pkl','rb')); base=M['base']; out=M['out']
def translit(s):
    tbl=dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','sch','','y','','e','yu','ya']))
    out=''.join(tbl.get(c,c) for c in s.lower())
    return re.sub(r'[^a-z0-9]+','-',out).strip('-')[:60]
GENERAL=re.compile(r'школ|гимнази|лице|сош\b|центр образования|образовательный центр|кадетск|пансион|интернат', re.I)
NOTGENERAL=re.compile(r'глух|слеп|слабо|коррекц|ОВЗ|ограниченн|санатор|больниц|здоровья|воскресн|православн.*воскресн|вечерн|коррекц|для пациентов|надомн|дополнительного|досуг|творчеств|ЦПМСС|реабилит|семинари|академия|университет|институт|колледж|училищ|техникум|детский сад|дошкол', re.I)
used=set(); ubld=[]
for b in base:
    r=out[b['sid']]
    for g in r['buildings']:
        if g['osm']: used.add(g['osm'])
        ubld.append((g['x'],g['y']))
ubld=np.array(ubld)
others=[]
for f in feats:
    if f['osm'] in used or f['excl'] or f['amenity'] not in ('school',''): continue
    nm=f['name'] or ''
    if not nm or not GENERAL.search(nm) or NOTGENERAL.search(nm): continue
    if len(ubld) and np.min(np.hypot(ubld[:,0]-f['x'],ubld[:,1]-f['y']))<80: continue
    others.append(f)
# группировка в организации
def okey(f):
    if f['num']: return 'n%d'%f['num']
    k=re.sub(r'[«»"“”\'().,]',' ',f['name'].lower())
    k=re.sub(r'\b(корпус|здание|учебн\w*|основное|отделение|подразделение|структурное|начальн\w*|школьн\w*|№|\d+)\b',' ',k)
    return 'm'+' '.join(k.split()[:4])
groups=defaultdict(list)
for f in others: groups[okey(f)].append(f)
orgs=[]
for k,fs in groups.items():
    # делим по кластерам 4 км
    rest=list(fs)
    while rest:
        seed=rest[0]; cl=[g for g in rest if math.hypot(g['x']-seed['x'],g['y']-seed['y'])<=4000]
        rest=[g for g in rest if g not in cl]
        ded=[]
        for g in cl:
            if all(math.hypot(g['x']-h['x'],g['y']-h['y'])>60 for h in ded): ded.append(g)
        nm=sorted([g['name'] for g in ded], key=len)[0]
        if seed['num']: nm=re.sub(r'\s*[\.,(].*$','',nm) if re.match(r'^(Школа|Гимназия|Лицей|Центр образования)\s*№',nm) else nm
        orgs.append(dict(name=nm, num=seed['num'], buildings=[dict(osm=g['osm'], name=g['name'], lon=g['lon'], lat=g['lat'], x=g['x'], y=g['y'], geom=g['geom'], src='OSM') for g in ded], district=seed['district']))
print('other OSM schools (orgs):', len(orgs), 'buildings', sum(len(o['buildings']) for o in orgs))
print(Counter('Москва' if o['district'] else 'область/край' for o in orgs))
for o in orgs[:40]: print('  ', o['name'], '|', o['district'], '|', len(o['buildings']))
S=[]
for b in base:
    r=out[b['sid']]
    if r['status'] in ('дубль','спортивная академия — не школа','не найдено'): continue
    S.append(dict(sid=b['sid'], name=b['name'], category=b['category'], tier=b['tier'] or '', index=b['index'], district=b['district'], okrug=b['okrug'], address=b['address'], site=b['site'], why=b['why'], grant=b['grant'],
                  in_base=True, geo_status=r['status'], buildings=r['buildings']))
for i,o in enumerate(orgs):
    S.append(dict(sid='osm-%d-%s'%(i, translit(o['name'])[:30]), name=o['name'], category='Другая', tier='', index=None, district=o['district'], okrug='', address='', site='', why='', grant='',
                  in_base=False, geo_status='корпуса OSM', buildings=o['buildings']))
print('final schools', len(S), Counter(s['category'] for s in S), 'buildings', sum(len(s['buildings']) for s in S))
notfound=[dict(name=b['name'], category=b['category'], district=b['district'], tier=b['tier'], status=out[b['sid']]['status'], dup_of=out[b['sid']].get('dup_of','')) for b in base if out[b['sid']]['status'] in ('дубль','спортивная академия — не школа','не найдено')]
pickle.dump(dict(schools=S, notfound=notfound), open('out/schools_final.pkl','wb'))
