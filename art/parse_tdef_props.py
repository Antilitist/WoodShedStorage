from pathlib import Path
import struct

data = Path(r"X:\SteamLibrary\steamapps\workshop\content\108600\2687798127\mods\WaterDispenser\media\water_dispenser.tiles").read_bytes()
off = 0

def u32():
    global off
    v = struct.unpack_from("<I", data, off)[0]
    off += 4
    return v

def line():
    global off
    start = off
    while off < len(data) and data[off] != 0x0A:
        off += 1
    s = data[start:off].decode("ascii", errors="replace")
    if off < len(data) and data[off] == 0x0A:
        off += 1
    return s

assert data[0:4] == b"tdef"; off = 4
print("ver", u32())
print("nsets", u32())
print("name", line())
print("png", line())
cols, rows, flag = u32(), u32(), u32()
print("grid", cols, rows, "flag", flag)
ntiles = u32()
print("ntiles", ntiles)
for i in range(ntiles):
    nprops = u32()
    props = []
    for _ in range(nprops):
        k = line()
        v = line()
        props.append((k, v))
    if nprops:
        print(f"tile {i}: {props}")
print("end off", off, "len", len(data), "remain", len(data) - off)
