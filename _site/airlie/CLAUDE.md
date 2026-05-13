# Airlie — typeface microsite

Self-contained static template for a typeface specimen + commerce page. Currently lives inside `terrygillespie.com` as `/airlie/`; will lift into its own `typejnr` repo unchanged when that launches.

## Local dev

From the repo root (one level up):

```bash
npm run dev:airlie   # serves just this folder at http://localhost:4001
npm run dev          # serves the parent site at http://localhost:4000/airlie/
```

Pure static — no build step, no bundler, no framework. Edit a file, refresh.

## Files

```
airlie/
├── index.html      Single-page: hero · about · specimen · glyphs · buy · footer
├── config.js       The ONLY file a fork needs to edit (window.TYPEFACE = {...})
├── viewer.js       FontFace loader, controls, glyph grid, drag-drop, drawer
├── styles.css      All styling
└── fonts/          Drop Airlie.woff2 here (gitkeep placeholder for now)
```

## How it fits together

- `config.js` declares `window.TYPEFACE` — typeface metadata, axes, OT features, sample text, accent colour, Stripe IDs, fallback Google Font.
- `viewer.js` runs as one IIFE. Sections in order:
  1. Theme + accent persistence (localStorage)
  2. Populate static copy from `T`
  3. Font loading: try `T.fontUrl` first, fall back to Google Font CSS
  4. Specimen controls — size / tracking / leading / italic / variable axes / OT features
  5. Glyph grid — default Unicode ranges, replaced by opentype.js cmap parse when a font is dropped
  6. Drag-drop document-wide font loader
  7. Stripe `<stripe-buy-button>` mount (or a stub when not configured)
  8. Footer accent picker
  9. Edit drawer (`?edit=1` or topbar Edit button)
- `styles.css` uses `light-dark()` driven by `color-scheme`. A single `data-theme` attribute on `<html>` flips the whole palette. Accent variants per mode are derived in OKLCH and clamped against the neutral background to keep contrast safe whatever colour the customer picks.

## The `?edit=1` wizard

Topbar "Edit" button or `?edit=1` query string opens a side drawer with form fields for name / tagline / designer / year / about / specimen sample / accent / Stripe IDs.

- Every keystroke mutates `window.TYPEFACE` in place and re-renders the affected DOM via the `PREVIEW_HOOKS` map in viewer.js. The page IS the live preview.
- "Copy config.js" serialises the mutated object to a complete `config.js` file and writes it to the clipboard. Designer pastes it back into their repo via GitHub's web editor and commits.
- Backdrop click + Escape close the drawer.

## Persistence

Two localStorage keys, per-origin:

- `airlie:theme` — `'light'` or `'dark'` (absent = follow system)
- `airlie:accent` — hex string, set by the footer picker or the drawer

Neither is required; the page works fine with both cleared.

## Customer flow (target)

1. **Use this template** on GitHub (one-click fork into their account)
2. **Enable Pages** in repo settings (Source: main / root)
3. **Drop `.woff2`** into `airlie/fonts/Airlie.woff2` via GitHub's drag-drop
4. **`?edit=1`** drawer to fill in copy + accent + Stripe IDs → "Copy config.js" → paste over `airlie/config.js` and commit
5. **Optional** Stripe Buy Button — paste `buyButtonId` + `publishableKey` into the Stripe section of the drawer

## Roadmap

- Hero carousel section (CSS scroll-snap) + drawer field for image list
- Empty-state nudge: when `config.js` still has the template's default values, banner pointing to `?edit=1`
- Axes / OT-features list editor in the drawer (add / remove / reorder rows)
- Drag-drop upload of font/images directly inside the drawer (still requires a paste-into-GitHub step on static Pages)
- Spin out into a clean `typejnr` repo with a marketing landing + this template

## Conventions

- No backend, no database. GitHub itself is the storage layer; the page state lives in `window.TYPEFACE` + localStorage.
- Self-contained folder. No dependency on Jekyll or anything outside `airlie/`. When the typejnr repo gets created, this folder copies in unchanged.
- Single-file edits over multi-file refactors. Keep `config.js` as the only file customers touch.
- No emoji in the UI. Text labels.
