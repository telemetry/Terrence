#!/usr/bin/env python3
"""
Analog Vision LUTs — film-emulation Lightroom/ACR camera profiles.

This script builds 10 original film-look 3D LUTs from a parametric film model
and writes each one as an Adobe Camera Raw "enhanced" .xmp profile with the
RGB look table embedded (the same on-disk format Adobe's "Create Profile"
produces from a .cube file).

Color science is original work — it reproduces the *documented character* of
each named stock (tone response, colour crosstalk, white balance, split-tone)
and uses no proprietary scan data.

The Adobe embedded-LUT encoder (binary layout + zlib + base85 + XMP template)
faithfully matches the public, reverse-engineered enhanced-profile format so
the files import directly into Lightroom Classic / CC / ACR (10.3+).

Usage:  python3 generate_profiles.py
Output: profiles/*.xmp
"""

import os
import struct
import zlib
import hashlib
import uuid as _uuid
import numpy as np

GRID = 32  # Adobe enhanced profiles cap the RGB table at 32^3
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")

# ---------------------------------------------------------------------------
# Colour-space helpers (sRGB <-> linear). The LUT is display-referred sRGB,
# the convention every photographic .cube LUT and ACR's cube import uses.
# ---------------------------------------------------------------------------

def srgb_to_linear(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1.0 / 2.4)) - 0.055)

REC709_LUMA = np.array([0.2126, 0.7152, 0.0722])

def luma(rgb):
    return rgb @ REC709_LUMA

def scurve(x, k):
    """Symmetric contrast S-curve pinned at 0 and 1, pivot 0.5. k=0 -> identity."""
    if k == 0:
        return x
    t = np.tanh(k * 0.5)
    return 0.5 + 0.5 * np.tanh(k * (x - 0.5)) / t

# ---------------------------------------------------------------------------
# Parametric film model.
#
# Pipeline per sample:
#   sRGB -> linear
#   white balance (per-channel linear gain)
#   coupler crosstalk (3x3, near-identity -> hue character / inter-layer effects)
#   saturation around Rec709 luma (linear)
#   linear -> sRGB (display referred)
#   tonal: contrast S-curve -> gamma -> black lift / white rolloff
#   split-tone: shadow + highlight tints weighted by luma
#   (monochrome stocks: spectral channel mix -> tone -> toner tint)
# ---------------------------------------------------------------------------

def process(rgb, p):
    x = srgb_to_linear(rgb)

    # white balance / overall cast (linear gains)
    x = x * np.asarray(p.get("wb", [1, 1, 1]))

    # coupler crosstalk
    mix = p.get("mix")
    if mix is not None:
        x = x @ np.asarray(mix).T
    x = np.clip(x, 0.0, None)

    if p.get("mono"):
        w = np.asarray(p.get("mono_mix", [0.299, 0.587, 0.114]))
        g = np.clip(x @ w, 0.0, 1.0)
        d = linear_to_srgb(g)[:, None].repeat(3, axis=1)
        d = scurve(d, p.get("contrast", 0.0))
        gamma = p.get("gamma", 1.0)
        if gamma != 1.0:
            d = np.clip(d, 0, 1) ** (1.0 / gamma)
        black, white = p.get("black", 0.0), p.get("white", 1.0)
        d = black + (white - black) * d
        toner = np.asarray(p.get("toner", [0, 0, 0]))
        # toner strongest in midtones/shadows, fades in highlights
        tw = (1.0 - d.mean(axis=1, keepdims=True))
        d = d + toner * tw
        return np.clip(d, 0.0, 1.0)

    # saturation in linear around luma
    sat = p.get("sat", 1.0)
    if sat != 1.0:
        l = luma(x)[:, None]
        x = l + sat * (x - l)
        x = np.clip(x, 0.0, None)

    d = linear_to_srgb(x)

    # tone
    d = scurve(d, p.get("contrast", 0.0))
    gamma = p.get("gamma", 1.0)
    if gamma != 1.0:
        d = np.clip(d, 0, 1) ** (1.0 / gamma)
    black, white = p.get("black", 0.0), p.get("white", 1.0)
    d = black + (white - black) * d

    # split tone (display space), weighted by luma
    dl = luma(np.clip(d, 0, 1))[:, None]
    sw = np.clip(1.0 - dl, 0, 1) ** p.get("shadow_falloff", 1.0)
    hw = np.clip(dl, 0, 1) ** p.get("highlight_falloff", 1.0)
    d = d + np.asarray(p.get("shadow_tint", [0, 0, 0])) * sw
    d = d + np.asarray(p.get("highlight_tint", [0, 0, 0])) * hw

    return np.clip(d, 0.0, 1.0)

# ---------------------------------------------------------------------------
# The 10 stocks. Tints are in display-sRGB units (~ +/-0.06 is a strong cast).
# ---------------------------------------------------------------------------

STOCKS = [
    {
        "file": "01_Portra_400.xmp", "name": "AV — Portra 400",
        "desc": "Kodak Portra 400: warm-neutral skin, gentle low contrast, creamy highlight rolloff.",
        "wb": [1.045, 1.0, 0.945], "sat": 0.92, "contrast": 0.55, "gamma": 1.04,
        "black": 0.012, "white": 0.985,
        "shadow_tint": [0.0, 0.006, 0.012], "highlight_tint": [0.014, 0.008, -0.006],
        "highlight_falloff": 1.6,
    },
    {
        "file": "02_Gold_200.xmp", "name": "AV — Gold 200",
        "desc": "Kodak Gold 200: nostalgic golden warmth, amber highlights, punchy mids.",
        "wb": [1.085, 1.005, 0.85], "sat": 1.06, "contrast": 0.8, "gamma": 1.02,
        "black": 0.01, "white": 0.99,
        "shadow_tint": [0.012, 0.004, -0.01], "highlight_tint": [0.03, 0.018, -0.02],
        "highlight_falloff": 1.4,
    },
    {
        "file": "03_UltraMax_400.xmp", "name": "AV — UltraMax 400",
        "desc": "Kodak UltraMax 400: consumer warmth, magenta-red lean, higher contrast & saturation.",
        "wb": [1.075, 0.99, 0.9], "sat": 1.12, "contrast": 0.95,
        "mix": [[1.03, -0.02, -0.01], [-0.015, 1.02, -0.005], [0.0, -0.015, 1.015]],
        "black": 0.014, "white": 0.99,
        "shadow_tint": [0.016, 0.0, 0.004], "highlight_tint": [0.024, 0.01, -0.012],
    },
    {
        "file": "04_ColorPlus_200.xmp", "name": "AV — ColorPlus 200",
        "desc": "Kodak ColorPlus 200: vintage muted warmth, soft contrast, yellow-green mids.",
        "wb": [1.06, 1.02, 0.86], "sat": 0.95, "contrast": 0.5, "gamma": 1.06,
        "black": 0.022, "white": 0.975,
        "shadow_tint": [0.004, 0.012, -0.008], "highlight_tint": [0.026, 0.02, -0.016],
        "highlight_falloff": 1.5,
    },
    {
        "file": "05_Kodacolor_100.xmp", "name": "AV — Kodacolor 100",
        "desc": "Kodak Kodacolor 100: classic clean Kodak warmth, balanced contrast, fine tonality.",
        "wb": [1.04, 1.0, 0.93], "sat": 1.0, "contrast": 0.72, "gamma": 1.02,
        "black": 0.01, "white": 0.99,
        "shadow_tint": [0.004, 0.006, 0.0], "highlight_tint": [0.016, 0.012, -0.008],
    },
    {
        "file": "06_Pro_400H.xmp", "name": "AV — Fuji Pro 400H",
        "desc": "Fujifilm Pro 400H: cool airy pastels, signature mint-cyan greens, lifted blacks.",
        "wb": [0.95, 1.01, 1.06], "sat": 0.88, "contrast": 0.42, "gamma": 1.05,
        "mix": [[1.0, 0.0, 0.0], [0.02, 1.01, 0.01], [0.0, 0.02, 1.0]],
        "black": 0.03, "white": 0.97,
        "shadow_tint": [-0.01, 0.008, 0.014], "highlight_tint": [-0.006, 0.006, 0.01],
        "highlight_falloff": 1.3,
    },
    {
        "file": "07_Velvia_100.xmp", "name": "AV — Velvia 100",
        "desc": "Fujifilm Velvia 100: ultra-saturated slide film, deep contrast, vivid blues & greens.",
        "wb": [1.0, 1.0, 1.005], "sat": 1.38, "contrast": 1.35, "gamma": 0.97,
        "mix": [[1.06, -0.04, -0.02], [-0.03, 1.05, -0.02], [-0.02, -0.04, 1.07]],
        "black": 0.0, "white": 1.0,
        "shadow_tint": [0.0, 0.002, 0.008], "highlight_tint": [0.004, 0.0, -0.002],
    },
    {
        "file": "08_HP5_Plus.xmp", "name": "AV — HP5 Plus (B&W)",
        "desc": "Ilford HP5 Plus: classic medium-contrast monochrome, smooth tonality, neutral-cool tone.",
        "mono": True, "mono_mix": [0.30, 0.59, 0.11], "contrast": 0.7, "gamma": 1.02,
        "black": 0.02, "white": 0.985, "toner": [-0.004, 0.0, 0.006],
    },
    {
        "file": "09_CineStill_800T.xmp", "name": "AV — CineStill 800T",
        "desc": "CineStill 800T: tungsten-balanced cinema look, teal shadows, warm red halation, cool cast.",
        "wb": [0.93, 0.99, 1.09], "sat": 1.04, "contrast": 0.78, "gamma": 1.03,
        "black": 0.018, "white": 0.985,
        "shadow_tint": [-0.018, 0.006, 0.022], "highlight_tint": [0.03, 0.004, -0.006],
        "shadow_falloff": 1.2, "highlight_falloff": 1.8,
    },
    {
        "file": "10_Ektar_100.xmp", "name": "AV — Ektar 100",
        "desc": "Kodak Ektar 100: vivid yet accurate, fine grain, punchy reds and clean vibrant blues.",
        "wb": [1.02, 1.0, 0.99], "sat": 1.22, "contrast": 1.05, "gamma": 0.99,
        "mix": [[1.04, -0.025, -0.015], [-0.02, 1.03, -0.01], [-0.01, -0.03, 1.04]],
        "black": 0.006, "white": 0.995,
        "shadow_tint": [0.004, 0.0, 0.006], "highlight_tint": [0.012, 0.008, -0.006],
    },
]

# ---------------------------------------------------------------------------
# Build a GRID^3 LUT as a flat sample list ordered R-fastest:
#   index = r + g*GRID + b*GRID^2   (matches the Adobe encoder below)
# ---------------------------------------------------------------------------

def build_lut(stock, grid=GRID):
    axis = np.linspace(0.0, 1.0, grid)
    # meshgrid with index = r + g*grid + b*grid^2  -> r fastest
    b, g, r = np.meshgrid(axis, axis, axis, indexing="ij")
    # the above gives shape [b,g,r]; flatten so r varies fastest
    rgb = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)
    out = process(rgb, stock)
    return out  # [grid^3, 3] in [0,1], ordered r-fastest

# ---------------------------------------------------------------------------
# Adobe enhanced-profile encoder.
# Faithful to the public reverse-engineered format: residual-from-identity
# uint16 samples, [1,1,3,size] header, footer, zlib (with 4-byte raw-size
# prefix), and the custom base85 alphabet. crs:RGBTable / crs:Table_ keyed by
# the MD5 of the *uncompressed* block.
# ---------------------------------------------------------------------------

K_ENCODE = ("0123456789abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?`'|()[]{}@%$#")

def encode_base85(data: bytes) -> str:
    padded = data + b"\x00\x00\x00"
    out = []
    remaining = len(data)
    for i in range(0, len(data), 4):
        x = struct.unpack("<I", padded[i:i + 4])[0]
        for j in range(5):
            out.append(K_ENCODE[x % 85])
            x //= 85
            if j > 0:
                remaining -= 1
                if remaining == 0:
                    break
    return "".join(out)

def build_table_block(samples, size):
    nop = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    block = bytearray()
    block.extend(struct.pack("<4I", 1, 1, 3, size))
    sample_bytes = bytearray(size * size * size * 6)
    for bi in range(size):
        for gi in range(size):
            for ri in range(size):
                cube_idx = ri + gi * size + bi * size * size
                rv, gv, bv = samples[cube_idx]
                out_idx = (ri * size * size + gi * size + bi) * 6
                tr = (int(round(rv * 65535)) - nop[ri]) & 0xFFFF
                tg = (int(round(gv * 65535)) - nop[gi]) & 0xFFFF
                tb = (int(round(bv * 65535)) - nop[bi]) & 0xFFFF
                struct.pack_into("<HHH", sample_bytes, out_idx, tr, tg, tb)
    block.extend(sample_bytes)
    block.extend(struct.pack("<3I", 0, 1, 0))
    block.extend(struct.pack("<2d", 0.0, 2.0))
    return bytes(block)

XMP_TEMPLATE = '''<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:PresetType="Look"
   crs:Cluster=""
   crs:UUID="{uuid}"
   crs:SupportsAmount="True"
   crs:SupportsColor="True"
   crs:SupportsMonochrome="True"
   crs:SupportsHighDynamicRange="True"
   crs:SupportsNormalDynamicRange="True"
   crs:SupportsSceneReferred="True"
   crs:SupportsOutputReferred="True"
   crs:RequiresRGBTables="False"
   crs:CameraModelRestriction=""
   crs:Copyright=""
   crs:ContactInfo=""
   crs:Version="14.3"
   crs:ProcessVersion="11.0"
   crs:ConvertToGrayscale="False"
   crs:RGBTable="{md5}"
   crs:Table_{md5}="{table}"
   crs:HasSettings="True">
   <crs:Name>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{name}</rdf:li>
    </rdf:Alt>
   </crs:Name>
   <crs:ShortName>
    <rdf:Alt>
     <rdf:li xml:lang="x-default"/>
    </rdf:Alt>
   </crs:ShortName>
   <crs:SortName>
    <rdf:Alt>
     <rdf:li xml:lang="x-default"/>
    </rdf:Alt>
   </crs:SortName>
   <crs:Group>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">Analog Vision</rdf:li>
    </rdf:Alt>
   </crs:Group>
   <crs:Description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{desc}</rdf:li>
    </rdf:Alt>
   </crs:Description>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
'''

def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def write_profile(stock):
    samples = build_lut(stock)
    block = build_table_block(samples, GRID)
    md5 = hashlib.md5(block).hexdigest().upper()
    compressed = struct.pack("<I", len(block)) + zlib.compress(block, 9)
    table = encode_base85(compressed)
    uid = _uuid.UUID(bytes=hashlib.md5((md5 + stock["name"]).encode()).digest()).hex.upper()
    xmp = XMP_TEMPLATE.format(
        uuid=uid, md5=md5, table=table,
        name=xml_escape(stock["name"]), desc=xml_escape(stock["desc"]))
    path = os.path.join(OUT_DIR, stock["file"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(xmp)
    return path, len(samples), len(table)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Generating {len(STOCKS)} profiles at {GRID}^3 = {GRID**3} nodes each\n")
    for s in STOCKS:
        path, n, tlen = write_profile(s)
        print(f"  ✓ {os.path.basename(path):28s}  {n} nodes  table {tlen} chars")
    print(f"\nDone -> {OUT_DIR}")

if __name__ == "__main__":
    main()
