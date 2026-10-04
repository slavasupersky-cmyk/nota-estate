/* NOTA · Подбор планировки — интерфейс. (Сайт: ссылки на дома относительные, у ячеек таблицы домов data-label для телефона.) Логика расчёта — в konf-core.js (NotaKonf).
   Правила интерфейса:
   — пресет задаёт только состав семьи и образ жизни; простор, доп. комнаты, бюджет и класс не трогает и не сбрасывает;
   — пресет подсвечен, пока поля «кто живёт», «как живёте» и «животные и вещи» совпадают с ним;
   — похожие планировки открываются в окне, страница не прокручивается;
   — #gen3, #family и другие ключи пресетов в адресе открывают подбор сразу с этим составом. */
(function () {
  'use strict';
  var K = window.NotaKonf; if (!K) return;
  var form = document.getElementById('kf'); if (!form) return;
  function $(id) { return document.getElementById(id); }
  var DATA = null, showAll = false, lastRes = null, lastMatch = null;

  /* состав семьи и образ жизни; простор, extra, budget, klass сюда не входят */
  var HH = ['adults', 'pairs', 'kidsSmall', 'kidsBig', 'elders', 'nanny', 'guests', 'party', 'wfh', 'cook', 'dog', 'cat', 'stroller', 'bikes', 'sport'];
  var BASE = { adults: 2, pairs: 1, kidsSmall: 0, kidsBig: 0, elders: 0, nanny: false, guests: 0, party: 0, wfh: 0, cook: 0, dog: 0, cat: false, stroller: false, bikes: 0, sport: false };
  function P(o) { var r = {}, k; for (k in BASE) r[k] = BASE[k]; for (k in o) r[k] = o[k]; return r; }
  var PRESETS = {
    solo:     P({ adults: 1, pairs: 0, guests: 1, party: 1, bikes: 1 }),
    pair:     P({ guests: 1, party: 1, wfh: 1, cook: 1 }),
    wfh:      P({ guests: 1, wfh: 2, cook: 1 }),
    baby:     P({ kidsSmall: 1, stroller: true }),
    family:   P({ kidsBig: 2, guests: 1, party: 1, wfh: 1, cook: 1, cat: true, bikes: 4, sport: true }),
    nanny:    P({ kidsSmall: 2, nanny: true, cook: 1, stroller: true }),
    gen3:     P({ kidsSmall: 1, kidsBig: 1, elders: 2, party: 1, wfh: 1, cook: 2, stroller: true, bikes: 2 }),
    twopairs: P({ adults: 4, pairs: 2, guests: 1, party: 1, wfh: 1, cook: 1 }),
    active:   P({ kidsBig: 1, guests: 1, party: 1, wfh: 1, cook: 1, dog: 2, bikes: 3, sport: true }),
    party:    P({ guests: 2, party: 2, cook: 1, dog: 1 })
  };

  function rad(n) { var e = form.querySelector('input[name="' + n + '"]:checked'); return e ? parseInt(e.value, 10) : 0; }
  function setRad(n, v) { var e = form.querySelector('input[name="' + n + '"][value="' + v + '"]'); if (e) e.checked = true; }
  function num(id) { var v = parseInt($(id).value, 10); return isNaN(v) ? 0 : v; }
  function fmt(x) { return (Math.round(x * 10) / 10).toString().replace('.', ','); }
  function money(m) { return m >= 1000 ? fmt(m / 1000) + ' млрд ₽' : Math.round(m).toLocaleString('ru-RU') + ' млн ₽'; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function read() {
    var ex = {};
    form.querySelectorAll('input[name="extra"]:checked').forEach(function (e) { ex[e.value] = 1; });
    return K.normalize({
      space: rad('space'), adults: num('adults'), pairs: num('pairs'), kidsSmall: num('kidsSmall'), kidsBig: num('kidsBig'),
      elders: num('elders'), nanny: $('nanny').checked, guests: rad('guests'), party: rad('party'), wfh: rad('wfh'), cook: rad('cook'),
      dog: rad('dog'), cat: $('cat').checked, stroller: $('stroller').checked, bikes: num('bikes'), sport: $('sport').checked,
      extra: ex, budget: $('budget').value, klass: $('klass').value
    });
  }
  function writeHH(p) {
    ['adults', 'pairs', 'kidsSmall', 'kidsBig', 'elders', 'bikes'].forEach(function (k) { $(k).value = p[k]; });
    ['nanny', 'cat', 'stroller', 'sport'].forEach(function (k) { $(k).checked = !!p[k]; });
    ['guests', 'party', 'wfh', 'cook', 'dog'].forEach(function (k) { setRad(k, p[k]); });
  }

  /* границы степперов и зависимые поля: пар не больше половины взрослых, работающих дома не больше взрослых */
  function syncControls() {
    var a = Math.max(1, Math.min(6, num('adults')));
    $('pairs').max = Math.floor(a / 2);
    ['adults', 'pairs', 'kidsSmall', 'kidsBig', 'elders', 'bikes'].forEach(function (id) {
      var e = $(id), v = Math.max(+e.min, Math.min(+e.max, num(id)));
      e.value = v;
      var bs = e.parentNode.querySelectorAll('button');
      bs[0].disabled = v <= +e.min; bs[1].disabled = v >= +e.max;
    });
    var w2 = $('w2'); w2.disabled = a < 2; if (a < 2 && w2.checked) setRad('wfh', 1);
  }

  function activePreset(s) {
    var key = null;
    Object.keys(PRESETS).some(function (k) {
      var p = K.normalize(PRESETS[k]);
      var same = HH.every(function (f) { return p[f] === s[f]; });
      if (same) key = k;
      return same;
    });
    return key;
  }

  var HINT = [
    'Комнаты по нижней границе, необязательное не закладываем, коридоры и стены +6–10 %.',
    'Комнаты обычного размера; без чего можно обойтись, помечено «можно без».',
    'Комнаты на 15–25 % больше, всё помеченное «можно без» становится обязательным, коридоры +12–18 %.'
  ];

  function render() {
    syncControls();
    var s = read(), r = K.calc(s);
    lastRes = r;
    $('spaceHint').textContent = HINT[s.space];
    $('rArea').textContent = r.lo + '–' + r.hi;
    $('rFormat').textContent = r.fmt;
    var mn = $('rMin');
    if (r.min < r.lo) { mn.hidden = false; mn.textContent = 'Без помеченного «можно без» — от ' + r.min + ' м²'; } else mn.hidden = true;
    $('rFacts').innerHTML = r.facts.map(function (f) { return '<span>' + esc(f) + '</span>'; }).join('');
    $('rRooms').innerHTML = r.rooms.map(function (x) {
      return '<tr' + (x.o ? ' class="opt"' : '') + '><td>' + esc(x.n) + '</td><td class="n">' + fmt(x.lo) + '–' + fmt(x.hi) + '</td><td>' + esc(x.w) + '</td></tr>';
    }).join('') +
      '<tr class="cor"><td>Коридоры и стены</td><td class="n">+' + r.corridors + ' %</td><td>в удачной планировке меньше, в резиденциях больше</td></tr>' +
      '<tr class="sum"><td>Итого</td><td class="n">' + r.lo + '–' + r.hi + '</td><td>общая площадь без балконов и террас</td></tr>';
    $('rHouse').innerHTML = r.house.map(function (h) {
      if (typeof h === 'object') return '<li>' + esc(h.t).replace('рейтинге NOTA', '<a href="../../reytingi/shkoly-moskvy/">рейтинге NOTA</a>') + '</li>';
      return '<li>' + esc(h) + '</li>';
    }).join('');
    $('rPlans').innerHTML = K.plans(r, 3).map(function (p) {
      return '<button type="button" data-plan="' + p.id + '"><img src="' + p.img + '" alt="План: ' + esc(p.cap) + '" loading="lazy"><span>' + esc(p.cap) + '</span></button>';
    }).join('');
    var ap = activePreset(s);
    document.querySelectorAll('.presets button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.preset === ap ? 'true' : 'false'); });
    $('bArea').textContent = r.lo + '–' + r.hi + ' м²';
    $('bFmt').textContent = r.studio ? 'спальня и кухня-гостиная' : (r.mr >= 5 ? r.mr + ' комнат' : r.mr + '-комнатная') + ', ' + r.facts[0];
    renderMatch();
  }

  function renderMatch() {
    var r = lastRes; if (!r) return;
    if (!DATA) { $('mNote').textContent = 'Загружаем дома из базы…'; return; }
    var budget = parseInt($('budget').value, 10) || 0, kl = $('klass').value;
    var m = K.match(r, DATA, { budget: budget, klass: kl });
    lastMatch = m;
    var n = m.rows.length;
    var withPrice = m.rows.filter(function (x) { return x.est != null; });
    var fmtName = r.studio ? 'студии, 1- и 2-комнатные' : r.mr < 4 ? r.mr + '-комнатные' : (r.mr === 4 ? '4-комнатные' : 'многокомнатные') + ' (в базе — «4+»)';
    if (n) {
      $('mTitle').textContent = 'Где такие квартиры продаются сейчас: ' + n + ' ' + K.plural(n, 'дом', 'дома', 'домов');
      var parts = Object.keys(m.byClass).map(function (k) { return k + ' — ' + m.byClass[k]; });
      $('mNote').textContent = 'Формат — ' + fmtName + ', площади пересекаются с ' + r.lo + '–' + r.hi + ' м². По классам: ' + parts.join(', ') + '.' +
        (m.overBudget ? ' Ещё ' + m.overBudget + ' ' + K.plural(m.overBudget, 'дом', 'дома', 'домов') + ' дороже бюджета.' : '') +
        (m.unpriced ? ' Без цены в базе — ' + m.unpriced + ', их не показываем, пока задан бюджет.' : '');
      $('rMarket').innerHTML = 'В базе NOTA — <b>' + n + ' ' + K.plural(n, 'дом', 'дома', 'домов') + '</b>' + (withPrice.length ? ', оценка от <b>' + money(withPrice[0].est) + '</b>' : '');
    } else {
      $('mTitle').textContent = 'Таких квартир в базе сейчас нет';
      $('mNote').textContent = (m.overBudget ? 'В бюджет не проходит ни один из ' + m.overBudget + ' подходящих домов; самая доступная оценка — ' + money(m.cheapestOver) + '. ' : 'Попробуйте снять фильтр по классу. ') +
        (m.unpriced ? 'Ещё ' + m.unpriced + ' ' + K.plural(m.unpriced, 'дом', 'дома', 'домов') + ' без цены в базе. ' : '') +
        'Большой семье часто выгоднее купить две соседние квартиры и объединить их — так делают 5–10 % покупателей премиума.';
      $('rMarket').innerHTML = m.overBudget ? 'В бюджет не проходит, оценка от <b>' + money(m.cheapestOver) + '</b>' : 'В базе NOTA таких сейчас нет';
    }
    var list = showAll ? m.rows : m.rows.slice(0, 8);
    $('mRows').innerHTML = list.map(function (x) {
      var link = x.h.p ? '../../doma/' + x.slug + '/' : '../../karta.html#h-' + x.slug;
      return '<tr><td data-label="Дом"><a href="' + link + '">' + esc(x.h.n) + '</a></td><td data-label="Класс">' + esc(x.h.c) + '</td><td data-label="Район">' + esc(x.h.d || '') + '</td><td class="n" data-label="Площади этого формата">' + (x.a === x.b ? fmt(x.a) : fmt(x.a) + '–' + fmt(x.b)) + ' м²</td><td class="n" data-label="Оценка за нужные метры">' +
        (x.est != null ? '≈ ' + money(x.est) + ' за ' + Math.round(x.area) + ' м²' : 'цена по запросу') + '</td></tr>';
    }).join('');
    var more = $('mMore'); more.hidden = n <= 8; more.textContent = showAll ? 'Свернуть' : 'Показать все ' + n;
  }

  function summary() {
    var r = lastRes, s = r.state, rows = lastMatch ? lastMatch.rows : [];
    var ex = Object.keys(s.extra);
    var t = 'Подбор планировки — NOTA\n';
    t += 'Кто живёт: взрослых ' + s.adults + ' (пар ' + s.pairs + '), дети до 6 лет — ' + s.kidsSmall + ', 6–17 лет — ' + s.kidsBig + ', бабушки и дедушки — ' + s.elders + (s.nanny ? ', няня живёт с семьёй' : '') + '\n';
    t += 'Простор: ' + ['компактно', 'комфортно', 'просторно'][s.space] + (ex.length ? '; ещё комнаты: ' + ex.map(function (x) { return form.querySelector('label[for="x_' + x + '"]').textContent; }).join(', ') : '') + '\n';
    t += 'Нужно: ' + r.lo + '–' + r.hi + ' м²' + (r.min < r.lo ? ' (без необязательного — от ' + r.min + ')' : '') + '. ' + r.fmt + '\n';
    t += r.facts.join(' · ') + '\n\nПомещения:\n' + r.rooms.map(function (x) { return '— ' + x.n + ': ' + fmt(x.lo) + '–' + fmt(x.hi) + ' м²' + (x.o ? ' (можно без)' : ''); }).join('\n');
    t += '\n\nВ доме: ' + r.house.map(function (h) { return typeof h === 'object' ? h.t : h; }).join('; ');
    if (rows.length) t += '\n\nДома из базы NOTA: ' + rows.slice(0, 8).map(function (x) { return x.h.n; }).join(', ');
    return t;
  }

  /* окно с планом */
  var dlg = $('zoom');
  function openPlan(id) {
    var p = K.PLANS.filter(function (x) { return x.id === id; })[0]; if (!p) return;
    $('zImg').src = p.img; $('zImg').alt = 'План: ' + p.cap;
    $('zTitle').textContent = p.cap;
    $('zText').textContent = p.where + '. ' + p.txt;
    $('zLink').href = 'index.html#' + p.id;
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
  }
  $('rPlans').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-plan]'); if (!b) return;
    e.preventDefault(); openPlan(b.dataset.plan);
  });
  $('zClose').addEventListener('click', function () { dlg.close(); });
  dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });

  /* события формы */
  form.addEventListener('click', function (e) {
    var b = e.target.closest('.step button'); if (!b || b.disabled) return;
    var inp = b.parentNode.querySelector('input');
    inp.value = (parseInt(inp.value, 10) || 0) + parseInt(b.dataset.d, 10);
    render();
  });
  form.addEventListener('input', render);
  form.addEventListener('change', function (e) { if (e.target.name === 'budget' || e.target.name === 'klass') showAll = false; render(); });
  form.addEventListener('submit', function (e) { e.preventDefault(); });
  function applyPreset(key) {
    var p = PRESETS[key]; if (!p) return false;
    writeHH(p); showAll = false; render(); return true;
  }
  document.querySelectorAll('.presets button').forEach(function (btn) {
    btn.addEventListener('click', function () { applyPreset(btn.dataset.preset); });
  });
  $('mMore').addEventListener('click', function () { showAll = !showAll; renderMatch(); });
  $('kCopy').addEventListener('click', function () {
    var txt = summary(), ta = $('kText'), btn = $('kCopy');
    function done() { btn.textContent = 'Скопировано'; setTimeout(function () { btn.textContent = 'Скопировать расчёт'; }, 2200); }
    function fallback() { ta.value = txt; ta.classList.remove('vh'); ta.style.cssText = 'width:100%;height:180px;margin-top:8px;font:13px var(--f)'; ta.removeAttribute('aria-hidden'); ta.focus(); ta.select(); btn.textContent = 'Текст выделен — скопируйте его'; }
    try { navigator.clipboard.writeText(txt).then(done, fallback); } catch (err) { fallback(); }
  });

  /* полоска результата на телефоне: видна, пока карточка результата за экраном */
  var bar = $('kbar');
  if ('IntersectionObserver' in window) {
    var seen = { card: true, doma: false };
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) { seen[en.target.id === 'kcard' ? 'card' : 'doma'] = en.isIntersecting; });
      bar.classList.toggle('on', !seen.card && !seen.doma);
    });
    io.observe($('kcard')); io.observe($('doma'));
  }

  /* старт: пресет из адреса (#gen3) или «Пара и малыш» */
  var key = (location.hash || '').replace('#', '');
  if (!applyPreset(key)) applyPreset('baby');
  window.addEventListener('hashchange', function () { applyPreset((location.hash || '').replace('#', '')); });

  fetch('loty.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { DATA = d; renderMatch(); })
    .catch(function () { $('mNote').textContent = 'Не удалось загрузить дома из базы. Расчёт комнат и метров работает и без них.'; $('rMarket').textContent = 'Список домов не загрузился'; });
})();
