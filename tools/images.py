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
    n = 0
    for f in sorted(src.iterdir()):
        if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
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
