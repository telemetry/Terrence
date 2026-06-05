# Knead

Edit one letterform at a time, on a phone.

A lowercase **a** fills the screen as a live vector outline. Shape it two ways:

- **Mould it directly** — drag the anchor points and bezier handles right on the glyph.
- **Nudge it on the trackpad** — select a point, then drag on the pad in the
  bottom half of the screen. Your finger never covers the node you're shaping,
  and a sensitivity slider trades reach for precision. This is the bit that
  makes real vector editing feel possible on a touchscreen.

A standalone prototype — its own thing, not part of the Airlie / GlyphSketch
work. Pure static: no build step, no framework, no dependencies. Drop it on any
host (or open `index.html`) and it runs.

## Run it

```bash
cd knead
python3 -m http.server 4055      # then open http://localhost:4055
```

Best on a phone. Works with a mouse on the desktop too.

## What's here

```
knead/
├── index.html   markup + the bottom deck (tools, trackpad, sensitivity)
├── styles.css   dark, single-instrument look
├── app.js       the editor: render, hit-testing, moulding, trackpad, export
└── glyphs.js    baked letterforms — real cubic outlines (see below)
```

## Controls

- **Letter rail** (right edge) — switch between a e g n o r t. Edits are kept
  per letter for the session.
- **‹ ›** — step the selection from point to point (easier than tapping a tiny
  node with a thumb).
- **Point · In · Out** — choose whether the trackpad moves the anchor or one of
  its two bezier handles.
- **Smooth / Corner** — toggle the selected node. Smooth keeps the two handles
  colinear as you drag one.
- **Fill** — see it as solid type instead of an outline.
- **Undo · Reset** — per letter.
- **Export** — copy the current glyph as an `<svg>` to the clipboard.

## The letterforms

`glyphs.js` holds real cubic-bezier outlines, not hand-faked paths. They were
extracted from **Young Serif** (SIL Open Font License) with fontTools —
TrueType quadratics converted to cubics, y-flipped into SVG space, and baked to
JSON. Regenerate or add letters by editing the `LETTERS` string in
`build_glyphs.py` and running it against a Young Serif TTF.

## Idea backlog

- Add / delete points; open paths.
- Pinch-zoom and pan the stage for close work.
- Two-finger "balance" on the trackpad to move a handle pair together.
- Load a real `.woff2` (opentype.js) and edit any glyph in it.
- Persist edits to localStorage; export a whole edited set.
- Onion-skin the original outline behind the edit.
