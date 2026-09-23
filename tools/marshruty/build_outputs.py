import numpy as np, pickle, csv, json, math, re, time
import shapely
from shapely import wkb
from shapely.geometry import LineString, Polygon, MultiPolygon
from pyproj import Transformer
from collections import Counter, defaultdict
TR=Transformer.from_crs('EPSG:4326','EPSG:32637',always_xy=True)
TRI=Transformer.from_crs('EPSG:32637','EPSG:4326',always_xy=True)
SPEED=75.0  # м/мин = 4,5 км/ч
R=pickle.load(open('out/routes_raw.pkl','rb')); res=R['res']; pts=R['pts']; snap=R['snap_d']
XY=np.load('out/xy_all.npy')
SF=pickle.load(open('out/schools_final.pkl','rb')); S=SF['schools']
ZHK=list(csv.DictReader(open('/mnt/user-data/uploads/nota-estate/data/zhk-moskva-biznes-plus-geo.csv',encoding='utf-8-sig'),delimiter=';'))
zxy=[TR.transform(float(z['lon']),float(z['lat'])) for z in ZHK]
zv={p[1]:k for k,p in enumerate(pts) if p[0]=='z'}

def enc(coords):  # Google polyline, precision 5, coords = [(lon,lat)]
    out=[]; plat=plon=0
    for lon,lat in coords:
        ilat=int(round(lat*1e5)); ilon=int(round(lon*1e5))
        for v in (ilat-plat, ilon-plon):
            v=~(v<<1) if v<0 else (v<<1)
            while v>=0x20:
                out.append(chr((0x20|(v&0x1f))+63)); v>>=5
            out.append(chr(v+63))
        plat,plon=ilat,ilon
    return ''.join(out)
def xy2ll(arr):
    lon,lat=TRI.transform(arr[:,0],arr[:,1]); return list(zip(lon,lat))

def mins(m): return int(round(m/SPEED))
def ylink(lat1,lon1,lat2,lon2,mode): return 'https://yandex.ru/maps/?rtext=%.6f,%.6f~%.6f,%.6f&rtt=%s'%(lat1,lon1,lat2,lon2,mode)
TIER_RANK={'Отметка':3,'На заметку':2,'Лучшая в районе':1,'':0}

pairs=[]   # dicts
routes=[]  # encoded
for zi,z in enumerate(ZHK):
    zx,zy=zxy[zi]
    for si,bi,t,path in sorted(res.get(zi,[]), key=lambda r:r[2]):
        if t>2250: continue
        s=S[si]; g=s['buildings'][bi]
        straight=math.hypot(g['x']-zx,g['y']-zy)
        rid=-1
        if path is not None:
            arr=XY[np.array(path)]
            arr=np.vstack([[zx,zy],arr,[g['x'],g['y']]])
            ls=LineString(arr).simplify(2.5)
            routes.append(enc(xy2ll(np.array(ls.coords))))
            rid=len(routes)-1
        pairs.append(dict(zi=zi,si=si,bi=bi,m=t,straight=straight,rid=rid))
print('pairs<=30min', len(pairs), 'routes', len(routes), 'route chars', sum(len(r) for r in routes))

# ---------- CSV ----------
ZSNAP={p[1]:snap[k] for k,p in enumerate(pts) if p[0]=='z'}
ZIDX={id(z):i for i,z in enumerate(ZHK)}
def prec_note(z):
    p=z['geo_precision']; notes=[]
    if not p.startswith('адрес'): notes.append('координаты дома приблизительные (%s) — минуты ±5'%p)
    d=ZSNAP.get(ZIDX[id(z)],0)
    if d>120: notes.append('точка дома в %d м от ближайшей пешеходной дорожки (стройплощадка или закрытая территория) — время ориентировочное'%round(d,-1))
    return '; '.join(notes)
BOM='﻿'
import os
os.makedirs('out/data',exist_ok=True)
with open('out/data/zhk-shkoly-peshkom.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter=';'); f.write(BOM)
    w.writerow(['zhk','developer','zhk_class','zhk_okrug','zhk_district','zhk_geo_precision','school','school_id','in_nota_base','school_type','school_tier','nota_index','building','building_lat','building_lon','walk_min','walk_m','straight_m','detour','note','yandex_walk','yandex_transit','yandex_car'])
    for p in pairs:
        z=ZHK[p['zi']]; s=S[p['si']]; g=s['buildings'][p['bi']]
        note=[prec_note(z)]
        if g['src']!='OSM': note.append('школа привязана к адресу, не к корпусу' if g['src'] in ('адрес','дом') else 'школа привязана примерно')
        la,lo=float(z['lat']),float(z['lon'])
        w.writerow([z['name'],z['developer'],z['class_final'],z['okrug'],z['district'],z['geo_precision'],s['name'],s['sid'],'да' if s['in_base'] else 'нет',s['category'],s['tier'],s['index'] if s['index'] is not None else '',
                    g['name'],'%.6f'%g['lat'],'%.6f'%g['lon'],mins(p['m']),int(round(p['m'])),int(round(p['straight'])),'%.2f'%(p['m']/max(p['straight'],1)),'; '.join(x for x in note if x),
                    ylink(la,lo,g['lat'],g['lon'],'pd'),ylink(la,lo,g['lat'],g['lon'],'mt'),ylink(la,lo,g['lat'],g['lon'],'auto')])

# сводка по ЖК
byz=defaultdict(list)
for p in pairs: byz[p['zi']].append(p)
allz=defaultdict(list)
for zi in range(len(ZHK)):
    for si,bi,t,path in res.get(zi,[]): allz[zi].append((t,si,bi))
base_idx=[si for si,s in enumerate(S) if s['in_base'] and s['index'] is not None]
def fmt_s(si,m=None,extra=''):
    s=S[si]; t=(s['tier'] or 'без пометки').lower()
    return '%s — %d мин · %s · %s'%(s['name'], mins(m), t, s['index'] if s['index'] is not None else '—')
zsum=[]
with open('out/data/zhk-shkoly-svodka.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter=';'); f.write(BOM)
    w.writerow(['zhk','developer','zhk_class','okrug','district','geo_precision','nearest_school','nearest_school_min','nearest_nota_school','nearest_nota_min','nota_10','nota_15','nota_20','nota_30','marked_20','marked_30','zametka_30','best_20','best_30','strong_5km_straight','note'])
    for zi,z in enumerate(ZHK):
        lst=sorted(allz[zi]); nb=[(t,si) for t,si,bi in lst if S[si]['in_base']]
        near=lst[0] if lst else None; nearb=nb[0] if nb else None
        c=lambda lim: sum(1 for t,si in nb if t<=lim*SPEED)
        mk=lambda lim, tier: sum(1 for t,si in nb if t<=lim*SPEED and S[si]['tier']==tier)
        def best(lim):
            cand=[(-(S[si]['index'] or 0),t,si) for t,si in nb if t<=lim*SPEED and S[si]['index']]
            if not cand: return ''
            cand.sort(); _,t,si=cand[0]; return fmt_s(si,t)
        zx,zy=zxy[zi]
        strong=[]
        for si in base_idx:
            s=S[si]
            if (s['index'] or 0)<40: continue
            d=min(math.hypot(g['x']-zx,g['y']-zy) for g in s['buildings'])
            if d<=5000: strong.append((-(s['index']),d,si))
        strong.sort()
        strong_txt='; '.join('%s — %s км · %d'%(S[si]['name'],('%.1f'%(d/1000)).replace('.',','),-ni) for ni,d,si in strong[:3])
        note=prec_note(z)
        if z['okrug']=='Рублёвка': note=(note+'; ' if note else '')+'за МКАД: школы Подмосковья в базе NOTA пока не оценены'
        row=[z['name'],z['developer'],z['class_final'],z['okrug'],z['district'],z['geo_precision'],
             S[near[1]]['name'] if near else '', mins(near[0]) if near else '',
             S[nearb[1]]['name'] if nearb else '', mins(nearb[0]) if nearb else '',
             c(10),c(15),c(20),c(30),mk(20,'Отметка'),mk(30,'Отметка'),mk(30,'На заметку'),best(20),best(30),strong_txt,note]
        w.writerow(row)
        zsum.append(dict(zi=zi, near=(mins(near[0]),near[1]) if near else None, nearb=(mins(nearb[0]),nearb[1]) if nearb else None, c10=c(10),c15=c(15),c20=c(20),c30=c(30), m20=mk(20,'Отметка'), m30=mk(30,'Отметка'), strong=[(si,round(d)) for ni,d,si in strong[:5]]))

# сводка по школам
bys=defaultdict(list)
for zi in range(len(ZHK)):
    for t,si,bi in allz[zi]: bys[si].append((t,zi))
with open('out/data/shkoly-zhk-svodka.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter=';'); f.write(BOM)
    w.writerow(['school','school_id','type','tier','nota_index','okrug','district','buildings','zhk_10','zhk_15','zhk_20','zhk_30','zhk_list_20'])
    for si,s in enumerate(S):
        if not s['in_base']: continue
        lst=sorted(bys[si]); c=lambda lim: sum(1 for t,zi in lst if t<=lim*SPEED)
        w.writerow([s['name'],s['sid'],s['category'],s['tier'],s['index'] if s['index'] is not None else '',s['okrug'],s['district'],len(s['buildings']),c(10),c(15),c(20),c(30),
                    '; '.join('%s — %d мин'%(ZHK[zi]['name'],mins(t)) for t,zi in lst if t<=20*SPEED)])
# корпуса
with open('out/data/shkoly-korpusa-geo.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter=';'); f.write(BOM)
    w.writerow(['school_id','school','in_nota_base','type','tier','building','lat','lon','source','osm_id'])
    for s in S:
        for g in s['buildings']:
            w.writerow([s['sid'],s['name'],'да' if s['in_base'] else 'нет',s['category'],s['tier'],g['name'],'%.6f'%g['lat'],'%.6f'%g['lon'],
                        {'OSM':'OpenStreetMap, корпус','адрес':'адрес из базы','дом':'точный адрес'}.get(g['src'],'примерно: '+g['src']),g['osm']])
pickle.dump(dict(pairs=pairs, routes=routes, zsum=zsum, bys=dict(bys), allz=dict(allz)), open('out/outputs.pkl','wb'))
print('csv done')
