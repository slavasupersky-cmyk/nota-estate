import numpy as np, pickle, csv, time, math
import shapely
from shapely import wkb
from shapely.strtree import STRtree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from pyproj import Transformer
t0=time.time()
TR=Transformer.from_crs('EPSG:4326','EPSG:32637',always_xy=True)
G=np.load('out/graph.npz', allow_pickle=False)
xy, a, b, L, lab, main = G['xy'], G['a'], G['b'], G['L'], G['lab'], int(G['main'])
m=lab[a]==main; a,b,L=a[m],b[m],L[m]
N=len(xy)
segs=shapely.linestrings(np.stack([xy[a],xy[b]],axis=1)); tree=STRtree(segs)
# препятствия: ж/д, вода, магистрали
F=pickle.load(open('out/features.pkl','rb'))
def proj_line(c): 
    x,y=TR.transform([p[0] for p in c],[p[1] for p in c]); return shapely.linestrings(np.column_stack([x,y]))
obst=[proj_line(c) for c in F['rail']]+[proj_line(c) for cls,nm,c in F['roads'] if cls==1]
for nm,g in F['water']:
    g=wkb.loads(g)
    if g.area*1e10>0: 
        gg=shapely.transform(g, lambda arr: np.column_stack(TR.transform(arr[:,0],arr[:,1])))
        if gg.area>3000: obst.append(gg.boundary)
otree=STRtree(obst)
print('obstacles', len(obst), '%.0fs'%(time.time()-t0))

ZHK=list(csv.DictReader(open('/mnt/user-data/uploads/nota-estate/data/zhk-moskva-biznes-plus-geo.csv',encoding='utf-8-sig'),delimiter=';'))
S=pickle.load(open('out/schools_final.pkl','rb'))['schools']
pts=[]
for i,z in enumerate(ZHK):
    x,y=TR.transform(float(z['lon']),float(z['lat']))
    approx = not z['geo_precision'].startswith('адрес')
    pts.append(('z',i,-1,x,y,approx))
for si,s in enumerate(S):
    for bi,g in enumerate(s['buildings']):
        pts.append(('b',si,bi,g['x'],g['y'],g['src']!='OSM'))
P=shapely.points(np.array([[p[3],p[4]] for p in pts]))
near_idx, near_d = tree.query_nearest(P, return_distance=True)
d0=np.full(len(pts),np.inf); d0[near_idx[0]]=near_d
PEN=1.15
con_p=[]; con_seg=[]; con_len=[]
for k,p in enumerate(pts):
    r=min(max(d0[k]+ (150 if p[5] else 80), 120), d0[k]+250)
    cand=tree.query(P[k].buffer(r))
    if len(cand)==0: continue
    dd=shapely.distance(P[k], segs[cand])
    o=np.argsort(dd)[:24]
    cand,dd=cand[o],dd[o]
    kept=0
    for j,(sg,d) in enumerate(zip(cand,dd)):
        if d>r: break
        q=shapely.get_coordinates(shapely.shortest_line(P[k], segs[sg]))[1]
        if j>0 and d>1:
            ln=shapely.linestrings([[p[3],p[4]],q])
            hit=otree.query(ln, predicate='intersects')
            if len(hit): continue
        con_p.append(k); con_seg.append(sg); con_len.append(d); kept+=1
        if kept>=12: break
con_p=np.array(con_p); con_seg=np.array(con_seg); con_len=np.array(con_len)
print('connectors', len(con_p), 'per point avg %.1f'%(len(con_p)/len(pts)), '%.0fs'%(time.time()-t0))
# узлы: точки p (N..N+len(pts)), проекции q (дальше)
Np=len(pts); pnode=N+np.arange(Np)
qpos=shapely.get_coordinates(shapely.shortest_line(P[con_p], segs[con_seg]))[1::2]
qnode=N+Np+np.arange(len(con_p))
ta=np.hypot(qpos[:,0]-xy[a[con_seg],0], qpos[:,1]-xy[a[con_seg],1]); tb=np.maximum(L[con_seg]-ta,0)
ea=np.concatenate([a, pnode[con_p], qnode, qnode]); eb=np.concatenate([b, qnode, a[con_seg], b[con_seg]])
ew=np.concatenate([L, con_len*PEN, ta, tb])+0.01
NN=N+Np+len(con_p)
Gc=coo_matrix((ew,(ea,eb)),shape=(NN,NN)).tocsr()
XYall=np.vstack([xy, np.array([[p[3],p[4]] for p in pts]), qpos])
np.save('out/xy_all.npy', XYall)
zk=[k for k,p in enumerate(pts) if p[0]=='z']
bk=np.array([k for k,p in enumerate(pts) if p[0]=='b'])
b_school=np.array([pts[k][1] for k in bk]); b_bld=np.array([pts[k][2] for k in bk])
LIMIT=3900.0
res={}
B=8
for s0 in range(0,len(zk),B):
    src=[N+k for k in zk[s0:s0+B]]
    D,Pr=dijkstra(Gc, directed=False, indices=src, limit=LIMIT, return_predecessors=True)
    for j,k in enumerate(zk[s0:s0+B]):
        zi=pts[k][1]
        d=D[j, N+bk]; ok=np.isfinite(d)
        best={}
        for t,si,bi,kk in zip(d[ok], b_school[ok], b_bld[ok], bk[ok]):
            if si not in best or t<best[si][0]: best[si]=(t,bi,kk)
        out=[]
        for si,(t,bi,kk) in best.items():
            path=None
            if t<=2700:
                node=N+kk; seq=[node]
                while node!=src[j] and node>=0:
                    node=Pr[j,node]; seq.append(node)
                path=seq[::-1]
            out.append((int(si),int(bi),float(t),path))
        res[zi]=out
print('routing done %.0fs'%(time.time()-t0))
pickle.dump(dict(res=res, snap_d=d0, pts=pts, N=N, mode='multisnap'), open('out/routes_raw.pkl','wb'))
