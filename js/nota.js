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

/* ---- калькулятор «Сколько стоит въехать» ---- */
(function(){
 var box=document.getElementById('calc'); if(!box) return;
 var g=function(id){return document.getElementById(id)};
 var ids=['c-area','c-new','c-rem','c-wait','c-rent','c-old','c-rem2','c-torg'];
 function num(v,d){return v.toLocaleString('ru-RU',{minimumFractionDigits:d||0,maximumFractionDigits:d||0})}
 function mln(r){return (r/1e6).toLocaleString('ru-RU',{minimumFractionDigits:1,maximumFractionDigits:1})+' млн ₽'}
 function mon(m){var n=Math.round(m),a=n%10,b=n%100;var w=(a==1&&b!=11)?'месяц':(a>=2&&a<=4&&(b<12||b>14))?'месяца':'месяцев';return n+' '+w}
 function draw(){
  var v={};ids.forEach(function(i){var el=g(i);v[i]=parseFloat(el.value);var o=el.nextElementSibling;o.textContent=num(v[i],i=='c-torg'?1:0)+' '+o.dataset.u});
  var A=v['c-area'];
  var priceNew=A*v['c-new']*1e3, rem=A*v['c-rem']*1e3;
  var remMonths=v['c-rem']>0?6:0, waitAll=v['c-wait']+remMonths;
  var rent=v['c-rent']*1e3*waitAll;
  var totalNew=priceNew+rem+rent;
  var priceOld=A*v['c-old']*1e3, torg=priceOld*v['c-torg']/100, rem2=A*v['c-rem2']*1e3, m2=v['c-rem2']>0?(v['c-rem2']>40?4:2):0, rent2=v['c-rent']*1e3*m2, totalOld=priceOld-torg+rem2+rent2;
  g('o-new').textContent=mln(totalNew);
  g('o-new-d').textContent='Квартира '+mln(priceNew)+' + ремонт '+mln(rem)+' + аренда '+mln(rent)+'. Въезд через '+mon(waitAll)+'.';
  g('o-old').textContent=mln(totalOld);
  g('o-old-d').textContent='Квартира '+mln(priceOld)+' − торг '+mln(torg)+(rem2?' + ремонт '+mln(rem2)+' + аренда '+mln(rent2)+'. Въезд через '+mon(m2)+'.':'. Въезд — после сделки.');
  var d=totalNew-totalOld, t;
  if(Math.abs(d)<5e5) t='Въезд обходится почти одинаково. Решают ставка ипотеки, дом и срок.';
  else if(d>0) t='Готовая квартира дешевле на <em>'+mln(d)+'</em> и даёт въехать на '+mon(Math.max(0,waitAll-m2))+' раньше. У новостройки остаются новый дом, паркинг по проекту и льготная ставка.';
  else t='Новостройка дешевле на <em>'+mln(-d)+'</em>, даже с ремонтом и арендой. Цена — ожидание: '+mon(waitAll)+' до въезда.';
  g('o-v').innerHTML=t;
 }
 ids.forEach(function(i){g(i).addEventListener('input',draw)});
 draw();
})();
