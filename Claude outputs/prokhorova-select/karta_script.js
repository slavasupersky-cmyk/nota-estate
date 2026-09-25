/* ---------- объекты: дома реальные (база NOTA), квартиры и цены — демо ---------- */
const OBJ = {{OBJ_JSON}};
const SN = {w:"Был ранее",n:"Новый за неделю",g:"Ушёл за неделю"};
const ORDER = {n:0,w:1,g:2};
const fmt = n => n.toLocaleString("ru-RU");
const cnt = s => OBJ.filter(o=>o.s===s).length;
document.querySelector('[data-stat=all]').textContent = OBJ.length - cnt('g');
document.querySelector('[data-stat=new]').textContent = "+"+cnt('n');
document.querySelector('[data-stat=gone]').textContent = "−"+cnt('g');

const pts = document.getElementById('pts');
const list = document.getElementById('objlist');
const panel = document.getElementById('panel');
let sel = null, filter = 'all';
const COL = {w:'var(--was)',n:'var(--new)',g:'var(--gone)'};

/* точки на карте */
OBJ.forEach(o=>{
  const g = document.createElementNS('http://www.w3.org/2000/svg','g');
  g.setAttribute('class','pt'); g.dataset.id=o.id;
  const r = o.p>=200?7.5:o.p>=120?6:5;
  g.innerHTML = `<circle class="h" cx="${o.x}" cy="${o.y}" r="16"/><circle class="d" cx="${o.x}" cy="${o.y}" r="${r}" fill="${COL[o.s]}" stroke="var(--bg2)" stroke-width="1.5" ${o.s==='g'?'opacity=".8"':''}/>`;
  g.addEventListener('click',()=>select(o.id,true));
  pts.appendChild(g);
});

/* таблица: группы по статусу, внутри — по цене */
const sorted = [...OBJ].sort((a,b)=>ORDER[a.s]-ORDER[b.s] || a.p-b.p);
sorted.forEach(o=>{
  const row = document.createElement('div');
  row.className = 'orow'; row.dataset.id=o.id; row.dataset.s=o.s;
  row.innerHTML = `<button class="rowbtn" aria-expanded="false">
      <i class="st-${o.s}"></i>
      <span class="c-name"><b>${o.n}</b><small>${o.d} · ${o.a}</small></span>
      <span class="c-area">${o.m}</span><span class="c-rooms">${o.r}</span><span class="c-floor">${o.f}/${o.ff}</span>
      <span class="c-price"><b>${fmt(o.p)} млн</b></span><span class="c-m2">${fmt(Math.round(o.p*1e6/o.m/1000))} тыс.</span>
    </button><div class="odet" hidden></div>`;
  row.querySelector('.rowbtn').addEventListener('click',()=>select(o.id,false));
  list.appendChild(row);
});

function detailHTML(o){
  const gone = o.s==='g';
  const gal = [];
  if(o.img) gal.push(`<figure><img src="${o.img}" alt="${o.n}"><figcaption>Дом · фото из базы NOTA</figcaption></figure>`);
  if(o.pic1) gal.push(`<figure><img src="${o.pic1}" alt="Интерьер"><figcaption>Интерьер · демо-визуализация</figcaption></figure>`);
  if(o.pic2) gal.push(`<figure><img src="${o.pic2}" alt="Фасад"><figcaption>${o.cap2||"Фасад"} · демо-визуализация</figcaption></figure>`);
  if(o.plan) gal.push(`<figure class="plan">${o.plan}<figcaption>Планировка · вымышленная, для прототипа</figcaption></figure>`);
  return `<div class="odet-in">
    <div class="ogal ${gal.length>2?'wide':''}">${gal.join('')}</div>
    <div class="oinfo">
      <span class="tag"><i class="st-${o.s}"></i>${SN[o.s]}</span>
      <div class="price">${fmt(o.p)} млн ₽ <span class="mute" style="font-size:14px">· ${fmt(Math.round(o.p*1e6/o.m/1000))} тыс. ₽/м²</span></div>
      <div class="params"><div><small>Площадь</small>${o.m} м²</div><div><small>Спален</small>${o.r}</div><div><small>Этаж</small>${o.f} из ${o.ff}</div><div><small>Класс дома</small>${o.c}</div><div><small>Потолки</small>${o.h||'—'}</div><div><small>Состояние</small>${o.st}</div></div>
      <p class="mute" style="font-size:14px">${o.t||(gone?'Объект ушёл с рынка на этой неделе. Могу показать похожие, которые ещё готовятся к выходу.':'Проверен: документы, история прав, перепланировки, дом. Презентация и точный адрес — после запроса.')}</p>
      <div class="acts">${gone?`<a class="btn" href="#kupit">Подобрать похожие</a>`:`
        <button class="btn" data-lead="Запросить подробности">Запросить подробности</button>
        <button class="btn ghost" data-lead="Получить презентацию">Получить презентацию</button>
        <button class="btn ghost" data-lead="Записаться на просмотр">Узнать условия / записаться на просмотр</button>`}</div>
    </div></div>`;
}

function renderPanel(){
  if(sel===null){
    const n=cnt('n'),g=cnt('g');
    panel.innerHTML = `<p class="eyebrow">За неделю</p>
      <div class="stats"><div class="n"><b>+${n}</b><small>новых</small></div><div class="g"><b>−${g}</b><small>ушли</small></div><div><b>${OBJ.length-g}</b><small>в продаже</small></div></div>
      <p class="mute">Нажмите на точку или строку в таблице ниже. Точка крупнее — дороже.</p>
      <p class="mute" style="font-size:14px">Ушедшие объекты остаются на карте неделю: так видно, как двигается рынок в вашем районе.</p>
      <div class="acts"><a class="btn ghost" href="#kupit">Ищете другое? Оставьте параметры</a></div>`;
    return;
  }
  const o = OBJ[sel];
  panel.innerHTML = `${o.img?`<img class="pimg" src="${o.img}" alt="">`:''}
    <span class="tag"><i class="st-${o.s}"></i>${SN[o.s]}</span>
    <div><p class="eyebrow">${o.d}</p><h3 style="margin-top:6px">${o.n}</h3><p class="mute" style="font-size:13px">${o.a}</p></div>
    <div class="price">${fmt(o.p)} млн ₽</div>
    <div class="params"><div><small>Площадь</small>${o.m} м²</div><div><small>Спален</small>${o.r}</div><div><small>Этаж</small>${o.f} из ${o.ff}</div></div>
    <div class="acts"><button class="btn ghost sm" id="torow">Подробнее в таблице ↓</button></div>`;
  panel.querySelector('#torow').addEventListener('click',()=>{const r=list.querySelector(`.orow[data-id="${o.id}"]`);r.scrollIntoView({behavior:'smooth',block:'start'})});
}

function select(id, fromMap){
  const same = sel===id;
  sel = same && !fromMap ? null : id;
  document.querySelectorAll('.pt').forEach(p=>p.classList.toggle('sel',+p.dataset.id===sel));
  list.querySelectorAll('.orow').forEach(r=>{
    const open = +r.dataset.id===sel;
    const det = r.querySelector('.odet'), btn = r.querySelector('.rowbtn');
    if(open && !det.innerHTML){ det.innerHTML = detailHTML(OBJ[sel]); det.querySelectorAll('[data-lead]').forEach(b=>b.addEventListener('click',()=>openLead(b.dataset.lead,OBJ[sel]))); }
    det.hidden = !open; btn.setAttribute('aria-expanded', open);
    r.classList.toggle('open', open);
  });
  renderPanel();
  if(fromMap && sel!==null){
    const r = list.querySelector(`.orow[data-id="${sel}"]`);
    const rect = r.getBoundingClientRect();
    if(rect.top<0 || rect.top>window.innerHeight*0.7) r.scrollIntoView({behavior:'smooth',block:'start'});
  }
}
function applyFilter(){
  let shown=0;
  document.querySelectorAll('.pt').forEach(p=>{const o=OBJ[+p.dataset.id];const h=filter!=='all'&&o.s!==filter;p.classList.toggle('hidden',h);if(!h)shown++});
  list.querySelectorAll('.orow').forEach(r=>r.classList.toggle('hidden',filter!=='all'&&r.dataset.s!==filter));
  document.getElementById('map-count').textContent = shown+' на карте';
  if(sel!==null && filter!=='all' && OBJ[sel].s!==filter){ select(sel,false); }
}
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
  filter=c.dataset.f;document.querySelectorAll('.chip').forEach(x=>x.setAttribute('aria-pressed',x===c));applyFilter();
}));
renderPanel(); applyFilter();
