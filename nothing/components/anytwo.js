// Copyright © 2026 Terrence Gillespie. All rights reserved.
// All ideas and prototypes remain the intellectual property of Terrence Gillespie.

// ——————————————————————————————————————
// AnyTwo — Random hole hand generator
// Midnight theme, ported from SwiftUI
// ——————————————————————————————————————

(function () {
  const container = document.getElementById('anytwo-container');
  if (!container) return;

  // Midnight theme colours
  const THEME = {
    cardBg: 'rgb(38, 38, 51)',
    hearts:   'rgb(255, 77, 102)',
    diamonds: 'rgb(77, 179, 255)',
    clubs:    'rgb(77, 255, 128)',
    spades:   'rgb(217, 217, 230)',
  };

  const SUITS = ['hearts', 'diamonds', 'clubs', 'spades'];
  const RANKS = ['A', 'K', 'Q', 'J', '10', '9', '8', '7', '6', '5', '4', '3', '2'];
  const SUIT_SYMBOLS = { hearts: '♥', diamonds: '♦', clubs: '♣', spades: '♠' };

  // Rank symbol for notation (10 → T)
  function notationRank(r) { return r === '10' ? 'T' : r; }

  // Rank value for comparison (A highest)
  function rankValue(r) {
    const order = ['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
    return order.indexOf(r);
  }

  // Build a full 52-card deck, shuffle, draw 2
  function deal() {
    const deck = [];
    for (const suit of SUITS) {
      for (const rank of RANKS) {
        deck.push({ rank, suit });
      }
    }
    // Fisher-Yates shuffle
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    return [deck[0], deck[1]];
  }

  // Classify hand into standard notation
  function classify(c1, c2) {
    const v1 = rankValue(c1.rank), v2 = rankValue(c2.rank);
    const high = v1 >= v2 ? c1 : c2;
    const low = v1 >= v2 ? c2 : c1;
    const hr = notationRank(high.rank), lr = notationRank(low.rank);
    if (high.rank === low.rank) return hr + lr;
    const suited = high.suit === low.suit;
    return hr + lr + (suited ? 's' : 'o');
  }

  // Random rotation for a card (-5 to -1 or 1 to 5)
  function cardAngle(side) {
    if (side === 'left') return -(Math.random() * 4 + 1);
    return Math.random() * 4 + 1;
  }

  // Build DOM
  container.innerHTML = `
    <div class="anytwo-wrapper">
      <div class="anytwo-widget">
        <div class="anytwo-hand">
          <div class="anytwo-card" id="anytwo-card-1"></div>
          <div class="anytwo-card" id="anytwo-card-2"></div>
        </div>
      </div>
      <button class="anytwo-deal" id="anytwo-shuffle">Deal</button>
    </div>
  `;

  const card1El = document.getElementById('anytwo-card-1');
  const card2El = document.getElementById('anytwo-card-2');
  const shuffleBtn = document.getElementById('anytwo-shuffle');

  function renderCard(el, card, side) {
    const color = THEME[card.suit];
    el.style.background = THEME.cardBg;
    el.style.transform = `rotate(${cardAngle(side)}deg)`;
    el.innerHTML = `
      <span class="anytwo-rank" style="color:${color}">${card.rank}</span>
      <span class="anytwo-suit" style="color:${color}">${SUIT_SYMBOLS[card.suit]}</span>
    `;
  }

  function dealAndRender() {
    const [c1, c2] = deal();
    // Animate out
    card1El.style.opacity = '0';
    card2El.style.opacity = '0';
    card1El.style.transform = 'rotate(0deg) scale(0.8)';
    card2El.style.transform = 'rotate(0deg) scale(0.8)';

    setTimeout(() => {
      renderCard(card1El, c1, 'left');
      renderCard(card2El, c2, 'right');
      // Animate in
      card1El.style.opacity = '1';
      card2El.style.opacity = '1';
    }, 120);
  }

  shuffleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dealAndRender();
  });

  // Initial deal
  dealAndRender();
})();
