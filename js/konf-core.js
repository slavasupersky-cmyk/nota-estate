/* NOTA · Подбор планировки — логика без DOM.
   calc(state)  → помещения, метры, формат, санузлы, что проверить в доме
   match(res, data, filters) → дома из базы, где такой формат продаётся
   plans(res)   → похожие планировки из подборки
   Ориентиры размеров — РБК (мастер-блок), МК (премиум), Коммерсантъ (персонал), СП 54 (минимумы). */
(function (root) {
  'use strict';

  var DEF = {
    space: 1, adults: 2, pairs: 1, kidsSmall: 0, kidsBig: 0, elders: 0, nanny: false,
    guests: 0, party: 0, wfh: 0, cook: 0, dog: 0, cat: false, stroller: false, bikes: 0, sport: false,
    extra: {}, budget: 0, klass: ''
  };
  var EXTRAS = ['study', 'lib', 'wardrobe', 'play', 'gym', 'cinema', 'hobby', 'guest', 'wine', 'spa'];

  function int(v, lo, hi) { v = parseInt(v, 10); if (isNaN(v)) v = lo; return Math.max(lo, Math.min(hi, v)); }

  /* Приводим ввод к допустимому: пар не больше половины взрослых, работающих из дома не больше взрослых */
  function normalize(s) {
    var o = {}, k;
    for (k in DEF) o[k] = (s && s[k] !== undefined) ? s[k] : DEF[k];
    o.space = int(o.space, 0, 2);
    o.adults = int(o.adults, 1, 6);
    o.pairs = int(o.pairs, 0, Math.floor(o.adults / 2));
    o.kidsSmall = int(o.kidsSmall, 0, 4);
    o.kidsBig = int(o.kidsBig, 0, 4);
    o.elders = int(o.elders, 0, 2);
    o.nanny = !!o.nanny;
    o.guests = int(o.guests, 0, 2);
    o.party = int(o.party, 0, 2);
    o.wfh = int(o.wfh, 0, Math.min(2, o.adults));
    o.cook = int(o.cook, 0, 2);
    o.dog = int(o.dog, 0, 2);
    o.cat = !!o.cat; o.stroller = !!o.stroller; o.sport = !!o.sport;
    o.bikes = int(o.bikes, 0, 8);
    var ex = {}; EXTRAS.forEach(function (x) { if (o.extra && o.extra[x]) ex[x] = 1; }); o.extra = ex;
    o.budget = Math.max(0, parseInt(o.budget, 10) || 0);
    o.klass = o.klass || '';
    return o;
  }

  function r5(x) { return Math.round(x / 5) * 5; }
  function plural(n, a, b, c) { var m10 = n % 10, m100 = n % 100; return (m10 === 1 && m100 !== 11) ? a : (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) ? b : c; }

  function calc(input) {
    var s = normalize(input);
    var SP = s.space, EX = s.extra;
    var A = s.adults, P = s.pairs, KS = s.kidsSmall, KB = s.kidsBig, E = s.elders, N = s.nanny;
    var kids = KS + KB;
    var people = A + kids + E + (N ? 1 : 0);
    var rooms = [], house = [], facts = [];
    var bedrooms = 0, closed = 0;
    var LO = [0.9, 1, 1.15][SP], HI = [0.9, 1, 1.25][SP];

    /* kind: bed — спальня, room — другая закрытая комната (считается в комнатности),
       wet — санузел, open — общая зона, aux — хозяйственное */
    function add(name, lo, hi, why, kind, opt) {
      if (opt && SP === 0) return null;      // компактно: необязательное не закладываем
      if (SP === 2) opt = false;             // просторно: закладываем всё
      var r = { n: name, lo: Math.round(lo * LO * 10) / 10, hi: Math.round(hi * HI * 10) / 10, w: why || '', kind: kind, o: !!opt };
      rooms.push(r);
      if (kind === 'bed') { bedrooms++; closed++; }
      if (kind === 'room') closed++;
      return r;
    }

    var singles = A - 2 * P;                 // взрослые без пары
    var extraAdults = P >= 1 ? singles : singles - 1;   // кроме хозяина главной спальни
    var onlyAdults = (kids === 0 && E === 0 && !N);
    var smallHome = onlyAdults && A <= 2 && P <= 1 && extraAdults === 0;

    /* главная спальня */
    if (smallHome && SP < 2) {
      add('Спальня', 14, 18, 'в глубине квартиры, без сквозного прохода', 'bed');
      add('Гардеробная', 2, 4, 'вместо шкафов вдоль стен', 'aux', true);
      add('Санузел', 4, 6, 'ванна или душ и место под стиральную машину, если нет постирочной', 'wet');
    } else {
      add('Мастер-спальня', 16, 20, kids ? 'спальня родителей в глубине квартиры, без сквозного прохода' : 'в глубине квартиры, без сквозного прохода', 'bed');
      add('Гардеробная при спальне', 4, 6, 'за той же дверью, что и спальня', 'aux', true);
      add('Ванная при спальне', 5, 7, kids ? 'своя ванная родителей: утром не стоять в очереди с детьми' : 'своя ванная за дверью спальни', 'wet');
    }
    /* вторые пары */
    for (var i = 1; i < P; i++) {
      add(i === 1 ? 'Вторая мастер-спальня' : 'Ещё одна мастер-спальня', 15, 18, 'в другом крыле от первой — пары не слышат друг друга', 'bed');
      add('Ванная при ней', 4, 5, 'у каждой пары свой санузел', 'wet');
    }
    /* взрослые без пары */
    for (var j = 0; j < extraAdults; j++) add('Спальня взрослого', 12, 15, 'взрослому ребёнку или родственнику — своя дверь', 'bed');
    for (var b = 0; b < Math.ceil(extraAdults / 2); b++) add('Санузел для взрослых', 4, 5, extraAdults - 2 * b > 1 ? 'один на двоих взрослых' : 'свой душ — меньше очереди по утрам', 'wet');
    /* старшее поколение */
    if (E > 0) {
      add(E === 2 ? 'Комната бабушки и дедушки' : 'Комната старшего', E === 2 ? 16 : 14, E === 2 ? 18 : 16, 'ближе ко входу и кухне, без ступенек' + (E === 2 ? '; если они не пара — нужны две комнаты' : ''), 'bed');
      add('Санузел при ней', 4, 5, 'душ без поддона, поручни, дверь открывается наружу', 'wet');
    }
    /* дети */
    var smallLeft = KS;
    while (smallLeft > 0) {
      var two = smallLeft >= 2;
      add(two ? 'Детская на двоих малышей' : 'Детская', two ? 13 : 11, two ? 15 : 13, two ? 'до 6 лет можно вместе; к школе — по комнате' : 'кроватка, пеленальный столик, место для игр', 'bed');
      smallLeft -= two ? 2 : 1;
    }
    for (var m = 0; m < KB; m++) add('Детская школьника', 11, 13, 'своя комната, стол у окна', 'bed');
    for (var kb = 0; kb < Math.ceil(kids / 3); kb++) {
      add(kb === 0 ? 'Детская ванная' : 'Ещё один детский санузел', 4, 6, KS > 0 ? 'ванна, а не только душ: малыша купают' : 'один санузел на двух-трёх детей', 'wet', kids === 1);
    }
    /* персонал */
    if (N) {
      add('Комната няни или помощницы', 10, 12, kids ? 'отдельно от спален семьи, ближе к кухне и детской' : 'отдельно от спален семьи, ближе к кухне', 'bed');
      add('Душ при ней', 3, 4, 'свой санузел обязателен', 'wet');
    }
    /* кабинет и библиотека */
    var studyN = Math.max(s.wfh, EX.study ? 1 : 0);
    if (studyN === 1) add(EX.lib ? 'Кабинет-библиотека' : 'Кабинет', EX.lib ? 16 : 10, EX.lib ? 20 : 12, EX.lib ? 'стол у окна, стеллажи на 6–8 м погонных, кресло для чтения' : 'дверь, которая закрывается, и не в спальном крыле', 'room');
    if (studyN === 2) add(EX.lib ? 'Кабинет-библиотека на двоих' : 'Кабинет на двоих', EX.lib ? 19 : 13, EX.lib ? 24 : 15, 'два рабочих места' + (EX.lib ? ', стеллажи по длинной стене' : ' или второе место в другом конце квартиры'), 'room');
    if (!studyN && EX.lib) add('Библиотека', 12, 16, 'стеллажи на 6–8 м погонных, кресло и свет для чтения', 'room');
    /* гости */
    if (s.guests === 2 || EX.guest) {
      add('Гостевая спальня', 11, 13, s.guests === 2 ? 'гости раз в месяц — уже отдельная комната' : 'отдельная комната для гостей и родственников', 'room');
      add('Душ при гостевой', 3, 4, 'гости не ходят в ванную хозяев', 'wet', true);
    } else if (s.guests === 1) {
      facts.push(studyN ? 'кабинет с диваном — он же гостевая' : 'гостям — диван в гостиной');
    }
    /* дополнительные комнаты */
    if (EX.play) add('Игровая', 14, 20, kids ? 'рядом с детскими, пол без ковра, место для игр на полу' : 'комната для игр и хобби всей семьи', 'room');
    if (EX.gym) add('Домашний спортзал', 12, 18, 'тренажёр, коврик и зеркало; рядом с санузлом', 'room');
    if (EX.cinema) add('Кинозал', 16, 24, 'без окон или с блэкаут-шторами, акустика; экран в 3–4 м от дивана', 'room');
    if (EX.hobby) add('Мастерская', 8, 12, 'хобби и инструменты; вытяжка и отдельная линия электричества', 'room');
    if (EX.wardrobe) add('Гардеробная-комната', 6, 10, 'общая гардеробная с вентиляцией вместо шкафов по спальням', 'aux');
    if (EX.wine) add('Винная комната', 3, 6, 'климат-шкаф или комната с постоянными 12–14 °C, без окна', 'aux');
    if (EX.spa) { add('Сауна или хаммам', 5, 8, 'только если застройщик заложил вентиляцию и гидроизоляцию', 'wet'); add('Душ при спа', 3, 4, 'рядом с сауной', 'wet'); }

    /* кухня и гостиная */
    var kl = [20 + 3 * (people - 1), 24 + 3 * (people - 1)];
    if (s.party === 1) { kl[0] += 4; kl[1] += 4; }
    if (s.party === 2) { kl[0] += 8; kl[1] += 10; }
    var kitchenMode;
    if (s.cook === 2) {
      kitchenMode = 'closed';
      add('Кухня', 10, 13, 'отдельная: запахи и шум остаются за дверью', 'open');
      add('Гостиная-столовая', kl[0] - 4, kl[1] - 4, 'стол на всех, кто живёт' + (s.party ? ', и на гостей' : ''), 'open');
    } else if (s.cook === 1 && people >= 4) {
      kitchenMode = 'slide';
      add('Кухня-гостиная с перегородкой', kl[0], kl[1], 'кухню закрывают раздвижной перегородкой, когда готовят', 'open');
    } else {
      kitchenMode = 'open';
      add('Кухня-гостиная', kl[0], kl[1], s.party === 2 ? 'остров и стол на 8–10 человек' : 'одна общая комната — главная в квартире', 'open');
    }
    /* гостевой санузел */
    if (people >= 5 || s.party === 2) add('Гостевой санузел', 2, 3, 'большой семье и гостям — отдельно от спален', 'wet');
    else if (people >= 3 || s.party === 1 || s.guests >= 1) add('Гостевой санузел', 2, 3, 'гости не ходят через спальни', 'wet', true);
    /* хозяйство */
    if (people >= 4 || kids > 0) add('Постирочная', 3, 5, 'стиральная и сушильная машины, сушилка не в гостиной', 'aux');
    else if (s.dog > 0 || people === 3) add('Постирочная', 3, 5, 'стиральная и сушильная машины, сушилка не в гостиной', 'aux', true);
    else add('Ниша под стиральную машину', 1, 1.5, 'в санузле или в коридоре', 'aux');
    var hall = [4 + 0.3 * people, 6 + 0.4 * people];
    if (s.stroller) { hall[0] += 1.5; hall[1] += 2; }
    if (s.dog === 2) { hall[0] += 1; hall[1] += 1.5; }
    var hallWhy = [s.stroller ? 'коляска стоит, не перегораживая проход' : '', s.dog ? 'место вытереть собаку и повесить поводок' : '', (!s.stroller && !s.dog) ? 'шкаф на верхнюю одежду всей семьи' : ''].filter(Boolean).join('; ');
    add('Прихожая', hall[0], hall[1], hallWhy, 'aux');
    if (people >= 3) add('Кладовая', 2, 4, 'пылесос, чемоданы, сезонные вещи', 'aux', people < 4);

    /* сумма */
    var lo = 0, hi = 0, req = 0;
    rooms.forEach(function (r) { lo += r.lo; hi += r.hi; if (!r.o) req += r.lo; });
    var CF = [[1.06, 1.10], [1.08, 1.14], [1.12, 1.18]][SP];
    var tLo = r5(lo * CF[0]), tHi = r5(hi * CF[1]), tMin = Math.min(tLo, r5(req * CF[0]));

    /* формат */
    var studio = (A === 1 && onlyAdults && studyN === 0 && closed === 1 && s.guests < 2);
    var mr = closed + 1;                      // закрытые комнаты + гостиная (или кухня-гостиная)
    var others = rooms.filter(function (r) { return r.kind === 'room'; }).map(function (r) { return r.n.toLowerCase().replace('гостевая спальня', 'гостевая').replace('домашний спортзал', 'спортзал'); });
    if (N) others.unshift('комната персонала');
    var bedOnly = bedrooms - (N ? 1 : 0);
    var fmt;
    if (studio) fmt = 'Евродвушка: спальня и кухня-гостиная. Если спать в общей комнате — хватит студии 28–35 м²';
    else {
      fmt = bedOnly + ' ' + plural(bedOnly, 'спальня', 'спальни', 'спален') + others.map(function (o) { return ' + ' + o; }).join('') +
        (kitchenMode === 'closed' ? ', кухня отдельно' : ', кухня-гостиная') +
        (mr >= 5 ? ' — в объявлениях «многокомнатная», ' + mr + ' комнат' :
          ' — в объявлениях «' + mr + '-комнатная»' + (kitchenMode === 'closed' ? '' : ' или «евро-' + mr + '»'));
    }
    var wets = rooms.filter(function (r) { return r.kind === 'wet' && !/сауна/i.test(r.n); });
    var baths = wets.length, bathsReq = wets.filter(function (r) { return !r.o; }).length;
    facts.unshift((bathsReq < baths ? bathsReq + '–' + baths : baths) + ' ' + plural(baths, 'санузел', 'санузла', 'санузлов'));
    var twoWings = P >= 2 || (P >= 1 && (E > 0 || extraAdults > 0));
    if (twoWings) facts.push('две взрослые зоны в разных крыльях');
    if (kitchenMode === 'closed') facts.push('кухня отдельно');
    if (kitchenMode === 'slide') facts.push('кухня закрывается');
    if (N) facts.push('комната персонала');

    /* дом */
    if (s.stroller || KS > 0) house.push('Колясочная в лобби и путь от двери подъезда до лифта без ступенек');
    if (kids > 0) house.push({ t: 'Школа и сад пешком — минуты до школ есть в карточке каждого дома, лучшие школы — в рейтинге NOTA', link: 'shkoly' });
    if (E > 0) house.push('Лифт с уровня земли, поликлиника и аптека рядом, лавочки во дворе');
    if (s.dog > 0) house.push('Лапомойка в лобби и площадка для выгула' + (s.dog === 2 ? '; для крупной собаки — выход во двор без длинных коридоров' : ''));
    if (s.cat) house.push('Сетки на окна — уточнить у застройщика, можно ли их ставить на этом фасаде');
    if (s.bikes > 0 || s.sport) { var kel = Math.max(2, Math.round(1 + s.bikes * 0.8 + (s.sport ? 1.5 : 0))); house.push('Келлер около ' + kel + ' м² или места для малого транспорта в паркинге' + (s.bikes >= 3 ? '; велокомната у входа с пандусом' : '')); }
    if (s.party === 2) house.push('Лаунж или терраса на крыше для больших компаний, гостевой паркинг');
    if (s.party > 0 || s.guests > 0) house.push('Звукоизоляция между квартирами — спросить индекс в дБ, застройщики его редко публикуют');
    if (s.wfh > 0 && SP === 0) house.push('Коворкинг в доме — рабочее место без лишних метров в квартире');
    if (N) house.push('Отдельный вход в зону персонала бывает только в больших квартирах; в остальных — двери с хорошей шумоизоляцией');
    if (EX.gym) house.push('Фитнес в доме — проверьте, не заменит ли он домашний спортзал');
    if (EX.spa) house.push('Сауна или хаммам в квартире — только по проекту дома: спросите, где это заложено');
    if (!house.length) house.push('Фитнес, коворкинг и мейлрум — дом добирает то, чего нет в квартире');

    return {
      state: s, rooms: rooms, lo: tLo, hi: tHi, min: tMin, corridors: ['6–10', '8–14', '12–18'][SP],
      mr: mr, studio: studio, fmt: fmt, facts: facts, house: house,
      bedrooms: bedrooms, baths: baths, bathsReq: bathsReq, twoWings: twoWings, kitchen: kitchenMode, people: people
    };
  }

  /* Сколько комнат у лота в нашей базе. У части застройщиков тип считается по спальням («2 спальни» = евро-3) — флаг e */
  function lotRooms(tip, e) {
    if (tip === 'студия') return 1;
    if (tip === '4+') return 4 + (e ? 1 : 0);
    return parseInt(tip, 10) + (e ? 1 : 0);
  }

  function match(res, data, f) {
    f = f || {};
    var budget = parseInt(f.budget, 10) || 0, kl = f.klass || '';
    var need = res.lo, needHi = res.hi;
    var want = res.studio ? [1, 2] : [res.mr];
    var rows = [], seen = {}, overBudget = 0, cheapest = null, overSeen = {}, noPrice = {};
    (data.l || []).forEach(function (x) {
      var slug = x[0], tip = x[1], a = x[2], b = x[3], c = x[4], e = x[5], cmax = x[6], h = data.h[slug];
      if (!h) return;
      var rr = lotRooms(tip, e);
      var ok = want.some(function (w) { return w >= 4 ? (tip === '4+' || rr === w) : rr === w; });
      if (!ok) return;
      if (kl) { if (kl === 'элит') { if (h.c !== 'элитный' && h.c !== 'делюкс') return; } else if (h.c !== kl) return; }
      if (b < need * 0.92 || a > needHi * 1.05) return;
      /* какую площадь этого формата здесь можно купить и за сколько:
         от цены метра самого дешёвого лота × нужная площадь до цены метра самого дорогого × верх нужной площади (не дороже самого дорогого лота) */
      var buyLo = Math.min(b, Math.max(a, need)), buyHi = Math.max(buyLo, Math.min(b, needHi));
      var area = buyLo, est = null, estHi = null;
      if (c) {
        var ppmLo = c / a, ppmHi = cmax ? Math.max(cmax / b, ppmLo) : ppmLo;
        est = ppmLo * buyLo;
        estHi = Math.max(est, cmax ? Math.min(cmax, ppmHi * buyHi) : ppmLo * buyHi);
      }
      if (budget && est == null) { noPrice[slug] = 1; return; }
      if (budget && est && est > budget) { if (!overSeen[slug]) { overSeen[slug] = 1; overBudget++; } if (cheapest === null || est < cheapest) cheapest = est; return; }
      var cur = seen[slug];
      if (!cur) { cur = seen[slug] = { slug: slug, h: h, a: a, b: b, est: est, estHi: estHi, area: area, areaHi: buyHi, rooms: [rr] }; rows.push(cur); return; }
      cur.a = Math.min(cur.a, a); cur.b = Math.max(cur.b, b);
      if (cur.rooms.indexOf(rr) < 0) cur.rooms.push(rr);
      if (est != null && (cur.est == null || est < cur.est)) { cur.est = est; cur.area = area; }
      if (estHi != null && (cur.estHi == null || estHi > cur.estHi)) { cur.estHi = estHi; cur.areaHi = buyHi; }
    });
    rows.sort(function (p, q) { if (p.est == null) return 1; if (q.est == null) return -1; return p.est - q.est; });
    overBudget = Object.keys(overSeen).filter(function (k) { return !seen[k]; }).length;
    var unpriced = Object.keys(noPrice).filter(function (k) { return !seen[k] && !overSeen[k]; }).length;
    var byClass = {};
    rows.forEach(function (x) { byClass[x.h.c] = (byClass[x.h.c] || 0) + 1; });
    return { rows: rows, byClass: byClass, overBudget: overBudget, cheapestOver: cheapest, unpriced: unpriced };
  }

  /* Похожие планировки из подборки «Как бывает» */
  var PLANS = [
    { id: 'p-16', img: 'img/zorge-9-016.svg', a: 16.4, mr: 1, cap: 'Микростудия, 16,4 м²', where: '«Зорге 9», апартаменты, бизнес', txt: 'Кровать, стол на двоих, кухонный модуль и ванная. Такие метры бывают только в апартаментах.' },
    { id: 'p-24', img: 'img/khay-layf-024.svg', a: 24.1, mr: 1, cap: '«Однушка» на 24 метра', where: '«Хай Лайф», бизнес', txt: 'Комната 13,1 м² с кухней в нише и санузел 3,1 м². По сути студия с прихожей.' },
    { id: 'p-28', img: 'img/ostrov-028.svg', a: 28.4, mr: 1, cap: 'Студия, 28,4 м²', where: '«Остров», бизнес', txt: 'Кухня-гостиная 19,4 м², коридор 5,3 м², санузел 3,7 м². Чуть больше московского минимума в 28 м².' },
    { id: 'p-59', img: 'img/krylatskaya-33-059.svg', a: 59, mr: 2, cap: 'Евродвушка, 59 м²', where: '«Крылатская 33», бизнес', txt: 'Кухня-гостиная 28,6 м², спальня 17,3 м², один санузел. Одному или паре.' },
    { id: 'p-77', img: 'img/krylatskaya-33-077.svg', a: 77.2, mr: 2, cap: 'Классическая двушка, 77,2 м²', where: '«Крылатская 33», бизнес', txt: 'Кухня 13 м² отдельно, гостиная 24,8 м², спальня 14,1 м², два санузла и постирочная.' },
    { id: 'p-109', img: 'img/krylatskaya-33-109.svg', a: 108.9, mr: 3, two: 1, cap: 'Две спальни в разных крыльях, 108,9 м²', where: '«Крылатская 33», бизнес', txt: 'У каждой спальни свой санузел и гардеробная, между ними — кухня, гостиная и гостевой санузел.' },
    { id: 'p-106', img: 'img/ostrov-106.svg', a: 105.8, mr: 4, cap: 'Евро-4, 105,8 м²', where: '«Остров», бизнес', txt: 'Три спальни и кухня-гостиная 36,6 м², два санузла. Детские помещаются, мастер-блок — нет.' },
    { id: 'p-144', img: 'img/ostrov-144.svg', a: 144.1, mr: 5, cap: '5 комнат и кухня отдельно, 144,1 м²', where: '«Остров», бизнес', txt: 'Четыре спальни, гостиная 28,9 м² и кухня 14,1 м², три санузла.' },
    { id: 'p-182', img: 'img/ostrov-183.svg', a: 182.8, mr: 4, cap: 'Клубный корпус с террасой, 182,8 м²', where: '«Остров», клубный корпус', txt: 'Три спальни, мастер-блок с ванной 12 м² и гардеробной 16,6 м², кухня-гостиная 47,7 м², терраса 61,3 м².' },
    { id: 'p-233', img: 'img/ostrov-233.svg', a: 233.4, mr: 6, cap: 'Пентхаус с игровой и кабинетом, 233,4 м²', where: '«Остров», пентхаус', txt: 'Гостиная 62,7 м², игровая 22,9 м², кабинет 10 м², постирочная, терраса 37 м².' },
    { id: 'p-262', img: 'img/ostrov-262.svg', a: 262.4, mr: 6, two: 1, cap: 'Шесть комнат с комнатой персонала, 262,4 м²', where: '«Остров», клубный корпус', txt: 'Кухня-гостиная 81,4 м², мастер-блок, две детские, кабинет и комната персонала 6,9 м².' },
    { id: 'p-403', img: 'img/le-dom-403.svg', a: 403, mr: 7, two: 1, cap: 'Резиденция 403 м²', where: '«Лё Дом», делюкс', txt: 'Пять спален, кабинет, две гостиные и столовая, прачечная, три гардеробные. Коридоры — 13 % площади.' }
  ];
  function plans(res, n) {
    var mid = (res.lo + res.hi) / 2;
    var target = res.studio ? 1.5 : res.mr;
    return PLANS.map(function (p) {
      var score = Math.abs(Math.min(p.mr, 7) - Math.min(target, 7)) * 35 + Math.abs(p.a - mid) / mid * 100 - (res.twoWings && p.two ? 25 : 0);
      return { p: p, score: score };
    }).sort(function (x, y) { return x.score - y.score; }).slice(0, n || 3).map(function (x) { return x.p; });
  }


  /* Рынок для нужной квартиры: оценки цены по домам базы (без фильтра бюджета).
     Зоны вилки: red — дешевле самого доступного дома, yellow — до первой четверти (выбор узкий), green — дальше. */
  function q(arr, p) { if (!arr.length) return null; return arr[Math.min(arr.length - 1, Math.max(0, Math.round(p * (arr.length - 1))))]; }
  function market(res, data, klass) {
    var m = match(res, data, { klass: klass || '' });
    var priced = m.rows.filter(function (x) { return x.est != null; }).sort(function (a, b) { return a.est - b.est; });
    var e = priced.map(function (x) { return x.est; });
    return { rows: m.rows, priced: priced, n: m.rows.length, np: priced.length,
      min: e.length ? e[0] : null, p25: q(e, 0.25), p50: q(e, 0.5), p75: q(e, 0.75), p90: q(e, 0.9), max: e.length ? e[e.length - 1] : null,
      cheapest: priced[0] || null,
      maxHi: priced.reduce(function (m, x) { return Math.max(m, x.estHi || x.est); }, 0),
      priciest: priced.slice().sort(function (a, b) { return (b.estHi || b.est) - (a.estHi || a.est); })[0] || null };
  }
  function zone(mk, b, a) {
    if (!mk.np) return 'none';
    if (a != null && a > mk.maxHi) return 'above';
    if (b == null) return 'open';
    if (b < mk.min) return 'red';
    if (b < mk.p25) return 'yellow';
    return 'green';
  }
  /* сколько домов в вилке [a, b] и сколько дешевле её */
  function fork(mk, a, b) {
    var inF = [], below = [];
    mk.priced.forEach(function (x) {
      var hi = x.estHi != null ? x.estHi : x.est;
      if (b != null && x.est > b) return;           // дороже вилки
      if (a && hi < a) below.push(x); else inF.push(x);
    });
    /* сначала дорогие: по тому, сколько из вилки можно потратить в доме (верх цены, но не выше вилки), затем по нижней цене */
    function key(x) { var hi = x.estHi != null ? x.estHi : x.est; return b != null ? Math.min(hi, b) : hi; }
    function top(p, q) { return (key(q) - key(p)) || (q.est - p.est); }
    inF.sort(top); below.sort(top);
    return { inFork: inF, below: below };
  }

  /* дома, где хоть какой-то лот стоит в пределах вилки: для бюджета выше цен на нужную квартиру */
  function budgetHouses(data, a, b, klass) {
    var by = {}, out = [];
    (data.l || []).forEach(function (x) {
      var slug = x[0], h = data.h[slug], c = x[4], cmax = x[6] || x[4]; if (!h || !c) return;
      if (klass) { if (klass === 'элит') { if (h.c !== 'элитный' && h.c !== 'делюкс') return; } else if (h.c !== klass) return; }
      if (b != null && c > b) return; if (cmax < a) return;
      var r = by[slug]; if (!r) { r = by[slug] = { slug: slug, h: h, a: x[2], b: x[3], pmin: c, pmax: cmax, tips: [] }; out.push(r); }
      r.a = Math.min(r.a, x[2]); r.b = Math.max(r.b, x[3]); r.pmin = Math.min(r.pmin, c); r.pmax = Math.max(r.pmax, cmax);
      var t = x[1] === 'студия' ? 'студии' : x[1] + (x[5] ? ' сп.' : ''); if (r.tips.indexOf(t) < 0) r.tips.push(t);
    });
    return out.sort(function (p, q) { return q.pmax - p.pmax; });
  }

  var API = { DEF: DEF, EXTRAS: EXTRAS, normalize: normalize, calc: calc, match: match, market: market, zone: zone, fork: fork, budgetHouses: budgetHouses, plans: plans, PLANS: PLANS, lotRooms: lotRooms, plural: plural };
  if (typeof module !== 'undefined' && module.exports) module.exports = API; else root.NotaKonf = API;
})(this);
