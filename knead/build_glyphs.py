#!/usr/bin/env python3
# Bake letterform outlines into glyphs.js.
#
#   pip install fonttools
#   python3 build_glyphs.py
#
# Point FONT at a Young Serif TTF (SIL OFL, https://fonts.google.com/specimen/Young+Serif).
# TrueType quadratics are converted to cubics (all_cubic); app.js flips them into
# SVG (y-down) space at load time, so here we emit font-unit, y-up coordinates.

import json
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.qu2cuPen import Qu2CuPen

FONT = "YoungSerif-Regular.ttf"   # path to a Young Serif TTF
LETTERS = "aegnort"   # characterful lowercase: bowls, counters, junctions

f = TTFont(FONT)
gs = f.getGlyphSet()
cmap = f.getBestCmap()
upm = f["head"].unitsPerEm
asc = f["hhea"].ascent
desc = f["hhea"].descent
try:
    os2 = f["OS/2"]; xheight = os2.sxHeight; capheight = os2.sCapHeight
except Exception:
    xheight = int(upm*0.5); capheight = int(upm*0.7)

def third(a, b):
    return (a[0] + (b[0]-a[0])/3.0, a[1] + (b[1]-a[1])/3.0)

def extract(ch):
    g = gs[cmap[ord(ch)]]
    rec = RecordingPen()
    g.draw(Qu2CuPen(rec, max_err=1.0, all_cubic=True))
    adv = g.width if hasattr(g, "width") else gs[cmap[ord(ch)]].width
    contours = []
    cur = None        # list of anchors for current contour
    start = None      # moveTo point
    last = None       # last on-curve point
    for op, pts in rec.value:
        if op == "moveTo":
            cur = []
            start = pts[0]
            last = pts[0]
            cur.append({"x":last[0],"y":last[1],"inX":last[0],"inY":last[1],"outX":last[0],"outY":last[1],"line":False})
        elif op == "lineTo":
            end = pts[0]
            o = third(last, end); i = third(end, last)
            cur[-1]["outX"], cur[-1]["outY"] = o
            cur.append({"x":end[0],"y":end[1],"inX":i[0],"inY":i[1],"outX":end[0],"outY":end[1],"line":True})
            last = end
        elif op == "curveTo":
            c1, c2, end = pts
            cur[-1]["outX"], cur[-1]["outY"] = c1
            cur.append({"x":end[0],"y":end[1],"inX":c2[0],"inY":c2[1],"outX":end[0],"outY":end[1],"line":False})
            last = end
        elif op in ("closePath","endPath"):
            if cur and len(cur) > 1:
                # merge trailing anchor that coincides with start
                a0 = cur[0]; an = cur[-1]
                if abs(an["x"]-a0["x"])<1 and abs(an["y"]-a0["y"])<1:
                    a0["inX"], a0["inY"] = an["inX"], an["inY"]
                    a0["line"] = an["line"]
                    cur.pop()
                else:
                    # implicit straight close
                    o = third((an["x"],an["y"]),(a0["x"],a0["y"]))
                    i = third((a0["x"],a0["y"]),(an["x"],an["y"]))
                    an["outX"], an["outY"] = o
                    a0["inX"], a0["inY"] = i
                    a0["line"] = True
                if len(cur) >= 3:
                    contours.append(cur)
            cur = None
    return {"advance": adv, "contours": contours}

glyphs = {}
for ch in LETTERS:
    glyphs[ch] = extract(ch)

out = {
    "font": "Young Serif",
    "upm": upm,
    "ascent": asc, "descent": desc,
    "xHeight": xheight, "capHeight": capheight,
    "glyphs": glyphs,
}
js = "/* Baked letterform data — cubic outlines extracted from Young Serif (OFL).\n   Coordinates in font units (y-up, em=%d). Generated, do not hand-edit. */\nwindow.GLYPHS = %s;\n" % (upm, json.dumps(out, separators=(",", ":")))
import os
open(os.path.join(os.path.dirname(__file__), "glyphs.js"), "w").write(js)
# quick report
for ch,d in glyphs.items():
    print(ch, "adv",d["advance"], "contours",[len(c) for c in d["contours"]])
print("bytes", len(js))
