#!/bin/bash
# Выкладка сайта на nota.expert (хостинг nic.ru) по FTP — только изменённые файлы.
#
#   bash deploy/deploy.sh            проверка: покажет, что будет загружено (ничего не меняет)
#   bash deploy/deploy.sh go         выложить
#   bash deploy/deploy.sh go clean   выложить и удалить на хостинге файлы, которых больше нет в репозитории
#
# Как понимает, что изменилось: хранит у вас на Mac список файлов с «отпечатками» (хешами)
# от прошлой выкладки (~/.cache/nota-deploy/manifest.txt) и грузит только то, что поменялось.
# Первый запуск грузит всё.
#
# Пароль НЕ хранится здесь: он в ~/.netrc (строка: machine ХОСТ login ЛОГИН password ПАРОЛЬ).
set -uo pipefail
export LC_COLLATE=C

FTP_HOST="ftp.not7954625.nichost.ru"   # сервер FTP из панели nic.ru → «FTP»
SITE_URL="https://nota.expert"
# Сертификат FTP-сервера nic.ru выписан не на это имя, поэтому доверяем ровно этому сертификату (по отпечатку).
# Если nic.ru сменит сертификат, lftp покажет новый отпечаток — его нужно будет вписать сюда.
FTP_CERT_FP="6C:6D:D1:87:CD:EA:A8:C4:20:1E:D8:11:20:A3:AD:28:51:A5:2B:C4"

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$HOME/.cache/nota-deploy"
STAGE="$WORK/site"
MANIFEST="$WORK/manifest.txt"
MODE="${1:-check}"; CLEAN="${2:-}"

command -v lftp >/dev/null || { echo "Нет lftp. Установите: brew install lftp"; exit 1; }
grep -q "machine $FTP_HOST" ~/.netrc 2>/dev/null || { echo "Нет логина/пароля для $FTP_HOST в ~/.netrc"; exit 1; }

cd "$REPO" || exit 1
[ -z "$(git status --porcelain)" ] || echo "⚠ Есть незакоммиченные изменения — выложится текущее состояние файлов на диске."

# 1. Чистая копия сайта: только файлы из git, без служебных папок
rm -rf "$STAGE"; mkdir -p "$STAGE"
git ls-files -z -- . \
  ':(exclude,glob).git*' ':(exclude).nojekyll' ':(exclude)README.md' \
  ':(exclude)Claude outputs' ':(exclude)tools' ':(exclude)data' \
  ':(exclude)img/_inbox' ':(exclude)_to_delete' ':(exclude)deploy' \
  | while IFS= read -r -d '' f; do if [ -e "$f" ]; then printf '%s\0' "$f"; fi; done \
  | rsync -a --from0 --files-from=- ./ "$STAGE/" || { echo "Ошибка при сборке копии сайта"; exit 1; }
cp deploy/.htaccess "$STAGE/.htaccess"
# публичная выгрузка базы — на неё ссылается разбор «Что не сходится в классах»
mkdir -p "$STAGE/data" && cp data/doma.csv "$STAGE/data/doma.csv"
# снять метку превью: на GitHub Pages страницы закрыты от поисковиков, на nota.expert открыты
find "$STAGE" -name '*.html' -exec perl -0pi -e 's/\n?<meta name="robots" content="noindex" data-preview>//g' {} +
LEFT=$(grep -rl 'data-preview' "$STAGE" --include='*.html' | wc -l | tr -d ' ')
[ "$LEFT" = "0" ] || { echo "Метка превью осталась в $LEFT файлах — выкладка остановлена"; exit 1; }
[ -f "$STAGE/robots.txt" ] && [ -f "$STAGE/sitemap.xml" ] || echo "⚠ Нет robots.txt или sitemap.xml в выкладке — закоммитьте их (их пишет tools/build.py)"

# 2. Что изменилось с прошлой выкладки
NEW="$WORK/manifest.new"
(cd "$STAGE" && find . -type f -print0 | sort -z | xargs -0 shasum -a 1 | sed 's|  \./|  |') > "$NEW"
touch "$MANIFEST"
CHANGED="$(comm -13 <(sort "$MANIFEST") <(sort "$NEW") | sed 's/^[0-9a-f]*  //')"
GONE="$(comm -23 <(sed 's/^[0-9a-f]*  //' "$MANIFEST" | sort) <(sed 's/^[0-9a-f]*  //' "$NEW" | sort))"
N_CH=$( [ -n "$CHANGED" ] && echo "$CHANGED" | wc -l | tr -d ' ' || echo 0 )
N_GO=$( [ -n "$GONE" ] && echo "$GONE" | wc -l | tr -d ' ' || echo 0 )

echo "Файлов сайта: $(wc -l < "$NEW" | tr -d ' ')"
echo "Изменилось и будет загружено: $N_CH"
[ -n "$CHANGED" ] && echo "$CHANGED" | head -15 | sed 's/^/  + /'
[ "$N_CH" -gt 15 ] && echo "  … и ещё $((N_CH-15))"
if [ "$N_GO" -gt 0 ]; then
  if [ "$CLEAN" = "clean" ]; then echo "Будет удалено на хостинге: $N_GO"; else echo "Удалено из репозитория (на хостинге останутся, убрать: go clean): $N_GO"; fi
  echo "$GONE" | head -10 | sed 's/^/  − /'
fi

if [ "$MODE" != "go" ]; then
  echo "— Это проверка, на сервере ничего не менялось. Выложить: bash deploy/deploy.sh go —"
  exit 0
fi
if [ "$N_CH" -eq 0 ] && { [ "$CLEAN" != "clean" ] || [ "$N_GO" -eq 0 ]; }; then
  echo "Нечего выкладывать — на хостинге уже актуальная версия."; exit 0
fi

# 3. Команды для lftp
CMDS="$WORK/lftp-cmds.txt"
{
  echo "set ftp:ssl-allow yes; set ssl:verify-certificate/$FTP_CERT_FP no; set net:max-retries 2; set net:timeout 20; set cmd:fail-exit yes"
  echo "open $FTP_HOST"
  # все папки, где лежат изменённые файлы (вместе с родительскими)
  echo "$CHANGED" | grep -v '^$' | awk -F/ '{p=""; for(i=1;i<NF;i++){p=(p==""?$i:p"/"$i); print p}}' | sort -u | while read -r d; do
    echo "mkdir -p -f \"$d\""; echo "chmod 755 \"$d\" || echo"
  done
  echo "$CHANGED" | grep -v '^$' | while read -r f; do
    echo "put \"$STAGE/$f\" -o \"$f\""; echo "chmod 644 \"$f\" || echo"
  done
  if [ "$CLEAN" = "clean" ]; then echo "$GONE" | grep -v '^$' | while read -r f; do echo "rm -f \"$f\""; done; fi
  echo "bye"
} > "$CMDS"

echo "Загружаю…"
if lftp -f "$CMDS" 2>&1 | grep -v "^$"; [ "${PIPESTATUS[0]}" -eq 0 ]; then
  if [ "$CLEAN" = "clean" ]; then cp "$NEW" "$MANIFEST"
  else
    # запоминаем новое состояние, но удалённые из репо файлы оставляем в списке — они ещё на хостинге
    { cat "$NEW"; grep -F -f <(echo "$GONE" | grep -v '^$' | sed 's/^/  /;s/$//') "$MANIFEST" 2>/dev/null; } | sort -u -k2 > "$MANIFEST.tmp" && mv "$MANIFEST.tmp" "$MANIFEST"
  fi
  echo "Готово. Проверка: $(curl -sI "$SITE_URL" | head -1)"
else
  echo "✗ Выкладка прервалась с ошибкой (см. выше). Пришлите вывод Claude или просто запустите ещё раз."
fi
