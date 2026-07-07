#!/usr/bin/env python3
"""
TERRA — an authored system of ten color looks for Lightroom / Camera Raw.

Designed for photographs that start life as Apple-processed iPhone HEICs:
Smart HDR flattens global contrast, greys the sky, and pre-boosts skin, so
every Terra look rebuilds real tonal weight and treats color with restraint
where Apple has already spent it.

Engine (per LUT sample, display-referred sRGB in/out):

  sRGB -> linear
    -> white balance (per-channel gain)
    -> AgX-lite tone: inset gamut (desat matrix) -> per-channel filmic
       sigmoid in encoded space -> outset (partial inverse). Gives the
       film "path to white": saturated colors gently desaturate as they
       brighten instead of clipping to neon, and contrast carries its own
       saturation (Hunt effect) without a saturation slider.
    -> hue-band color sculpting (8 smooth bands, like an HSL panel baked
       into the LUT): per-band hue shift / sat scale / luma scale
    -> split tone (luma-weighted shadow + highlight tints)
    -> toe & shoulder: tinted matte black lift, soft white ceiling

Monochrome looks: spectral channel mix -> sigmoid tone -> paper/toner duotone.

The .xmp container matches Adobe's enhanced-profile format (verified
importable in this project's v1): residual-from-identity uint16 32^3 table,
zlib + Adobe base85, MD5-keyed crs:Table_.
"""

import os
import struct
import zlib
import hashlib
import uuid as _uuid
import numpy as np

GRID = 32
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "profiles")

REC709 = np.array([0.2126, 0.7152, 0.0722])

# ---------------------------------------------------------------- transfer

def srgb_to_linear(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1 / 2.4)) - 0.055)

# ------------------------------------------------------------- tone engine

def desat_matrix(k):
    """Blend toward Rec709 luma by k. k=0 -> identity."""
    return (1.0 - k) * np.eye(3) + k * np.outer(np.ones(3), REC709)

def sigmoid(x, k, pivot):
    """Filmic S-curve on encoded values, pinned to (0,0)-(1,1), k>0."""
    a = np.tanh(k * (x - pivot))
    a0 = np.tanh(k * (0.0 - pivot))
    a1 = np.tanh(k * (1.0 - pivot))
    return (a - a0) / (a1 - a0)

def agx_lite(lin, contrast, pivot, inset, outset_ratio):
    """Inset gamut -> per-channel encoded sigmoid -> partial outset.

    outset_ratio < 1 re-expands more than the inset compressed, so contrast
    brings a matched saturation lift with it (dcamprof's neutral tone
    reproduction insight) while highlights still walk to white.
    """
    m_in = desat_matrix(inset)
    m_out = np.linalg.inv(desat_matrix(inset * outset_ratio))
    x = np.clip(lin @ m_in.T, 0.0, None)
    d = linear_to_srgb(x)
    d = sigmoid(d, contrast, pivot)
    x = srgb_to_linear(d)
    x = x @ m_out.T
    return np.clip(x, 0.0, None)

# --------------------------------------------------------- hue-band engine

def rgb_to_hsv(rgb):
    mx = rgb.max(axis=1)
    mn = rgb.min(axis=1)
    df = mx - mn
    h = np.zeros_like(mx)
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    m = df > 1e-12
    idx = m & (mx == r)
    h[idx] = ((g[idx] - b[idx]) / df[idx]) % 6
    idx = m & (mx == g) & (mx != r)
    h[idx] = (b[idx] - r[idx]) / df[idx] + 2
    idx = m & (mx == b) & (mx != r) & (mx != g)
    h[idx] = (r[idx] - g[idx]) / df[idx] + 4
    h = h * 60.0
    s = np.where(mx > 1e-12, df / np.maximum(mx, 1e-12), 0.0)
    return h, s, mx

def hsv_to_rgb(h, s, v):
    h = (h % 360.0) / 60.0
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=1)

# Lightroom-style band centers (degrees)
BAND_HUES = {"red": 0, "orange": 30, "yellow": 60, "green": 120,
             "aqua": 180, "blue": 225, "purple": 280, "magenta": 320}

def band_weight(h, center, width):
    d = np.abs((h - center + 180.0) % 360.0 - 180.0)
    return np.exp(-(d / width) ** 2)

def hue_band_ops(rgb, bands, global_sat=1.0, band_width=32.0):
    """bands: {name: (hue_shift_deg, sat_scale, val_scale)}."""
    h, s, v = rgb_to_hsv(np.clip(rgb, 0, 1))
    dh = np.zeros_like(h)
    ds = np.ones_like(s)
    dv = np.ones_like(v)
    for name, (hs, ss, vs) in bands.items():
        w = band_weight(h, BAND_HUES[name], band_width)
        dh += hs * w
        ds *= 1.0 + (ss - 1.0) * w
        dv *= 1.0 + (vs - 1.0) * w
    # neutrals must not swing: gate hue shift by chroma
    chroma_gate = np.clip(s * 4.0, 0.0, 1.0)
    h = h + dh * chroma_gate
    s = np.clip(s * ds * global_sat, 0.0, 1.0)
    v = np.clip(v * dv, 0.0, 1.0)
    return hsv_to_rgb(h, s, v)

# ------------------------------------------------------------ look process

def process(rgb, p):
    x = srgb_to_linear(rgb)
    x = x * np.asarray(p.get("wb", [1, 1, 1]))

    if p.get("mono"):
        w = np.asarray(p["mono_mix"], dtype=float)
        w = w / w.sum()
        g = np.clip(x @ w, 0.0, 1.0)
        d = linear_to_srgb(g)
        d = sigmoid(d, p.get("contrast", 1.8), p.get("pivot", 0.46))
        black = np.asarray(p.get("black", [0, 0, 0]), dtype=float)
        white = p.get("white", 1.0)
        d3 = d[:, None].repeat(3, axis=1)
        d3 = black + (white - black) * d3
        toner = np.asarray(p.get("toner", [0, 0, 0]))
        tw = 4.0 * d3.mean(axis=1, keepdims=True) * (1 - d3.mean(axis=1, keepdims=True))
        d3 = d3 + toner * tw  # toner strongest in mids, protects paper white & max black
        return np.clip(d3, 0.0, 1.0)

    x = agx_lite(x, p.get("contrast", 1.8), p.get("pivot", 0.455),
                 p.get("inset", 0.12), p.get("outset_ratio", 0.85))
    d = linear_to_srgb(x)

    d = hue_band_ops(d, p.get("bands", {}), p.get("sat", 1.0),
                     p.get("band_width", 32.0))

    l = (np.clip(d, 0, 1) @ REC709)[:, None]
    sw = np.clip(1.0 - l, 0, 1) ** p.get("shadow_falloff", 1.3)
    hw = np.clip(l, 0, 1) ** p.get("highlight_falloff", 1.5)
    d = d + np.asarray(p.get("shadow_tint", [0, 0, 0])) * sw
    d = d + np.asarray(p.get("highlight_tint", [0, 0, 0])) * hw

    black = np.asarray(p.get("black", [0, 0, 0]), dtype=float)
    white = p.get("white", 1.0)
    d = black + (white - black) * np.clip(d, 0, 1)
    return np.clip(d, 0.0, 1.0)

# ------------------------------------------------------------------ looks
#
# Shared DNA: filmic per-channel tone with path-to-white; skin (orange band)
# protected everywhere — sat never boosted, luminance nudged up; shadows
# lean cool while highlights lean warm (scaled per family); every color
# look carries a deliberate toe. Assertive at Amount=100 by design.

LOOKS = [
    # ----- warm family -----
    {
        "file": "Terra_01_Hearth.xmp", "name": "Terra 01 — Hearth",
        "desc": "The warm anchor. Creamy golden highlights, cool matte shadows, "
                "quiet olive greens, skin first. Portra spirit, assertive build.",
        "wb": [1.062, 1.0, 0.895], "contrast": 1.95, "pivot": 0.45,
        "inset": 0.14, "outset_ratio": 0.84, "sat": 0.97,
        "bands": {"orange": (0, 0.93, 1.05), "yellow": (-6, 0.95, 1.0),
                  "green": (-14, 0.82, 0.98), "blue": (-4, 0.88, 0.97)},
        "shadow_tint": [-0.008, 0.004, 0.014],
        "highlight_tint": [0.040, 0.022, -0.016],
        "highlight_falloff": 1.4,
        "black": [0.030, 0.032, 0.036], "white": 0.968,
    },
    {
        "file": "Terra_02_Meridian.xmp", "name": "Terra 02 — Meridian",
        "desc": "Golden-hour nostalgia. Amber light poured over everything, "
                "sunny yellows, warm matte toe. Gold 200 spirit, unapologetic.",
        "wb": [1.10, 1.01, 0.82], "contrast": 2.1, "pivot": 0.45,
        "inset": 0.13, "outset_ratio": 0.83, "sat": 1.0,
        "bands": {"red": (4, 1.05, 1.0), "orange": (0, 1.0, 1.04),
                  "yellow": (-4, 1.10, 1.02), "green": (-20, 0.85, 0.98),
                  "blue": (0, 0.92, 0.95)},
        "shadow_tint": [0.014, 0.007, -0.008],
        "highlight_tint": [0.050, 0.030, -0.028],
        "highlight_falloff": 1.3,
        "black": [0.026, 0.021, 0.013], "white": 0.975,
    },
    # ----- neutral / documentary family -----
    {
        "file": "Terra_03_Field.xmp", "name": "Terra 03 — Field",
        "desc": "Muted documentary. Restrained color, hard honest shadows, "
                "suppressed magenta, a whisper of amber in the toe. "
                "Classic Chrome spirit for street and travel.",
        "wb": [1.005, 1.0, 0.995], "contrast": 2.25, "pivot": 0.415,
        "inset": 0.11, "outset_ratio": 0.95, "sat": 0.82,
        "bands": {"orange": (0, 0.97, 1.03), "yellow": (6, 0.85, 1.0),
                  "green": (8, 0.78, 0.97), "aqua": (0, 0.85, 1.0),
                  "blue": (6, 0.85, 0.94), "magenta": (0, 0.68, 1.0),
                  "purple": (0, 0.75, 1.0)},
        "shadow_tint": [0.010, 0.005, -0.004],
        "highlight_tint": [0.004, 0.002, 0.0],
        "black": [0.010, 0.009, 0.008], "white": 0.985,
    },
    {
        "file": "Terra_04_Glasshouse.xmp", "name": "Terra 04 — Glasshouse",
        "desc": "Cool pastel air. Mint greens, lifted luminous shadows, soft "
                "cyan skies, gentle magenta skin. Pro 400H spirit, high-key.",
        "wb": [0.945, 1.0, 1.065], "contrast": 1.45, "pivot": 0.49,
        "inset": 0.12, "outset_ratio": 0.92, "sat": 0.86,
        "bands": {"orange": (2, 0.9, 1.06), "yellow": (10, 0.8, 1.04),
                  "green": (16, 0.78, 1.06), "aqua": (0, 0.9, 1.05),
                  "blue": (-6, 0.85, 1.05)},
        "shadow_tint": [-0.004, 0.008, 0.014],
        "highlight_tint": [-0.004, 0.006, 0.014],
        "highlight_falloff": 1.3,
        "black": [0.036, 0.041, 0.047], "white": 0.962,
    },
    # ----- cinematic family -----
    {
        "file": "Terra_05_Harbor.xmp", "name": "Terra 05 — Harbor",
        "desc": "Night cinema. Teal shadows against tungsten-warm highlights, "
                "protected skin, glowing signs. CineStill spirit for the city "
                "after dark and moody daylight.",
        "wb": [0.935, 0.995, 1.095], "contrast": 2.05, "pivot": 0.44,
        "inset": 0.13, "outset_ratio": 0.86, "sat": 1.0,
        "bands": {"red": (2, 1.06, 1.0), "orange": (0, 1.0, 1.05),
                  "green": (12, 0.8, 0.95), "aqua": (0, 1.08, 1.0),
                  "blue": (-4, 1.06, 0.97)},
        "shadow_tint": [-0.030, 0.010, 0.032],
        "highlight_tint": [0.046, 0.014, -0.012],
        "shadow_falloff": 1.15, "highlight_falloff": 1.6,
        "black": [0.010, 0.019, 0.027], "white": 0.982,
    },
    {
        "file": "Terra_06_Ember.xmp", "name": "Terra 06 — Ember",
        "desc": "Dense and timeless. Deep blacks, rich reds that glow without "
                "shouting, painterly weight. Kodachrome spirit.",
        "wb": [1.030, 1.0, 0.955], "contrast": 2.4, "pivot": 0.44,
        "inset": 0.16, "outset_ratio": 0.78, "sat": 1.0,
        "bands": {"red": (-3, 1.16, 0.95), "orange": (-2, 1.04, 1.0),
                  "yellow": (-8, 1.0, 0.97), "green": (-6, 0.88, 0.93),
                  "blue": (2, 1.05, 0.90)},
        "shadow_tint": [0.004, 0.001, 0.002],
        "highlight_tint": [0.020, 0.010, -0.006],
        "black": [0.004, 0.004, 0.005], "white": 0.992,
    },
    # ----- vivid family -----
    {
        "file": "Terra_07_Reef.xmp", "name": "Terra 07 — Reef",
        "desc": "Vivid and clean. Hue-accurate punch — deep blue skies, clear "
                "water, crisp reds — with skin kept honest. Ektar spirit.",
        "wb": [1.005, 1.0, 1.010], "contrast": 2.2, "pivot": 0.455,
        "inset": 0.15, "outset_ratio": 0.72, "sat": 1.02,
        "bands": {"red": (0, 1.08, 0.98), "orange": (0, 0.95, 1.04),
                  "yellow": (2, 1.05, 1.0), "green": (0, 1.02, 0.97),
                  "aqua": (0, 1.10, 1.0), "blue": (0, 1.14, 0.94)},
        "shadow_tint": [0.0, 0.001, 0.004],
        "highlight_tint": [0.010, 0.007, -0.004],
        "black": [0.006, 0.006, 0.007], "white": 0.990,
    },
    {
        "file": "Terra_08_Slate.xmp", "name": "Terra 08 — Slate",
        "desc": "Silver and severe. Bleach-bypass restraint — color pulled "
                "nearly to metal, high contrast, skin left breathing. For "
                "hard light, concrete, winter.",
        "wb": [0.99, 1.0, 1.01], "contrast": 2.55, "pivot": 0.44,
        "inset": 0.10, "outset_ratio": 1.0, "sat": 0.45,
        "bands": {"orange": (0, 1.35, 1.03), "red": (0, 1.15, 1.0),
                  "blue": (0, 0.85, 0.95)},
        "shadow_tint": [-0.004, 0.0, 0.006],
        "highlight_tint": [0.006, 0.004, 0.0],
        "black": [0.012, 0.012, 0.014], "white": 0.980,
    },
    # ----- monochrome family -----
    {
        "file": "Terra_09_Gravure.xmp", "name": "Terra 09 — Gravure",
        "desc": "Punchy monochrome. Deep blacks, bright honest highlights, "
                "red-leaning mix that darkens skies and lifts skin. "
                "Tri-X spirit for street.",
        "mono": True, "mono_mix": [0.38, 0.52, 0.10],
        "contrast": 2.5, "pivot": 0.45,
        "black": [0.005, 0.005, 0.005], "white": 0.992,
        "toner": [0.006, 0.003, -0.002],  # faint warm paper
    },
    {
        "file": "Terra_10_Vellum.xmp", "name": "Terra 10 — Vellum",
        "desc": "Calm monochrome. Long smooth tonality, gentle contrast, "
                "cool selenium cast. Acros spirit for portraits and quiet "
                "scenes.",
        "mono": True, "mono_mix": [0.26, 0.60, 0.14],
        "contrast": 1.65, "pivot": 0.47,
        "black": [0.020, 0.021, 0.024], "white": 0.972,
        "toner": [-0.004, 0.000, 0.008],  # selenium cool
    },
]

# ------------------------------------------------- LUT build + Adobe encode

def build_lut(look, grid=GRID):
    axis = np.linspace(0.0, 1.0, grid)
    b, g, r = np.meshgrid(axis, axis, axis, indexing="ij")
    rgb = np.stack([r.ravel(), g.ravel(), b.ravel()], axis=1)  # r fastest
    return process(rgb, look)

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
    sample_bytes = bytearray(size ** 3 * 6)
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
     <rdf:li xml:lang="x-default">Terra</rdf:li>
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

def write_profile(look):
    samples = build_lut(look)
    block = build_table_block(samples, GRID)
    md5 = hashlib.md5(block).hexdigest().upper()
    compressed = struct.pack("<I", len(block)) + zlib.compress(block, 9)
    table = encode_base85(compressed)
    uid = _uuid.UUID(bytes=hashlib.md5((md5 + look["name"]).encode()).digest()).hex.upper()
    xmp = XMP_TEMPLATE.format(uuid=uid, md5=md5, table=table,
                              name=xml_escape(look["name"]),
                              desc=xml_escape(look["desc"]))
    path = os.path.join(OUT_DIR, look["file"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(xmp)
    return path

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"TERRA — building {len(LOOKS)} looks at {GRID}^3\n")
    for lk in LOOKS:
        path = write_profile(lk)
        print(f"  ✓ {os.path.basename(path)}")
    print(f"\nDone -> {OUT_DIR}")

if __name__ == "__main__":
    main()
