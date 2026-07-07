#!/usr/bin/env python3
"""Round-trip validator for the Terra profiles (decode xmp -> LUT -> compare)."""

import os, re, struct, zlib, hashlib
import xml.etree.ElementTree as ET
import numpy as np
import generate_terra as T

DEC = {c: i for i, c in enumerate(T.K_ENCODE)}

def decode_base85(s):
    out = bytearray()
    for i in range(0, len(s), 5):
        chunk = s[i:i + 5]
        x = 0
        for j, c in enumerate(chunk):
            x += DEC[c] * (85 ** j)
        out.extend(struct.pack("<I", x & 0xFFFFFFFF)[:len(chunk) - 1])
    return bytes(out)

def decode_lut(path, size=T.GRID):
    txt = open(path, encoding="utf-8").read()
    md5 = re.search(r'crs:RGBTable="([0-9A-Fa-f]+)"', txt).group(1)
    table = re.search(r'crs:Table_' + md5 + r'="([^"]+)"', txt).group(1)
    comp = decode_base85(table)
    raw_size = struct.unpack("<I", comp[:4])[0]
    block = zlib.decompress(comp[4:])
    assert len(block) == raw_size and hashlib.md5(block).hexdigest().upper() == md5
    assert struct.unpack("<4I", block[:16]) == (1, 1, 3, size)
    nop = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    vals = np.frombuffer(block[16:16 + size**3 * 6], dtype="<u2").reshape(size, size, size, 3)
    samples = np.zeros((size**3, 3))
    for ri in range(size):
        for gi in range(size):
            for bi in range(size):
                tr, tg, tb = vals[ri, gi, bi]
                samples[ri + gi*size + bi*size*size] = (
                    ((int(tr) + nop[ri]) & 0xFFFF) / 65535.0,
                    ((int(tg) + nop[gi]) & 0xFFFF) / 65535.0,
                    ((int(tb) + nop[bi]) & 0xFFFF) / 65535.0)
    foot = block[16 + size**3 * 6:]
    assert struct.unpack("<3I", foot[:12]) == (0, 1, 0)
    assert struct.unpack("<2d", foot[12:28]) == (0.0, 2.0)
    return samples

def main():
    for lk in T.LOOKS:
        path = os.path.join(T.OUT_DIR, lk["file"])
        ET.parse(path)  # well-formed XML
        err = np.abs(decode_lut(path) - T.build_lut(lk)).max() * 65535
        status = "OK " if err <= 1.0 else "FAIL"
        print(f"[{status}] {lk['file']:28s} round-trip max err {err:.2f} LSB")
        assert err <= 1.0
    print("\nAll Terra profiles are well-formed and round-trip cleanly.")

if __name__ == "__main__":
    main()
