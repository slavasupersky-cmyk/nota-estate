import pickle, json, csv, math, numpy as np
from collections import Counter
R=pickle.load(open('out/routes_raw.pkl','rb')); pts=R['pts']; snap=R['snap_d']
O=pickle.load(open('out/outputs.pkl','rb'))
S=pickle.load(open('out/schools_final.pkl','rb'))['schools']
ZHK=list(csv.DictReader(open('/mnt/user-data/uploads/nota-estate/data/zhk-moskva-biznes-plus-geo.csv',encoding='utf-8-sig'),delimiter=';'))
zsnap={p[1]:snap[k] for k,p in enumerate(pts) if p[0]=='z'}
def num(x):
    try: return int(float(x))
    except: return None
zhk=[[z['name'],z['developer'],z['class_final'],z['okrug'],z['district'],round(float(z['lat']),5),round(float(z['lon']),5),z['geo_precision'],num(z['units_total']),z['stage'],z['deadline'],num(z['price_from_m2']),z['website'],int(round(zsnap[i]))] for i,z in enumerate(ZHK)]
def short_why(s): return (s.get('why') or '')[:220]
schools=[[s['name'],s['category'],s['tier'],s['index'],s['district'],s['okrug'],1 if s['in_base'] else 0,short_why(s),s['site'],s['address'],
          [[round(g['lat'],5),round(g['lon'],5),g['name'][:90],g['src']] for g in s['buildings']]] for s in S]
pairs=[[p['zi'],p['si'],p['bi'],int(round(p['m'])),int(round(p['straight'])),p['rid']] for p in O['pairs']]
meta=dict(speed_m_min=75, osm_moscow='BBBike, выгрузка OpenStreetMap от 19.09.2026', osm_west='Overpass (зеркало maps.mail.ru), 23.09.2026', built='23.09.2026')
D=dict(meta=meta, zhk=zhk, schools=schools, pairs=pairs, routes=O['routes'])
s=json.dumps(D, ensure_ascii=False, separators=(',',':'))
open('out/data.json','w',encoding='utf-8').write(s)
print('data.json %.2f MB'%(len(s.encode())/1e6), 'zhk',len(zhk),'schools',len(schools),'pairs',len(pairs))
# статистика
zs=O['zsum']
n=len(zs)
def share(f): c=sum(1 for z in zs if f(z)); return '%d из %d (%d%%)'%(c,n,round(100*c/n))
city=[z for z in zs if ZHK[z['zi']]['okrug'] not in ('Рублёвка',)]
nc=len(city)
def cshare(f): c=sum(1 for z in city if f(z)); return '%d из %d (%d%%)'%(c,nc,round(100*c/nc))
print('город (без Рублёвки):', nc)
print(' любая школа ≤10 мин:', cshare(lambda z: z['near'] and z['near'][0]<=10))
print(' школа базы ≤10:', cshare(lambda z: z['c10']>0), ' ≤15:', cshare(lambda z: z['c15']>0), ' ≤20:', cshare(lambda z: z['c20']>0))
print(' с отметкой ≤20:', cshare(lambda z: z['m20']>0), ' ≤30:', cshare(lambda z: z['m30']>0))
near=np.array([z['near'][0] for z in city if z['near']]); print(' медиана до ближайшей любой школы', np.median(near), 'мин')
nb=np.array([z['nearb'][0] for z in city if z['nearb']]); print(' медиана до ближайшей школы базы', np.median(nb), 'мин')
top=sorted(city, key=lambda z:(-z['m20'],-z['c20']))[:12]
print(' больше всего отмеченных школ ≤20 мин:', [(ZHK[z['zi']]['name'],z['m20'],z['c20']) for z in top])
far=sorted(city, key=lambda z:-(z['near'][0] if z['near'] else 99))[:10]
print(' дальше всех от любой школы:', [(ZHK[z['zi']]['name'],z['near'][0] if z['near'] else None) for z in far])
bycls=Counter(); bycls_m=Counter()
for z in city:
    c=ZHK[z['zi']]['class_final']; bycls[c]+=1; bycls_m[c]+= (z['m20']>0)
print(' отметка ≤20 по классам:', {c:'%d/%d'%(bycls_m[c],bycls[c]) for c in bycls})
# школы с отметкой: сколько ЖК ≤15
bys=O['bys']
lst=[]
for si,s in enumerate(S):
    if s['tier']=='Отметка':
        c=sum(1 for t,zi in bys.get(si,[]) if t<=15*75)
        lst.append((c,s['name']))
lst.sort(reverse=True); print(' отметка: больше всего домов ≤15 мин:', lst[:10])
print(' отметка без единого дома ≤20 мин:', sum(1 for si,s in enumerate(S) if s['tier']=='Отметка' and not any(t<=20*75 for t,zi in bys.get(si,[]))), 'из', sum(1 for s in S if s['tier']=='Отметка'))
