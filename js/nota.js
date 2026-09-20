(function(){
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
  var groups={};
  document.querySelectorAll('[data-group]').forEach(function(b){(groups[b.dataset.group]=groups[b.dataset.group]||[]).push(b)});
  var rows=Array.prototype.slice.call(document.querySelectorAll('#base tr[data-c]'));
  var state={cls:'all',bin:'all'};
  function apply(){
   var n=0;
   rows.forEach(function(r){
    var on=(state.cls==='all'||r.dataset.c===state.cls)&&(state.bin==='all'||r.dataset.b===state.bin);
    r.style.display=on?'':'none'; if(on)n++;
   });
   var c=document.getElementById('cnt');
   if(c)c.textContent='Показано '+n+' из '+rows.length+' строк среза. Полная база — 288 домов.';
   var dots=document.querySelectorAll('#mapdots [data-c]');
   dots.forEach(function(d){
    var on=(state.cls==='all'||d.dataset.c===state.cls)&&(state.bin==='all'||d.dataset.b===state.bin);
    d.style.opacity=on?'1':'.12';
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
    var el=document.createElement('span');el.textContent=(n+1)+'. '+i.dataset.k+' · '+i.value;rank.appendChild(el);
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
 }
})();
