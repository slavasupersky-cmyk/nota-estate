import json, re
css=open('style.css',encoding='utf-8').read()
mlcss=open('/home/claude/work/npm/package/dist/maplibre-gl.css',encoding='utf-8').read()
body=open('body.html',encoding='utf-8').read()
js=open('app.js',encoding='utf-8').read()
data=open('/home/claude/work/out/data.json',encoding='utf-8').read().replace('</','<\\/')
base=open('/home/claude/work/out/base.json',encoding='utf-8').read().replace('</','<\\/')
head=('<title>До школы пешком</title>\n'
 '<meta name="description" content="Пешие маршруты по улицам от 288 новых домов Москвы до школ: минуты, корпуса, отметка NOTA и обратный поиск домов у школы.">\n'
 '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
 '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;800&display=swap">\n'
 '<style>'+mlcss+'</style>\n<style>'+css+'</style>\n')
tail=('<script type="application/json" id="d-data">'+data+'</script>\n'
 '<script type="application/json" id="d-base">'+base+'</script>\n'
 '<script src="https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>\n'
 '<script>'+js+'</script>\n')
art=head+body+'\n'+tail
open('/home/claude/work/page/do-shkoly-peshkom.html','w',encoding='utf-8').write(art)
full=('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
      +head+'</head>\n<body>\n'+body+'\n'+tail+'</body>\n</html>\n')
open('/home/claude/work/page/shkoly-marshruty.html','w',encoding='utf-8').write(full)
print('artifact %.2f MB, standalone %.2f MB'%(len(art.encode())/1e6, len(full.encode())/1e6))
