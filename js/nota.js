(function(){
 /* ---- шапка: прозрачная над героем, плотная при скролле ---- */
 var bar=document.getElementById('top-bar'), hero=document.querySelector('.hero');
 if(bar&&hero){
  var last=window.scrollY, tick=false;
  var apply=function(){
   var y=window.scrollY;
   bar.classList.toggle('solid', y>40);
   if(window.innerWidth<=860){
    if(y>last&&y>200) bar.classList.add('away');
    else if(y<last-4||y<90) bar.classList.remove('away');
   } else bar.classList.remove('away');
   last=y; tick=false;
  };
  apply();
  window.addEventListener('scroll',function(){ if(!tick){tick=true;requestAnimationFrame(apply)} },{passive:true});
 }
 /* ---- свои выпадающие списки ---- */
 var sels=Array.prototype.slice.call(document.querySelectorAll('.sel'));
 function closeAll(except){
  sels.forEach(function(s){ if(s!==except){s.classList.remove('open');s.querySelector('.sel-btn').setAttribute('aria-expanded','false');} });
 }
 sels.forEach(function(s){
  var btn=s.querySelector('.sel-btn'), list=s.querySelector('.sel-list');
  var items=Array.prototype.slice.call(list.querySelectorAll('li'));
  btn.setAttribute('aria-haspopup','listbox');btn.setAttribute('aria-expanded','false');
  list.setAttribute('role','listbox');
  s.dataset.value=btn.textContent.trim();
  items.forEach(function(li,i){
   li.setAttribute('role','option');
   li.setAttribute('aria-selected', i===0 ? 'true':'false');
   li.addEventListener('click',function(){
    items.forEach(function(x){x.setAttribute('aria-selected','false')});
    li.setAttribute('aria-selected','true');
    btn.textContent=li.textContent; s.dataset.value=li.textContent.trim();
    closeAll(); btn.focus();
    s.dispatchEvent(new CustomEvent('selchange',{bubbles:true}));
   });
  });
  btn.addEventListener('click',function(e){
   e.stopPropagation();
   var open=s.classList.contains('open');
   closeAll(); if(!open){s.classList.add('open');btn.setAttribute('aria-expanded','true');}
  });
  s.addEventListener('keydown',function(e){
   if(e.key==='Escape'){closeAll();btn.focus();}
   if(e.key==='ArrowDown'||e.key==='ArrowUp'){
    e.preventDefault();
    var cur=items.findIndex(function(x){return x.getAttribute('aria-selected')==='true'});
    var n=Math.min(items.length-1,Math.max(0,cur+(e.key==='ArrowDown'?1:-1)));
    items[n].click(); if(!s.classList.contains('open')){s.classList.add('open');btn.setAttribute('aria-expanded','true');}
   }
  });
 });
 document.addEventListener('click',function(){closeAll()});
 function val(name){var s=document.querySelector('.sel[data-name="'+name+'"]');return s?s.dataset.value:''}

 /* ---- фильтры базы ---- */
 var chipsBox=document.getElementById('chips');
 if(chipsBox){
  var KEY={cls:'c',bin:'b',form:'f'};
  var groups={};
  document.querySelectorAll('[data-group]').forEach(function(b){(groups[b.dataset.group]=groups[b.dataset.group]||[]).push(b)});
  var rows=Array.prototype.slice.call(document.querySelectorAll('#base tr[data-c]'));
  var state={};
  Object.keys(groups).forEach(function(g){state[g]='all'});
  function ok(el){
   return Object.keys(state).every(function(g){
    return state[g]==='all' || el.dataset[KEY[g]]===state[g];
   });
  }
  function apply(){
   var n=0;
   rows.forEach(function(r){var on=ok(r);r.style.display=on?'':'none';if(on)n++});
   var c=document.getElementById('cnt');
   if(c)c.textContent='Показано '+n+' из '+rows.length+' строк среза. Полная база — 288 домов.';
   document.querySelectorAll('#mapdots [data-c]').forEach(function(d){
    var on=ok(d); d.style.opacity=on?'1':'.10';
   });
  }
  Object.keys(groups).forEach(function(g){
   groups[g].forEach(function(b){
    b.addEventListener('click',function(){
     groups[g].forEach(function(x){x.setAttribute('aria-pressed','false')});
     b.setAttribute('aria-pressed','true'); state[g]=b.dataset.k; apply();
    });
   });
  });
  apply();
 }

/* ---- активный пункт меню ---- */
 (function(){
  var f=(location.pathname.split('/').pop()||'index.html');
  var map={'karta.html':'karta','razbory.html':'razbory','razbor-hamovniki.html':'razbory','nota-index.html':'index'};
  var k=map[f]||(/^index-\d/.test(f)?'index':null); if(!k)return;
  document.querySelectorAll('.nav a[data-m="'+k+'"]').forEach(function(a){a.classList.add('cur')});
 })();

 /* ---- бургер ---- */
 var bg=document.getElementById('burger'), nv=document.querySelector('.nav');
 if(bg&&nv){
  var setm=function(on){
   nv.classList.toggle('open',on); bg.classList.toggle('on',on);
   bg.setAttribute('aria-expanded',on?'true':'false');
   document.documentElement.style.overflow=on?'hidden':'';
  };
  bg.addEventListener('click',function(){setm(!nv.classList.contains('open'))});
  nv.addEventListener('click',function(e){if(e.target.tagName==='A')setm(false)});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')setm(false)});
 }

 /* ---- анкета ---- */
 var host=document.getElementById('sliders');
 if(host){
  ['Место','Вид','Дом','Планировка','Двор','Свет','Сценарий'].forEach(function(k){
   var d=document.createElement('div');d.className='row';
   d.innerHTML='<label>'+k+'</label><input type="range" min="1" max="10" value="5" data-k="'+k+'" aria-label="Вес: '+k+'"><output>5</output>';
   host.appendChild(d);
  });
  var draw=function(){
   var ins=Array.prototype.slice.call(host.querySelectorAll('input'));
   ins.forEach(function(i){i.nextElementSibling.textContent=i.value});
   var s=ins.slice().sort(function(a,b){return b.value-a.value});
   var rank=document.getElementById('rank');rank.innerHTML='';
   s.slice(0,3).forEach(function(i,n){
    var el=document.createElement('span');el.textContent=i.dataset.k+' · '+i.value;rank.appendChild(el);
   });
   var low=s[s.length-1], spread=s[0].value-low.value;
   var v='Больше всего для вас значит '+s[0].dataset.k.toLowerCase()+', меньше всего — '+low.dataset.k.toLowerCase()+'. ';
   v+= spread<3 ? 'Веса почти ровные — так бывает, когда сценарий ещё не выбран. Тогда начнём с разговора, а не с подборки.'
     : 'С такими весами домов останется меньше, чем кажется, — и это нормально: мы ставим отметку восемнадцати из 288.';
   var sc=val('scen'), bd=val('budget');
   if(sc&&bd)v+=' '+sc+'. '+bd.charAt(0).toUpperCase()+bd.slice(1)+'.';
   document.getElementById('verdict').textContent=v;
  };
  host.addEventListener('input',draw);
  document.addEventListener('selchange',draw);
  draw();

  /* ---- окно «соберите подборку» ---- */
  var mdl=document.getElementById('mdl'), ask=document.getElementById('ask');
  function summary(){
   var ins=Array.prototype.slice.call(host.querySelectorAll('input'));
   var s2=ins.slice().sort(function(a,b){return b.value-a.value});
   var top=s2.slice(0,3).filter(function(i){return i.value>=6}).map(function(i){return i.dataset.k.toLowerCase()});
   var low=s2.slice(-2).filter(function(i){return i.value<=4}).map(function(i){return i.dataset.k.toLowerCase()});
   var t=[];
   var sc=val('scen'), bd=val('budget'), gr=val('gor'), sr=val('srok');
   if(sc) t.push(sc.charAt(0).toUpperCase()+sc.slice(1)+'.');
   if(bd) t.push(bd+'.');
   if(gr) t.push(gr+'.');
   if(sr) t.push(sr+'.');
   var w='';
   if(top.length) w='Важнее всего — '+top.join(', ')+'.';
   else w='Веса расставлены ровно, без явного фаворита.';
   if(low.length) w+=' Готовы уступить в том, что касается: '+low.join(', ')+'.';
   return t.join(' ')+' '+w;
  }
  if(ask&&mdl){
   var close=function(){mdl.hidden=true; document.body.style.overflow=''};
   ask.addEventListener('click',function(){
    document.getElementById('mdl-sum').textContent=summary();
    mdl.hidden=false; document.body.style.overflow='hidden';
    var f=mdl.querySelector('input'); if(f)setTimeout(function(){f.focus()},60);
   });
   mdl.addEventListener('click',function(e){ if(e.target.hasAttribute('data-close')) close(); });
   document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&!mdl.hidden) close(); });
  }
 }
})();

/* ---- калькулятор «Сколько стоит ожидание» ---- */
(function(){
 var box=document.getElementById('calc'); if(!box) return;
 var g=function(id){return document.getElementById(id)};
 var ids=['c-area','c-rent','c-wait'];
 var remBtns=Array.prototype.slice.call(document.querySelectorAll('#c-rem .chip'));
 function num(v){return v.toLocaleString('ru-RU')}
 function mln(r){return (r/1e6).toLocaleString('ru-RU',{minimumFractionDigits:1,maximumFractionDigits:1})+' млн ₽'}
 function mon(m){var n=Math.round(m),a=n%10,b=n%100;var w=(a==1&&b!=11)?'месяц':(a>=2&&a<=4&&(b<12||b>14))?'месяца':'месяцев';return n+' '+w}
 function draw(){
  var v={};ids.forEach(function(i){var el=g(i);v[i]=parseFloat(el.value);var o=el.nextElementSibling;o.textContent=num(v[i])+' '+o.dataset.u});
  var on=remBtns.filter(function(b){return b.getAttribute('aria-pressed')==='true'})[0]||remBtns[1];
  var per=+on.dataset.v, rm=+on.dataset.m;
  var rem=v['c-area']*per*1e3, months=v['c-wait']+rm, rent=v['c-rent']*1e3*months;
  g('o-rem').textContent=mln(rem);
  g('o-rem-d').textContent=num(v['c-area'])+' м² × '+per+' тыс ₽ за метр. Примерно '+mon(rm)+' работ.';
  g('o-rent').textContent=mln(rent);
  g('o-rent-d').textContent=mon(v['c-wait'])+' стройки и '+mon(rm)+' ремонта — всего '+mon(months)+' на съёмной квартире.';
  g('o-v').innerHTML='Сверх цены квартиры: <em>'+mln(rem+rent)+'</em> и '+mon(months)+' до переезда. Эту сумму стоит держать в голове, когда сравниваете новостройку с готовой квартирой.';
 }
 ids.forEach(function(i){g(i).addEventListener('input',draw)});
 remBtns.forEach(function(b){b.addEventListener('click',function(){remBtns.forEach(function(x){x.setAttribute('aria-pressed','false')});b.setAttribute('aria-pressed','true');draw();})});
 draw();
})();

/* ---- карта объектов: фильтры, карточка дома, список ---- */
(function(){
 var map=document.getElementById('kmap'); if(!map) return;
 var data=JSON.parse(document.getElementById('kdata').textContent);
 var dots=[].slice.call(map.querySelectorAll('.kd')), items=[].slice.call(document.querySelectorAll('.hs'));
 var chips=[].slice.call(document.querySelectorAll('.kmap-l .chip')), cnt=document.getElementById('kcnt'), kt=document.getElementById('kt');
 var st={c:'all',y:'all',f:'all'};
 var SZ={biz:[45,70,100],prem:[60,90,130],elit:[90,140,200],dlx:[120,180,250]};
 function ok(el){return (st.c=='all'||el.dataset.c==st.c)&&(st.y=='all'||el.dataset.y==st.y)&&(st.f=='all'||(' '+el.dataset.f+' ').indexOf(' '+st.f+' ')>-1)}
 function okExcept(el,g,k){var t={c:st.c,y:st.y,f:st.f};t[g]=k;return (t.c=='all'||el.dataset.c==t.c)&&(t.y=='all'||el.dataset.y==t.y)&&(t.f=='all'||(' '+el.dataset.f+' ').indexOf(' '+t.f+' ')>-1)}
 function facets(){chips.forEach(function(b){var n=0;items.forEach(function(it){if(okExcept(it,b.dataset.g,b.dataset.k))n++});var c=b.querySelector('.cn');if(c)c.textContent=n;b.classList.toggle('zero',n===0&&b.getAttribute('aria-pressed')!=='true')})}
 function apply(){var n=0;facets();dots.forEach(function(d){d.classList.toggle('off',!ok(d))});items.forEach(function(it){var on=ok(it);it.hidden=!on;if(on)n++});cnt.textContent='Показано '+n+' из '+items.length;if(kt&&!kt.hidden){var i=+kt.dataset.i;if(!ok(dots[i]))hideT()}}
 chips.forEach(function(b){b.addEventListener('click',function(){var g=b.dataset.g;chips.filter(function(x){return x.dataset.g==g}).forEach(function(x){x.setAttribute('aria-pressed','false')});b.setAttribute('aria-pressed','true');st[g]=b.dataset.k;apply()})});
 document.querySelectorAll('[data-reset]').forEach(function(b){b.addEventListener('click',function(){st={c:'all',y:'all',f:'all'};chips.forEach(function(x){x.setAttribute('aria-pressed',x.dataset.k=='all'?'true':'false')});apply()})});
 function mln(v){return v.toLocaleString('ru-RU',{minimumFractionDigits:1,maximumFractionDigits:1})}
 function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
 function side(it){
  var sd=it.querySelector('.hs-side'); if(sd.dataset.done) return; var r=data[+it.dataset.i], h='';
  h+='<div class="hs-ex"><p class="k">Примеры стоимости</p>';
  if(r.p){h+='<ul>'+SZ[r.k].map(function(s){return '<li><b>'+s+' м²</b><span>≈ '+mln(r.p*s/1000)+' млн ₽</span></li>'}).join('')+'</ul><p class="hint">Расчёт от цены «от», а не предложение: этаж, вид и отделка двигают цену.</p>'}
  else h+='<p>Цену застройщик не публикует — узнаем для вас.</p>';
  h+='</div><div class="hs-real"><p class="k">Что в продаже сейчас</p>';
  h+= r.x ? '<p>В продаже '+esc(r.x[0]||'—')+' лотов, самый доступный — '+esc(r.x[1]||'—')+' м² за '+esc(r.x[2]||'—')+' млн ₽. Сверка '+esc(r.x[3]||'')+'.</p>' : '<p>Застройщики меняют прайс и набор лотов каждую неделю. Пришлём, что в продаже сейчас: минимальный лот, планировки и условия оплаты.</p>';
  h+='</div><div class="btns"><button class="btn hs-cta" type="button" data-house="'+esc(r.n)+'">Хочу актуальное предложение</button>'+(r.dm?' <a class="btn btn-l" href="doma/'+r.dm+'/">Подробный разбор</a>':'')+'</div>';
  sd.innerHTML=h; sd.dataset.done=1;
 }
 function openItem(it,scroll){
  items.forEach(function(x){if(x!==it&&x.classList.contains('open')){x.classList.remove('open');x.querySelector('.hs-body').hidden=true;x.querySelector('.hs-row').setAttribute('aria-expanded','false')}});
  side(it); it.classList.add('open'); it.querySelector('.hs-body').hidden=false; it.querySelector('.hs-row').setAttribute('aria-expanded','true');
  dots.forEach(function(d){d.classList.toggle('sel',d.dataset.i==it.dataset.i)});
  if(scroll) it.scrollIntoView({behavior:'smooth',block:'start'});
 }
 items.forEach(function(it){it.querySelector('.hs-row').addEventListener('click',function(){
  if(it.classList.contains('open')){it.classList.remove('open');it.querySelector('.hs-body').hidden=true;this.setAttribute('aria-expanded','false');dots[+it.dataset.i].classList.remove('sel')} else openItem(it,false)})});
 function showT(d,pinned){
  var r=data[+d.dataset.i], box=map.getBoundingClientRect(), p=d.getBoundingClientRect();
  kt.innerHTML=(pinned?'<button class="kt-x" type="button" aria-label="Закрыть">×</button>':'')+(r.img?'<div class="kt-img" style="background-image:url(img/doma/'+r.s+'.jpg)"></div>':'')+
   '<div class="kt-b"><b>'+esc(r.n)+'</b><span class="m">'+esc(r.d)+'</span><span class="m">'+esc(r.c)+' · '+esc(r.ds)+'</span><span class="kt-pr">'+(r.p?'от '+r.p.toLocaleString('ru-RU')+' тыс ₽ за м²':'цена по запросу')+'</span><span class="m">Ключи: '+esc(r.w)+'</span>'+
   (pinned?'<button class="btn" type="button" data-open="'+d.dataset.i+'">Открыть карточку</button>':'')+'</div>';
  kt.dataset.i=d.dataset.i; kt.hidden=false;
  var x=p.left-box.left+p.width/2+14, y=p.top-box.top-10, w=kt.offsetWidth, hgt=kt.offsetHeight;
  if(x+w>box.width) x=p.left-box.left-w-14; if(y+hgt>box.height) y=box.height-hgt-6; if(y<6) y=6;
  kt.style.left=Math.max(6,x)+'px'; kt.style.top=y+'px'; kt.dataset.pin=pinned?1:'';
 }
 function hideT(){kt.hidden=true;kt.dataset.pin=''}
 dots.forEach(function(d){
  d.addEventListener('mouseenter',function(){if(!kt.dataset.pin) showT(d,false)});
  d.addEventListener('mouseleave',function(){if(!kt.dataset.pin) hideT()});
  d.addEventListener('click',function(ev){ev.stopPropagation();showT(d,true);dots.forEach(function(x){x.classList.toggle('sel',x===d)})});
 });
 kt.addEventListener('click',function(ev){
  if(ev.target.classList.contains('kt-x')){hideT();return}
  var o=ev.target.getAttribute('data-open'); if(o!==null){var it=items.filter(function(x){return x.dataset.i==o})[0]; hideT(); if(it){it.hidden=false; openItem(it,true)}}
 });
 map.addEventListener('click',function(ev){
  if(ev.target.tagName==='circle'||kt.contains(ev.target)) return;
  var best=null,bd=18*18; dots.forEach(function(d){if(d.classList.contains('off'))return;var q=d.getBoundingClientRect(),dx=q.left+q.width/2-ev.clientX,dy=q.top+q.height/2-ev.clientY,dd=dx*dx+dy*dy;if(dd<bd){bd=dd;best=d}});
  if(best){showT(best,true);dots.forEach(function(x){x.classList.toggle('sel',x===best)})} else hideT();
 });
 /* заявка по дому */
 var md=document.getElementById('kmdl');
 document.addEventListener('click',function(ev){var b=ev.target.closest&&ev.target.closest('.hs-cta'); if(!b||!md) return;
  document.getElementById('kmdl-h').textContent=b.dataset.house; md.hidden=false; document.body.style.overflow='hidden'});
 if(md){md.addEventListener('click',function(ev){if(ev.target.hasAttribute('data-close')){md.hidden=true;document.body.style.overflow=''}});
  document.addEventListener('keydown',function(ev){if(ev.key==='Escape'&&!md.hidden){md.hidden=true;document.body.style.overflow=''}})}
 if(location.hash.indexOf('#h-')===0){var it0=document.getElementById(location.hash.slice(1)); if(it0) openItem(it0,true)}
 apply();
})();
