import pickle, json, numpy as np, shapely
from shapely import wkb
from shapely.geometry import LineString, Polygon, MultiPolygon, box
from pyproj import Transformer
TR=Transformer.from_crs('EPSG:4326','EPSG:32637',always_xy=True)
TRI=Transformer.from_crs('EPSG:32637','EPSG:4326',always_xy=True)
F=pickle.load(open('out/features.pkl','rb'))
def enc(coords):
    out=[]; plat=plon=0
    for lon,lat in coords:
        ilat=int(round(lat*1e5)); ilon=int(round(lon*1e5))
        for v in (ilat-plat, ilon-plon):
            v=~(v<<1) if v<0 else (v<<1)
            while v>=0x20: out.append(chr((0x20|(v&0x1f))+63)); v>>=5
            out.append(chr(v+63))
        plat,plon=ilat,ilon
    return ''.join(out)
def to_xy(g): return shapely.transform(g, lambda a: np.column_stack(TR.transform(a[:,0],a[:,1])))
def to_ll(g): return shapely.transform(g, lambda a: np.column_stack(TRI.transform(a[:,0],a[:,1])))
def ring_enc(r): 
    c=list(r.coords); return enc(c) if len(c)>=4 else None
out={}
# дороги
roads=[]
for cls,nm,c in F['roads']:
    if len(c)<2: continue
    tol={1:4,2:4,3:4,4:4,5:3,6:3}[cls]
    g=to_ll(to_xy(LineString(c)).simplify(tol))
    roads.append([cls, enc(list(g.coords))])
out['roads']=roads
# рельсы
out['rail']=[enc(list(to_ll(to_xy(LineString(c)).simplify(5)).coords)) for c in F['rail'] if len(c)>=2]
# полигоны
def polys(items, minarea, tol):
    res=[]
    for nm,gb in items:
        g=to_xy(wkb.loads(gb))
        if g.area<minarea: continue
        g=g.simplify(tol, preserve_topology=True)
        if g.is_empty: continue
        g=to_ll(g)
        gs=[g] if g.geom_type=='Polygon' else list(getattr(g,'geoms',[]))
        for p in gs:
            if p.geom_type!='Polygon' or p.is_empty: continue
            rings=[ring_enc(p.exterior)]+[ring_enc(i) for i in p.interiors if Polygon(i).area>0]
            rings=[r for r in rings if r]
            if rings: res.append(rings)
    return res
out['water']=polys(F['water'], 800, 3)
out['green']=polys(F['green'], 15000, 6)
# районы (граница)
dist=[]
for a in F['admin']:
    if a['level'] in ('8',):
        g=to_ll(to_xy(wkb.loads(a['geom'])).simplify(15))
        gs=[g] if g.geom_type=='Polygon' else list(g.geoms)
        nm=a['name']
        dist.append([nm, [[ring_enc(p.exterior)] for p in gs if p.geom_type=='Polygon']])
out['districts']=dist
# метро
seen=set(); metro=[]
for m in F['metro']:
    k=(m['name'], round(m['lon'],3), round(m['lat'],3))
    if not m['name'] or k in seen: continue
    seen.add(k); metro.append([m['name'], round(m['lat'],5), round(m['lon'],5)])
out['metro']=metro
s=json.dumps(out, ensure_ascii=False, separators=(',',':'))
open('out/base.json','w',encoding='utf-8').write(s)
print('base.json %.2f MB'%(len(s.encode())/1e6), {k:len(v) for k,v in out.items()})
for k in out: print(k, '%.2f MB'%(len(json.dumps(out[k],ensure_ascii=False,separators=(',',':')).encode())/1e6))
