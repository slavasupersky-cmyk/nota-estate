# Пешие маршруты «дом ↔ школа» — как пересчитать

Скрипты запускаются в облачной сессии Claude (Python 3.11: `pip install osmium shapely pyproj scipy numpy`).
На маке ничего ставить не нужно. Результат — файлы в `data/` и страница `shkoly-marshruty.html`.

## Входные данные

1. `nota-moscow-bbbike.osm.pbf` — Москва из OpenStreetMap: https://download.bbbike.org/osm/bbbike/Moscow/Moscow.osm.pbf (≈85 МБ, обновляется раз в несколько дней). Облако и оболочка мака в интернет не ходят — качает встроенный браузер Claude в «Загрузки», дальше файл забирается в облако.
2. `nota-ovp-mailru.osm` — запад (Рублёвка, Новая Рига, Сколково) и север (Долгопрудный) из Overpass, запрос ниже; работает зеркало `https://maps.mail.ru/osm/tools/overpass/api/interpreter`.
3. `schools-artifact-data.json` — база школ: `data/shkoly-baza-2026-09-23.json` (формат `{"__SCHOOLS__": [...]}`) или свежий снимок со страницы «Школы Москвы под отметку».
4. `data/zhk-moskva-biznes-plus-geo.csv` и `data/index-2026-09-shkoly-geo.csv` — дома и прежний геокод школ. В скриптах путь к ним — `/mnt/user-data/uploads/nota-estate/data/`.

Запрос Overpass:

```
[out:xml][timeout:180];
(
  way["highway"](55.655,36.98,55.875,37.335);
  way["highway"](55.900,37.44,55.965,37.63);
  nwr["amenity"~"^(school|kindergarten|college|university)$"](55.655,36.98,55.875,37.335);
  nwr["amenity"~"^(school|kindergarten|college|university)$"](55.900,37.44,55.965,37.63);
);
(._;>;);
out body;
```

## Порядок

| Шаг | Скрипт | Что делает |
|---|---|---|
| 1 | `extract.py` | Пешеходная сеть, барьеры, школы и сады, адреса, районы, подложка карты → `out/graph_raw.npz`, `out/features.pkl` |
| 2 | `west_roads.py` | Дороги запада и севера для подложки |
| 3 | `graph.py` | Граф в метрах (UTM 37N), связность → `out/graph.npz` |
| 4 | `match_schools.py` → `match2.py` | Привязка 488 школ базы к корпусам OSM по номеру, названию и адресу; ручные поправки — `MANUAL_ADDR`, `MANUAL_PT`, словарь `NAMED` |
| 5 | `schools_final.py` | Школы базы + прочие школы из OSM → `out/schools_final.pkl` |
| 6 | `route2.py` | Маршруты: Дейкстра от каждого дома, лимит 3,9 км, подходы к сети не через ж/д, воду и магистрали |
| 7 | `build_outputs.py` | CSV в `out/data/` |
| 8 | `build_base.py`, `build_data.py` | Подложка и данные страницы → `out/base.json`, `out/data.json` |
| 9 | `page/assemble.py` | Сборка страницы из `page/style.css`, `body.html`, `app.js` |

Скорость — 75 м/мин (4,5 км/ч) — задаётся в `build_outputs.py` и `build_data.py`.
