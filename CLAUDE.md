# terrygillespie.com

Personal site (Jekyll + GitHub Pages) plus the `airlie/` typeface microsite — a self-contained static template that will eventually move to its own repo at typejnr.com.

## Local dev

```bash
npm run dev          # whole repo at http://localhost:4000   (uses npx serve, no install)
npm run dev:airlie   # just /airlie/ at http://localhost:4001
npm run dev:py       # Python 3 fallback if Node isn't around
npm run dev:jekyll   # full Jekyll build (needs `bundle install` first)
```

Day-to-day for typeface work: `npm run dev` and visit `http://localhost:4000/airlie/` (or `?edit=1` for the in-page editor).

## Repo layout

```
.
├── index.md, archive.md       # Jekyll-rendered pages
├── _layouts/, _data/, _posts/ # Jekyll
├── product-designer/          # static subfolder (CV / portfolio)
├── nothing/                   # static subfolder (project)
└── airlie/                    # static typeface microsite — primary active project
```

## airlie/ — typeface microsite template

Pure static. No build step. Drop a `.woff2` in, edit one config file, ship.

```
airlie/
├── index.html      Single-page: hero · about · specimen · glyphs · buy
├── config.js       The ONLY file a fork needs to edit (window.TYPEFACE = {...})
├── viewer.js       FontFace loader, controls, glyph grid, drag-drop, drawer
├── styles.css      All styling
└── fonts/          Drop Airlie.woff2 here
```

### Architecture

- `config.js` declares `window.TYPEFACE` — typeface metadata, axes, OT features, sample text, accent colour, Stripe IDs.
- `viewer.js` runs as one IIFE. Sections (in order): theme + accent persistence, populate static copy, font loading, specimen controls (size/tracking/leading/italic/axes/features), glyph grid, drag-drop, Stripe mount, accent picker, edit drawer.
- `styles.css` uses `light-dark()` driven by `color-scheme`, so a single `data-theme` attr on `<html>` flips the whole palette. Accent variants per mode are derived in OKLCH and clamped against the neutral background for contrast.

### The `?edit=1` wizard

Query string or topbar "Edit" button opens a side drawer with form fields for name / tagline / designer / year / about / specimen sample / accent / Stripe IDs. Every keystroke mutates `window.TYPEFACE` in place and re-renders the affected DOM via the `PREVIEW_HOOKS` map in viewer.js. "Copy config.js" serialises the mutated object to a complete config file and writes it to the clipboard for the designer to paste back into their repo via GitHub's web editor.

### Persistence

Two localStorage keys, both per-origin:

- `airlie:theme` — `'light'` or `'dark'` (absent = follow system)
- `airlie:accent` — hex string, set by the footer accent picker or the drawer

Neither is required — the page works fine with everything cleared.

### Customer flow (planned, not all built)

1. **Use this template** on GitHub (one-click fork)
2. **Enable Pages** in repo settings (Source: main / root)
3. **Drop `.woff2`** into `airlie/fonts/Airlie.woff2` via GitHub's drag-drop
4. **`?edit=1` drawer** to fill in copy, accent, Stripe IDs → "Copy config.js" → paste over `airlie/config.js` and commit
5. **Optional**: hero carousel images, custom axes/features (still TODO)
6. **Optional**: Stripe Buy Button — paste `buyButtonId` + `publishableKey` into the Stripe section of the drawer

## Deploy

GitHub Pages serves from `main` at `terrygillespie.com`. Pushing to main triggers a Pages rebuild (~30–60s). No CI; the static files in the repo are what ships.

## Roadmap

- Hero carousel section (CSS scroll-snap) + drawer field for image list
- Empty-state nudge: when config.js still has the template's default values, show a banner pointing to `?edit=1`
- Axes / OT-features list editor in the drawer (add / remove / reorder rows)
- Drag-drop upload of font/images directly inside the drawer (still requires a paste-into-GitHub step on static Pages)
- Eventually: spin out into a clean `typejnr` repo with a marketing landing + the template

## Conventions

- No backend, no database. GitHub itself is the storage layer.
- Self-contained `airlie/` folder so it lifts cleanly when the typejnr repo gets created.
- Single-file edits over multi-file refactors. Keep `config.js` as the only thing customers touch.
- No emoji in the UI. Text labels.
