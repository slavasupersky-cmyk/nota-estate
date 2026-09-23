"""Картинки домов: исходники в img/_src/doma/<slug>.(jpg|jpeg|png|webp) → img/doma/<slug>.jpg
960×600 (кадр 16:10 по центру), JPEG ~80, без метаданных. Лёгкие файлы идут в git, исходники — нет."""
import pathlib
from PIL import Image, ImageOps

W, H = 960, 600


def build(root):
    src = root / 'img/_src/doma'
    out = root / 'img/doma'
    out.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return
    # только дома, которые есть на сайте: у дублей и скрытых домов картинку не делаем
    import csv
    dp = root / 'data/doma.csv'
    live = {r['slug'] for r in csv.DictReader(dp.open(encoding='utf-8-sig'), delimiter=';')} if dp.exists() else None
    n = 0
    for f in sorted(src.iterdir()):
        if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        if live is not None and f.stem.lower() not in live:
            continue
        dst = out / (f.stem.lower() + '.jpg')
        if dst.exists() and dst.stat().st_mtime >= f.stat().st_mtime:
            continue
        im = ImageOps.exif_transpose(Image.open(f)).convert('RGB')
        im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.5))
        im.save(dst, 'JPEG', quality=80, optimize=True, progressive=True)
        n += 1
    if n:
        print('картинки домов: обработано', n)
