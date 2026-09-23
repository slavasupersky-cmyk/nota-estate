(function(){
'use strict';
const D = JSON.parse(document.getElementById('d-data').textContent);
const BASE = JSON.parse(document.getElementById('d-base').textContent);
const SPEED = D.meta.speed_m_min;
const Z = D.zhk, S = D.schools, P = D.pairs, RT = D.routes;
// Z: [name, dev, cls, okrug, district, lat, lon, prec, units, stage, deadline, price, site, snap]
// S: [name, cat, tier, index, district, okrug, inbase, why, site, address, [[lat,lon,name,src]]]
// P: [zi, si, bi, m, straight, rid]
const byZ = new Map(), byS = new Map();
P.forEach((p,i)=>{
  if(!byZ.has(p[0])) byZ.set(p[0],[]); byZ.get(p[0]).push(i);
  if(!byS.has(p[1])) byS.set(p[1],[]); byS.get(p[1]).push(i);
});

function dec(s){
  let i=0, lat=0, lon=0; const out=[];
  while(i<s.length){
    let b, sh=0, r=0;
    do{ b=s.charCodeAt(i++)-63; r|=(b&31)<<sh; sh+=5; }while(b>=32);
    lat += (r&1) ? ~(r>>1) : (r>>1);
    sh=0; r=0;
    do{ b=s.charCodeAt(i++)-63; r|=(b&31)<<sh; sh+=5; }while(b>=32);
    lon += (r&1) ? ~(r>>1) : (r>>1);
    out.push([lon/1e5, lat/1e5]);
  }
  return out;
}
const rcache = new Map();
function route(rid){ if(!rcache.has(rid)) rcache.set(rid, dec(RT[rid])); return rcache.get(rid); }

const mins = m => Math.max(1, Math.round(m/SPEED));
const fmtDist = m => m<1000 ? (Math.round(m/10)*10)+' м' : (m/1000).toFixed(1).replace('.',',')+' км';
const esc = s => String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const nf = new Intl.NumberFormat('ru-RU');
const TIER = {'Отметка':'mark','На заметку':'note','Лучшая в районе':'best'};
const TIER_RANK = {'Отметка':4,'На заметку':3,'Лучшая в районе':2};
function kOf(si){ const s=S[si]; if(!s[6]) return 0; return TIER_RANK[s[2]]||1; }
function tierPill(si){
  const s=S[si], t=s[2];
  let h = t ? '<span class="pill '+TIER[t]+'">'+esc(t)+'</span>' : '';
  if(s[6] && s[3]!=null) h += '<span class="pill num">'+s[3]+' из 100</span>';
  if(s[6] && s[1] && s[1]!=='Городская') h += '<span class="pill">'+esc(s[1].toLowerCase())+'</span>';
  if(!s[6]) h += '<span class="pill">нет в базе NOTA</span>';
  return h;
}
function yl(a,b,mode){ return 'https://yandex.ru/maps/?rtext='+a[0].toFixed(6)+','+a[1].toFixed(6)+'~'+b[0].toFixed(6)+','+b[1].toFixed(6)+'&rtt='+mode; }
function links(a,b,walk){
  return '<div class="links"><span class="lkl">Яндекс:</span>'+(walk?'<a class="lk" target="_blank" rel="noopener" title="Пеший маршрут в Яндекс Картах" href="'+yl(a,b,'pd')+'">пешком ↗</a>':'')+
    '<a class="lk" target="_blank" rel="noopener" title="Маршрут на транспорте в Яндекс Картах" href="'+yl(a,b,'mt')+'">транспорт ↗</a>'+
    '<a class="lk" target="_blank" rel="noopener" title="Маршрут на машине в Яндекс Картах" href="'+yl(a,b,'auto')+'">авто ↗</a></div>';
}
function plural(n, f){ const a=Math.abs(n)%100, b=a%10; return a>10&&a<20 ? f[2] : b>1&&b<5 ? f[1] : b===1 ? f[0] : f[2]; }
function hav(la1,lo1,la2,lo2){
  const R=6371000, r=Math.PI/180, dLa=(la2-la1)*r, dLo=(lo2-lo1)*r;
  const x=Math.sin(dLa/2)**2+Math.cos(la1*r)*Math.cos(la2*r)*Math.sin(dLo/2)**2;
  return 2*R*Math.asin(Math.sqrt(x));
}
const CLS_ORDER = {'бизнес':1,'премиум':2,'элитный':3,'делюкс':4};

// ---------- состояние ----------
const findZ = n => Z.findIndex(z=>z[0]===n);
const findS = n => S.findIndex(s=>s[0]===n);
const state = { mode:'zhk', zi: Math.max(0,findZ('Фрунзенский')), si: Math.max(0,findS('Пятьдесят седьмая школа')), lim:20, scope:'all', cls:'all' };
try{ const saved = JSON.parse(localStorage.getItem('nota-shkoly-v1')||'null'); if(saved && typeof saved.lim==='number'){ state.lim=saved.lim; } }catch(e){}

// ---------- статистика в подзаголовке ----------
(function(){
  const city = Z.map((z,i)=>i).filter(i=>Z[i][3]!=='Рублёвка');
  let b15=0, m20=0;
  city.forEach(zi=>{
    const lst=(byZ.get(zi)||[]).map(i=>P[i]);
    if(lst.some(p=>S[p[1]][6] && p[3]<=15*SPEED)) b15++;
    if(lst.some(p=>S[p[1]][2]==='Отметка' && p[3]<=20*SPEED)) m20++;
  });
  const pc = x=>Math.round(100*x/city.length);
  document.getElementById('dek').innerHTML = 'Минуты по улицам, а не по прямой. У <b>'+pc(b15)+'%</b> домов в городе школа из базы NOTA — в 15 минутах пешком, школа с отметкой в 20 минутах — у <b>'+pc(m20)+'%</b>.';
  const nb = S.filter(s=>s[6]).length, no = S.length-nb;
  document.getElementById('m-schools').textContent = 'В расчёте '+nf.format(nb)+' школ из базы NOTA с отметкой и '+nf.format(no)+' школ без оценки — всё, что OpenStreetMap знает как общеобразовательную школу рядом с домами.';
  document.getElementById('m-data').textContent = 'Данные: '+D.meta.osm_moscow+'; запад и север — '+D.meta.osm_west+'. Расчёт '+D.meta.built+'. © участники OpenStreetMap.';
})();

// ---------- элементы ----------
const $ = id => document.getElementById(id);
const elQ=$('q'), elSugg=$('sugg'), elCard=$('card'), elList=$('list');

function chips(el, items, cur, onpick){
  el.innerHTML = items.map(([v,l])=>'<button class="chip" type="button" data-v="'+v+'" aria-pressed="'+(String(v)===String(cur))+'">'+l+'</button>').join('');
  el.onclick = e=>{ const b=e.target.closest('.chip'); if(!b) return; onpick(b.dataset.v); };
}
function renderControls(){
  chips($('c-min'), [[10,'10 мин'],[15,'15 мин'],[20,'20 мин'],[30,'30 мин']], state.lim, v=>{ state.lim=+v; try{localStorage.setItem('nota-shkoly-v1', JSON.stringify({lim:state.lim}));}catch(e){} update(); });
  if(state.mode==='zhk'){
    $('c-l2').textContent='Школы';
    chips($('c-2'), [['all','Все'],['base','Из базы NOTA'],['top','Отметка и на заметку']], state.scope, v=>{ state.scope=v; update(); });
  } else {
    $('c-l2').textContent='Класс';
    chips($('c-2'), [['all','Все'],['бизнес','Бизнес'],['премиум','Премиум'],['элитный','Элит'],['делюкс','Делюкс']], state.cls, v=>{ state.cls=v; update(); });
  }
  $('m-zhk').setAttribute('aria-selected', state.mode==='zhk');
  $('m-sch').setAttribute('aria-selected', state.mode==='sch');
  elQ.placeholder = state.mode==='zhk' ? 'Дом, застройщик, район или школа' : 'Школа: номер, название или район';
}
$('m-zhk').onclick=()=>{ if(state.mode!=='zhk'){ state.mode='zhk'; elQ.value=''; update(true);} };
$('m-sch').onclick=()=>{ if(state.mode!=='sch'){ state.mode='sch'; elQ.value=''; update(true);} };

// ---------- поиск ----------
const norm = s => String(s||'').toLowerCase().replace(/ё/g,'е').replace(/[«»"()]/g,' ').replace(/№\s*/g,'').replace(/\s+/g,' ').trim();
const ZN = Z.map(z=>norm(z[0]+' '+z[1]+' '+z[4]+' '+z[3]));
const SN = S.map(s=>norm(s[0]+' '+s[4]+' '+s[5]));
let suggIdx=-1, suggItems=[];
function search(){
  const q=norm(elQ.value);
  if(!q){ elSugg.hidden=true; return; }
  const words=q.split(' ');
  const hit = arr => arr.map((t,i)=>[t,i]).filter(([t])=>words.every(w=>t.includes(w))).map(([,i])=>i);
  const zs = hit(ZN).map(i=>({k:'z',i,t:Z[i][0],s:'дом · '+Z[i][2]+' · '+Z[i][4]}));
  let sr = hit(SN); sr.sort((a,b)=>(S[b][6]-S[a][6])||((S[b][3]||0)-(S[a][3]||0)));
  const ss = sr.map(i=>({k:'s',i,t:S[i][0],s:'школа · '+(S[i][2]||(S[i][6]?'база NOTA':'без оценки'))+(S[i][4]?' · '+S[i][4]:'')}));
  suggItems = (state.mode==='zhk' ? zs.slice(0,8).concat(ss.slice(0,4)) : ss.slice(0,8).concat(zs.slice(0,4))).slice(0,10);
  suggIdx = suggItems.length?0:-1;
  elSugg.innerHTML = suggItems.length ? suggItems.map((x,j)=>'<li><button type="button" data-j="'+j+'" class="'+(j===suggIdx?'on':'')+'"><span>'+esc(x.t)+'</span><small>'+esc(x.s)+'</small></button></li>').join('') : '<li><button type="button" disabled><span>Ничего не нашли</span></button></li>';
  elSugg.hidden=false;
}
function pick(x){ elSugg.hidden=true; elQ.value=''; if(x.k==='z'){ state.mode='zhk'; state.zi=x.i; } else { state.mode='sch'; state.si=x.i; } update(true); }
elQ.addEventListener('input', search);
elQ.addEventListener('keydown', e=>{
  if(elSugg.hidden) return;
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){ e.preventDefault(); if(!suggItems.length) return; suggIdx=(suggIdx+(e.key==='ArrowDown'?1:-1)+suggItems.length)%suggItems.length; [...elSugg.querySelectorAll('button')].forEach((b,j)=>b.classList.toggle('on',j===suggIdx)); }
  else if(e.key==='Enter'){ e.preventDefault(); if(suggIdx>=0) pick(suggItems[suggIdx]); }
  else if(e.key==='Escape'){ elSugg.hidden=true; }
});
elSugg.addEventListener('click', e=>{ const b=e.target.closest('button[data-j]'); if(b) pick(suggItems[+b.dataset.j]); });
document.addEventListener('click', e=>{ if(!e.target.closest('.search')) elSugg.hidden=true; });

// ---------- панель: дом ----------
function rowsHtml(items){ return items.join(''); }
function renderZhk(){
  const zi=state.zi, z=Z[zi], zp=[z[5],z[6]];
  const all=(byZ.get(zi)||[]).map(i=>P[i]).sort((a,b)=>a[3]-b[3]);
  const lim=state.lim*SPEED;
  const inLim=all.filter(p=>p[3]<=lim);
  const scoped=inLim.filter(p=> state.scope==='all' ? true : state.scope==='base' ? S[p[1]][6]===1 : (S[p[1]][2]==='Отметка'||S[p[1]][2]==='На заметку'));
  const base=scoped.filter(p=>S[p[1]][6]===1), other=scoped.filter(p=>S[p[1]][6]===0);
  const nearest=all[0];
  const nMark=inLim.filter(p=>S[p[1]][2]==='Отметка').length;
  const nBase=inLim.filter(p=>S[p[1]][6]===1).length;
  const meta=[z[1], z[2], z[4]+(z[3]&&z[3]!==z[4]?', '+z[3]:''), z[9]+(z[10]?' · сдача '+z[10]:'')].filter(Boolean).map(esc).join(' · ');
  let flags='';
  if(!String(z[7]).startsWith('адрес')) flags+='<div class="flag"><b>Координаты дома приблизительные</b> ('+esc(z[7])+'): минуты могут отличаться на ±5.</div>';
  if(z[13]>120) flags+='<div class="flag"><b>Дом стоит в '+nf.format(Math.round(z[13]/10)*10)+' м от ближайшей пешеходной дорожки</b> — стройплощадка или закрытая территория. Выходы из квартала появятся со сдачей, время пока ориентировочное.</div>';
  if(z[3]==='Рублёвка') flags+='<div class="flag"><b>За МКАД школы Подмосковья в базе NOTA пока не оценены</b> — ниже школы из OpenStreetMap без отметки.</div>';
  elCard.innerHTML =
    '<div class="eyebrow">Дом</div><h2>'+esc(z[0])+'</h2><div class="meta">'+meta+'</div>'+
    '<div class="stats">'+
      '<div><b>'+(nearest?mins(nearest[3]):'—')+'</b><span>мин до ближайшей школы'+(nearest?'':' (дальше 30 мин)')+'</span></div>'+
      '<div><b>'+nBase+'</b><span>'+plural(nBase,['школа','школы','школ'])+' из базы NOTA за '+state.lim+' мин</span></div>'+
      '<div><b class="'+(nMark?'red':'')+'">'+nMark+'</b><span>'+plural(nMark,['школа','школы','школ'])+' с отметкой за '+state.lim+' мин</span></div>'+
    '</div>'+flags;
  const row = p=>{
    const s=S[p[1]], b=s[10][p[2]], bp=[b[0],b[1]];
    const bn = b[3]==='OSM' && b[2] && norm(b[2])!==norm(s[0]) ? 'корпус: '+b[2] : (b[3]!=='OSM' ? (b[3]==='адрес'||b[3]==='дом' ? 'по адресу школы' : 'место примерное') : '');
    const sub=[bn, fmtDist(p[3])+' по улицам, '+fmtDist(p[4])+' по прямой'].filter(Boolean).map(esc).join(' · ');
    return '<div class="row" tabindex="0" data-rid="'+p[5]+'" data-lat="'+b[0]+'" data-lon="'+b[1]+'" data-si="'+p[1]+'">'+
      '<div class="t">'+mins(p[3])+'<small>мин</small></div>'+
      '<div class="b"><div class="n">'+esc(s[0])+'</div><div class="pills">'+tierPill(p[1])+'</div>'+
      '<div class="s">'+sub+'</div>'+(s[2]&&s[7]?'<div class="w">'+esc(s[7])+'</div>':'')+links(zp,bp,true)+'</div></div>';
  };
  let h='';
  if(state.scope!=='top' || base.length){
    h+='<div class="sec"><div class="sec-h"><h3>Школы из базы NOTA</h3><span>'+base.length+' за '+state.lim+' мин</span></div>';
    h+= base.length ? base.map(row).join('') : '<div class="empty">В '+state.lim+' минутах пешком школ из базы нет. Попробуйте 30 минут или посмотрите сильные школы дальше.</div>';
    h+='</div>';
  }
  if(state.scope==='all' && other.length){
    const show=other.slice(0,4), rest=other.slice(4);
    h+='<div class="sec"><div class="sec-h"><h3>Другие школы рядом</h3><span>'+other.length+' без оценки NOTA</span></div>'+show.map(row).join('');
    if(rest.length) h+='<div id="rest" hidden>'+rest.map(row).join('')+'</div><button class="more" type="button" id="more">Показать ещё '+rest.length+'</button>';
    h+='</div>';
  }
  // сильные школы дальше — по прямой до 5 км
  const shown=new Set(inLim.map(p=>p[1]));
  const strong=[];
  S.forEach((s,si)=>{
    if(!s[6] || (s[3]||0)<40 || shown.has(si)) return;
    let best=null;
    s[10].forEach((b,bi)=>{ const d=hav(z[5],z[6],b[0],b[1]); if(!best||d<best[0]) best=[d,bi]; });
    if(best && best[0]<=5000) strong.push([si,best[0],best[1]]);
  });
  strong.sort((a,b)=>(S[b[0]][3]-S[a[0]][3])||(a[1]-b[1]));
  if(strong.length){
    h+='<div class="sec"><div class="sec-h"><h3>Сильные школы дальше</h3><span>до 5 км по прямой</span></div>'+
      strong.slice(0,5).map(([si,d,bi])=>{ const s=S[si], b=s[10][bi];
        return '<div class="row far" tabindex="0" data-lat="'+b[0]+'" data-lon="'+b[1]+'" data-si="'+si+'"><div class="t">'+(d/1000).toFixed(1).replace('.',',')+'<small>км</small></div>'+
        '<div class="b"><div class="n">'+esc(s[0])+'</div><div class="pills">'+tierPill(si)+'</div><div class="s">по прямой · пешком дальше '+state.lim+' мин</div>'+(s[7]?'<div class="w">'+esc(s[7])+'</div>':'')+links(zp,[b[0],b[1]],false)+'</div></div>'; }).join('')+'</div>';
  }
  elList.innerHTML=h;
  const more=$('more'); if(more) more.onclick=()=>{ $('rest').hidden=false; more.remove(); };
  return scoped;
}

// ---------- панель: школа ----------
function renderSchool(){
  const si=state.si, s=S[si];
  const all=(byS.get(si)||[]).map(i=>P[i]).sort((a,b)=>a[3]-b[3]);
  const lim=state.lim*SPEED;
  const inLim=all.filter(p=>p[3]<=lim && (state.cls==='all' || Z[p[0]][2]===state.cls));
  const nearest=all[0];
  const meta=[s[1]&&s[1]!=='Другая'?s[1]:'школа без оценки NOTA', s[4]+(s[5]&&s[5]!==s[4]?', '+s[5]:''), s[9]].filter(Boolean).map(esc).join(' · ');
  elCard.innerHTML =
    '<div class="eyebrow">Школа</div><h2>'+esc(s[0])+'</h2><div class="pills">'+tierPill(si)+'</div><div class="meta">'+meta+'</div>'+
    (s[7]?'<div class="why">'+esc(s[7])+'</div>':'')+
    (s[8]?'<div class="site"><a href="'+esc(s[8])+'" target="_blank" rel="noopener">'+esc(s[8].replace(/^https?:\/\//,'').replace(/\/$/,''))+' ↗</a></div>':'')+
    '<div class="stats">'+
      '<div><b>'+s[10].length+'</b><span>'+plural(s[10].length,['здание','здания','зданий'])+' на карте</span></div>'+
      '<div><b>'+inLim.length+'</b><span>'+plural(inLim.length,['новый дом','новых дома','новых домов'])+' за '+state.lim+' мин</span></div>'+
      '<div><b>'+(nearest?mins(nearest[3]):'—')+'</b><span>мин до ближайшего дома</span></div>'+
    '</div>';
  const row=p=>{
    const z=Z[p[0]], b=s[10][p[2]];
    const sub=[z[1], z[4], z[9]+(z[10]?' · сдача '+z[10]:''), z[11]?'от '+nf.format(z[11])+' ₽/м²':'', fmtDist(p[3])+' по улицам'].filter(Boolean).map(esc).join(' · ');
    return '<div class="row" tabindex="0" data-rid="'+p[5]+'" data-lat="'+z[5]+'" data-lon="'+z[6]+'" data-zi="'+p[0]+'">'+
      '<div class="t">'+mins(p[3])+'<small>мин</small></div>'+
      '<div class="b"><div class="n">'+esc(z[0])+'</div><div class="pills"><span class="pill">'+esc(z[2])+'</span>'+(String(z[7]).startsWith('адрес')?'':'<span class="pill">координаты примерные</span>')+'</div>'+
      '<div class="s">'+sub+'</div>'+links([z[5],z[6]],[b[0],b[1]],true)+'</div></div>';
  };
  elList.innerHTML='<div class="sec"><div class="sec-h"><h3>Новые дома рядом</h3><span>'+inLim.length+' за '+state.lim+' мин</span></div>'+
    (inLim.length?inLim.map(row).join(''):'<div class="empty">Домов из базы NOTA в '+state.lim+' минутах пешком нет'+(all.length?'. Ближайший — '+esc(Z[all[0][0]][0])+', '+mins(all[0][3])+' мин.':'.')+'</div>')+'</div>';
  return inLim;
}

// ---------- карта ----------
const narrow = window.matchMedia('(max-width: 900px)').matches;
if(narrow){ const lg=document.getElementById('legend'); if(lg) lg.open=false; }
let map=null, mapReady=false, label=null, popup=null;
function fc(f){ return {type:'FeatureCollection', features:f}; }
function initMap(){
  if(!window.maplibregl){ $('loading').textContent='Карта не загрузилась: нет доступа к библиотеке MapLibre. Список слева работает.'; return; }
  map = new maplibregl.Map({
    container:'map',
    style:{version:8, sources:{}, layers:[{id:'bg', type:'background', paint:{'background-color':'#EEF0F2'}}]},
    bounds:[[37.35,55.57],[37.87,55.91]], fitBoundsOptions:{padding:20},
    maxBounds:[[36.4,55.3],[38.4,56.2]], minZoom:8.5, maxZoom:17.5,
    dragRotate:false, pitchWithRotate:false, touchPitch:false, attributionControl:false,
    cooperativeGestures: narrow,
    locale:{'CooperativeGesturesHandler.MobileHelpText':'Двигайте карту двумя пальцами','CooperativeGesturesHandler.WindowsHelpText':'Ctrl + колесо — масштаб','CooperativeGesturesHandler.MacHelpText':'⌘ + колесо — масштаб','NavigationControl.ZoomIn':'Приблизить','NavigationControl.ZoomOut':'Отдалить'}
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({showCompass:false}), 'top-right');
  map.addControl(new maplibregl.AttributionControl({compact:true, customAttribution:'© участники OpenStreetMap'}), 'bottom-right');
  map.on('load', onLoad);
  map.on('error', e=>{ if(e && e.error) console.warn(e.error.message); });
}
function sqIcon(fill){
  const s=28, c=document.createElement('canvas'); c.width=c.height=s; const x=c.getContext('2d');
  x.fillStyle='#FFFFFF'; x.fillRect(2,2,s-4,s-4); x.fillStyle=fill; x.fillRect(6,6,s-12,s-12);
  return x.getImageData(0,0,s,s);
}
function onLoad(){
  const poly = rings => ({type:'Feature', properties:{}, geometry:{type:'Polygon', coordinates:rings.map(dec)}});
  map.addSource('green',{type:'geojson', data:fc(BASE.green.map(poly))});
  map.addSource('water',{type:'geojson', data:fc(BASE.water.map(poly))});
  map.addSource('rail',{type:'geojson', data:fc(BASE.rail.map(s=>({type:'Feature',properties:{},geometry:{type:'LineString',coordinates:dec(s)}})))});
  map.addSource('roads',{type:'geojson', data:fc(BASE.roads.map(([c,s])=>({type:'Feature',properties:{c},geometry:{type:'LineString',coordinates:dec(s)}})))});
  map.addSource('districts',{type:'geojson', data:fc(BASE.districts.map(([n,polys])=>({type:'Feature',properties:{n},geometry:{type:'MultiPolygon',coordinates:polys.map(r=>r.map(dec))}})))});
  map.addSource('metro',{type:'geojson', data:fc(BASE.metro.map(([n,la,lo])=>({type:'Feature',properties:{n},geometry:{type:'Point',coordinates:[lo,la]}})))});
  const sch=[];
  S.forEach((s,si)=>{ const k=kOf(si); s[10].forEach((b,bi)=>sch.push({type:'Feature',properties:{si,k},geometry:{type:'Point',coordinates:[b[1],b[0]]}})); });
  map.addSource('schools',{type:'geojson', data:fc(sch)});
  map.addSource('zhk',{type:'geojson', data:fc(Z.map((z,i)=>({type:'Feature',properties:{i, c:CLS_ORDER[z[2]]||1},geometry:{type:'Point',coordinates:[z[6],z[5]]}})))});
  map.addSource('routes',{type:'geojson', data:fc([])});
  map.addSource('hl',{type:'geojson', data:fc([])});
  map.addSource('sel',{type:'geojson', data:fc([])});
  map.addImage('z1', sqIcon('#9AA2AA'), {pixelRatio:2}); map.addImage('z2', sqIcon('#6A727B'), {pixelRatio:2});
  map.addImage('z3', sqIcon('#3A4047'), {pixelRatio:2}); map.addImage('z4', sqIcon('#101317'), {pixelRatio:2});

  const zi = (a,b)=>['interpolate',['linear'],['zoom']].concat(a.flatMap((z,j)=>[z,b[j]]));
  const zim = (a,b,mult)=>['interpolate',['linear'],['zoom']].concat(a.flatMap((z,j)=>[z,['*',mult,b[j]]]));
  map.addLayer({id:'green', type:'fill', source:'green', paint:{'fill-color':'#E2E7E1'}});
  map.addLayer({id:'water', type:'fill', source:'water', paint:{'fill-color':'#D3DDE6'}});
  map.addLayer({id:'dist', type:'line', source:'districts', paint:{'line-color':'#BFC6CD','line-width':zi([9,14],[0.5,1]),'line-dasharray':[3,2]}});
  map.addLayer({id:'rail', type:'line', source:'rail', paint:{'line-color':'#BAC1C8','line-width':zi([9,15],[0.6,1.6])}});
  map.addLayer({id:'road-minor-c', type:'line', source:'roads', minzoom:12.5, filter:['>=',['get','c'],5], layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#D9DEE3','line-width':zi([12.5,14,16,17.5],[0.8,3.2,8,14])}});
  map.addLayer({id:'road-ter-c', type:'line', source:'roads', minzoom:11, filter:['==',['get','c'],4], layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#D3D9DF','line-width':zi([11,14,16,17.5],[1.2,4.2,10,16])}});
  map.addLayer({id:'road-maj-c', type:'line', source:'roads', filter:['<=',['get','c'],3], layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#C4CCD3','line-width':zi([9,12,14,16,17.5],[1.1,2.4,6,13,20])}});
  map.addLayer({id:'road-minor', type:'line', source:'roads', minzoom:12.5, filter:['>=',['get','c'],5], layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#FFFFFF','line-width':zi([12.5,14,16,17.5],[0.4,2.2,6.5,12])}});
  map.addLayer({id:'road-ter', type:'line', source:'roads', minzoom:11, filter:['==',['get','c'],4], layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#FFFFFF','line-width':zi([11,14,16,17.5],[0.6,3,8.5,14])}});
  map.addLayer({id:'road-maj', type:'line', source:'roads', filter:['<=',['get','c'],3], layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#FFFFFF','line-width':zi([9,12,14,16,17.5],[0.6,1.6,4.6,11,18])}});
  map.addLayer({id:'metro', type:'circle', source:'metro', minzoom:12, paint:{'circle-radius':zi([12,16],[2.5,5]),'circle-color':'#FFFFFF','circle-stroke-color':'#6A727B','circle-stroke-width':1.4}});
  map.addLayer({id:'rt-case', type:'line', source:'routes', layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#FFFFFF','line-width':zi([10,14,17],[2.5,5.5,9]),'line-opacity':0.9}});
  map.addLayer({id:'rt', type:'line', source:'routes', layout:{'line-join':'round','line-cap':'round','line-sort-key':['get','k']}, paint:{'line-color':['case',['==',['get','k'],4],'#CE2029','#101317'],'line-opacity':['case',['==',['get','k'],4],0.85,0.5],'line-width':zi([10,14,17],[1.2,3,5])}});
  map.addLayer({id:'hl-case', type:'line', source:'hl', layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#FFFFFF','line-width':zi([10,14,17],[5,9,13])}});
  map.addLayer({id:'hl', type:'line', source:'hl', layout:{'line-join':'round','line-cap':'round'}, paint:{'line-color':'#CE2029','line-width':zi([10,14,17],[2.5,5,7])}});
  map.addLayer({id:'sch-osm', type:'circle', source:'schools', minzoom:12, filter:['==',['get','k'],0], paint:{'circle-radius':zi([12,16],[2.2,4.8]),'circle-color':'#FFFFFF','circle-stroke-color':'#9AA2AA','circle-stroke-width':1.3}});
  map.addLayer({id:'sch', type:'circle', source:'schools', filter:['>',['get','k'],0], layout:{'circle-sort-key':['get','k']}, paint:{
    'circle-radius':zim([9,12,15,17],[2.4,3.6,5.6,8],['match',['get','k'],4,1.35,3,1.1,2,1,0.85]),
    'circle-color':['match',['get','k'],4,'#CE2029',3,'#FFFFFF',2,'#6A727B','#AEB5BC'],
    'circle-stroke-color':['match',['get','k'],3,'#101317','#FFFFFF'],
    'circle-stroke-width':['match',['get','k'],3,2,1.2]}});
  map.addLayer({id:'zhk', type:'symbol', source:'zhk', layout:{'icon-image':['concat','z',['to-string',['get','c']]],'icon-size':zi([9,12,15,17],[0.5,0.7,1,1.25]),'icon-allow-overlap':true,'icon-ignore-placement':true,'symbol-sort-key':['get','c']}});
  map.addLayer({id:'sel', type:'circle', source:'sel', paint:{'circle-radius':zi([9,14,17],[9,14,18]),'circle-color':'rgba(0,0,0,0)','circle-stroke-color':'#101317','circle-stroke-width':2}});

  popup = new maplibregl.Popup({closeButton:false, closeOnClick:false, offset:10, maxWidth:'280px'});
  const hover = (layer, html)=>{
    map.on('mousemove', layer, e=>{ map.getCanvas().style.cursor='pointer'; const f=e.features[0]; popup.setLngLat(f.geometry.coordinates).setHTML(html(f.properties)).addTo(map); });
    map.on('mouseleave', layer, ()=>{ map.getCanvas().style.cursor=''; popup.remove(); });
  };
  const minsTo = (zi,si)=>{ const ps=(byZ.get(zi)||[]).map(i=>P[i]).filter(p=>p[1]===si); return ps.length?mins(ps[0][3]):null; };
  hover('zhk', p=>{ const z=Z[p.i]; let t='<b>'+esc(z[0])+'</b><br>'+esc(z[2])+' · '+esc(z[4]); if(state.mode==='sch'){ const m=minsTo(p.i,state.si); if(m) t+='<br>'+m+' мин до школы'; } return t; });
  const shov = p=>{ const s=S[p.si]; let t='<b>'+esc(s[0])+'</b>'+(s[2]?'<br>'+esc(s[2])+(s[3]!=null?' · '+s[3]+' из 100':''):(s[6]?'':'<br>без оценки NOTA')); if(state.mode==='zhk'){ const m=minsTo(state.zi,p.si); if(m) t+='<br>'+m+' мин пешком'; } return t; };
  hover('sch', shov); hover('sch-osm', shov);
  hover('metro', p=>'м. '+esc(p.n));
  map.on('click','zhk', e=>{ state.mode='zhk'; state.zi=e.features[0].properties.i; update(true); });
  const sclick = e=>{ state.mode='sch'; state.si=e.features[0].properties.si; update(true); };
  map.on('click','sch', sclick); map.on('click','sch-osm', sclick);
  label = new maplibregl.Marker({element:Object.assign(document.createElement('div'),{className:'maplabel'}), anchor:'bottom'});
  mapReady=true; $('loading').hidden=true;
  update(true);
}
function drawMap(pairs, fit){
  if(!mapReady) return;
  const feats=[];
  pairs.forEach(p=>{ if(p[5]>=0) feats.push({type:'Feature', properties:{rid:p[5], k: state.mode==='zhk'?kOf(p[1]):1}, geometry:{type:'LineString', coordinates:route(p[5])}}); });
  map.getSource('routes').setData(fc(feats));
  map.getSource('hl').setData(fc([]));
  let pt, name;
  if(state.mode==='zhk'){ const z=Z[state.zi]; pt=[z[6],z[5]]; name=z[0]; map.getSource('sel').setData(fc([{type:'Feature',properties:{},geometry:{type:'Point',coordinates:pt}}])); }
  else { const s=S[state.si]; name=s[0]; map.getSource('sel').setData(fc(s[10].map(b=>({type:'Feature',properties:{},geometry:{type:'Point',coordinates:[b[1],b[0]]}})))); pt=[s[10][0][1],s[10][0][0]]; }
  label.getElement().textContent=name; label.setLngLat(pt).addTo(map);
  if(fit){
    const b=new maplibregl.LngLatBounds(pt,pt);
    if(state.mode==='sch') S[state.si][10].forEach(x=>b.extend([x[1],x[0]]));
    feats.forEach(f=>f.geometry.coordinates.forEach(c=>b.extend(c)));
    if(feats.length===0){ map.flyTo({center:pt, zoom:14, duration:600}); }
    else map.fitBounds(b, {padding: narrow? 36 : {top:60,bottom:60,left:60,right:60}, maxZoom:16, duration:600});
  }
}
function setHL(rid){
  if(!mapReady) return;
  map.getSource('hl').setData(fc(rid>=0?[{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:route(rid)}}]:[]));
}
elList.addEventListener('mouseover', e=>{ const r=e.target.closest('.row[data-rid]'); if(r) setHL(+r.dataset.rid); });
elList.addEventListener('mouseout', e=>{ const r=e.target.closest('.row[data-rid]'); if(r && !r.contains(e.relatedTarget)) setHL(-1); });
elList.addEventListener('focusin', e=>{ const r=e.target.closest('.row[data-rid]'); if(r) setHL(+r.dataset.rid); });
elList.addEventListener('click', e=>{
  if(e.target.closest('a,button')) return;
  const r=e.target.closest('.row'); if(!r||!mapReady) return;
  const rid=+(r.dataset.rid||-1);
  setHL(rid);
  if(rid>=0){ const b=new maplibregl.LngLatBounds(); route(rid).forEach(c=>b.extend(c)); map.fitBounds(b,{padding:70,maxZoom:16.5,duration:500}); }
  else map.flyTo({center:[+r.dataset.lon,+r.dataset.lat], zoom:14.5, duration:500});
  if(narrow) document.querySelector('.mapwrap').scrollIntoView({behavior:'smooth', block:'start'});
});
elList.addEventListener('keydown', e=>{ if(e.key==='Enter'){ const r=e.target.closest('.row'); if(r) r.click(); } });

function update(fit){
  renderControls();
  const pairs = state.mode==='zhk' ? renderZhk() : renderSchool();
  drawMap(pairs, fit);
}
update(false);
initMap();
})();
