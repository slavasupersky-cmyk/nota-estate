# Проверки паспорта 01, 04, 05, 09 по doma.csv. Запуск из nota-estate: python3 tools/checks.py [write]; после записи proverki.csv — CRLF
import sys,csv,statistics as st,collections,io
sys.path.insert(0,'tools'); import karta
B='../nota-baza/'; TODAY='24.09.2026'
W=karta.grab(open('nota-karta-zhk.html').read(),'W'); TTK=W['rings']['ТТК']
def inpoly(x,y,P):
    c=False
    for i in range(len(P)):
        x1,y1=P[i]; x2,y2=P[(i+1)%len(P)]
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
OLD={'ЦАО','САО','СВАО','ВАО','ЮВАО','ЮАО','ЮЗАО','ЗАО','СЗАО'}
PARK={'бизнес':0.8,'премиум':1.5,'элитный':2.0,'делюкс':2.0}
UN={'бизнес':837,'премиум':665,'элитный':100,'делюкс':30}
UPF={'бизнес':12,'премиум':5,'элитный':3,'делюкс':3}  # квартир на этаже, kriterii.csv 04 (решение Supersky 24.09)
def num(v):
    try: return float(str(v).replace(' ','').replace(',','.'))
    except: return None
r=[x for x in csv.DictReader(open(B+'doma.csv',encoding='utf-8-sig'),delimiter=';') if x['stage']!='дубль']
rows=list(csv.DictReader(open(B+'proverki.csv',encoding='utf-8-sig'),delimiter=';')); cols=list(rows[0])
last={}
for x in rows: last[(x['slug'],x['check'])]=x
pr=collections.defaultdict(list)
for x in r:
    v=num(x['price_from_m2'])
    if v: pr[(x['district'],x['class'])].append(v)
src='каталоги, декларации, сайты застройщиков (база NOTA)'
new=[]
def add(s,c,a,v,so,note):
    o=last.get((s,c))
    if o and o['answer']==a and o['value']==v: return
    new.append(dict(slug=s,check=c,answer=a,value=v,source=so,checked=TODAY,who='Claude',note=note))
for x in r:
    s,cl=x['slug'],x['class']; gp='точность геокода: '+x['geo_precision']
    if x['okrug'] in ('Рублёвка','Сколково'): a,v='не применяется',x['okrug']
    elif cl=='бизнес': a,v=('да' if x['okrug'] in OLD else 'нет'),x['okrug']
    elif cl=='премиум':
        ins=inpoly(*karta.proj(float(x['lat']),float(x['lon'])),TTK); a,v=('да','внутри Третьего кольца') if ins else ('нет','за Третьим кольцом')
    else: a,v=('да' if x['okrug']=='ЦАО' else 'нет'),x['okrug']
    add(s,'01',a,v,'координаты базы; кольцо — схема из nota-karta-zhk',gp)
    u,pk,uf=num(x['units_total']),num(x['parking']),num(x['units_per_floor'])
    if x['okrug'] in ('Рублёвка','Сколково') and x['type'] not in ('квартиры','апартаменты'):
        # посёлки: в units_total число домов, нормы многоквартирного дома не применимы (решение Supersky 24.09)
        add(s,'04','не применяется','посёлок: '+x['type'],'','')
        add(s,'05','не применяется','посёлок: '+x['type'],'','')
    else:
        if u or uf:
            bad=[]; val=[]
            if u:
                val.append(f'{int(u)} квартир')
                if u>UN[cl]: bad.append(f'квартир больше нормы класса ({UN[cl]})')
            if uf:
                val.append(f'{uf:g} на этаже')
                if uf>UPF[cl]: bad.append(f'на этаже больше нормы класса ({UPF[cl]})')
            note='; '.join(bad) if bad else ('' if (u and uf) else ('квартир на этаже — не собрано' if u else 'всего квартир — не раскрыто'))
            add(s,'04','нет' if bad else 'да',' · '.join(val),src,note)
        else: add(s,'04','нет данных','','', 'число квартир не раскрыто')
        if u and pk: add(s,'05','да' if pk/u>=PARK[cl] else 'нет',f'{pk/u:.2f} м/м на квартиру ({int(pk)} на {int(u)})',src,'')
        else: add(s,'05','нет данных','','','машиноместа не раскрыты' if u else 'квартиры или машиноместа не раскрыты')
    v=num(x['price_from_m2'])
    if not v: add(s,'09','нет данных','','','цена не опубликована'); continue
    L=pr[(x['district'],cl)]; val=f'от {int(v):,} ₽/м²'.replace(',',' ')
    if 'не бьётся' in x['price_check']: add(s,'09','нет',val,src,'цена не бьётся с классом')
    elif len(L)>=3 and v>1.3*st.median(L): add(s,'09','нет',val,src,f'дороже медианы класса в районе ({int(st.median(L)):,} ₽/м², {len(L)} домов) на {round((v/st.median(L)-1)*100)}% — проверить причину'.replace(',',' '))
    else: add(s,'09','да',val,src,f'медиана класса в районе {int(st.median(L)):,} ₽/м² ({len(L)} домов)'.replace(',',' ') if len(L)>=3 else 'в районе меньше 3 домов класса — сверка с медианой класса по базе')
print(collections.Counter((n['check'],n['answer']) for n in new))
if len(sys.argv)>1:
    buf=io.StringIO(); w=csv.DictWriter(buf,cols,delimiter=';',lineterminator='\r\n'); w.writeheader(); w.writerows(rows+new)
    open(B+'proverki.csv','w',encoding='utf-8',newline='').write('﻿'+buf.getvalue()); print('записано',len(new))
