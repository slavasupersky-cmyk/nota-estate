#!/usr/bin/env python3
"""
Векторизация лого «Прохорова Select» из растрового макета.

Что делает: режет макет на элементы (знак PS, «ПРОХОРОВА», «SELECT», черта,
«PRIVATE REAL ESTATE»), увеличивает в 4 раза, переводит в маску по яркости и
обводит потрейсом. Собирает один SVG с бронзовым градиентом и два варианта
(светлый/тёмный фон) + отдельно знак. Кривые шрифта сохраняются как контуры,
размытия и тени нет.

Нужен potrace в PATH:  brew install potrace  |  apt install potrace
Запуск:  python3 logo_vector.py макет.jpg  → папка logo-svg/
"""
import re, subprocess, sys, os
from pathlib import Path
from PIL import Image, ImageOps

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "logo.jpg")
OUT = Path("logo-svg"); OUT.mkdir(exist_ok=True)
SCALE = 4          # увеличение перед трассировкой — глаже кривые
THRESH = 195       # яркость: темнее — элемент, светлее — фон
# Области на исходном макете 1254×1254 (x0, y0, x1, y1) и роль цвета
PARTS = {
    "mark":   ((470, 80, 770, 490), "bronze"),
    "name":   ((270, 500, 985, 590), "ink"),
    "select": ((445, 595, 800, 655), "bronze"),
    "line":   ((560, 672, 700, 688), "bronze"),
    "sub":    ((420, 712, 830, 745), "bronze"),
}

im = Image.open(SRC).convert("L")

def trace(box):
    x0, y0, x1, y1 = box
    crop = im.crop(box).resize(((x1 - x0) * SCALE, (y1 - y0) * SCALE), Image.LANCZOS)
    mask = crop.point(lambda v: 0 if v < THRESH else 255)          # чёрное = фигура
    pbm = OUT / "_tmp.pbm"; svg = OUT / "_tmp.svg"
    ImageOps.invert(mask).convert("1").save(pbm)                    # potrace ждёт чёрное на белом
    mask.convert("1").save(pbm)
    subprocess.run(["potrace", str(pbm), "-s", "-o", str(svg), "-a", "1.2", "-O", "0.2", "-t", "6", "--flat"], check=True)
    txt = svg.read_text()
    d = " ".join(re.findall(r'd="([^"]+)"', txt))
    # potrace отдаёт координаты в pt с transform; берём его transform как есть
    tr = re.search(r'<g transform="([^"]+)"', txt).group(1)
    return x0, y0, (x1 - x0), (y1 - y0), d, tr

paths = {k: trace(box) for k, (box, _) in PARTS.items()}
for f in ("_tmp.pbm", "_tmp.svg"): (OUT / f).unlink(missing_ok=True)

# Собираем композицию в координатах исходного макета (px), обрезанную по краям лого
X0, Y0, X1, Y1 = 260, 70, 995, 755
W, H = X1 - X0, Y1 - Y0

def group(k, fill):
    x0, y0, w, h, d, tr = paths[k]
    # potrace: viewBox = w*SCALE pt при 1px=1pt → масштабируем обратно в px макета
    return (f'<g transform="translate({x0 - X0},{y0 - Y0}) scale({1 / SCALE})"><g transform="{tr}">'
            f'<path fill="{fill}" d="{d}"/></g></g>')

DEFS = """<defs>
<linearGradient id="bronze" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#C9A97E"/><stop offset=".45" stop-color="#8E6F4B"/><stop offset="1" stop-color="#5E4630"/>
</linearGradient>
<linearGradient id="bronzeDark" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#E2C89E"/><stop offset=".5" stop-color="#B8976A"/><stop offset="1" stop-color="#8A6C48"/>
</linearGradient>
</defs>"""

def compose(ink, grad, bg=None):
    body = "".join(group(k, ink if role == "ink" else f"url(#{grad})") for k, (_, role) in PARTS.items())
    rect = f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'{DEFS}{rect}{body}</svg>')

(OUT / "prokhorova-select-light.svg").write_text(compose("#1F1B17", "bronze"))
(OUT / "prokhorova-select-dark.svg").write_text(compose("#ECE5DB", "bronzeDark"))
(OUT / "prokhorova-select-light-bg.svg").write_text(compose("#1F1B17", "bronze", "#E4DDD4"))
(OUT / "prokhorova-select-dark-bg.svg").write_text(compose("#ECE5DB", "bronzeDark", "#1A1917"))

# Отдельно знак PS
mx0, my0, mw, mh, md, mtr = paths["mark"]
for name, grad in (("mark-light", "bronze"), ("mark-dark", "bronzeDark")):
    (OUT / f"{name}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {mw} {mh}" width="{mw}" height="{mh}">{DEFS}'
        f'<g transform="scale({1 / SCALE})"><g transform="{mtr}"><path fill="url(#{grad})" d="{md}"/></g></g></svg>')

print("готово:", sorted(p.name for p in OUT.iterdir()))
