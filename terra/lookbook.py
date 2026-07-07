#!/usr/bin/env python3
"""Render the Terra lookbook: a photographic synthetic scene through every look."""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import generate_terra as T

W, H = 420, 340

def test_scene():
    """A scene built to expose look character: sky with a sun (path-to-white),
    skin gradients, foliage range, neutral ramp, night strip, swatches."""
    img = np.zeros((H, W, 3))
    yy, xx = np.mgrid[0:H, 0:W]

    # --- sky with sun glow (rows 0..110) ---
    t = (yy[:110] / 110.0)
    sky = np.stack([0.38 + 0.16 * t, 0.56 + 0.12 * t, 0.86 - 0.10 * t], axis=-1)
    cx, cy, rad = W * 0.78, 26, 90.0
    dist = np.sqrt((xx[:110] - cx) ** 2 + (yy[:110] - cy) ** 2)
    glow = np.clip(1.0 - dist / rad, 0, 1) ** 1.6
    sun = np.array([1.0, 0.94, 0.80])
    img[:110] = sky * (1 - glow[..., None]) + sun * glow[..., None]
    img[:110] = np.clip(img[:110] + glow[..., None] * 0.35, 0, 1)

    # --- foliage band with variation (110..150) ---
    fol = 0.5 + 0.5 * np.sin(xx[110:150] / 23.0)
    img[110:150] = (np.array([0.16, 0.34, 0.13])[None, None] * (1 - fol[..., None] * 0.5)
                    + np.array([0.38, 0.52, 0.20])[None, None] * (fol[..., None] * 0.5))

    # --- skin gradients: three tones, lit left->shadow right (150..200) ---
    skins = [[0.89, 0.69, 0.56], [0.72, 0.50, 0.40], [0.52, 0.36, 0.28]]
    third = W // 3
    shade = 1.0 - 0.45 * ((xx[150:200] % third) / third)
    for i, s in enumerate(skins):
        seg = (xx[150:200] >= i * third) & (xx[150:200] < (i + 1) * third)
        for c in range(3):
            img[150:200, :, c] = np.where(seg, s[c] * shade, img[150:200, :, c])

    # --- neutral ramp (200..235) ---
    img[200:235] = (xx[200:235] / (W - 1))[..., None]

    # --- night strip: dark blue street + warm window lights (235..285) ---
    img[235:285] = np.array([0.05, 0.07, 0.12])
    for i, lx in enumerate(range(30, W, 65)):
        m = (np.abs(xx[235:285] - lx) < 9) & (np.abs(yy[235:285] - 258) < 13)
        img[235:285][m] = [0.95, 0.72, 0.35] if i % 3 else [0.85, 0.85, 0.9]

    # --- swatches (285..340) ---
    sw = [[0.78, 0.12, 0.10], [0.90, 0.55, 0.10], [0.88, 0.80, 0.12],
          [0.12, 0.58, 0.22], [0.10, 0.55, 0.70], [0.14, 0.28, 0.80],
          [0.55, 0.20, 0.70], [0.85, 0.25, 0.55]]
    wsw = W // len(sw)
    for i, c in enumerate(sw):
        img[285:340, i * wsw:(i + 1) * wsw] = c
    return np.clip(img, 0, 1)

def apply_look(scene, look):
    return T.process(scene.reshape(-1, 3), look).reshape(scene.shape)

def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).round().astype("uint8"))

def main():
    scene = test_scene()
    tiles = [("Original — Apple-flat starting point", scene)]
    tiles += [(lk["name"], apply_look(scene, lk)) for lk in T.LOOKS]

    cols, lh, pad = 4, 28, 10
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W + pad * (cols + 1),
                              rows * (H + lh) + pad * (rows + 1)), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    for i, (name, arr) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (W + pad)
        y = pad + r * (H + lh + pad)
        d.text((x + 2, y + 4), name, fill=(235, 235, 235), font=font)
        sheet.paste(to_img(arr), (x, y + lh))
    out = os.path.join(T.HERE, "terra_lookbook.png")
    sheet.save(out)
    print("Wrote", out, sheet.size)

if __name__ == "__main__":
    main()
