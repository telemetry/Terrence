// Copyright © 2026 Terrence Gillespie. All rights reserved.
// All ideas and prototypes remain the intellectual property of Terrence Gillespie.

// Sloooow — vanilla JS port of SwiftUI year clock
// A conic gradient that completes one rotation per year
(function () {
  const container = document.getElementById('sloooow-container');
  if (!container) return;

  const flavours = [
    '#ffffff', '#6ac4dc', '#ac8e68', '#66d4cf', '#ff8ff3', '#ff6b95',
    '#ff3b30', '#ff9500', '#ffcc00', '#34c759', '#5ac8fa', '#007aff',
    '#af52de', '#8e8e93',
  ];

  let currentFlavour = 1;

  function getDayOfYear() {
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 0);
    return Math.floor((now - start) / (1000 * 60 * 60 * 24));
  }

  function getTotalDays() {
    const y = new Date().getFullYear();
    return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 366 : 365;
  }

  // Build the DOM once
  const day = getDayOfYear();
  const total = getTotalDays();

  const dots = flavours.map((hex, i) =>
    `<div class="sloooow-dot${i === currentFlavour ? ' active' : ''}" style="background:${hex}" data-i="${i}"></div>`
  ).join('');

  container.innerHTML = `
    <div class="sloooow-wrapper">
      <div class="sloooow-watch">
        <div class="sloooow-face" id="sloooow-face"></div>
      </div>
      <div class="sloooow-info" id="sloooow-info"></div>
      <div class="sloooow-flavours">${dots}</div>
      <div class="sloooow-url"><a href="https://sloooow.app" target="_blank">sloooow.app</a></div>
    </div>
  `;

  function render() {
    const day = getDayOfYear();
    const total = getTotalDays();
    const angle = (day / total) * 360;
    const colour = flavours[currentFlavour];

    const face = document.getElementById('sloooow-face');
    const info = document.getElementById('sloooow-info');
    if (!face) return;

    face.style.background = `conic-gradient(from ${angle}deg, ${colour}, #000000)`;
    info.textContent = `Day ${day} of ${total}  ·  ${((day / total) * 100).toFixed(1)}%  ·  ${angle.toFixed(1)}°`;
  }

  // Dot clicks
  container.querySelectorAll('.sloooow-dot').forEach(dot => {
    dot.addEventListener('click', () => {
      currentFlavour = parseInt(dot.dataset.i);
      container.querySelectorAll('.sloooow-dot').forEach(d => d.classList.remove('active'));
      dot.classList.add('active');
      render();
    });
  });

  // Scroll to cycle
  let scrollAcc = 0;
  container.querySelector('.sloooow-watch').addEventListener('wheel', (e) => {
    e.preventDefault();
    scrollAcc += e.deltaY;
    if (Math.abs(scrollAcc) < 50) return;
    const dir = scrollAcc > 0 ? 1 : -1;
    scrollAcc = 0;
    currentFlavour = (currentFlavour + dir + flavours.length) % flavours.length;
    container.querySelectorAll('.sloooow-dot').forEach((d, i) => {
      d.classList.toggle('active', i === currentFlavour);
    });
    render();
  }, { passive: false });

  render();
  setInterval(render, 60000);
})();
