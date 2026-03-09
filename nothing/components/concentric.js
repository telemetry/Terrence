// Copyright © 2026 Terrence Gillespie. All rights reserved.
// All ideas and prototypes remain the intellectual property of Terrence Gillespie.

// Concentric Clock — faithful port of SwiftUI layer structure
(function () {
  const container = document.getElementById('concentric-container');
  if (!container) return;

  let demo = false;
  let demoTick = 0;
  let intervalId = null;

  container.innerHTML = `
    <div class="concentric-wrapper">
      <div class="concentric-watch">
        <div class="concentric-outer" id="concentric-outer">
          <div class="concentric-inner" id="concentric-inner">
            <svg class="concentric-svg" viewBox="0 0 560 560">
              <circle cx="280" cy="280" r="250" fill="none" stroke="white" stroke-width="44" opacity="0.9"/>
            </svg>
            <div class="concentric-dot" id="concentric-dot">
              <span class="concentric-hour" id="concentric-hour"></span>
            </div>
          </div>
        </div>
      </div>
      <div class="concentric-controls">
        <button class="concentric-toggle active" id="concentric-toggle">Live</button>
        <button class="concentric-toggle" id="concentric-toggle-warp">Time Warp</button>
      </div>
    </div>
  `;

  const btnLive = document.getElementById('concentric-toggle');
  const btnWarp = document.getElementById('concentric-toggle-warp');

  const watchEl = container.querySelector('.concentric-watch');

  function setMode(isDemo) {
    demo = isDemo;
    btnLive.classList.toggle('active', !demo);
    btnWarp.classList.toggle('active-cyan', demo);

    // Kill transitions for the mode switch so the angle jump is instant
    watchEl.classList.add('no-transition');
    watchEl.classList.toggle('timewarp', demo);

    clearInterval(intervalId);
    if (demo) {
      const now = new Date();
      demoTick = now.getHours() * 60 + now.getMinutes();
      update();
      // Re-enable transitions after the instant jump
      requestAnimationFrame(() => {
        watchEl.classList.remove('no-transition');
      });
      intervalId = setInterval(update, 200);
    } else {
      update();
      requestAnimationFrame(() => {
        watchEl.classList.remove('no-transition');
      });
      intervalId = setInterval(update, 1000);
    }
  }

  btnLive.addEventListener('click', () => setMode(false));
  btnWarp.addEventListener('click', () => setMode(true));

  function update() {
    let angle, hour;

    if (demo) {
      angle = demoTick * 6;
      hour = Math.floor(demoTick / 60) % 24;
      demoTick++;
    } else {
      const now = new Date();
      angle = now.getMinutes() * 6;
      hour = now.getHours();
    }

    const outer = document.getElementById('concentric-outer');
    const inner = document.getElementById('concentric-inner');
    const dot = document.getElementById('concentric-dot');
    const hourEl = document.getElementById('concentric-hour');
    if (!outer || !inner || !dot || !hourEl) return;

    outer.style.transform = `rotate(${angle}deg)`;
    inner.style.transform = `rotate(${-angle}deg)`;
    dot.style.transform = `rotate(${angle}deg)`;
    hourEl.style.transform = `rotate(${-angle}deg)`;
    hourEl.textContent = hour;
  }

  update();
  intervalId = setInterval(update, 1000);
})();
