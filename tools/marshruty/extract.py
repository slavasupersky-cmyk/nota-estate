# Проход по OSM: пешеходная сеть, барьеры, школы/сады, адреса, районы, подложка карты
import osmium, json, time, sys, pickle
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely import wkb

WALK = {'footway','path','steps','pedestrian','living_street','residential','service','unclassified',
        'tertiary','tertiary_link','secondary','secondary_link','primary','primary_link','track',
        'cycleway','corridor','elevator','road','platform'}
FOOT_OK = {'yes','designated','permissive','destination','customers'}
ACCESS_NO = {'no','private','agricultural','forestry','military','delivery','psv','no|no'}

def walkable(t):
    hw = t.get('highway')
    if hw is None: return False
    foot = t.get('foot','')
    if foot in ('no','private','use_sidepath'): return False
    if hw not in WALK and foot not in FOOT_OK: return False
    if t.get('access','') in ACCESS_NO and foot not in FOOT_OK: return False
    return True

MAPROAD = {'motorway':1,'motorway_link':1,'trunk':1,'trunk_link':1,'primary':2,'primary_link':2,
           'secondary':3,'secondary_link':3,'tertiary':4,'tertiary_link':4,'residential':5,'unclassified':5,'living_street':5,'pedestrian':6}

class H(osmium.SimpleHandler):
    def __init__(self, src):
        super().__init__()
        self.src=src
        self.eu=[]; self.ev=[]; self.ehw=[]
        self.nodes={}  # osm node id -> (lon,lat)
        self.barrier=set()
        self.feat=[]   # schools etc
        self.addr=[]
        self.admin=[]
        self.water=[]; self.green=[]; self.roads=[]; self.rail=[]; self.metro=[]
        self.nw=0
    def node(self, n):
        t=n.tags
        if 'barrier' in t:
            foot=t.get('foot',''); acc=t.get('access','')
            if foot in ('no','private') or (acc in ('no','private') and foot not in FOOT_OK):
                self.barrier.add(n.id)
        am=t.get('amenity')
        if am in ('school','kindergarten','college','university') or (t.get('building') in ('school',) and 'name' in t):
            self.feat.append(dict(src=self.src, osm='n%d'%n.id, amenity=am or '', building=t.get('building',''), tags=dict(t), lon=n.location.lon, lat=n.location.lat, geom=None))
        if 'addr:street' in t and 'addr:housenumber' in t:
            self.addr.append((t['addr:street'], t['addr:housenumber'], n.location.lon, n.location.lat, 'n%d'%n.id))
        if t.get('station')=='subway' or (t.get('railway')=='station' and t.get('station')=='subway'):
            self.metro.append(dict(name=t.get('name',''), colour=t.get('colour',''), lon=n.location.lon, lat=n.location.lat))
    def way(self, w):
        t=w.tags
        hw=t.get('highway')
        if hw and walkable(t):
            prev=None
            for nd in w.nodes:
                if not nd.location.valid():
                    prev=None; continue
                self.nodes[nd.ref]=(nd.location.lon, nd.location.lat)
                if prev is not None:
                    self.eu.append(prev); self.ev.append(nd.ref); self.ehw.append(hw)
                prev=nd.ref
            self.nw+=1
        if self.src=='bbbike':
            if hw in MAPROAD and t.get('area')!='yes':
                coords=[(nd.location.lon, nd.location.lat) for nd in w.nodes if nd.location.valid()]
                if len(coords)>=2: self.roads.append((MAPROAD[hw], t.get('name',''), coords))
            rw=t.get('railway')
            if rw=='rail' and t.get('service') is None and t.get('usage') in ('main','branch','industrial',None) and t.get('tunnel')!='yes':
                coords=[(nd.location.lon, nd.location.lat) for nd in w.nodes if nd.location.valid()]
                if len(coords)>=2: self.rail.append(coords)
    def area(self, a):
        t=a.tags
        am=t.get('amenity')
        isfeat = am in ('school','kindergarten','college','university') or (t.get('building')=='school' and 'name' in t)
        isaddr = 'addr:street' in t and 'addr:housenumber' in t
        isadmin = t.get('boundary')=='administrative' and t.get('admin_level') in ('4','5','8')
        iswater = self.src=='bbbike' and (t.get('natural')=='water' or t.get('waterway')=='riverbank' or t.get('landuse') in ('reservoir','basin'))
        isgreen = self.src=='bbbike' and (t.get('leisure') in ('park','garden','nature_reserve') or t.get('landuse') in ('forest','recreation_ground') or t.get('natural') in ('wood',) or t.get('boundary')=='protected_area')
        if not (isfeat or isaddr or isadmin or iswater or isgreen): return
        try:
            polys=[]
            for outer in a.outer_rings():
                oc=[(n.lon,n.lat) for n in outer]
                inners=[[(n.lon,n.lat) for n in inner] for inner in a.inner_rings(outer)]
                if len(oc)>=4: polys.append(Polygon(oc, [i for i in inners if len(i)>=4]))
            if not polys: return
            g = polys[0] if len(polys)==1 else MultiPolygon(polys)
            if not g.is_valid: g=g.buffer(0)
        except Exception as e:
            return
        oid=('w%d' if a.from_way() else 'r%d')%a.orig_id()
        c=g.representative_point() if g.area>0 else g.centroid
        if isfeat:
            self.feat.append(dict(src=self.src, osm=oid, amenity=am or '', building=t.get('building',''), tags=dict(t), lon=c.x, lat=c.y, geom=wkb.dumps(g)))
        if isaddr:
            self.addr.append((t['addr:street'], t['addr:housenumber'], c.x, c.y, oid))
        if isadmin:
            self.admin.append(dict(level=t.get('admin_level'), name=t.get('name',''), geom=wkb.dumps(g)))
        if iswater: self.water.append((t.get('name',''), wkb.dumps(g)))
        if isgreen: self.green.append((t.get('name',''), wkb.dumps(g)))
        if t.get('station')=='subway' or (t.get('railway')=='station' and t.get('station')=='subway'):
            self.metro.append(dict(name=t.get('name',''), colour=t.get('colour',''), lon=c.x, lat=c.y))

res={}
for src, path in (('bbbike','nota-moscow-bbbike.osm.pbf'), ('ovp','nota-ovp-mailru.osm')):
    t0=time.time()
    h=H(src); h.apply_file(path, locations=True, idx='flex_mem')
    print(src, 'secs %.0f'%(time.time()-t0), 'walk ways', h.nw, 'edges', len(h.eu), 'nodes', len(h.nodes), 'barriers', len(h.barrier), 'feat', len(h.feat), 'addr', len(h.addr), 'admin', len(h.admin), 'water', len(h.water), 'green', len(h.green), 'roads', len(h.roads), 'rail', len(h.rail), 'metro', len(h.metro), flush=True)
    res[src]=h

# merge
nodes={}
for h in res.values(): nodes.update(h.nodes)
ids=np.fromiter(nodes.keys(), dtype=np.int64, count=len(nodes))
ll=np.array([nodes[i] for i in ids], dtype=np.float64)
eu=np.concatenate([np.array(h.eu,dtype=np.int64) for h in res.values()])
ev=np.concatenate([np.array(h.ev,dtype=np.int64) for h in res.values()])
ehw=np.concatenate([np.array(h.ehw,dtype=object) for h in res.values()])
barrier=np.array(sorted(set().union(*[h.barrier for h in res.values()])),dtype=np.int64)
np.savez_compressed('out/graph_raw.npz', ids=ids, ll=ll, eu=eu, ev=ev, ehw=ehw.astype('U16'), barrier=barrier)
feat=[f for h in res.values() for f in h.feat]
addr=[a for h in res.values() for a in h.addr]
pickle.dump(dict(feat=feat, addr=addr, admin=res['bbbike'].admin+res['ovp'].admin,
                 water=res['bbbike'].water, green=res['bbbike'].green, roads=res['bbbike'].roads, rail=res['bbbike'].rail,
                 metro=res['bbbike'].metro+res['ovp'].metro), open('out/features.pkl','wb'))
print('saved; unique nodes', len(ids), 'edges', len(eu), 'feat', len(feat), 'addr', len(addr))
