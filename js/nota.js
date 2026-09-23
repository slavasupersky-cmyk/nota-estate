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
  var map={'karta.html':'karta','razbory.html':'razbory','razbor-hamovniki.html':'razbory','reytingi.html':'reytingi'};
  var k=map[f]||(/\/reytingi\//.test(location.pathname)?'reytingi':/\/razbory\//.test(location.pathname)?'razbory':null); if(!k)return;
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
 var G=['c','y','f','o','r'], ALL={c:'all',y:'all',f:'all',o:'all',r:'all'}, st=Object.assign({},ALL);
 var SZ={biz:[45,70,100],prem:[60,90,130],elit:[90,140,200],dlx:[120,180,250]};
 var MULTI={c:1,y:1};
 function test(el,t){return G.every(function(g){var v=t[g];if(v=='all')return true;var d=el.dataset[g]||'';if(MULTI[g])return v.indexOf(d)>-1;return g=='f'?(' '+d+' ').indexOf(' '+v+' ')>-1:d==v})}
 function ok(el){return test(el,st)}
 function okExcept(el,g,k){var t=Object.assign({},st);t[g]=(MULTI[g]&&k!=='all')?[k]:k;if(g=='o')t.r='all';return test(el,t)}
 function rows(){[].slice.call(document.querySelectorAll('.kmap-l .kr')).forEach(function(r){r.hidden=r.dataset.for!==st.o})}
 function facets(){chips.forEach(function(b){var n=0;items.forEach(function(it){if(okExcept(it,b.dataset.g,b.dataset.k))n++});var c=b.querySelector('.cn');if(c)c.textContent=n;b.classList.toggle('zero',n===0&&b.getAttribute('aria-pressed')!=='true')})}
 function press(g,k){var gc=chips.filter(function(x){return x.dataset.g==g});
  if(MULTI[g]){var cur=(k==='all'||st[g]==='all')?[]:st[g].slice();if(k!=='all'){var i=cur.indexOf(k);if(i<0)cur.push(k);else cur.splice(i,1)}
   if(!cur.length||cur.length>=gc.length-1)cur='all';st[g]=cur;
   gc.forEach(function(x){x.setAttribute('aria-pressed',(cur==='all'?x.dataset.k==='all':cur.indexOf(x.dataset.k)>-1)?'true':'false')});return}
  gc.forEach(function(x){x.setAttribute('aria-pressed',x.dataset.k==k&&(g!='r'||x.dataset.o==st.o||k=='all')?'true':'false')});st[g]=k}
 /* список — порциями по LIM, чтобы на телефоне страница не уходила в бесконечность */
 var LIM=20, lim=LIM, more=document.getElementById('kmore');
 function apply(){var n=0;rows();facets();dots.forEach(function(d){d.classList.toggle('off',!ok(d))});
  items.forEach(function(it){var on=ok(it);if(on)n++;it.hidden=!(on&&(n<=lim||it.classList.contains('open')))});
  cnt.textContent=(n===items.length?'Все '+n+' домов':'Найдено '+n+' из '+items.length)+(n>lim?' · показаны первые '+lim:'');
  if(more){var left=n-lim;more.hidden=left<=0;more.textContent='Показать ещё '+Math.min(LIM,left)+' · осталось '+left}
  if(kt&&!kt.hidden){var i=+kt.dataset.i;if(!ok(dots[i]))hideT()}}
 if(more) more.addEventListener('click',function(){lim+=LIM;apply()});
 chips.forEach(function(b){b.addEventListener('click',function(){var g=b.dataset.g;press(g,b.dataset.k);if(g=='o')press('r','all');lim=LIM;apply()})});
 document.querySelectorAll('[data-reset]').forEach(function(b){b.addEventListener('click',function(){st=Object.assign({},ALL);chips.forEach(function(x){x.setAttribute('aria-pressed',x.dataset.k=='all'?'true':'false')});lim=LIM;apply()})});
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

/* ---- рейтинги и длинные списки: фильтры-чипы со счётчиками, поиск, «Показать ещё» ---- */
(function(){
 [].slice.call(document.querySelectorAll('[data-rlist]')).forEach(function(box){
  var items=[].slice.call(box.querySelectorAll('.ri')), chips=[].slice.call(box.querySelectorAll('.chip[data-g]'));
  var G=[]; chips.forEach(function(c){if(G.indexOf(c.dataset.g)<0)G.push(c.dataset.g)});
  var st={}; G.forEach(function(g){st[g]='all'});
  var q=box.querySelector('input[type=search]'), qv='', cnt=box.querySelector('.ri-cnt'), more=box.querySelector('.ri-more');
  var LIM=+(box.getAttribute('data-lim')||20), lim=LIM;
  function norm(s){return (s||'').toLowerCase().replace(/ё/g,'е')}
  function test(el,t){for(var i=0;i<G.length;i++){var g=G[i],v=t[g];if(v==='all')continue;var d=' '+(el.dataset[g]||'')+' ',hit=false;
    for(var j=0;j<v.length;j++){if(d.indexOf(' '+v[j]+' ')>-1){hit=true;break}}if(!hit)return false}
   return !qv||norm(el.dataset.q).indexOf(qv)>-1}
  function facets(){chips.forEach(function(b){var t={};G.forEach(function(g){t[g]=st[g]});t[b.dataset.g]=b.dataset.k==='all'?'all':[b.dataset.k];var n=0;
   items.forEach(function(it){if(test(it,t))n++});var c=b.querySelector('.cn');if(c)c.textContent=n;
   b.classList.toggle('zero',n===0&&b.getAttribute('aria-pressed')!=='true')})}
  function apply(){var n=0;facets();
   items.forEach(function(it){var on=test(it,st);if(on)n++;it.hidden=!(on&&(n<=lim||it.classList.contains('open')))});
   if(cnt)cnt.textContent=(n===items.length?'Все '+n:'Найдено '+n+' из '+items.length)+(n>lim?' · показаны первые '+lim:'');
   if(more){var left=n-lim;more.hidden=left<=0;more.textContent='Показать ещё '+Math.min(LIM,left)+' · осталось '+left}}
  chips.forEach(function(b){b.addEventListener('click',function(){var g=b.dataset.g,k=b.dataset.k,gc=chips.filter(function(x){return x.dataset.g===g});
   var cur=(k==='all'||st[g]==='all')?[]:st[g].slice();if(k!=='all'){var i=cur.indexOf(k);if(i<0)cur.push(k);else cur.splice(i,1)}
   if(!cur.length||cur.length>=gc.length-1)cur='all';st[g]=cur;
   gc.forEach(function(x){x.setAttribute('aria-pressed',(cur==='all'?x.dataset.k==='all':cur.indexOf(x.dataset.k)>-1)?'true':'false')});lim=LIM;apply()})});
  if(q)q.addEventListener('input',function(){qv=norm(q.value.trim());lim=LIM;apply()});
  if(more)more.addEventListener('click',function(){lim+=LIM;apply()});
  [].slice.call(box.querySelectorAll('[data-reset]')).forEach(function(b){b.addEventListener('click',function(){
   G.forEach(function(g){st[g]='all'});chips.forEach(function(x){x.setAttribute('aria-pressed',x.dataset.k==='all'?'true':'false')});
   if(q){q.value='';qv=''}lim=LIM;apply()})});
  var dj=box.querySelector('.ri-data'), D=null; try{D=dj?JSON.parse(dj.textContent):null}catch(e){}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function near(it){var nb=it.querySelector('.ri-near[data-sid]');if(!nb||nb.dataset.done||!D)return;var L=D.n[nb.dataset.sid]||[];
   nb.innerHTML='<p class="k">Новые дома рядом, пешком</p><ul>'+L.map(function(x){var h=D.h[x[0]]||[x[0],''];
    return '<li><a href="'+D.R+'karta.html#h-'+x[0]+'">'+esc(h[0])+'</a><span>'+esc(h[1])+' · '+x[1]+' мин</span></li>'}).join('')+'</ul>';nb.dataset.done=1}
  function toggle(it,on){it.classList.toggle('open',on);if(on)near(it);var bd=it.querySelector('.ri-body'),bt=it.querySelector('.ri-row');if(bd)bd.hidden=!on;if(bt)bt.setAttribute('aria-expanded',on?'true':'false')}
  items.forEach(function(it){var bt=it.querySelector('.ri-row');if(bt)bt.addEventListener('click',function(){toggle(it,!it.classList.contains('open'))})});
  function fromHash(){if(!location.hash)return;var t=null;try{t=box.querySelector(location.hash)}catch(e){}
   if(t&&t.classList.contains('ri')){toggle(t,true);apply();setTimeout(function(){t.scrollIntoView({block:'start'})},30)}}
  window.addEventListener('hashchange',fromHash);
  /* подборка: школы → дома рядом пешком (рейтинг школ) */
  var bar=box.querySelector('.pickbar'), md=box.querySelector('.modal');
  if(bar&&md&&D){
   var KEY='nota-pick-schools', picked=[];
   try{picked=JSON.parse(localStorage.getItem(KEY)||'[]')||[]}catch(e){picked=[]}
   picked=picked.filter(function(id){return !!document.getElementById('s-'+id)});
   function save(){try{localStorage.setItem(KEY,JSON.stringify(picked))}catch(e){}}
   function pl(n,a,b,c){var x=n%10,y=n%100;return x===1&&y!==11?a:(x>=2&&x<=4&&(y<10||y>20)?b:c)}
   function nameOf(id){var el=document.getElementById('s-'+id);return el?el.getAttribute('data-name'):id}
   function houses(){var m={};picked.forEach(function(id){(D.n[id]||[]).forEach(function(x){if(x[1]>20)return;var h=D.h[x[0]];if(!h)return;var c=m[x[0]],nm=nameOf(id);
     if(!c)m[x[0]]={s:x[0],n:h[0],c:h[1],p:h[2],min:x[1],sch:[nm]};else{if(x[1]<c.min)c.min=x[1];if(c.sch.indexOf(nm)<0)c.sch.push(nm)}})});
    return Object.keys(m).map(function(k){return m[k]}).sort(function(a,b){return a.min-b.min||(a.p||1e12)-(b.p||1e12)})}
   function mark(){items.forEach(function(it){var id=it.id.slice(2),on=picked.indexOf(id)>-1;it.classList.toggle('picked',on);var b=it.querySelector('.ri-pick');if(b){b.textContent=on?'Убрать из подборки':'В подборку';b.classList.toggle('on',on)}})}
   function renderBar(){bar.hidden=!picked.length;document.body.classList.toggle('has-pick',picked.length>0);if(!picked.length)return;var n=houses().length;
    bar.querySelector('.pb-t').innerHTML='Выбрано: <b>'+picked.length+'</b> '+pl(picked.length,'школа','школы','школ')+' · домов рядом: <b>'+n+'</b>'}
   function fill(){var L=houses();
    md.querySelector('.pk-sel').innerHTML=picked.map(function(id){return '<span class="pk-s">'+esc(nameOf(id))+'<button type="button" data-unpick="'+id+'" aria-label="Убрать">×</button></span>'}).join('');
    md.querySelector('.pk-list').innerHTML=L.length?('<p class="hint">'+L.length+' '+pl(L.length,'дом','дома','домов')+' в 20 минутах пешком, от ближайших:</p><ul>'+L.map(function(h){return '<li><a href="'+D.R+'karta.html#h-'+h.s+'">'+esc(h.n)+'</a><span>'+esc(h.c)+(h.p?' · от '+(h.p>=1e6?(Math.round(h.p/1e5)/10).toString().replace('.',',')+' млн':Math.round(h.p/1000)+' тыс')+' ₽/м²':'')+' · '+h.min+' мин пешком · '+esc(h.sch.join(', '))+'</span></li>'}).join('')+'</ul>'):
     '<p class="hint">В 20 минутах пешком от выбранных школ домов из нашей базы нет. Напишите нам — подберём варианты по соседству.</p>'}
   function openM(){fill();md.hidden=false;document.body.style.overflow='hidden'}
   function closeM(){md.hidden=true;document.body.style.overflow=''}
   box.addEventListener('click',function(ev){var b=ev.target.closest&&ev.target.closest('.ri-pick');if(!b)return;var id=b.getAttribute('data-pick'),i=picked.indexOf(id);
    if(i<0)picked.push(id);else picked.splice(i,1);save();mark();renderBar()});
   bar.querySelector('.pb-clr').addEventListener('click',function(){picked=[];save();mark();renderBar()});
   bar.querySelector('.pb-go').addEventListener('click',openM);
   md.addEventListener('click',function(ev){if(ev.target.hasAttribute('data-close')){closeM();return}var u=ev.target.getAttribute('data-unpick');
    if(u){picked.splice(picked.indexOf(u),1);save();mark();renderBar();if(!picked.length)closeM();else fill()}});
   document.addEventListener('keydown',function(ev){if(ev.key==='Escape'&&!md.hidden)closeM()});
   md.querySelector('.pk-copy').addEventListener('click',function(){var L=houses(),btn=this;
    var t='Школы: '+picked.map(nameOf).join('; ')+'\nДома рядом пешком: '+L.map(function(h){return h.n+' — '+h.min+' мин'}).join('; ');
    function manual(){var ta=md.querySelector('.pk-ta');if(!ta){ta=document.createElement('textarea');ta.className='pk-ta';ta.readOnly=true;md.querySelector('.pk-list').appendChild(ta)}ta.value=t;ta.focus();ta.select();btn.textContent='Выделено — скопируйте'}
    if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(function(){btn.textContent='Список скопирован'},manual);else manual()});
   mark();renderBar();
  }
  apply(); fromHash();
 });
})();

/* ---- сценарии: на телефоне раскрываются по кнопке ---- */
(function(){
 var cs=[].slice.call(document.querySelectorAll('article.cs')); if(!cs.length) return;
 cs.forEach(function(a){var top=a.querySelector('.cs-top'); if(!top) return;
  var b=document.createElement('button'); b.type='button'; b.className='cs-more'; b.textContent='Раскрыть сценарий'; b.setAttribute('aria-expanded','false');
  top.insertAdjacentElement('afterend',b);
  b.addEventListener('click',function(){var o=a.classList.toggle('open'); b.textContent=o?'Свернуть':'Раскрыть сценарий'; b.setAttribute('aria-expanded',o?'true':'false'); if(!o) a.scrollIntoView({block:'start'})});
 });
 function fromHash(){var t=location.hash&&document.getElementById(location.hash.slice(1)); if(t&&t.classList.contains('cs')&&!t.classList.contains('open')){var b=t.querySelector('.cs-more'); if(b) b.click(); t.scrollIntoView({block:'start'})}}
 window.addEventListener('hashchange',fromHash); fromHash();
})();
