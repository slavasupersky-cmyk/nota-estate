# Класс NOTA из заявленного класса и признаков (см. nota-baza/README.md, «Два класса»). Запуск из nota-estate: python3 tools/klass.py [write]
import sys,csv,io,re,collections
sys.path.insert(0,'tools'); import karta
B='../nota-baza/'
W=karta.grab(open('nota-karta-zhk.html').read(),'W'); TTK=W['rings']['ТТК']
def inpoly(x,y,P):
    c=False
    for i in range(len(P)):
        x1,y1=P[i]; x2,y2=P[(i+1)%len(P)]
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
ORD=['бизнес','премиум','элитный','делюкс']
OLD={'ЦАО','САО','СВАО','ВАО','ЮВАО','ЮАО','ЮЗАО','ЗАО','СЗАО'}
PARK={'бизнес':0.8,'премиум':1.5,'элитный':2.0,'делюкс':2.0}
UN={'бизнес':837,'премиум':665,'элитный':100,'делюкс':30}
CEIL={'бизнес':2.8,'премиум':3.2,'элитный':3.3,'делюкс':3.3}  # решение Supersky 24.09: 3,3 м, как в kriterii.csv
def num(v):
    try: return float(str(v).replace(' ','').replace(',','.'))
    except: return None
def declared(txt, cur):
    t=txt.lower()
    found=[]
    for k,pat in [('делюкс',r'делюкс|de ?luxe|deluxe'),('элитный',r'элит'),('премиум',r'премиум'),('бизнес',r'бизнес'),('комфорт',r'комфорт')]:
        if re.search(pat,t): found.append(k)
    if not found: return cur,'не заявлен — взят класс базы'
    top=[k for k in ['делюкс','элитный','премиум','бизнес','комфорт'] if k in found][0]
    if len(found)>1 and cur in found: top=cur   # класс базы уже выбран чатом базы из этих вариантов
    return top, ('источники расходятся: '+txt) if len(found)>1 else ''
def fails(z,cl):
    f=[]; known=0
    if z['okrug'] not in ('Рублёвка','Сколково'):
        known+=1
        if cl=='бизнес': ok=z['okrug'] in OLD
        elif cl=='премиум': ok=inpoly(*karta.proj(float(z['lat']),float(z['lon'])),TTK)
        else: ok=z['okrug']=='ЦАО'
        if not ok: f.append('адрес')
    u,pk,ce=num(z['units_total']),num(z['parking']),num(z['ceilings_m'])
    if u: known+=1; (u>UN[cl]) and f.append('плотность')
    if u and pk: known+=1; (pk/u<PARK[cl]) and f.append('паркинг')
    if ce: known+=1; (ce<CEIL[cl]) and f.append('потолки')
    return f
raw=open(B+'doma.csv',encoding='utf-8-sig',newline='').read(); nl='\r\n' if '\r\n' in raw else '\n'
rows=list(csv.DictReader(io.StringIO(raw),delimiter=';')); cols=list(rows[0])
if 'class_zayavlen' not in cols: cols.insert(cols.index('class')+1,'class_zayavlen'); cols.insert(cols.index('class_zayavlen')+1,'class_why')
ch=collections.Counter(); moves=[]
for z in rows:
    OVR={'mod':'премиум','simfoniya-34':'премиум','pride':'премиум','preobrazhenskaya-ploschad':'бизнес'}
    dz,note=declared(z['class_declared'],z['class'])
    if z['slug'] in OVR: dz=OVR[z['slug']]
    if z.get('class_zayavlen'): dz,note=z['class_zayavlen'],''   # уже заполнен (или поправлен руками) — не трогаем
    z['class_zayavlen']=dz
    base= dz if dz in ORD else 'бизнес'
    f=fails(z,base)
    nota=base
    if len(f)>=2 and ORD.index(base)>0: nota=ORD[ORD.index(base)-1]
    why=[]
    if dz=='комфорт': why.append('заявлен комфорт — в базе держим от бизнеса')
    if nota!=base: why.append(f'понижен: не дотягивает до класса «{base}» по двум и более признакам — '+', '.join(f))
    elif f: why.append('минус к классу: '+', '.join(f))
    if note: why.append(note)
    z['class_why']='; '.join(why)
    if z['stage']!='дубль':
        ch[(z['class'],nota)]+=1
        if z['class']!=nota: moves.append((z['slug'],z['class'],'→',nota,dz))
    z['class']=nota
    z['class_disputed']='да' if nota!=dz else ''
print(sorted(ch.items())); print(len(moves)); print(moves[:60])
print(collections.Counter(z['class'] for z in rows if z['stage']!='дубль'), collections.Counter(z['class_zayavlen'] for z in rows if z['stage']!='дубль'))
if len(sys.argv)>1:
    b=io.StringIO(); w=csv.DictWriter(b,cols,delimiter=';',lineterminator=nl); w.writeheader(); w.writerows(rows)
    open(B+'doma.csv','w',encoding='utf-8',newline='').write('﻿'+b.getvalue()); print('записано')
