import numpy as np, time, pickle
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
t0=time.time()
z=np.load('out/graph_raw.npz', allow_pickle=False)
ids, ll, eu, ev, ehw, barrier = z['ids'], z['ll'], z['eu'], z['ev'], z['ehw'], z['barrier']
order=np.argsort(ids); ids=ids[order]; ll=ll[order]
u=np.searchsorted(ids, eu); v=np.searchsorted(ids, ev)
assert (ids[u]==eu).all() and (ids[v]==ev).all()
# barrier nodes: drop edges touching them
bmask=np.isin(ids, barrier)
keep=~(bmask[u]|bmask[v]) & (u!=v)
u,v,ehw=u[keep],v[keep],ehw[keep]
# dedupe undirected
a=np.minimum(u,v); b=np.maximum(u,v)
key=a.astype(np.int64)*4000000+b
_,first=np.unique(key, return_index=True)
a,b,ehw=a[first],b[first],ehw[first]
tr=Transformer.from_crs('EPSG:4326','EPSG:32637',always_xy=True)
x,y=tr.transform(ll[:,0], ll[:,1])
xy=np.column_stack([x,y])
L=np.hypot(x[a]-x[b], y[a]-y[b])
n=len(ids)
G=coo_matrix((L,(a,b)),shape=(n,n)).tocsr()
ncomp, lab = connected_components(G, directed=False)
cnt=np.bincount(lab)
main=np.argmax(cnt)
print('nodes',n,'edges',len(a),'components',ncomp,'main size',cnt[main],'share %.3f'%(cnt[main]/n))
big=np.argsort(-cnt)[:8]; print('largest comps', cnt[big])
inmain = lab[a]==main
np.savez_compressed('out/graph.npz', ids=ids, ll=ll, xy=xy, a=a, b=b, L=L, hw=ehw, lab=lab, main=main)
print('total km main', L[inmain].sum()/1000, 'secs %.0f'%(time.time()-t0))
from collections import Counter
print(Counter(ehw[inmain]).most_common(25))
