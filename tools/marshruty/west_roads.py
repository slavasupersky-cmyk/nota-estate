import osmium, json
MAPROAD = {'motorway':1,'motorway_link':1,'trunk':1,'trunk_link':1,'primary':2,'primary_link':2,
           'secondary':3,'secondary_link':3,'tertiary':4,'tertiary_link':4,'residential':5,'unclassified':5,'living_street':5,'pedestrian':6}
roads=[]
class H(osmium.SimpleHandler):
    def way(self, w):
        hw=w.tags.get('highway')
        if hw in MAPROAD and w.tags.get('area')!='yes':
            c=[(n.location.lon,n.location.lat) for n in w.nodes if n.location.valid()]
            # только то, что вне выгрузки BBBike (запад и север)
            if len(c)>=2 and any(lo<37.322 or la>55.916 for lo,la in c):
                roads.append((MAPROAD[hw], w.tags.get('name',''), c))
H().apply_file('nota-ovp-mailru.osm', locations=True)
import pickle
F=pickle.load(open('out/features.pkl','rb'))
n0=len(F['roads']); F['roads']=F['roads']+roads
pickle.dump(F, open('out/features.pkl','wb'))
print('added west/north roads', len(roads), 'total', len(F['roads']), 'was', n0)
