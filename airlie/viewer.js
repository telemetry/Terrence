(() => {
  const T = window.TYPEFACE;
  if (!T) { console.error('config.js missing'); return; }

  // ---------- Theme + accent (persisted) ----------
  const THEME_KEY  = 'airlie:theme';
  const ACCENT_KEY = 'airlie:accent';
  const root = document.documentElement;
  const mql  = window.matchMedia('(prefers-color-scheme: dark)');

  function effectiveTheme(saved) {
    if (saved === 'light' || saved === 'dark') return saved;
    return mql.matches ? 'dark' : 'light';
  }

  function applyTheme(saved) {
    if (saved === 'light' || saved === 'dark') {
      root.setAttribute('data-theme', saved);
    } else {
      root.removeAttribute('data-theme');
    }
    const eff = effectiveTheme(saved);
    document.querySelectorAll('[data-theme-set]').forEach(b => {
      b.setAttribute('aria-pressed', String(b.dataset.themeSet === eff));
    });
  }

  applyTheme(localStorage.getItem(THEME_KEY) || 'system');
  mql.addEventListener('change', () => {
    if (!localStorage.getItem(THEME_KEY)) applyTheme('system');
  });
  document.querySelectorAll('[data-theme-set]').forEach(btn => {
    btn.addEventListener('click', () => {
      const t = btn.dataset.themeSet;
      localStorage.setItem(THEME_KEY, t);
      applyTheme(t);
    });
  });

  // ---------- Populate static copy ----------
  const initialAccent = localStorage.getItem(ACCENT_KEY) || T.accent;
  if (initialAccent) root.style.setProperty('--accent-base', initialAccent);
  document.title = `${T.name} — a typeface`;
  document.getElementById('brand').textContent = T.name;
  document.getElementById('display-name').textContent = T.name;
  document.getElementById('tagline').textContent = T.tagline;
  document.getElementById('designer').textContent = T.designer;
  document.getElementById('year').textContent = T.year;
  document.getElementById('spiel-body').textContent = T.spiel;
  document.getElementById('sample').textContent = T.sampleText;

  // ---------- Font loading ----------
  // Strategy:
  //   1. Try the local fontUrl. If it loads, register it as "TYPEFACE".
  //   2. If it fails (e.g. file not committed yet), inject the Google Fonts
  //      stylesheet for the fallback family AND alias it to "TYPEFACE" so the
  //      rest of the page doesn't have to know which path we took.
  //   3. When a user drops a font, replace the "TYPEFACE" registration.

  const styleEl = document.createElement('style');
  document.head.appendChild(styleEl);

  function applyAliasedGoogleFont(family, cssUrl) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = cssUrl;
    document.head.appendChild(link);
    styleEl.textContent = `:root { --type: "${family}", Georgia, serif; }`;
  }

  async function tryLoadLocalFont() {
    if (!T.fontUrl) return false;
    try {
      const res = await fetch(T.fontUrl);
      if (!res.ok) return false;
      const buf = await res.arrayBuffer();
      const ff = new FontFace('TYPEFACE', buf);
      await ff.load();
      document.fonts.add(ff);
      styleEl.textContent = `:root { --type: "TYPEFACE", Georgia, serif; }`;
      // also parse for glyph table
      tryParseAndRenderGlyphs(buf);
      return true;
    } catch (e) {
      return false;
    }
  }

  // ---------- Specimen controls ----------
  const sample = document.getElementById('sample');
  const sizeIn = document.getElementById('size');
  const trackIn = document.getElementById('track');
  const lhIn = document.getElementById('lh');
  const italicIn = document.getElementById('italic');
  const sizeOut = document.getElementById('size-out');
  const trackOut = document.getElementById('track-out');
  const lhOut = document.getElementById('lh-out');

  const axisValues = {};
  const featureValues = {};

  function applySampleStyle() {
    sample.style.fontSize = sizeIn.value + 'px';
    sample.style.letterSpacing = (trackIn.value / 1000) + 'em';
    sample.style.lineHeight = (lhIn.value / 100).toFixed(2);
    sample.style.fontStyle = italicIn.checked ? 'italic' : 'normal';

    const variations = Object.entries(axisValues)
      .map(([tag, v]) => `"${tag}" ${v}`).join(', ');
    sample.style.fontVariationSettings = variations || 'normal';

    const enabled = Object.entries(featureValues)
      .map(([tag, on]) => `"${tag}" ${on ? 1 : 0}`).join(', ');
    sample.style.fontFeatureSettings = enabled || 'normal';

    sizeOut.textContent = sizeIn.value;
    trackOut.textContent = trackIn.value;
    lhOut.textContent = (lhIn.value / 100).toFixed(2);
  }

  [sizeIn, trackIn, lhIn, italicIn].forEach(el =>
    el.addEventListener('input', applySampleStyle));

  // Axis sliders
  const axisHost = document.getElementById('axis-controls');
  T.axes.forEach(axis => {
    axisValues[axis.tag] = axis.default;
    const label = document.createElement('label');
    label.innerHTML = `
      <span class="axis-name"><span>${axis.name} (${axis.tag})</span><output>${axis.default}</output></span>
      <input type="range" min="${axis.min}" max="${axis.max}" step="${axis.step ?? 1}" value="${axis.default}">
    `;
    const input = label.querySelector('input');
    const output = label.querySelector('output');
    input.addEventListener('input', () => {
      axisValues[axis.tag] = Number(input.value);
      output.textContent = input.value;
      applySampleStyle();
    });
    axisHost.appendChild(label);
  });

  // Feature toggles
  const featHost = document.getElementById('feature-controls');
  T.features.forEach(feat => {
    featureValues[feat.tag] = feat.default;
    const label = document.createElement('label');
    label.innerHTML = `
      <input type="checkbox" ${feat.default ? 'checked' : ''}>
      <span>${feat.name} <code>${feat.tag}</code></span>
    `;
    const input = label.querySelector('input');
    input.addEventListener('change', () => {
      featureValues[feat.tag] = input.checked;
      applySampleStyle();
    });
    featHost.appendChild(label);
  });

  applySampleStyle();

  // ---------- Glyph grid ----------
  // Default codepoint set when we don't have a parsed font (covers Basic Latin
  // + Latin-1 Supplement + common punctuation).
  const DEFAULT_RANGES = [
    { name: 'Uppercase',  ranges: [[0x41, 0x5A]] },
    { name: 'Lowercase',  ranges: [[0x61, 0x7A]] },
    { name: 'Numerals',   ranges: [[0x30, 0x39]] },
    { name: 'Punctuation',ranges: [[0x21, 0x2F], [0x3A, 0x40], [0x5B, 0x60], [0x7B, 0x7E]] },
    { name: 'Latin-1',    ranges: [[0xA1, 0xFF]] },
  ];

  const grid = document.getElementById('glyph-grid');
  const glyphsMeta = document.getElementById('glyphs-meta');

  function renderDefaultGlyphs() {
    grid.innerHTML = '';
    let count = 0;
    DEFAULT_RANGES.forEach(group => {
      const heading = document.createElement('div');
      heading.className = 'glyph-section-label';
      heading.textContent = group.name;
      grid.appendChild(heading);
      group.ranges.forEach(([lo, hi]) => {
        for (let cp = lo; cp <= hi; cp++) {
          appendGlyph(cp);
          count++;
        }
      });
    });
    glyphsMeta.textContent = `${count} codepoints · click any glyph to copy`;
  }

  function appendGlyph(codepoint) {
    const cell = document.createElement('div');
    cell.className = 'glyph';
    cell.dataset.cp = codepoint;
    const ch = String.fromCodePoint(codepoint);
    cell.innerHTML = `
      <span class="glyph__char">${ch === '<' ? '&lt;' : ch === '>' ? '&gt;' : ch === '&' ? '&amp;' : ch}</span>
      <span class="glyph__code">U+${codepoint.toString(16).toUpperCase().padStart(4, '0')}</span>
    `;
    cell.addEventListener('click', () => {
      navigator.clipboard?.writeText(ch);
      cell.classList.add('is-copied');
      setTimeout(() => cell.classList.remove('is-copied'), 800);
    });
    grid.appendChild(cell);
  }

  function tryParseAndRenderGlyphs(buf) {
    if (typeof opentype === 'undefined') return; // CDN not loaded; keep default
    try {
      const font = opentype.parse(buf);
      const codepoints = [];
      for (let i = 0; i < font.numGlyphs; i++) {
        const g = font.glyphs.get(i);
        if (typeof g.unicode === 'number') codepoints.push(g.unicode);
      }
      codepoints.sort((a, b) => a - b);
      grid.innerHTML = '';
      let lastBlock = null;
      codepoints.forEach(cp => {
        const block = blockNameFor(cp);
        if (block !== lastBlock) {
          const heading = document.createElement('div');
          heading.className = 'glyph-section-label';
          heading.textContent = block;
          grid.appendChild(heading);
          lastBlock = block;
        }
        appendGlyph(cp);
      });
      glyphsMeta.textContent = `${codepoints.length} codepoints · ${font.names.fontFamily?.en ?? 'font'} · click to copy`;
    } catch (e) {
      console.warn('opentype.js parse failed:', e);
    }
  }

  function blockNameFor(cp) {
    if (cp < 0x80) return 'Basic Latin';
    if (cp < 0x100) return 'Latin-1 Supplement';
    if (cp < 0x180) return 'Latin Extended-A';
    if (cp < 0x250) return 'Latin Extended-B';
    if (cp < 0x2B0) return 'IPA Extensions';
    if (cp < 0x300) return 'Spacing Modifiers';
    if (cp < 0x370) return 'Combining Diacritics';
    if (cp < 0x400) return 'Greek';
    if (cp < 0x500) return 'Cyrillic';
    if (cp < 0x2000) return 'Other';
    if (cp < 0x2070) return 'General Punctuation';
    if (cp < 0x20D0) return 'Superscripts & Currency';
    if (cp < 0x2200) return 'Symbols';
    if (cp < 0x2300) return 'Math Operators';
    return 'Extended';
  }

  renderDefaultGlyphs();

  // ---------- Drag & drop ----------
  const overlay = document.getElementById('drop-overlay');
  const fileInput = document.getElementById('file-input');
  document.getElementById('drop-trigger').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', e => {
    if (e.target.files[0]) loadDroppedFont(e.target.files[0]);
  });

  let dragDepth = 0;
  document.addEventListener('dragenter', e => {
    if (!hasFile(e)) return;
    e.preventDefault();
    dragDepth++;
    overlay.hidden = false;
  });
  document.addEventListener('dragover', e => { if (hasFile(e)) e.preventDefault(); });
  document.addEventListener('dragleave', e => {
    if (!hasFile(e)) return;
    dragDepth--;
    if (dragDepth <= 0) { dragDepth = 0; overlay.hidden = true; }
  });
  document.addEventListener('drop', e => {
    if (!hasFile(e)) return;
    e.preventDefault();
    dragDepth = 0;
    overlay.hidden = true;
    const f = e.dataTransfer.files[0];
    if (f) loadDroppedFont(f);
  });

  function hasFile(e) {
    return e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files');
  }

  async function loadDroppedFont(file) {
    const buf = await file.arrayBuffer();
    try {
      // Replace any prior dropped face.
      [...document.fonts].forEach(f => {
        if (f.family === 'TYPEFACE') document.fonts.delete(f);
      });
      const ff = new FontFace('TYPEFACE', buf);
      await ff.load();
      document.fonts.add(ff);
      styleEl.textContent = `:root { --type: "TYPEFACE", Georgia, serif; }`;
      // Update brand line so people remember whose font is on screen.
      document.getElementById('brand').textContent = file.name;
      tryParseAndRenderGlyphs(buf);
    } catch (e) {
      alert('Could not load that font: ' + e.message);
    }
  }

  // ---------- Stripe Buy Button ----------
  function mountStripeBuyButton() {
    const cfg = T.stripe || {};
    const section = document.getElementById('buy-section');
    const priceEl = document.getElementById('price');
    const noteEl = document.getElementById('license-note');
    const mount = document.getElementById('buy-mount');

    if (cfg.price) priceEl.textContent = cfg.price;
    if (cfg.licenseNote) noteEl.textContent = cfg.licenseNote;

    if (!cfg.buyButtonId || !cfg.publishableKey) {
      // Stub state — visible placeholder so the slot is obvious during dev.
      // Set stripe.buyButtonId + stripe.publishableKey in config.js to replace.
      mount.innerHTML = `
        <button class="buy-stub" type="button" disabled>Buy ${T.name}</button>
        <span class="buy-stub-tag">stub · configure Stripe in config.js</span>
      `;
      section.hidden = false;
      return;
    }

    // Inject Stripe Buy Button script once.
    if (!document.querySelector('script[data-stripe-buy]')) {
      const s = document.createElement('script');
      s.async = true;
      s.src = 'https://js.stripe.com/v3/buy-button.js';
      s.dataset.stripeBuy = '1';
      document.head.appendChild(s);
    }

    const btn = document.createElement('stripe-buy-button');
    btn.setAttribute('buy-button-id', cfg.buyButtonId);
    btn.setAttribute('publishable-key', cfg.publishableKey);
    mount.appendChild(btn);
    section.hidden = false;
  }
  mountStripeBuyButton();

  // ---------- Accent picker ----------
  const accentInput   = document.getElementById('accent-picker');
  const accentReadout = document.getElementById('accent-readout');
  const accentReset   = document.getElementById('accent-reset');
  const ORIGINAL_ACCENT = T.accent;

  function setAccent(hex, persist) {
    root.style.setProperty('--accent-base', hex);
    accentInput.value = hex;
    accentReadout.textContent = hex.toLowerCase();
    // Keep drawer accent input in sync
    const drawerAccent = document.querySelector('[data-field="accent"]');
    if (drawerAccent) drawerAccent.value = hex;
    if (persist) localStorage.setItem(ACCENT_KEY, hex);
  }
  setAccent(initialAccent, false);

  accentInput.addEventListener('input', e => setAccent(e.target.value, true));
  accentReset.addEventListener('click', () => {
    localStorage.removeItem(ACCENT_KEY);
    setAccent(ORIGINAL_ACCENT, false);
  });

  // ---------- Edit drawer (?edit=1) ----------
  const drawer = document.getElementById('edit-drawer');
  const editTrigger = document.getElementById('edit-trigger');
  const editClose   = document.getElementById('edit-close');

  function openDrawer() {
    drawer.hidden = false;
    document.body.classList.add('edit-open');
  }
  function closeDrawer() {
    drawer.hidden = true;
    document.body.classList.remove('edit-open');
  }
  editTrigger.addEventListener('click', openDrawer);
  editClose.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
  });

  // Open automatically when ?edit=1 is present
  if (new URLSearchParams(location.search).get('edit') === '1') openDrawer();

  // Dotted-path get/set helpers so "stripe.buyButtonId" works.
  const getPath = (obj, path) => path.split('.').reduce((o, k) => o?.[k], obj);
  function setPath(obj, path, value) {
    const parts = path.split('.');
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      if (cur[parts[i]] == null || typeof cur[parts[i]] !== 'object') cur[parts[i]] = {};
      cur = cur[parts[i]];
    }
    cur[parts[parts.length - 1]] = value;
  }

  // Re-render hooks per field. Anything not listed only updates the underlying
  // T object (and shows up when "Copy config.js" runs).
  const PREVIEW_HOOKS = {
    'name': v => {
      document.title = `${v} — a typeface`;
      document.getElementById('brand').textContent = v;
      document.getElementById('display-name').textContent = v;
      document.getElementById('buy-heading').textContent = `Get ${v}`;
    },
    'tagline':  v => { document.getElementById('tagline').textContent = v; },
    'designer': v => { document.getElementById('designer').textContent = v; },
    'year':     v => { document.getElementById('year').textContent = v; },
    'spiel':    v => { document.getElementById('spiel-body').textContent = v; },
    'sampleText': v => { document.getElementById('sample').textContent = v; },
    'accent': v => { setAccent(v, true); },
    'stripe.price':       v => { document.getElementById('price').textContent = v; },
    'stripe.licenseNote': v => { document.getElementById('license-note').textContent = v; },
    'stripe.buyButtonId':    () => mountStripeBuyButton(),
    'stripe.publishableKey': () => mountStripeBuyButton(),
  };

  // Pre-fill form fields from T.
  drawer.querySelectorAll('[data-field]').forEach(el => {
    const path = el.dataset.field;
    const value = getPath(T, path);
    if (value != null) el.value = value;
  });

  // Wire each field to mutate T + run its preview hook.
  drawer.querySelectorAll('[data-field]').forEach(el => {
    const path = el.dataset.field;
    el.addEventListener('input', () => {
      let v = el.value;
      if (el.type === 'number') v = Number(v);
      setPath(T, path, v);
      PREVIEW_HOOKS[path]?.(v);
    });
  });

  // Copy config.js
  function generateConfigSource() {
    const data = JSON.stringify(T, (_, v) => (typeof v === 'function' ? undefined : v), 2);
    return `// Airlie — typeface microsite config.
// Generated by the in-page editor (?edit=1). Paste this whole file over
// airlie/config.js on GitHub and commit. Comments are preserved in the
// repo's history; this output keeps just the data.
window.TYPEFACE = ${data};
`;
  }

  document.getElementById('edit-copy').addEventListener('click', async function () {
    try {
      await navigator.clipboard.writeText(generateConfigSource());
      const original = this.textContent;
      this.textContent = 'Copied — paste into config.js';
      this.classList.add('is-copied');
      setTimeout(() => {
        this.textContent = original;
        this.classList.remove('is-copied');
      }, 1800);
    } catch (e) {
      alert('Could not copy automatically. Open the console for the config text.');
      console.log(generateConfigSource());
    }
  });

  // ---------- Kick off font load ----------
  tryLoadLocalFont().then(loaded => {
    if (!loaded && T.fallbackGoogleFont) {
      applyAliasedGoogleFont(T.fallbackGoogleFont.family, T.fallbackGoogleFont.cssUrl);
    }
  });
})();
