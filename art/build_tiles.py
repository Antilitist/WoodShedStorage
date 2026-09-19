"""
Build Wood Shed tiles.

2x2 (cells 0-7): each facing sliced into 4 cells of 128x256.
2x1 lean-to (cells 8-11): S = 2 along X (W,E); E = 2 along Y (N,S).

Pack offsets are the tight sprite's top-left inside the 128x256 cell
(vanilla Tiles2x convention), NOT a hotspot.
"""
from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(r"F:\Grok\Nipsy\WoodShedStorage")
ART = ROOT / "art"
DROP = ART / "drop"
AVEA_DROP = Path(r"F:\Grok\avea\drop")
TILES = ART / "tiles"
PREVIEW = ART / "preview"

SHEET_NAME = "woodshed_01"
CELL_W, CELL_H = 128, 256

# 2 iso tiles wide. Roof may use extra height inside the 128x256 cells.
TARGET_W = 248
MAX_H = 300

OUT_MEDIA = [
    ROOT / "42" / "media",
    ROOT / "common" / "media",
]
# Optional: set ZOMBOID_USERDIR to also copy into the live mods folder.
_z = __import__("os").environ.get("ZOMBOID_USERDIR")
if _z:
    OUT_MEDIA += [
        Path(_z) / "mods" / "WoodShedStorage" / "42" / "media",
        Path(_z) / "mods" / "WoodShedStorage" / "common" / "media",
    ]


def src_png(name: str) -> Path:
    for folder in (DROP, AVEA_DROP):
        p = folder / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def _is_checker_bg(r, g, b, a):
    if a == 0:
        return True
    mn = r if r < g else g
    if b < mn:
        mn = b
    mx = r if r > g else g
    if b > mx:
        mx = b
    if mn >= 210 and (mx - mn) <= 32:
        return True
    if mn >= 185 and (mx - mn) <= 22 and (r + g + b) >= 580:
        return True
    return False


def key_light_bg(img: Image.Image) -> Image.Image:
    """Checkerboard / near-white JPEG bg -> alpha. Shed is brown/slate."""
    img = img.convert("RGBA")
    pix = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if _is_checker_bg(r, g, b, a):
                pix[x, y] = (0, 0, 0, 0)
    # Flood from edges so leftover checker around the silhouette goes too.
    seen = set()
    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in seen:
            continue
        seen.add((x, y))
        r, g, b, a = pix[x, y]
        if a == 0:
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            continue
        if _is_checker_bg(r, g, b, a):
            pix[x, y] = (0, 0, 0, 0)
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return img


def autocrop(img: Image.Image, pad: int = 2) -> Image.Image:
    bbox = img.split()[-1].getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(img.width, x1 + pad)
    y1 = min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))


def erode_alpha(img: Image.Image, radius: int = 1) -> Image.Image:
    """Eat JPEG halo around the silhouette."""
    a = img.split()[-1].filter(ImageFilter.MinFilter(radius * 2 + 1))
    out = img.copy()
    out.putalpha(a)
    return out


def fit_building(img: Image.Image, max_w: int = TARGET_W, max_h: int = MAX_H) -> Image.Image:
    img = erode_alpha(autocrop(key_light_bg(img)))
    img = autocrop(img, pad=1)
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    if (nw, nh) != (w, h):
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img


def iso_origins():
    """
    NW tile origin (south point of diamond) at (128, 256) in a 256x320 canvas.
    X+ east = (+64, +32). Y+ south = (-64, +32).
    """
    nw = (128, 256)
    ne = (nw[0] + 64, nw[1] + 32)
    sw = (nw[0] - 64, nw[1] + 32)
    se = (nw[0], nw[1] + 64)
    return {"NW": nw, "NE": ne, "SW": sw, "SE": se}


def iso_origins_2x1_x():
    """S lean-to: 2 tiles along east-west. W then E."""
    w = (128, 256)
    e = (w[0] + 64, w[1] + 32)
    return {"W": w, "E": e}


def iso_origins_2x1_y():
    """E lean-to: 2 tiles along north-south. N (far) then S (near)."""
    n = (128, 256)
    s = (n[0] - 64, n[1] + 32)
    return {"N": n, "S": s}


def cell_top_left(origin):
    ox, oy = origin
    return ox - 64, oy - CELL_H


def point_in_diamond(px, py, south_x, south_y, slop=1.02):
    # 128x64 diamond, south point at origin. Center is 32px north of south.
    cx, cy = south_x, south_y - 32
    return (abs(px - cx) / 64.0 + abs(py - cy) / 32.0) <= slop


def owner_tile(px, py, origins, prefer=None):
    """
    Project the pixel down (screen +Y) onto the ground diamonds.
    Roof pixels (above the cluster) keep the same X, so they belong to
    whichever tile's column they stand in.
    """
    order = prefer or tuple(origins.keys())
    for dy in (0, 8, 16, 32, 48, 64, 80, 96, 112, 128, 160, 192):
        gy = py + dy
        for key in order:
            sx, sy = origins[key]
            if point_in_diamond(px, gy, sx, sy):
                return key
    best, best_d = None, 1e9
    for key, (sx, sy) in origins.items():
        d = (px - sx) ** 2 + (py - sy) ** 2
        if d < best_d:
            best, best_d = key, d
    return best


PALETTE = {
    "NW": (40, 90, 200, 160),
    "NE": (40, 180, 90, 160),
    "SW": (200, 160, 40, 160),
    "SE": (200, 50, 50, 160),
    "W": (40, 90, 200, 160),
    "E": (200, 50, 50, 160),
    "N": (40, 180, 90, 160),
    "S": (200, 160, 40, 160),
}


def slice_iso(building: Image.Image, origins: dict, order: tuple, prefer=None):
    canvas_w, canvas_h = 256, 320
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    xs = [o[0] for o in origins.values()]
    ys = [o[1] for o in origins.values()]
    cx = (min(xs) + max(xs)) / 2.0
    bottom = max(ys)
    bx = int(cx - building.width / 2)
    by = int(bottom - building.height)
    canvas.paste(building, (bx, by), building)

    cells = {k: Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)) for k in order}
    cpx = {k: cells[k].load() for k in order}
    src = canvas.load()
    debug = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    dpx = debug.load()
    for y in range(canvas_h):
        for x in range(canvas_w):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            key = owner_tile(x, y, origins, prefer or order)
            tlx, tly = cell_top_left(origins[key])
            cx2, cy2 = x - tlx, y - tly
            if 0 <= cx2 < CELL_W and 0 <= cy2 < CELL_H:
                cpx[key][cx2, cy2] = (r, g, b, a)
            dpx[x, y] = PALETTE.get(key, (180, 180, 180, 160))
    return [cells[k] for k in order], canvas, debug


def slice_facing(building: Image.Image):
    origins = iso_origins()
    order = ("NW", "NE", "SW", "SE")
    prefer = ("SE", "SW", "NE", "NW")
    return slice_iso(building, origins, order, prefer)


def tight_in_cell(cell: Image.Image):
    bbox = cell.split()[-1].getbbox()
    if not bbox:
        return cell, 0, 0, CELL_W, CELL_H
    x0, y0, x1, y1 = bbox
    tight = cell.crop((x0, y0, x1, y1))
    return tight, x0, y0, x1 - x0, y1 - y0


def write_pack(path: Path, page: str, sheet: Image.Image, entries: list[dict]):
    buf = io.BytesIO()
    sheet.save(buf, format="PNG", optimize=True)
    png = buf.getvalue()

    out = bytearray()
    out += b"PZPK"
    out += struct.pack("<I", 1)
    out += struct.pack("<I", 1)
    page_b = page.encode("ascii")
    out += struct.pack("<I", len(page_b))
    out += page_b
    out += struct.pack("<I", len(entries))
    out += struct.pack("<I", 1)

    for e in entries:
        nb = e["name"].encode("ascii")
        out += struct.pack("<I", len(nb))
        out += nb
        out += struct.pack(
            "<8I",
            e["x"], e["y"], e["w"], e["h"],
            e["ox"], e["oy"],
            CELL_W, CELL_H,
        )

    out += struct.pack("<I", len(png))
    out += png
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    print("wrote pack", path, "bytes", len(out))


def write_tiles(path: Path, sheet_name: str, cols: int, rows: int, tile_props: list[list[tuple[str, str]]]):
    out = bytearray()
    out += b"tdef"
    out += struct.pack("<I", 1)
    out += struct.pack("<I", 1)

    def wline(s: str):
        nonlocal out
        out += s.encode("ascii") + b"\n"

    wline(sheet_name)
    wline(sheet_name + ".png")
    out += struct.pack("<III", cols, rows, 1)
    ntiles = cols * rows
    out += struct.pack("<I", ntiles)
    assert len(tile_props) == ntiles
    for props in tile_props:
        out += struct.pack("<I", len(props))
        for k, v in props:
            wline(k)
            wline(v)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    print("wrote tiles", path, "bytes", len(out))


def shared_props():
    return [
        ("BlocksPlacement", ""),
        ("CustomName", "Wood Shed"),
        ("GroupName", "Wood Shed"),
        ("IsHigh", ""),
        ("Material", "Wood"),
        ("Material2", "Nails"),
        ("PickUpWeight", "100"),
        ("solidtrans", ""),
    ]


def master_props(facing: str, grid_x: int, grid_y: int):
    # No SpriteGridPos. A 4-tile grid makes IsoObjectUtils look for the 3
    # SpriteConfig siblings we delete, which hides Disassemble and WARNs.
    return shared_props() + [
        ("CanScrap", ""),
        ("Facing", facing),
        ("container", "woodshed"),
        ("ContainerCapacity", "2000"),
    ]


def slave_props(facing: str, grid_x: int, grid_y: int):
    return shared_props() + [
        ("Facing", facing),
    ]


def make_poster(src: Path, dests: list[Path], size: int = 512):
    im = Image.open(src).convert("RGB")
    # Crop off the dark margin, then pad to square.
    arr_w, arr_h = im.size
    px = im.load()
    def is_bg(x, y):
        r, g, b = px[x, y]
        return r < 50 and g < 50 and b < 50
    minx, miny, maxx, maxy = arr_w, arr_h, 0, 0
    for y in range(arr_h):
        for x in range(arr_w):
            if not is_bg(x, y):
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    pad = 24
    minx = max(0, minx - pad)
    miny = max(0, miny - pad)
    maxx = min(arr_w - 1, maxx + pad)
    maxy = min(arr_h - 1, maxy + pad)
    crop = im.crop((minx, miny, maxx + 1, maxy + 1))
    side = max(crop.width, crop.height)
    sq = Image.new("RGB", (side, side), (30, 30, 30))
    sq.paste(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    out = sq.resize((size, size), Image.Resampling.LANCZOS)
    for d in dests:
        d.parent.mkdir(parents=True, exist_ok=True)
        out.save(d, "PNG")
        print("wrote poster", d)


def make_icon(building: Image.Image, dests: list[Path], size: int):
    b = autocrop(building, pad=1)
    scale = min((size - 2) / b.width, (size - 2) / b.height)
    nw, nh = max(1, int(b.width * scale)), max(1, int(b.height * scale))
    b = b.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(b, ((size - nw) // 2, (size - nh) // 2), b)
    for d in dests:
        d.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(d, "PNG")
        print("wrote icon", d, size)


def main():
    TILES.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)

    south = fit_building(Image.open(src_png("woodshed_2x2_south.png")))
    east = fit_building(Image.open(src_png("woodshed_2x2_east.png")))
    south.save(PREVIEW / "south_fit.png")
    east.save(PREVIEW / "east_fit.png")
    print("fit south", south.size, "east", east.size)

    s_cells, s_canvas, s_dbg = slice_facing(south)
    e_cells, e_canvas, e_dbg = slice_facing(east)
    s_canvas.save(PREVIEW / "south_canvas.png")
    e_canvas.save(PREVIEW / "east_canvas.png")
    s_dbg.save(PREVIEW / "south_owner.png")
    e_dbg.save(PREVIEW / "east_owner.png")

    lean_s = fit_building(Image.open(src_png("woodshed_2x1_south.png")), max_w=220, max_h=240)
    lean_e = fit_building(Image.open(src_png("woodshed_2x1_east.png")), max_w=220, max_h=240)
    lean_s.save(PREVIEW / "lean_s_fit.png")
    lean_e.save(PREVIEW / "lean_e_fit.png")
    print("fit lean S", lean_s.size, "E", lean_e.size)

    ls_cells, ls_canvas, ls_dbg = slice_iso(
        lean_s, iso_origins_2x1_x(), ("W", "E"), prefer=("E", "W")
    )
    le_cells, le_canvas, le_dbg = slice_iso(
        lean_e, iso_origins_2x1_y(), ("N", "S"), prefer=("S", "N")
    )
    ls_canvas.save(PREVIEW / "lean_s_canvas.png")
    le_canvas.save(PREVIEW / "lean_e_canvas.png")
    ls_dbg.save(PREVIEW / "lean_s_owner.png")
    le_dbg.save(PREVIEW / "lean_e_owner.png")

    cells = s_cells + e_cells + ls_cells + le_cells  # 0-7 2x2, 8-11 lean-to
    labels = [
        "S_NW", "S_NE", "S_SW", "S_SE",
        "E_NW", "E_NE", "E_SW", "E_SE",
        "L_S_W", "L_S_E",
        "L_E_N", "L_E_S",
    ]

    # 12 cells in a row on the tileset sheet
    sheet = Image.new("RGBA", (CELL_W * 12, CELL_H), (0, 0, 0, 0))
    entries = []
    for i, cell in enumerate(cells):
        sheet.paste(cell, (i * CELL_W, 0), cell)
        tight, ox, oy, tw, th = tight_in_cell(cell)
        tight.save(TILES / f"{SHEET_NAME}_{i}.png")
        cell.save(PREVIEW / f"cell_{i}_{labels[i]}.png")
        print(f"{SHEET_NAME}_{i} {labels[i]} tight=({ox},{oy},{tw},{th})")
        entries.append({
            "name": f"{SHEET_NAME}_{i}",
            "x": i * CELL_W + ox,
            "y": oy,
            "w": tw,
            "h": th,
            "ox": ox,  # cell-position, vanilla convention
            "oy": oy,
        })

    sheet.save(TILES / f"{SHEET_NAME}.png")
    sheet.save(PREVIEW / f"{SHEET_NAME}_sheet.png")
    print("sheet", sheet.size)

    # Reassemble preview at iso offsets (should look like the original).
    for tag, group in (("S", s_cells), ("E", e_cells)):
        origins = iso_origins()
        prev = Image.new("RGBA", (256, 320), (0, 0, 0, 0))
        for cell, key in zip(group, ("NW", "NE", "SW", "SE")):
            tlx, tly = cell_top_left(origins[key])
            prev.paste(cell, (tlx, tly), cell)
        prev.save(PREVIEW / f"reassemble_{tag}.png")

    for tag, group, origins, keys in (
        ("lean_S", ls_cells, iso_origins_2x1_x(), ("W", "E")),
        ("lean_E", le_cells, iso_origins_2x1_y(), ("N", "S")),
    ):
        prev = Image.new("RGBA", (256, 320), (0, 0, 0, 0))
        for cell, key in zip(group, keys):
            tlx, tly = cell_top_left(origins[key])
            prev.paste(cell, (tlx, tly), cell)
        prev.save(PREVIEW / f"reassemble_{tag}.png")

    # 0-7: 2x2. 8-11: lean-to. No SpriteGridPos (breaks disassemble).
    tile_props = [
        slave_props("S", 0, 0),   # 0 NW
        slave_props("S", 1, 0),   # 1 NE
        master_props("S", 0, 1),  # 2 SW  S open bay
        slave_props("S", 1, 1),   # 3 SE
        slave_props("E", 0, 0),   # 4 NW
        master_props("E", 1, 0),  # 5 NE  E open bay
        slave_props("E", 0, 1),   # 6 SW
        slave_props("E", 1, 1),   # 7 SE
        slave_props("S", 0, 0),   # 8 lean S west extra
        master_props("S", 1, 0),  # 9 lean S east master / open bay
        master_props("E", 0, 0),  # 10 lean E north master / open bay
        slave_props("E", 0, 1),   # 11 lean E south extra
    ]

    for media in OUT_MEDIA:
        write_pack(media / "texturepacks" / f"{SHEET_NAME}.pack", f"{SHEET_NAME}0", sheet, entries)
        write_tiles(media / f"{SHEET_NAME}.tiles", SHEET_NAME, 12, 1, tile_props)

    poster_src = src_png("woodshed_poster.png")
    poster_dests = [
        ROOT / "42" / "poster.png",
        ROOT / "common" / "poster.png",
    ]
    make_poster(poster_src, poster_dests, 512)

    icon48 = [
        ROOT / "42" / "media" / "textures" / "Build_WoodShed.png",
        ROOT / "common" / "media" / "textures" / "Build_WoodShed.png",
    ]
    lean_icon48 = [
        ROOT / "42" / "media" / "textures" / "Build_WoodShed_LeanTo.png",
        ROOT / "common" / "media" / "textures" / "Build_WoodShed_LeanTo.png",
    ]
    make_icon(south, icon48, 48)
    make_icon(lean_s, lean_icon48, 48)

    icon_mod = [
        ROOT / "42" / "icon.png",
        ROOT / "common" / "icon.png",
    ]
    make_icon(south, icon_mod, 256)

    print("DONE")


def write_container_tiles():
    """Rewrite .tiles only. Does not touch art or packs."""
    tile_props = [
        slave_props("S", 0, 0),
        slave_props("S", 1, 0),
        master_props("S", 0, 1),
        slave_props("S", 1, 1),
        slave_props("E", 0, 0),
        master_props("E", 1, 0),
        slave_props("E", 0, 1),
        slave_props("E", 1, 1),
        slave_props("S", 0, 0),
        master_props("S", 1, 0),
        master_props("E", 0, 0),
        slave_props("E", 0, 1),
    ]
    for media in OUT_MEDIA:
        write_tiles(media / f"{SHEET_NAME}.tiles", SHEET_NAME, 12, 1, tile_props)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--tiles-only":
        write_container_tiles()
    else:
        main()
