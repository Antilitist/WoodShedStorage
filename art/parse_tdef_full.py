from pathlib import Path
import struct

path = Path(r"X:\SteamLibrary\steamapps\workshop\content\108600\2687798127\mods\WaterDispenser\media\water_dispenser.tiles")
data = bytearray(path.read_bytes())
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
    s = bytes(data[start:off]).decode("ascii", errors="replace")
    if off < len(data) and data[off] == 0x0A:
        off += 1
    return s

assert data[off:off+4] == b"tdef"; off += 4
ver = u32(); print("ver", ver)
nsets = u32(); print("nsets", nsets)
for _ in range(nsets):
    name = line(); png = line()
    cols = u32(); rows = u32()
    print(f"set {name} / {png} grid={cols}x{rows}")
    magicish = u32(); print("after grid", magicish)  # 1
    # then per-tile property blobs?
    # From hex: 40 00 00 00 = 64, then properties
    # Actually next was 64 as 4th uint - wait we already consumed: cols rows 1 64
    # Restart mentally: cols=8 rows=8 unk=1 then what?

# re-parse carefully from start of props
# After "1", next is 0x40=64. That's tile count = cols*rows.
# For EACH tile: a list of properties.

off = 4 + 4 + 4  # skip magic handled differently
# reset
off = 0
assert data[off:off+4] == b"tdef"; off += 4
print("ver", u32())
print("nsets", u32())
name = line(); png = line()
cols, rows = u32(), u32()
print(name, png, cols, rows)
flag = u32(); print("flag", flag)
# tile count explicitly? 
# Peek
print("peek", struct.unpack_from("<I", data, off)[0])

# Based on ASCII dump, each tile has props as:
# repeated: uint32 keyLen, key bytes, uint32 valLen, val bytes
# empty val for boolean flags
# until a zero keyLen? or fixed count?

def read_props_for_tile(tile_index):
    global off
    props = {}
    # Don't know terminator. Looking at dump between tiles...
    # Actually each tile starts with property count?
    return props

# Dump next 200 bytes as mixed
pos = off
chunk = data[pos:pos+200]
print(chunk[:100])
