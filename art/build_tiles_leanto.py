"""
Build Wood Shed lean-to 2x1 tiles into woodshed_01 slots 8-11,
then rewrite pack+tiles as 12-wide sheet (0-7 = existing 2x2, 8-11 = lean-to).

S face: W + E on one row (SW + SE diamonds). Master/open = E (index 9).
E face: N + S on one column (NE + SE diamonds). Master/open = N (index 10).
"""
from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image, ImageFilter

# Reuse helpers from build_tiles
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_tiles as bt

SHEET = bt.SHEET_NAME
CELL_W, CELL_H = bt.CELL_W, bt.CELL_H
TILES = bt.TILES
PREVIEW = bt.PREVIEW
OUT_MEDIA = bt.OUT_MEDIA


def iso_origins_2x1_south():
    """West + East on the near (south) row of a 2x2 cluster."""
    o = bt.iso_origins()
    return {"W": o["SW"], "E": o["SE"]}


def iso_origins_2x1_east():
    """North + South on the east column of a 2x2 cluster."""
    o = bt.iso_origins()
    return {"N": o["NE"], "S": o["SE"]}


def owner_tile_2(px, py, origins, order):
    for dy in (0, 8, 16, 32, 48, 64, 80, 96, 112, 128, 160, 192):
        gy = py + dy
        for key in order:
            sx, sy = origins[key]
            if bt.point_in_diamond(px, gy, sx, sy):
                return key
    best, best_d = None, 1e9
    for key, (sx, sy) in origins.items():
        d = (px - sx) ** 2 + (py - sy) ** 2
        if d < best_d:
            best, best_d = key, d
    return best


def slice_2x1(building: Image.Image, origins: dict, order: tuple[str, ...]):
    canvas_w, canvas_h = 256, 320
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    bx = (canvas_w - building.width) // 2
    by = canvas_h - building.height
    canvas.paste(building, (bx, by), building)

    cells = {k: Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0)) for k in order}
    cpx = {k: cells[k].load() for k in order}
    src = canvas.load()
    debug = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    dpx = debug.load()
    colors = {
        "W": (40, 90, 200, 160),
        "E": (200, 50, 50, 160),
        "N": (40, 180, 90, 160),
        "S": (200, 160, 40, 160),
    }
    for y in range(canvas_h):
        for x in range(canvas_w):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            key = owner_tile_2(x, y, origins, order)
            tlx, tly = bt.cell_top_left(origins[key])
            cx, cy = x - tlx, y - tly
            if 0 <= cx < CELL_W and 0 <= cy < CELL_H:
                cpx[key][cx, cy] = (r, g, b, a)
            dpx[x, y] = colors.get(key, (180, 180, 180, 160))
    return [cells[k] for k in order], canvas, debug


def lean_shared():
    return [
        ("BlocksPlacement", ""),
        ("CustomName", "Wood Shed Lean-to"),
        ("GroupName", "Wood Shed Lean-to"),
        ("IsHigh", ""),
        ("Material", "Wood"),
        ("Material2", "Nails"),
        ("PickUpWeight", "80"),
        ("solidtrans", ""),
    ]


def lean_master(facing: str):
    return lean_shared() + [
        ("CanScrap", ""),
        ("Facing", facing),
        ("container", "woodshed"),
        ("ContainerCapacity", "2000"),
    ]


def lean_slave(facing: str):
    return lean_shared() + [
        ("Facing", facing),
    ]


def load_existing_2x2_cells():
    cells = []
    for i in range(8):
        p = TILES / f"{SHEET}_{i}.png"
        if not p.exists():
            raise FileNotFoundError(p)
        cells.append(Image.open(p).convert("RGBA"))
    return cells


def main():
    TILES.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)

    # Prefer freshly built 2x2 cells; if missing, run full 2x2 first.
    try:
        base = load_existing_2x2_cells()
    except FileNotFoundError:
        print("2x2 cells missing - running build_tiles.main() first")
        bt.main()
        base = load_existing_2x2_cells()

    south = bt.fit_building(Image.open(bt.src_png("woodshed_2x1_south.png")))
    east = bt.fit_building(Image.open(bt.src_png("woodshed_2x1_east.png")))
    south.save(PREVIEW / "leanto_south_fit.png")
    east.save(PREVIEW / "leanto_east_fit.png")
    print("lean-to fit south", south.size, "east", east.size)

    s_cells, s_canvas, s_dbg = slice_2x1(south, iso_origins_2x1_south(), ("W", "E"))
    e_cells, e_canvas, e_dbg = slice_2x1(east, iso_origins_2x1_east(), ("N", "S"))
    s_canvas.save(PREVIEW / "leanto_south_canvas.png")
    e_canvas.save(PREVIEW / "leanto_east_canvas.png")
    s_dbg.save(PREVIEW / "leanto_south_owner.png")
    e_dbg.save(PREVIEW / "leanto_east_owner.png")

    # Indices: 8 S_W, 9 S_E(master), 10 E_N(master), 11 E_S
    lean = s_cells + e_cells
    labels = ["LT_S_W", "LT_S_E", "LT_E_N", "LT_E_S"]

    all_cells = base + lean
    assert len(all_cells) == 12

    sheet = Image.new("RGBA", (CELL_W * 12, CELL_H), (0, 0, 0, 0))
    entries = []
    for i, cell in enumerate(all_cells):
        sheet.paste(cell, (i * CELL_W, 0), cell)
        tight, ox, oy, tw, th = bt.tight_in_cell(cell)
        tight_path = TILES / f"{SHEET}_{i}.png"
        # For 0-7 keep full cell files as before (already there); refresh all
        cell.save(TILES / f"{SHEET}_{i}.png")
        if i >= 8:
            cell.save(PREVIEW / f"cell_{i}_{labels[i - 8]}.png")
            print(f"{SHEET}_{i} {labels[i - 8]} tight=({ox},{oy},{tw},{th})")
        entries.append({
            "name": f"{SHEET}_{i}",
            "x": i * CELL_W + ox,
            "y": oy,
            "w": tw,
            "h": th,
            "ox": ox,
            "oy": oy,
        })

    sheet.save(TILES / f"{SHEET}.png")
    sheet.save(PREVIEW / f"{SHEET}_sheet.png")
    print("sheet", sheet.size)

    # Reassemble lean-to previews
    for tag, group, origins, order in (
        ("LT_S", s_cells, iso_origins_2x1_south(), ("W", "E")),
        ("LT_E", e_cells, iso_origins_2x1_east(), ("N", "S")),
    ):
        prev = Image.new("RGBA", (256, 320), (0, 0, 0, 0))
        for cell, key in zip(group, order):
            tlx, tly = bt.cell_top_left(origins[key])
            prev.paste(cell, (tlx, tly), cell)
        prev.save(PREVIEW / f"reassemble_{tag}.png")

    # Props: 0-7 unchanged from 2x2; 8-11 lean-to
    tile_props = [
        bt.slave_props("S", 0, 0),
        bt.slave_props("S", 1, 0),
        bt.master_props("S", 0, 1),
        bt.slave_props("S", 1, 1),
        bt.slave_props("E", 0, 0),
        bt.master_props("E", 1, 0),
        bt.slave_props("E", 0, 1),
        bt.slave_props("E", 1, 1),
        lean_slave("S"),    # 8 W
        lean_master("S"),   # 9 E open bay
        lean_master("E"),   # 10 N open bay
        lean_slave("E"),    # 11 S
    ]

    for media in OUT_MEDIA:
        bt.write_pack(media / "texturepacks" / f"{SHEET}.pack", f"{SHEET}0", sheet, entries)
        bt.write_tiles(media / f"{SHEET}.tiles", SHEET, 12, 1, tile_props)

    # Lean-to build icon (optional separate)
    icon_lt = [
        bt.ROOT / "42" / "media" / "textures" / "Build_WoodShed_LeanTo.png",
        bt.ROOT / "common" / "media" / "textures" / "Build_WoodShed_LeanTo.png",
    ]
    bt.make_icon(south, icon_lt, 48)

    print("LEAN-TO TILES DONE (slots 8-11)")


if __name__ == "__main__":
    main()
