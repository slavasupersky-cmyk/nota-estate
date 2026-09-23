import os,glob,shutil,csv,sys
from PIL import Image
B='foto'; TD='_to_delete/foto-bitye'; os.makedirs(TD,exist_ok=True)
REJ=set('''annabel-s aurus-rezidentsii aktsenty alia beregovoy-2 dom-na-chasovoy dom-sporta dostizhenie eli-estate eniteo era ever fon-dessin frunzenskiy full-house hide ilinka-3-8 imperium kod-sokolniki krylatskaya-33 kutuzov-grad kvartal-foriver kvartal-serebryanyy-bor l67 lavrushinskiy layf-taym mainstreet mirapolis mm22 monodom-lake nametkin-tauer nativ nazare novye-akademiki obydenskiy-1 palashevskiy-11 parkville-zhukovka peyv portlend primavera pyzhevskiy rakurs rozhdestvenka-8 sady-mayendorf savvinskaya-17 savvinskaya-27 sezar-budushchee sezar-silika shabolovka-34 skolkovo-one soul sreda-na-lobachevskogo tatum tishinskiy-bulvar usadba-demidova viktori-park-rezidensez zorge-9 zikkurat-preobrazhenskiy sydney-prime serebryanyy-bor tophills uno-gorbunova uno-sokolinaya-gora veri-na-miklukho-maklaya level-akademicheskaya level-streshnevo level-voykovskaya level-zvenigorodskaya-etap-2 level-prichalnyy'''.split())
CROP={'level-baumanskaya','level-michurinskiy','level-paveletskaya-siti'}
FIRST={'aura':'ns-2','mangazeya-na-rechnom':'ns-2','dom-a':'ns-1'}
def ok(f):
  try:
    im=Image.open(f); im.load(); return im
  except Exception: return None
def sig(im):
  t=im.convert('L').resize((16,9)); return list(t.getdata())
def same(a,b): return sum(abs(x-y) for x,y in zip(a,b))/len(a)<12
stat={'cover':0,'net':0,'bitye':0}; nocover=[]
for h in sorted(os.listdir(B)):
  d=f'{B}/{h}'
  if not os.path.isdir(d) or os.path.exists(f'{d}/cover.jpg'): continue
  cands=[]
  for f in sorted(glob.glob(f'{d}/site.*'))+sorted(glob.glob(f'{d}/ns-*')):
    im=ok(f)
    if im is None:
      os.makedirs(f'{TD}/{h}',exist_ok=True); shutil.move(f,f'{TD}/{h}/'); stat['bitye']+=1; continue
    im=im.convert('RGB'); w,hh=im.size; nm=os.path.basename(f).split('.')[0]
    if nm=='site':
      if h in CROP: im=im.crop((w//2,0,w,hh)); 
      elif h in REJ or w<700 or w/hh<1.15: continue
    cands.append((nm,im))
  if h in FIRST: cands.sort(key=lambda c: c[0]!=FIRST[h])
  pick=[]
  for nm,im in cands:
    s=sig(im)
    if any(same(s,p[2]) for p in pick): continue
    pick.append((nm,im,s))
  if not pick: nocover.append(h); stat['net']+=1; continue
  for i,(nm,im,s) in enumerate(pick[:3]):
    im.thumbnail((1920,1920)); im.save(f'{d}/'+('cover.jpg' if i==0 else f'{i+1}.jpg'),quality=86,optimize=True)
  stat['cover']+=1
print(stat); print('без обложки:',' '.join(nocover))
