#!/usr/bin/env python3
"""Build a stronger 'Portra 400 Pro' profile and a before/after preview."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import generate_profiles as G

PORTRA_PRO = {
    "file": "11_Portra_400_Pro.xmp", "name": "AV — Portra 400 Pro",
    "desc": "Kodak Portra 400 (stronger): warm creamy highlights, lifted film blacks, "
            "gentle teal shadows, refined low-saturation skin.",
    "wb": [1.078, 1.0, 0.895], "sat": 0.9, "contrast": 0.62, "gamma": 1.05,
    "black": 0.03, "white": 0.962,
    # softly desaturate reds/oranges so skin stays creamy, not ruddy
    "mix": [[0.985, 0.012, 0.003], [0.008, 0.99, 0.002], [0.0, 0.006, 0.994]],
    "shadow_tint": [-0.008, 0.01, 0.018], "highlight_tint": [0.032, 0.02, -0.016],
    "shadow_falloff": 1.2, "highlight_falloff": 1.4,
}

def main():
    path, n, tlen = G.write_profile(PORTRA_PRO)
    print(f"Wrote {os.path.basename(path)}  {n} nodes  table {tlen} chars")

    # before/after preview on the test scene
    import preview as P
    scene = P.test_scene()
    tiles = [
        ("Original (no profile)", scene),
        ("Portra 400 (original / mild)", P.apply_lut(scene, G.STOCKS[0])),
        ("Portra 400 Pro (stronger)", P.apply_lut(scene, PORTRA_PRO)),
    ]
    W, H, lh, pad = P.W, P.H, 26, 8
    sheet = Image.new("RGB", (3*W + pad*4, H + lh + pad*2), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    for i, (name, arr) in enumerate(tiles):
        x = pad + i*(W + pad)
        sheet.paste(P.to_img(arr), (x, lh))
        d.text((x + 4, 6), name, fill=(235, 235, 235), font=font)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portra_pro_compare.png")
    sheet.save(out)
    print("Wrote", out)

if __name__ == "__main__":
    main()
