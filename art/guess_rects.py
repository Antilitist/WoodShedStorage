from pathlib import Path
from PIL import Image, ImageDraw

sheet = Image.open(Path(r"F:\Grok\Nipsy\WoodShedStorage\art\raw\FA_sheet.png")).convert("RGBA")
sprites = [
    ("0", (93, 72, 39, 60, 80, 73, 128, 256)),
    ("1", (0, 72, 49, 40, 63, 98, 128, 256)),
    ("2", (0, 0, 51, 70, 14, 64, 128, 256)),
    ("3", (43, 141, 30, 49, 3, 95, 128, 256)),
]
out_dir = Path(r"F:\Grok\Nipsy\WoodShedStorage\art\raw\guess")
out_dir.mkdir(parents=True, exist_ok=True)

# Interpretation A: x,y,w,h,ox,oy,_,_
vis = sheet.copy()
d = ImageDraw.Draw(vis)
for name, v in sprites:
    x, y, w, h = v[0], v[1], v[2], v[3]
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=(255, 0, 0, 255))
    crop = sheet.crop((x, y, x + w, y + h))
    crop.save(out_dir / f"A_{name}.png")
vis.save(out_dir / "A_overlay.png")

# Interpretation B: ox,oy,w,h,x,y,_,_
vis = sheet.copy()
d = ImageDraw.Draw(vis)
for name, v in sprites:
    x, y, w, h = v[4], v[5], v[2], v[3]
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=(0, 255, 0, 255))
    crop = sheet.crop((x, y, x + w, y + h))
    crop.save(out_dir / f"B_{name}.png")
vis.save(out_dir / "B_overlay.png")
print("wrote", out_dir)
