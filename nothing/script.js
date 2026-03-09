// Copyright © 2026 Terrence Gillespie. All rights reserved.
// All ideas and prototypes remain the intellectual property of Terrence Gillespie.

// ——————————————————————————————————————
// Nothing Portfolio — v1.0-beta
// ——————————————————————————————————————

// Tile hover — subtle scale on preview area (desktop only)
if (window.matchMedia('(hover: hover)').matches) {
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
}

// Lightbox
(function () {
  const lightbox = document.getElementById('lightbox');
  const lbImg = document.getElementById('lightbox-img');
  const lbTitle = document.getElementById('lightbox-title');
  const lbDesc = document.getElementById('lightbox-desc');
  const lbStack = document.getElementById('lightbox-stack');
  const lbClose = document.getElementById('lightbox-close');
  const backdrop = lightbox.querySelector('.lightbox-backdrop');

  function openLightbox(tile) {
    const fallback = tile.dataset.img;
    if (!fallback) return;

    const name = tile.querySelector('.tile-name')?.textContent || '';
    const desc = tile.dataset.detail || tile.querySelector('.tile-desc')?.textContent || '';
    const stack = tile.querySelector('.tile-stack')?.textContent || '';

    lbImg.onerror = () => { lbImg.onerror = null; lbImg.src = fallback; };
    lbImg.src = tile.dataset.imgFull || fallback;
    lbImg.alt = name;
    lbTitle.textContent = name;
    lbDesc.textContent = desc;
    lbStack.textContent = stack;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
  }

  document.querySelectorAll('.tile[data-img]').forEach(tile => {
    tile.style.cursor = 'pointer';
    tile.addEventListener('click', () => openLightbox(tile));
  });

  lbClose.addEventListener('click', closeLightbox);
  backdrop.addEventListener('click', closeLightbox);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLightbox();
  });
})();
