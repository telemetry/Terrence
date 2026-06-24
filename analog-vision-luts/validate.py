#!/usr/bin/env python3
"""Round-trip validator: decode each generated .xmp back to its LUT and verify
it matches the source color science, and that headers/encoding are well-formed."""

import os, re, struct, zlib, hashlib
import numpy as np
import generate_profiles as G

K = G.K_ENCODE
DEC = {c: i for i, c in enumerate(K)}

def decode_base85(s: str) -> bytes:
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        chunk = s[i:i + 5]
        i += 5
        x = 0
        for j, c in enumerate(chunk):
            x += DEC[c] * (85 ** j)
        nbytes = len(chunk) - 1  # chars_per_group = bytes + 1
        out.extend(struct.pack("<I", x & 0xFFFFFFFF)[:nbytes])
    return bytes(out)

def parse_xmp(path):
    txt = open(path, encoding="utf-8").read()
    md5 = re.search(r'crs:RGBTable="([0-9A-Fa-f]+)"', txt).group(1)
    table = re.search(r'crs:Table_' + md5 + r'="([^"]+)"', txt).group(1)
    return md5, table

def decode_lut(path, size=G.GRID):
    md5, table = parse_xmp(path)
    comp = decode_base85(table)
    raw_size = struct.unpack("<I", comp[:4])[0]
    block = zlib.decompress(comp[4:])
    assert len(block) == raw_size, f"size mismatch {len(block)} != {raw_size}"
    assert hashlib.md5(block).hexdigest().upper() == md5, "MD5 mismatch"
    # header
    v1, v2, dims, gp = struct.unpack("<4I", block[:16])
    assert (v1, v2, dims, gp) == (1, 1, 3, size), f"bad header {(v1,v2,dims,gp)}"
    nop = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    body = block[16:16 + size**3 * 6]
    vals = np.frombuffer(body, dtype="<u2").reshape(size, size, size, 3)  # [r,g,b,3]
    samples = np.zeros((size**3, 3))
    for ri in range(size):
        for gi in range(size):
            for bi in range(size):
                cube_idx = ri + gi * size + bi * size * size
                tr, tg, tb = vals[ri, gi, bi]
                r = ((int(tr) + nop[ri]) & 0xFFFF) / 65535.0
                g = ((int(tg) + nop[gi]) & 0xFFFF) / 65535.0
                b = ((int(tb) + nop[bi]) & 0xFFFF) / 65535.0
                samples[cube_idx] = (r, g, b)
    # verify footer
    foot = block[16 + size**3 * 6:]
    a, b3, c = struct.unpack("<3I", foot[:12])
    d1, d2 = struct.unpack("<2d", foot[12:28])
    assert (a, b3, c) == (0, 1, 0) and (d1, d2) == (0.0, 2.0), "bad footer"
    return samples

def main():
    for s in G.STOCKS:
        path = os.path.join(G.OUT_DIR, s["file"])
        decoded = decode_lut(path)
        expected = G.build_lut(s)
        err = np.abs(decoded - expected).max()
        ok = err <= 1.5 / 65535
        # spot checks at key inputs
        gp = G.GRID
        def node(r, g, b):
            return decoded[int(round(r*(gp-1))) + int(round(g*(gp-1)))*gp + int(round(b*(gp-1)))*gp*gp]
        wht = node(1, 1, 1); blk = node(0, 0, 0); gry = node(.5, .5, .5)
        flag = "OK " if ok else "FAIL"
        print(f"[{flag}] {s['file']:22s} max_err={err*65535:5.2f}LSB  "
              f"black={blk.round(3)} gray={gry.round(3)} white={wht.round(3)}")
        assert ok, f"round-trip error too large for {s['file']}"
    print("\nAll profiles round-trip cleanly and match the source color science.")

if __name__ == "__main__":
    main()
