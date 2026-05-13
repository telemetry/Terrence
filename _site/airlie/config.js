// Airlie — typeface microsite config.
// This is the only file a fork needs to edit.
window.TYPEFACE = {
  name: 'Airlie',
  tagline: 'A serif for quiet evenings.',
  designer: 'Terry Gillespie',
  year: 2026,

  spiel: `Airlie is a text serif drawn in the long tail of the Aldine tradition,
    redrawn for the screen. It carries a low contrast, generous counters,
    and a humanist axis that keeps it readable down to small sizes while
    holding its character at display.`,

  // Brand accent. Pick one colour; the page derives accessible variants for
  // light & dark mode automatically (lightness is clamped against the
  // neutral backgrounds so the accent passes WCAG contrast in both).
  accent: '#b13b1f',

  // Local font file. If absent, the page falls back to fallbackGoogleFont.
  fontUrl: 'fonts/Airlie.woff2',
  fallbackGoogleFont: {
    family: 'Newsreader',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,200..800;1,6..72,200..800&display=swap',
  },

  // Variable axes. Sliders no-op for fonts that don't expose the axis.
  axes: [
    { tag: 'wght', name: 'Weight',       min: 200, max: 800, default: 400, step: 1 },
    { tag: 'opsz', name: 'Optical Size', min: 6,   max: 72,  default: 16,  step: 1 },
  ],

  // OpenType feature toggles.
  features: [
    { tag: 'liga', name: 'Standard Ligatures',       default: true  },
    { tag: 'dlig', name: 'Discretionary Ligatures',  default: false },
    { tag: 'smcp', name: 'Small Caps',               default: false },
    { tag: 'onum', name: 'Old-style Numerals',       default: false },
    { tag: 'tnum', name: 'Tabular Numerals',         default: false },
    { tag: 'ss01', name: 'Stylistic Set 01',         default: false },
  ],

  sampleText: `In the small hours of a Sunday in late autumn, when the
city has stopped pretending to be awake and the streetlights hum to
themselves, you can read a page slowly and feel the type breathe.`,

  // Commerce — Stripe Buy Button stub.
  // Create a Buy Button at https://dashboard.stripe.com/buy-buttons,
  // then drop the IDs in here. Leave null to hide the buy button.
  stripe: {
    buyButtonId: null,        // e.g. 'buy_btn_1Abc...'
    publishableKey: null,     // e.g. 'pk_live_...'
    price: '$24',             // shown as a label even if Stripe is unconfigured
    licenseNote: 'Single-user desktop & web license. Family $48. Studio $120.',
  },
};
