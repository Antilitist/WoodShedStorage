from pathlib import Path
import struct

path = Path(r"X:\SteamLibrary\steamapps\workshop\content\108600\2687798127\mods\WaterDispenser\media\water_dispenser.tiles")
data = path.read_bytes()
print(data[:4], len(data))
off = 0
magic = data[off:off+4]; off += 4
print("magic", magic)
ver, = struct.unpack_from("<I", data, off); off += 4
print("ver", ver)
tileset_count, = struct.unpack_from("<I", data, off); off += 4
print("tileset_count", tileset_count)

for t in range(tileset_count):
    # null-terminated strings?
    def read_cstr():
        global off
        start = off
        while data[off] != 0 and data[off] != 0x0A:
            # water dispenser used 0x0A newline not null!
            off += 1
            if off >= len(data):
                break
        # check
        s = data[start:off]
        if off < len(data) and data[off] in (0, 0x0A):
            off += 1
        return s.decode("ascii", errors="replace")

    # Actually from ASCII dump: name\n filename\n
    def read_line():
        global off
        start = off
        while off < len(data) and data[off] != 0x0A:
            off += 1
        s = data[start:off].decode("ascii", errors="replace")
        if off < len(data) and data[off] == 0x0A:
            off += 1
        return s

    name = read_line()
    png = read_line()
    print("tileset", name, png)
    # next likely cols, rows or tile count related
    print("next hex", data[off:off+32].hex())
    # try uint32s
    a,b,c,d = struct.unpack_from("<IIII", data, off)
    print("uints", a,b,c,d)
