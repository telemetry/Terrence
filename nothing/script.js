// Copyright © 2026 Terrence Gillespie. All rights reserved.
// All ideas and prototypes remain the intellectual property of Terrence Gillespie.

// ——————————————————————————————————————
// Nothing Portfolio — v1.0-beta
// ——————————————————————————————————————

// Tile hover — subtle scale on preview area
document.querySelectorAll('.tile:not(.tile--placeholder)').forEach(tile => {
  const preview = tile.querySelector('.tile-preview');
  if (!preview) return;

  tile.addEventListener('mouseenter', () => {
    preview.style.transform = 'scale(1.02)';
    preview.style.transition = 'transform 0.4s cubic-bezier(0.2, 0, 0, 1)';
  });

  tile.addEventListener('mouseleave', () => {
    preview.style.transform = 'scale(1)';
  });
});
