from pathlib import Path
import struct

pack_path = Path(r"X:\SteamLibrary\steamapps\workshop\content\108600\3042138819\mods\FunctionalAppliances2\42\media\texturepacks\FA.pack")
data = pack_path.read_bytes()
print("magic", data[:4])
assert data[:4] == b"PZPK"
off = 4
version, = struct.unpack_from("<I", data, off); off += 4
print("version", version)
unk1, = struct.unpack_from("<I", data, off); off += 4
print("unk1", unk1)
name_len, = struct.unpack_from("<I", data, off); off += 4
page = data[off : off + name_len].decode("ascii"); off += name_len
print("page", page, "name_len", name_len)
count, = struct.unpack_from("<I", data, off); off += 4
print("count", count)
unk2, = struct.unpack_from("<I", data, off); off += 4
print("unk2", unk2)

for i in range(count):
    nlen, = struct.unpack_from("<I", data, off); off += 4
    name = data[off : off + nlen].decode("ascii"); off += nlen
    vals = struct.unpack_from("<8I", data, off); off += 32
    print(i, name, vals)

print("offset after sprites", off)
print("next 32", data[off : off + 32])
png = data.find(b"\x89PNG")
print("png at", png, "delta", (png - off) if png >= 0 else None)
