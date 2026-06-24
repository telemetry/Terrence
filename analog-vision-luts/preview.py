#!/usr/bin/env python3
"""Render a contact sheet applying each profile's LUT to a synthetic test scene
(skin patches, sky, foliage, neutrals, color ramp). Purely a visual sanity check."""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import generate_profiles as G

W, H = 360, 300

def test_scene():
    img = np.zeros((H, W, 3))
    # sky gradient (top third)
    for y in range(0, 100):
        t = y / 100
        img[y, :] = np.array([0.45 + 0.1*t, 0.62 + 0.06*t, 0.85 - 0.05*t])
    # foliage / green band
    img[100:140, :] = [0.22, 0.42, 0.18]
    # skin-tone patches
    skins = [[0.86, 0.66, 0.54], [0.74, 0.52, 0.42], [0.55, 0.38, 0.30]]
    for i, s in enumerate(skins):
        img[140:185, i*120:(i+1)*120] = s
    # neutral ramp
    for x in range(W):
        img[185:225, x] = x / (W - 1)
    # primary/secondary swatches
    sw = [[0.8,0.1,0.1],[0.1,0.6,0.2],[0.15,0.3,0.85],
          [0.9,0.8,0.1],[0.8,0.2,0.7],[0.1,0.7,0.8]]
    for i, c in enumerate(sw):
        img[225:300, i*60:(i+1)*60] = c
    return np.clip(img, 0, 1)

def apply_lut(scene, stock):
    flat = scene.reshape(-1, 3)
    return G.process(flat, stock).reshape(scene.shape)

def to_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype("uint8"))

def main():
    scene = test_scene()
    tiles = [("Original (no profile)", scene)]
    for s in G.STOCKS:
        tiles.append((s["name"], apply_lut(scene, s)))

    cols, label_h, pad = 4, 26, 8
    rows = (len(tiles) + cols - 1) // cols
    tw, th = W, H + label_h
    sheet = Image.new("RGB", (cols*tw + pad*(cols+1), rows*th + pad*(rows+1)), (24, 24, 26))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        font = ImageFont.load_default()

    for i, (name, arr) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c*(tw + pad)
        y = pad + r*(th + pad)
        sheet.paste(to_img(arr), (x, y + label_h))
        draw.text((x + 4, y + 5), name, fill=(235, 235, 235), font=font)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.png")
    sheet.save(out)
    print("Wrote", out, sheet.size)

if __name__ == "__main__":
    main()
