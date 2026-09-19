from pathlib import Path
import struct
from PIL import Image
import io

pack_path = Path(r"X:\SteamLibrary\steamapps\workshop\content\108600\3042138819\mods\FunctionalAppliances2\42\media\texturepacks\FA.pack")
data = pack_path.read_bytes()
off = 4
version, unk1 = struct.unpack_from("<II", data, off); off += 8
nlen = struct.unpack_from("<I", data, off)[0]; off += 4
page = data[off:off+nlen]; off += nlen
count, unk2 = struct.unpack_from("<II", data, off); off += 8
sprites = []
for _ in range(count):
    nlen = struct.unpack_from("<I", data, off)[0]; off += 4
    name = data[off:off+nlen].decode("ascii"); off += nlen
    vals = struct.unpack_from("<8I", data, off); off += 32
    sprites.append((name, vals))

png_len = struct.unpack_from("<I", data, off)[0]; off += 4
png = data[off:off+png_len]
out = Path(r"F:\Grok\Nipsy\WoodShedStorage\art\raw\FA_sheet.png")
out.write_bytes(png)
img = Image.open(io.BytesIO(png))
print("sheet", img.size, "mode", img.mode, "png_len", png_len, "file", len(png))
for name, vals in sprites[:4]:
    print(name, vals)
