/* NOTA · Подбор: состав семьи → квартира → бюджет → дома из базы.
   Логика расчёта — konf-core.js (NotaKonf), поведение .sel, .bud, ползунков весов и окна #mdl — js/nota.js сайта.
   Правила:
   — кнопки «похожая семья» задают только то, что сказано в названии; кабинет, гостей, простор, бюджет и класс не трогают;
   — состав квартиры правится в таблице: «убрать», «вернуть», «душ вместо ванны»; спальни — только через состав семьи;
   — лестница по классам: самая доступная такая квартира в бизнесе, премиуме и элите при каждом просторе; клик выставляет класс и простор;
   — дома: метка «апартаменты», фильтр квартиры/апартаменты, порядок по цене, клик по дому открывает его карточку;
   — кнопка подсвечена, пока совпадают поля состава;
   — похожая планировка открывается в окне, страница не прокручивается;
   — шкала бюджета: красная зона — дешевле самого доступного дома базы, жёлтая — до первой четверти домов, салатовая — дальше;
   — #gen3, #family и другие ключи в адресе открывают подбор с этим составом семьи. */
(function () {
  'use strict';
  var K = window.NotaKonf; if (!K) return;
  var root = document.getElementById('kf'); if (!root) return;
  var CFG = document.body.dataset;                       // data-loty, data-img, data-kak на <body>
  var LOTY = CFG.loty || 'loty.json', IMG = CFG.img || '', KAK = CFG.kak || 'index.html';
  function $(id) { return document.getElementById(id); }
  function fmt(x) { return (Math.round(x * 10) / 10).toString().replace('.', ','); }
  function money(m) { if (m >= 1000) return fmt(m / 1000) + ' млрд ₽'; return (m >= 100 ? Math.round(m / 5) * 5 : Math.round(m)).toLocaleString('ru-RU') + ' млн ₽'; }
  function mln(m) { return m >= 1000 ? fmt(m / 1000) + ' млрд' : (m >= 100 ? Math.round(m / 5) * 5 : Math.round(m)).toLocaleString('ru-RU'); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var DATA = null, showAll = false, last = null, lastMk = null, lastFork = null;
  var OFF = {}, SHOWER = {}, SORT = null;               // правки состава руками; порядок домов (null — по умолчанию)

  /* ---------- состав семьи ---------- */
  var HH = ['adults', 'pairs', 'kidsSmall', 'kidsBig', 'elders', 'nanny', 'guests', 'party', 'wfh', 'cook', 'dog', 'cat', 'stroller', 'bikes', 'sport'];
  var BASE = { adults: 2, pairs: 1, kidsSmall: 0, kidsBig: 0, elders: 0, nanny: false, guests: 0, party: 0, wfh: 0, cook: 0, dog: 0, cat: false, stroller: false, bikes: 0, sport: false };
  function P(o) { var r = {}, k; for (k in BASE) r[k] = BASE[k]; for (k in o) r[k] = o[k]; return r; }
  var PRESETS = {                                       // только то, что сказано в названии: остальное человек отмечает сам
    solo: P({ adults: 1, pairs: 0 }),
    pair: P({}),
    wfh: P({ wfh: 2 }),
    baby: P({ kidsSmall: 1, stroller: true }),
    family: P({ kidsBig: 2 }),
    nanny: P({ kidsSmall: 2, nanny: true, stroller: true }),
    gen3: P({ kidsSmall: 1, kidsBig: 1, elders: 2, stroller: true }),
    twopairs: P({ adults: 4, pairs: 2 }),
    active: P({ dog: 2, bikes: 3, sport: true }),
    party: P({ party: 2 })
  };
  var RANGES = ['adults', 'pairs', 'kidsSmall', 'kidsBig', 'elders', 'bikes'];
  var ONE = ['space', 'guests', 'party', 'wfh', 'cook', 'dog'];
  var FLAGS = ['nanny', 'cat', 'stroller', 'sport'];

  function grp(name) { return root.querySelector('.chipgrp[data-one="' + name + '"]'); }
  function one(name) { var b = grp(name).querySelector('.chip[aria-pressed="true"]'); return b ? parseInt(b.dataset.v, 10) : 0; }
  function setOne(name, v) { grp(name).querySelectorAll('.chip').forEach(function (c) { c.setAttribute('aria-pressed', String(+c.dataset.v === +v)); }); }
  function flag(name) { var b = root.querySelector('.chip[data-flag="' + name + '"]'); return !!b && b.getAttribute('aria-pressed') === 'true'; }
  function setFlag(name, on) { var b = root.querySelector('.chip[data-flag="' + name + '"]'); if (b) b.setAttribute('aria-pressed', String(!!on)); }
  function rng(id) { return parseInt($(id).value, 10) || 0; }
  function setRng(id, v) { var e = $(id); e.value = v; showNum(id); }
  function showNum(id) { var e = $(id), o = root.querySelector('output[for="' + id + '"]'), st = root.querySelector('.kv-step[data-for="' + id + '"]');
    if (o) o.textContent = e.value;
    if (st) { st.querySelector('b').textContent = e.value; var bs = st.querySelectorAll('button'); bs[0].disabled = e.disabled || +e.value <= +e.min; bs[1].disabled = e.disabled || +e.value >= +e.max; } }

  function selV(n) { var li = document.querySelector('.sel[data-name="' + n + '"] li[aria-selected="true"]'); return li ? li.dataset.v || '' : ''; }
  function klass() { return selV('klass'); }
  function stt() { return selV('status'); }
  function setSel(n, v) { var li = document.querySelector('.sel[data-name="' + n + '"] li[data-v="' + v + '"]'); if (li && li.getAttribute('aria-selected') !== 'true') li.click(); }
  var bud = document.querySelector('.bud');
  function budget() {
    if (!bud || bud.classList.contains('none')) return null;
    var a = parseInt(bud.querySelector('.bud-a').value, 10) || 15, bv = bud.querySelector('.bud-b').value;
    return { a: a, b: bv === '' ? null : parseInt(bv, 10) };
  }

  function read() {
    var ex = {};
    root.querySelectorAll('.chip[data-extra][aria-pressed="true"]').forEach(function (c) { ex[c.dataset.extra] = 1; });
    var s = { extra: ex, klass: klass(), off: OFF, shower: SHOWER };
    RANGES.forEach(function (id) { s[id] = rng(id); });
    ONE.forEach(function (n) { s[n] = one(n); });
    FLAGS.forEach(function (n) { s[n] = flag(n); });
    return K.normalize(s);
  }
  function writeHH(p) {
    RANGES.forEach(function (id) { if (id !== 'pairs') setRng(id, p[id]); });
    syncControls(); setRng('pairs', p.pairs);
    ['guests', 'party', 'wfh', 'cook', 'dog'].forEach(function (n) { setOne(n, p[n]); });
    FLAGS.forEach(function (n) { setFlag(n, p[n]); });
  }
  function syncControls() {
    var a = rng('adults'), pr = $('pairs'), mx = Math.floor(a / 2);
    pr.max = mx; if (rng('pairs') > mx) pr.value = mx;
    pr.disabled = mx === 0;
    RANGES.forEach(showNum);
    var w2 = grp('wfh').querySelector('.chip[data-v="2"]');
    w2.disabled = a < 2; if (a < 2 && one('wfh') === 2) setOne('wfh', 1);
  }
  function activePreset(s) {
    var key = null;
    Object.keys(PRESETS).some(function (k) {
      var p = K.normalize(PRESETS[k]);
      if (HH.every(function (f) { return p[f] === s[f]; })) { key = k; return true; }
      return false;
    });
    return key;
  }
  var HINT = [
    'Комнаты по нижней границе, необязательное не закладываем, коридоры и стены +6–10 %.',
    'Комнаты обычного размера; без чего можно обойтись, помечено «можно без».',
    'Комнаты на 15–25 % больше, всё «можно без» становится обязательным, коридоры +12–18 %.'
  ];

  /* ---------- шаг 1: квартира ---------- */
  function render() {
    syncControls();
    var s = read(), r = K.calc(s);
    last = r;
    $('spaceHint').textContent = HINT[s.space];
    $('rArea').textContent = r.lo + '–' + r.hi;
    $('rFormat').textContent = r.fmt;
    var mn = $('rMin');
    if (r.min < r.lo) { mn.hidden = false; mn.textContent = 'Без помеченного «можно без» — от ' + r.min + ' м²'; } else mn.hidden = true;
    $('rFacts').innerHTML = r.facts.map(function (f) { return '<span>' + esc(f) + '</span>'; }).join('');
    $('rRooms').innerHTML = r.rooms.map(function (x) {
      var k = esc(x.k), ed = '';
      if (x.off) ed = '<button type="button" class="kv-ed" data-on="' + k + '">вернуть</button>';
      else {
        if (x.canSh) ed += '<button type="button" class="kv-ed" data-sh="' + k + '">' + (x.sh ? 'ванна' : 'душ вместо ванны') + '</button>';
        if (x.can) ed += '<button type="button" class="kv-ed" data-off="' + k + '">убрать</button>';
      }
      var cls = x.off ? 'off' : x.o ? 'opt' : '';
      return '<tr' + (cls ? ' class="' + cls + '"' : '') + '><td>' + esc(x.n) + '</td><td>' + (x.off ? '—' : fmt(x.lo) + '–' + fmt(x.hi)) + '</td><td>' + (x.off ? 'убрали' : esc(x.w)) + '</td><td class="kv-edc">' + ed + '</td></tr>';
    }).join('') +
      '<tr><td>Коридоры и стены</td><td>+' + r.corridors + ' %</td><td>в удачной планировке меньше, в резиденциях больше</td><td></td></tr>' +
      '<tr class="sum"><td>Итого</td><td>' + r.lo + '–' + r.hi + '</td><td>общая площадь без балконов и террас</td><td></td></tr>';
    $('rHouse').innerHTML = r.house.map(function (h) {
      if (typeof h === 'object') return '<li>' + esc(h.t).replace('рейтинге NOTA', '<a href="https://nota.expert/reytingi/shkoly-moskvy/">рейтинге NOTA</a>') + '</li>';
      return '<li>' + esc(h) + '</li>';
    }).join('');
    $('rPlans').innerHTML = K.plans(r, 3).map(function (p) {
      return '<button type="button" data-plan="' + p.id + '"><img src="' + IMG + p.img.replace('img/', '') + '" alt="План: ' + esc(p.cap) + '" loading="lazy"><span>' + esc(p.cap) + '</span></button>';
    }).join('');
    var ap = activePreset(s);
    document.querySelectorAll('#presets .chip').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.preset === ap)); });
    renderBudget();
  }

  /* ---------- шаг 2: бюджет ---------- */
  var DMIN = 10;
  function niceUp(v) { var st = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300, 400, 500, 700, 1000, 1500, 2000, 3000]; for (var i = 0; i < st.length; i++) if (st[i] >= v) return st[i]; return Math.ceil(v / 1000) * 1000; }
  function scaleHtml(mk, bg) {
    var dmax = Math.max(niceUp(Math.max((mk.p90 || 50) * 1.5, mk.maxHi * 1.15)), bg && bg.b ? bg.b * 1.15 : 0, bg ? bg.a * 1.3 : 0, 60);
    var L0 = Math.log(DMIN), L1 = Math.log(dmax);
    function x(v) { return Math.max(0, Math.min(100, (Math.log(Math.max(v, DMIN)) - L0) / (L1 - L0) * 100)); }
    var xr = x(mk.min), xy = x(mk.p25), xt = x(mk.maxHi);
    var h = '<div class="kv-bar">' +
      '<i class="z z-red" style="left:0;width:' + xr + '%"></i>' +
      '<i class="z z-yel" style="left:' + xr + '%;width:' + (xy - xr) + '%"></i>' +
      '<i class="z z-grn" style="left:' + xy + '%;width:' + Math.max(0, xt - xy) + '%"></i>' +
      (xt < 100 ? '<i class="z z-top" style="left:' + xt + '%;width:' + (100 - xt) + '%"></i>' : '') +
      '<i class="kv-mark" style="left:' + x(mk.p50) + '%" title="середина рынка"></i>';
    if (bg) {
      var xa = x(bg.a), xb = bg.b == null ? 100 : x(bg.b);
      h += '<span class="kv-fork' + (bg.b == null ? ' open' : '') + (xa > 60 ? ' right' : '') + '" style="left:' + xa + '%;width:' + Math.max(1, xb - xa) + '%"><span>ваша вилка ' + mln(bg.a) + '–' + (bg.b == null ? '∞' : mln(bg.b)) + ' млн</span></span>';
    }
    h += '</div><div class="kv-ticks">';
    var T = [10, 15, 20, 30, 50, 80, 120, 200, 300, 500, 800, 1000, 1500, 2000, 3000], lastX = -99;
    T.forEach(function (t) { var xt = x(t); if (t > dmax || xt - lastX < 8) return; lastX = xt; h += '<span style="left:' + xt + '%">' + (t >= 1000 ? fmt(t / 1000) + ' млрд' : t) + '</span>'; });
    h += '<span class="k" style="left:' + x(mk.min) + '%">от ' + mln(mk.min) + '</span>';
    if (x(mk.p50) - x(mk.min) > 14) h += '<span class="k" style="left:' + x(mk.p50) + '%">середина ' + mln(mk.p50) + '</span>';
    if (xt - x(mk.p50) > 14 && xt < 97) h += '<span class="k" style="left:' + xt + '%">до ' + mln(mk.maxHi) + '</span>';
    h += '</div><div class="kv-legend"><span><i class="z-red"></i>не найдётся</span><span><i class="z-yel"></i>впритык, выбор узкий</span><span><i class="z-grn"></i>хороший выбор</span><span><i class="z-top"></i>дороже такой квартиры нет</span><span>млн ₽, шкала сжата к дорогим</span></div>';
    return h;
  }
  var RAISE_MAX = 0.25;   // больше чем на четверть бюджет поднимать не предлагаем
  function pct(x) { return Math.round(x * 100) + ' %'; }
  function roundNice(v) { return v < 100 ? Math.ceil(v) : v < 1000 ? Math.ceil(v / 5) * 5 : Math.ceil(v / 50) * 50; }
  function raiseOption(mk, bg, nNow) {   // самая маленькая прибавка (10–25 %), после которой домов заметно больше
    var ps = [0.1, 0.15, 0.2, 0.25];
    for (var i = 0; i < ps.length; i++) {
      var b2 = roundNice(bg.b * (1 + ps[i])), n2 = K.fork(mk, bg.a, b2).inFork.length;
      if (n2 >= Math.max(nNow + 3, Math.ceil(nNow * 1.5))) return { b: b2, n: n2, p: b2 / bg.b - 1 };
    }
    return null;
  }
  function housesWord(n) { return n + ' ' + K.plural(n, 'дом', 'дома', 'домов'); }
  function fits(n) { return K.plural(n, 'помещается', 'помещаются', 'помещаются'); }
  function classesOf(list) {
    var c = {}; list.forEach(function (x) { c[x.h.c] = (c[x.h.c] || 0) + 1; });
    return Object.keys(c).sort(function (a, b) { return c[b] - c[a]; }).map(function (k) { return k + ' — ' + c[k]; }).join(', ');
  }
  function alt(spaceDelta) {   // тот же состав с другим простором
    var s = read(); var sp = Math.max(0, Math.min(2, s.space + spaceDelta)); if (sp === s.space) return null;
    var st = {}; for (var k in s) st[k] = s[k]; st.space = sp;
    var r = K.calc(st); return { r: r, mk: K.market(r, DATA, s.klass, stt()), space: sp };
  }
  function renderBudget() {
    var r = last; if (!r) return;
    showBud();
    if (!DATA) return;
    var kl = klass(), mk = K.market(r, DATA, kl, stt()), bg = budget();
    lastMk = mk;
    var adv = $('kvAdvice'), sc = $('kvScale');
    var area = r.lo + '–' + r.hi + ' м²';
    if (!mk.np) {
      sc.innerHTML = '';
      adv.innerHTML = '<p class="kv-verdict">Цен на такой формат в базе нет</p><p>' + (kl || stt() ? 'С фильтром «' + esc([kl ? document.querySelector('.sel[data-name="klass"] .sel-btn').textContent : '', stt() ? document.querySelector('.sel[data-name="status"] .sel-btn').textContent : ''].filter(Boolean).join(', ')) + '» подходящих домов с ценой не нашлось. Снимите фильтр.' : 'Подходящих домов с ценой не нашлось.') + ' Большой семье часто выгоднее купить две соседние квартиры и объединить их.</p>';
      $('rMarket').textContent = 'Цен на такой формат в базе нет';
      $('kvLadder').innerHTML = ladderHtml(r, null); renderHouses(mk, null); return;
    }
    sc.innerHTML = scaleHtml(mk, bg);
    var z = K.zone(mk, bg ? bg.b : null, bg ? bg.a : null), f = bg ? K.fork(mk, bg.a, bg.b) : { inFork: mk.priced, below: [] };
    lastFork = f;
    var Z = { red: ['z-red', 'Не помещается'], yellow: ['z-yel', 'Впритык'], green: ['z-grn', 'Хороший выбор'], open: ['z-grn', 'Хороший выбор'], above: ['z-top', 'Бюджет выше цен на такую квартиру'] };
    if (z === 'open' && bg && bg.a > mk.p75) Z.open = ['z-grn', 'Верх рынка'];
    var out = '', acts = [];
    if (!bg) {
      out = '<p class="kv-verdict">Сколько стоит такая квартира</p><p>Квартира на ' + area + ' в домах нашей базы стоит от ' + money(mk.min) + '. Основной выбор — от ' + money(mk.p25) + ' до ' + money(mk.p75) + ', середина — ' + money(mk.p50) + '. Задайте вилку слева — покажем, что в неё помещается.</p>';
    } else {
      var n = f.inFork.length;
      out = '<p class="kv-verdict"><i class="' + Z[z][0] + '"></i>' + Z[z][1] + (n ? ' · в вилке ' + housesWord(n) : '') + '</p>';
      if (z === 'red') {
        var ch = mk.cheapest, gap = mk.min / bg.b - 1;
        out += '<p>Самая доступная такая квартира (' + area + ') в нашей базе — ' + money(mk.min) + ': ' + esc(ch.h.n) + ', ' + esc(ch.h.c) + (ch.h.d ? ', ' + esc(ch.h.d) : '') + '. Это на ' + pct(gap) + ' больше верха вашей вилки.</p>';
        if (gap <= RAISE_MAX) acts.push(['budget', roundNice(mk.min), 'Поднять верх до ' + mln(roundNice(mk.min)) + ' млн (+' + pct(roundNice(mk.min) / bg.b - 1) + ')']);
        var c = alt(-1);
        if (c && c.mk.np) {
          var fc = K.fork(c.mk, bg.a, bg.b).inFork.length;
          if (fc) { out += '<p>Компактный вариант той же семьи — ' + c.r.lo + '–' + c.r.hi + ' м²: в вашу вилку ' + K.plural(fc, 'попадает', 'попадают', 'попадают') + ' ' + housesWord(fc) + '.</p>'; acts.push(['space', c.space, 'Посмотреть компактный вариант']); }
          else if (c.mk.min / bg.b - 1 <= RAISE_MAX) out += '<p>Компактный вариант (' + c.r.lo + '–' + c.r.hi + ' м²) начинается от ' + money(c.mk.min) + '.</p>';
        }
        if (kl) acts.push(['klass', '', 'Любой класс дома']);
        out += '<p>Есть и другие пути: вторичка, другой район, на одну комнату меньше. Их удобнее разобрать голосом.</p>';
        acts.push(['call', '', 'Обсудить по телефону']);
      } else if (z === 'yellow') {
        out += '<p>Выбор узкий: ' + classesOf(f.inFork) + '.</p>';
        var up = raiseOption(mk, bg, n);
        if (up) { out += '<p>Если добавить ' + pct(up.p) + ' — до ' + money(up.b) + ', домов станет ' + up.n + '.</p>'; acts.push(['budget', up.b, 'Поднять верх до ' + mln(up.b) + ' млн (+' + pct(up.p) + ')']); }
        var c2 = alt(-1);
        if (c2 && c2.mk.np) { var fc2 = K.fork(c2.mk, bg.a, bg.b).inFork.length; if (fc2 > n) { out += '<p>Компактный вариант (' + c2.r.lo + '–' + c2.r.hi + ' м²) даёт в той же вилке ' + housesWord(fc2) + '.</p>'; acts.push(['space', c2.space, 'Посмотреть компактный вариант']); } }
        if (!up && !acts.length) { out += '<p>Даже если поднять верх на четверть, вариантов в базе почти не прибавится. Что ещё можно найти в этом бюджете, подскажем по телефону.</p>'; acts.push(['call', '', 'Обсудить по телефону']); }
      } else if (z === 'above') {
        var pr = mk.priciest;
        out += '<p>Квартира на ' + area + ' в нашей базе стоит не дороже ' + money(mk.maxHi) + ' — столько она стоит в доме ' + esc(pr.h.n) + ' (' + esc(pr.h.c) + '). С бюджетом от ' + money(bg.a) + ' смотрят квартиры больше: ниже — дома, где в вашу вилку попадают квартиры любой площади, сначала самые дорогие.</p>';
        var s3 = alt(1); if (s3) acts.push(['space', s3.space, 'Посмотреть просторный вариант']);
        acts.push(['extra', 'study', 'Добавить кабинет']);
      } else {
        out += '<p>' + (n ? 'По классам: ' + classesOf(f.inFork) + '.' : '') + (f.below.length ? ' Ещё ' + housesWord(f.below.length) + ' дешевле нижней границы.' : '') + '</p>';
        if (bg.a > mk.p75) {
          var s2 = alt(1);
          out += '<p>Нижняя граница выше цен большинства домов: такую квартиру за эти деньги продают только дорогие дома. За ту же сумму можно взять больше метров' + (s2 ? ' — просторный вариант (' + s2.r.lo + '–' + s2.r.hi + ' м²).' : '.') + '</p>';
          if (s2) acts.push(['space', s2.space, 'Посмотреть просторный вариант']);
        } else if (bg.b != null && bg.b >= mk.p75 && read().space < 2) {
          out += '<p>Запас по бюджету есть: можно добавить простора или комнату — кабинет, гостевую.</p>';
          acts.push(['space', 2, 'Посмотреть просторный вариант']);
        }
      }
    }
    if (acts.length) out += '<div class="btns">' + acts.map(function (a, i) { return '<button type="button" class="btn btn-l" data-act="' + a[0] + '" data-v="' + a[1] + '">' + esc(a[2]) + '</button>'; }).join('') + '</div>';
    adv.innerHTML = out;
    var inN = bg ? f.inFork.length : mk.n;
    $('rMarket').innerHTML = bg ? (inN ? 'В вашей вилке — <b>' + housesWord(inN) + '</b>' : z === 'above' ? 'Бюджет выше: такая стоит до <b>' + money(mk.maxHi) + '</b>' : 'В вашу вилку не помещается, оценка от <b>' + money(mk.min) + '</b>') : 'В базе NOTA — <b>' + housesWord(mk.n) + '</b>, оценка от <b>' + money(mk.min) + '</b>';
    $('bTitle').textContent = bg ? (inN ? 'В вашу вилку ' + fits(inN) + ' ' + housesWord(inN) : z === 'above' ? 'Ваш бюджет выше цен на такую квартиру' : 'В вашу вилку такая квартира не помещается') : 'Сколько стоит такая квартира';
    $('bFmt').textContent = (r.studio ? 'евродвушка' : (r.mr >= 5 ? r.mr + ' комнат' : r.mr + '-комнатная')) + (bg ? ' · в вилке ' + housesWord(inN) : '');
    $('bArea').textContent = r.lo + '–' + r.hi + ' м²';
    $('kvLadder').innerHTML = ladderHtml(r, bg);
    renderHouses(mk, bg ? f : null, z === 'above' ? bg : null);
    showBud();
  }
  /* лестница по классам: самая доступная такая квартира в каждом классе при компактном, комфортном и просторном варианте */
  var KL = [['бизнес', 'Бизнес'], ['премиум', 'Премиум'], ['элит', 'Элит, делюкс']], ZC = { red: 'z-red', yellow: 'z-yel', green: 'z-grn', open: 'z-grn', above: 'z-top' };
  function ladderHtml(r, bg) {
    if (!DATA) return '';
    var s = read(), st = stt(), cur = klass();
    var R = [0, 1, 2].map(function (i) { var t = {}, k; for (k in s) t[k] = s[k]; t.space = i; return K.calc(t); });
    var any = false;
    var rows = KL.map(function (kl) {
      return '<tr><th scope="row">' + kl[1] + '</th>' + R.map(function (x, i) {
        var mk = K.market(x, DATA, kl[0], st);
        if (!mk.np) return '<td class="na">нет в базе</td>';
        any = true;
        var z = bg ? K.zone(mk, bg.b, bg.a) : '', on = cur === kl[0] && s.space === i;
        return '<td class="' + (ZC[z] || '') + (on ? ' on' : '') + '"><button type="button" data-kl="' + kl[0] + '" data-sp="' + i + '"' + (on ? ' aria-current="true"' : '') + '><b>от ' + mln(mk.min) + ' млн</b><span>' + housesWord(mk.np) + '</span></button></td>';
      }).join('') + '</tr>';
    }).join('');
    if (!any) return '';
    return '<p class="ttl">Вход по классам</p><p class="kv-lad-h">Самая доступная такая квартира в каждом классе — от компактной до просторной.' + (bg ? ' Цвет — как на шкале: зелёная клетка помещается в вашу вилку, жёлтая впритык, красная нет.' : '') + ' Нажмите на клетку — подбор пересчитается.</p>' +
      '<div class="tablewrap kv-lad"><table><thead><tr><th>Класс</th>' + R.map(function (x, i) { return '<th' + (s.space === i ? ' class="on"' : '') + '>' + ['Компактно', 'Комфортно', 'Просторно'][i] + '<small>' + x.lo + '–' + x.hi + ' м²</small></th>'; }).join('') + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }
  $('kvLadder').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-kl]'); if (!b) return;
    setOne('space', b.dataset.sp); showAll = false;
    if (klass() !== b.dataset.kl) setSel('klass', b.dataset.kl); else render();
  });
  function sortDesc(bg) { return SORT ? SORT === 'desc' : !!bg; }   // по умолчанию: с вилкой — сначала дорогие, без — сначала доступные
  function hiOf(x) { return x.estHi != null ? x.estHi : x.est; }
  function byPrice(desc) { return function (p, q) { if (p.est == null) return 1; if (q.est == null) return -1; return desc ? (hiOf(q) - hiOf(p)) || (q.est - p.est) : (p.est - q.est) || (hiOf(p) - hiOf(q)); }; }
  document.querySelectorAll('.kv-sort .chip').forEach(function (c) { c.addEventListener('click', function () { SORT = c.dataset.sort; renderBudget(); }); });
  var HEAD = '<tr><th>Дом</th><th>Класс</th><th>Район</th><th>Площади этого формата</th><th>Цена нужной квартиры</th></tr>';
  var HEAD_ALL = '<tr><th>Дом</th><th>Класс</th><th>Район</th><th>Что продаётся</th><th>Цены</th></tr>';
  function range(lo, hi) {
    if (hi < 1000) return mln(lo) + '–' + money(hi);
    if (lo >= 1000) return fmt(lo / 1000) + '–' + fmt(hi / 1000) + ' млрд ₽';
    return mln(lo) + ' млн – ' + money(hi);
  }
  function tipsText(t) {
    return t.map(function (x) { if (x === 'студии') return x; var e = / сп\.$/.test(x), n = x.replace(' сп.', ''); return e ? n + ' ' + (n === '1' ? 'спальня' : n === '4+' ? 'спален' : 'спальни') : n + (n === '4+' ? ' комн.' : '-комн.'); }).join(', ');
  }
  function pageOf(slug, h) { return h.p ? 'https://nota.expert/doma/' + slug + '/' : 'https://nota.expert/karta.html#h-' + slug; }
  function link(x) { return pageOf(x.slug, x.h); }
  function apTag(h) { var a = K.isAp(h); return a ? '<span class="kv-ap">' + (a === 2 ? 'апартаменты' : 'квартиры и апартаменты') + '</span>' : ''; }
  function houseCell(x) { return '<td><b><a href="' + link(x) + '" data-h="' + esc(x.slug) + '">' + esc(x.h.n) + '</a></b>' + apTag(x.h) + '</td>'; }
  function price(x) {
    if (x.est == null) return 'цена по запросу';
    var hi = x.estHi != null ? x.estHi : x.est, ar = Math.round(x.area) + (x.areaHi && Math.round(x.areaHi) > Math.round(x.area) ? '–' + Math.round(x.areaHi) : '');
    return '≈ ' + (Math.round(hi) > Math.round(x.est) * 1.05 ? range(x.est, hi) : money(x.est)) + ' за ' + ar + ' м²';
  }
  function rowHtml(x, cls) {
    return '<tr' + (cls ? ' class="' + cls + '"' : '') + '>' + houseCell(x) + '<td>' + esc(x.h.c) + '</td><td>' + esc(x.h.d || '') + '</td><td>' +
      (x.a === x.b ? fmt(x.a) : fmt(x.a) + '–' + fmt(x.b)) + ' м²</td><td>' + price(x) + '</td></tr>';
  }
  function rowAll(x) {
    return '<tr>' + houseCell(x) + '<td>' + esc(x.h.c) + '</td><td>' + esc(x.h.d || '') + '</td><td>' + esc(tipsText(x.tips)) + ', ' + fmt(x.a) + '–' + fmt(x.b) + ' м²</td><td>' + range(x.pmin, x.pmax) + '</td></tr>';
  }
  function renderHouses(mk, f, above) {
    var head = $('mRows').parentNode.querySelector('thead'), desc = sortDesc(f || above);
    document.querySelectorAll('.kv-sort .chip').forEach(function (c) { c.setAttribute('aria-pressed', String((c.dataset.sort === 'desc') === desc)); });
    $('mTitle').textContent = above ? 'Дома, где есть квартиры в вашей вилке' : f ? 'Дома в вашей вилке' : 'Дома, где есть такая квартира';
    if (above) {
      var L = K.budgetHouses(DATA, above.a, above.b, klass(), stt());
      if (!desc) L.sort(function (p, q) { return p.pmin - q.pmin; });
      head.innerHTML = HEAD_ALL;
      var shown = showAll ? L : L.slice(0, 8);
      $('mRows').innerHTML = shown.length ? shown.map(rowAll).join('') : '<tr><td colspan="5">В базе нет квартир в этой вилке. Проверьте нижнюю границу.</td></tr>';
      var mo = $('mMore'); mo.hidden = L.length <= 8; mo.textContent = showAll ? 'Свернуть' : 'Показать все ' + L.length;
      return;
    }
    head.innerHTML = HEAD;
    var main = f ? f.inFork.slice() : mk.rows.slice();
    var below = f ? f.below.slice() : [];
    if (!f || !desc) { main.sort(byPrice(desc)); below.sort(byPrice(desc)); }   // с вилкой и «сначала дорогие» — порядок fork(): по тому, сколько из вилки можно потратить
    var list = showAll ? main : main.slice(0, 8);
    var h = list.map(function (x) { return rowHtml(x); }).join('');
    if (showAll && below.length) h += '<tr class="sep"><td colspan="5">Дешевле вашей вилки — ' + housesWord(below.length) + '</td></tr>' + below.map(function (x) { return rowHtml(x, 'below'); }).join('');
    if (!main.length && !below.length) h = mk.priced.length ? '<tr class="sep"><td colspan="5">В вилку не попал ни один дом. Ближайшие по цене</td></tr>' + mk.priced.slice(0, 5).map(function (x) { return rowHtml(x); }).join('') : '<tr><td colspan="5">Подходящих домов нет. Снимите фильтр класса.</td></tr>';
    else if (!main.length) h = '<tr class="sep"><td colspan="5">В вилку не попал ни один дом. Ниже — дома дешевле вашей вилки</td></tr>' + (showAll ? '' : below.slice(0, 8).map(function (x) { return rowHtml(x, 'below'); }).join(''));
    $('mRows').innerHTML = h;
    var more = $('mMore'), total = main.length + below.length;
    more.hidden = total <= 8 && !below.length;
    more.textContent = showAll ? 'Свернуть' : 'Показать все ' + total;
  }
  $('kvAdvice').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act]'); if (!b) return;
    var act = b.dataset.act, v = b.dataset.v;
    if (act === 'budget') { var nb = bud.querySelector('.bud-b'); bud.classList.remove('none'); nb.value = v; nb.dispatchEvent(new Event('input', { bubbles: true })); nb.dispatchEvent(new Event('change', { bubbles: true })); }
    if (act === 'space') { setOne('space', v); render(); }
    if (act === 'klass') { var li = document.querySelector('.sel[data-name="klass"] li[data-v=""]'); if (li) li.click(); }
    if (act === 'call') { openCall(); return; }
    if (act === 'extra') { var ch = root.querySelector('.chip[data-extra="' + v + '"]'); if (ch) ch.setAttribute('aria-pressed', 'true'); render(); }
  });

  /* ---------- окна ---------- */
  function modal(el, on) { el.hidden = !on; document.body.style.overflow = on ? 'hidden' : ''; }
  var plan = $('kvPlan'), call = $('kvCall'), house = $('kvHouse');
  [plan, call, house].forEach(function (m) { m.addEventListener('click', function (e) { if (e.target.hasAttribute('data-close')) modal(m, false); }); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') [plan, call, house].forEach(function (m) { if (!m.hidden) modal(m, false); }); });

  /* карточка дома: что в нём продаётся, нужный формат выделен, ссылки и запрос планировок */
  function tipLabel(tip, e) {
    if (tip === 'студия') return 'Студии';
    if (e) return tip === '4+' ? '4 спальни и больше' : tip + ' ' + (tip === '1' ? 'спальня' : 'спальни') + ' + кухня-гостиная';
    return tip === '4+' ? '4 комнаты и больше' : tip + '-комнатные';
  }
  function fmtShort(r) { return r.studio ? 'евродвушка' : r.fmt.split(' — ')[0]; }
  var houseNow = null;
  function openHouse(slug) {
    var h = DATA && DATA.h[slug]; if (!h) return false;
    var r = last, want = r.studio ? [1, 2] : [r.mr], ap = K.isAp(h);
    var rows = DATA.l.filter(function (x) { return x[0] === slug; }).sort(function (p, q) { return K.lotRooms(p[1], p[5]) - K.lotRooms(q[1], q[5]) || p[2] - q[2]; });
    $('hTitle').textContent = h.n;
    $('hMeta').textContent = [h.c, h.d, ap === 2 ? 'апартаменты' : ap ? 'квартиры и апартаменты' : 'квартиры', h.s].filter(Boolean).join(' · ');
    var hap = $('hAp'); hap.hidden = !ap;
    hap.textContent = ap === 2 ? 'Апартаменты — нежилой статус: без постоянной прописки, налог и коммунальные платежи выше, семейная ипотека не действует.' : ap ? 'В доме есть и квартиры, и апартаменты: статус конкретного лота уточним до просмотра.' : '';
    var x = lastMk && lastMk.rows.filter(function (y) { return y.slug === slug; })[0];
    $('hNeed').innerHTML = x ? '<b>Ваша квартира здесь</b> — ' + esc(fmtShort(r)) + ': ' + price(x) : 'Квартиры вашего формата (' + esc(fmtShort(r)) + ', ' + r.lo + '–' + r.hi + ' м²) в этом доме по базе сейчас нет. Ниже — что продаётся.';
    $('hRows').innerHTML = rows.map(function (l) {
      var rr = K.lotRooms(l[1], l[5]), on = want.some(function (w) { return w >= 4 ? (l[1] === '4+' || rr === w) : rr === w; });
      var c = l[4], cm = l[6];
      return '<tr' + (on ? ' class="on"' : '') + '><td>' + tipLabel(l[1], l[5]) + (on ? '<span class="kv-your">ваш формат</span>' : '') + '</td><td>' + (Math.round(l[2]) === Math.round(l[3]) ? fmt(l[2]) : fmt(l[2]) + '–' + fmt(l[3])) + ' м²</td><td>' + (c ? (cm && cm > c * 1.02 ? range(c, cm) : 'от ' + money(c)) : 'по запросу') + '</td></tr>';
    }).join('') || '<tr><td colspan="3">Лотов в базе нет</td></tr>';
    $('hBtns').innerHTML = '<button type="button" class="btn" id="hReq">Прислать планировки этого формата</button>' +
      (h.p ? '<a class="btn btn-l" href="https://nota.expert/doma/' + slug + '/" target="_blank" rel="noopener">Страница дома ↗</a>' : '') +
      '<a class="btn btn-l" href="https://nota.expert/karta.html#h-' + slug + '" target="_blank" rel="noopener">На карте: школы и парки ↗</a>' +
      (h.w ? '<a class="btn btn-l" href="' + esc(h.w) + '" target="_blank" rel="noopener">Сайт застройщика ↗</a>' : '');
    houseNow = h.n;
    modal(house, true); return true;
  }
  $('hBtns').addEventListener('click', function (e) { if (e.target.id === 'hReq') { modal(house, false); openCall(houseNow); } });
  $('mRows').addEventListener('click', function (e) {
    var a = e.target.closest('a[data-h]'); if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
    if (openHouse(a.dataset.h)) e.preventDefault();
  });
  $('rPlans').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-plan]'); if (!b) return;
    var p = K.PLANS.filter(function (x) { return x.id === b.dataset.plan; })[0]; if (!p) return;
    $('zImg').src = IMG + p.img.replace('img/', ''); $('zImg').alt = 'План: ' + p.cap;
    $('zTitle').textContent = p.cap; $('zText').textContent = p.where + '. ' + p.txt;
    $('zLink').href = KAK + '#' + p.id;
    modal(plan, true);
  });
  $('callme').addEventListener('click', function () { openCall(); });
  if ($('callme2')) $('callme2').addEventListener('click', function () { openCall(); });

  /* ---------- текст расчёта для заявки ---------- */
  function summaryShort(noBudget) {
    var r = last; if (!r) return '';
    var s = r.state, bg = budget();
    var who = 'взрослых ' + s.adults + (s.pairs ? ' (пар ' + s.pairs + ')' : '') + (s.kidsSmall ? ', малышей ' + s.kidsSmall : '') + (s.kidsBig ? ', школьников ' + s.kidsBig : '') + (s.elders ? ', старших ' + s.elders : '') + (s.nanny ? ', няня' : '');
    var offN = r.rooms.filter(function (x) { return x.off; }).map(function (x) { return x.n.toLowerCase(); }), shN = r.rooms.filter(function (x) { return x.sh; }).length;
    var edits = (offN.length ? ' Без: ' + offN.join(', ') + '.' : '') + (shN ? ' Душ вместо ванны.' : '');
    return who + '. Нужно ' + r.lo + '–' + r.hi + ' м², ' + r.fmt.split(' — ')[0] + '.' + edits + (noBudget ? (bg && lastFork ? ' В вилке ' + housesWord(lastFork.inFork.length) + '.' : '') : ' ' + (bg ? 'Бюджет ' + bg.a + '–' + (bg.b == null ? 'без верхней границы' : bg.b + ' млн') + (lastFork ? ', в вилке ' + housesWord(lastFork.inFork.length) : '') + '.' : 'Бюджет пока не считали.'));
  }
  var ask = $('ask'), mdlSum = $('mdl-sum');
  if (ask && mdlSum) ask.addEventListener('click', function () {    // после обработчика js/nota.js: дописываем расчёт
    setTimeout(function () { mdlSum.textContent = 'Семья: ' + summaryShort(true) + ' ' + mdlSum.textContent; }, 0);
  });

  /* ---------- события ---------- */
  root.addEventListener('input', function (e) { if (e.target.type === 'range') render(); });
  root.addEventListener('click', function (e) {
    var sb = e.target.closest('.kv-step[data-for] button');
    if (sb) { if (sb.disabled) return; var inp = $(sb.parentNode.dataset.for); inp.value = Math.max(+inp.min, Math.min(+inp.max, (+inp.value || 0) + (+sb.dataset.d))); render(); return; }
    var c = e.target.closest('.chip'); if (!c || c.disabled) return;
    var g = c.closest('.chipgrp');
    if (g.hasAttribute('data-one')) { g.querySelectorAll('.chip').forEach(function (x) { x.setAttribute('aria-pressed', String(x === c)); }); }
    else c.setAttribute('aria-pressed', String(c.getAttribute('aria-pressed') !== 'true'));
    render();
  });
  function applyPreset(key) { var p = PRESETS[key]; if (!p) return false; OFF = {}; SHOWER = {}; writeHH(p); showAll = false; render(); return true; }
  $('rRooms').addEventListener('click', function (e) {          // правка состава: убрать, вернуть, душ вместо ванны
    var b = e.target.closest('button.kv-ed'); if (!b) return;
    if (b.dataset.off) OFF[b.dataset.off] = 1;
    if (b.dataset.on) delete OFF[b.dataset.on];
    if (b.dataset.sh) { if (SHOWER[b.dataset.sh]) delete SHOWER[b.dataset.sh]; else SHOWER[b.dataset.sh] = 1; }
    render();
  });
  document.querySelectorAll('#presets .chip').forEach(function (b) { b.addEventListener('click', function () { applyPreset(b.dataset.preset); }); });
  document.addEventListener('selchange', function (e) { if (e.target === bud || (e.target.dataset && /^(klass|status)$/.test(e.target.dataset.name))) { showAll = false; render(); } });
  if (bud) bud.querySelectorAll('input').forEach(function (i) { i.addEventListener('change', function () { render(); }); });
  $('mMore').addEventListener('click', function () { showAll = !showAll; renderBudget(); });
  if (bud) bud.addEventListener('click', function (e) {     // «+ / −» вилки на телефоне двигают те же ползунки, что и на десктопе
    var sb = e.target.closest('.kv-step[data-bud] button'); if (!sb) return;
    var r = bud.querySelector(sb.parentNode.dataset.bud === 'a' ? '.r-a' : '.r-b');
    r.value = Math.max(+r.min, Math.min(+r.max, +r.value + (+sb.dataset.d)));
    r.dispatchEvent(new Event('input', { bubbles: true }));
  });
  function showBud() {
    if (!bud) return;
    var a = bud.querySelector('.bud-a').value, bv = bud.querySelector('.bud-b').value;
    var sa = bud.querySelector('.kv-step[data-bud="a"]'), sbb = bud.querySelector('.kv-step[data-bud="b"]');
    if (sa) sa.querySelector('b').textContent = a || '15';
    if (sbb) sbb.querySelector('b').textContent = bv === '' ? '∞' : bv;
    var ra = bud.querySelector('.r-a'), rb = bud.querySelector('.r-b');
    if (sa && ra) { sa.children[0].disabled = +ra.value <= +ra.min; sa.children[2].disabled = +ra.value >= Math.min(+rb.value, +ra.max - 1); }
    if (sbb && rb) { sbb.children[0].disabled = +rb.value <= +ra.value; sbb.children[2].disabled = +rb.value >= +rb.max; }
  }
  /* веса из js/nota.js: на телефоне те же «+ / −» рядом с каждым ползунком */
  var host = $('sliders');
  if (host) {
    host.querySelectorAll('.row').forEach(function (row) {
      var r = row.querySelector('input[type=range]'); if (!r) return;
      var st = document.createElement('span'); st.className = 'kv-step';
      st.innerHTML = '<button type="button" data-d="-1" aria-label="Меньше: ' + r.dataset.k + '">−</button><b>' + r.value + '</b><button type="button" data-d="1" aria-label="Больше: ' + r.dataset.k + '">+</button>';
      row.appendChild(st);
    });
    host.addEventListener('click', function (e) {
      var sb = e.target.closest('.kv-step button'); if (!sb) return;
      var r = sb.parentNode.parentNode.querySelector('input[type=range]');
      r.value = Math.max(+r.min, Math.min(+r.max, +r.value + (+sb.dataset.d)));
      r.dispatchEvent(new Event('input', { bubbles: true }));
    });
    host.addEventListener('input', function () {
      host.querySelectorAll('.row').forEach(function (row) { var r = row.querySelector('input[type=range]'), b = row.querySelector('.kv-step b'); if (r && b) b.textContent = r.value; });
    });
  }

  /* полоска результата на телефоне */
  var bar = $('kbar');
  if (bar && 'IntersectionObserver' in window) {
    var vis = { kcard: true, byudzhet: false, anketa: false };
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) { vis[en.target.id] = en.isIntersecting; });
      var kto = $('kto').getBoundingClientRect();
      bar.hidden = vis.kcard || vis.anketa || kto.top > window.innerHeight;
    });
    ['kcard', 'byudzhet', 'anketa'].forEach(function (id) { io.observe($(id)); });
  }

  function openCall(houseName) {
    var t = summaryShort(); var s = $('kvCallSum');
    $('kvCall-h').textContent = typeof houseName === 'string' ? 'Пришлём планировки из «' + houseName + '»' : 'Позвоним и заполним анкету за вас';
    if (typeof houseName === 'string' && last) t = 'планировки «' + fmtShort(last) + '», ' + last.lo + '–' + last.hi + ' м², в доме «' + houseName + '». Семья: ' + t;
    s.hidden = !t; s.textContent = t ? (typeof houseName === 'string' ? 'Запрос: ' : 'Уже отмечено: ') + t : '';
    modal(call, true); var i = call.querySelector('input'); if (i) setTimeout(function () { i.focus(); }, 60);
  }
  var key = (location.hash || '').replace('#', '');
  if (!applyPreset(key)) applyPreset('baby');
  if (key === 'zvonok') openCall();
  window.addEventListener('hashchange', function () { var k = (location.hash || '').replace('#', ''); if (k === 'zvonok') openCall(); else applyPreset(k); });
  fetch(LOTY).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { DATA = d; renderBudget(); })
    .catch(function () { $('kvAdvice').innerHTML = '<p class="kv-verdict">Не удалось загрузить цены из базы</p><p>Расчёт комнат и метров работает и без них. Позвоните нам — сверим бюджет голосом.</p>'; $('rMarket').textContent = 'Список домов не загрузился'; });
})();
