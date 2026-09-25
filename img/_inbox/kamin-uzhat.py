"""Ужимает картинки разбора «Живой огонь в городе»: img/_inbox/kamin/*.jpg → img/<имя>.jpg, 1920 px по ширине, JPEG 85."""
import pathlib
from PIL import Image
root = pathlib.Path(__file__).resolve().parents[2]
src = root / 'img/_inbox/kamin'
for n in ('19-kamin', '19-kamin-plamya', '19-kamin-kreslo', '19-kamin-portal'):
    p = src / f'{n}.jpg'
    if not p.exists() or p.stat().st_size < 10000:
        print(n, '— нет файла'); continue
    im = Image.open(p).convert('RGB')
    if im.width > 1920:
        im = im.resize((1920, round(im.height * 1920 / im.width)), Image.LANCZOS)
    out = root / 'img' / f'{n}.jpg'
    im.save(out, quality=85, optimize=True, progressive=True)
    print(n, im.size, out.stat().st_size // 1024, 'КБ')
