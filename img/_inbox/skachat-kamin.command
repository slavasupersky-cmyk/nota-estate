#!/bin/bash
# Картинки для разбора «Камин в квартире» (Unsplash, свободная лицензия). Кладёт в img/_inbox/kamin/.
cd "$(dirname "$0")"; mkdir -p kamin
get(){ curl -sSL --max-time 60 -o "kamin/$1.jpg" "$2&w=2400&q=85&fm=jpg" && echo "$1 — ок" || echo "$1 — не скачалось"; }
get 19-kamin "https://images.unsplash.com/photo-1702411200201-3061d0eea802?ixlib=rb-4.1.0"
get 19-kamin-portal "https://images.unsplash.com/photo-1570720742903-8606f80901e5?ixlib=rb-4.1.0"
get 19-kamin-plamya "https://images.unsplash.com/photo-1595770205769-84b55f75a053?ixlib=rb-4.1.0"
get 19-kamin-kreslo "https://images.unsplash.com/photo-1695654673105-135d272503d8?ixlib=rb-4.1.0"
echo; echo "Готово. Напишите в чат: готово"
