// ============================================
// Infographic renderer — kid-level, all 50 terms
// Reads CATEGORIES + TERMS from glossary-data.js
// (single source of truth, no data duplication)
// ============================================

(function () {
  'use strict';

  const navEl = document.querySelector('#catNav .ig-nav-inner');
  const secWrap = document.getElementById('sections');

  // Group terms by category, preserving CATEGORIES order
  const byCat = {};
  TERMS.forEach(t => { (byCat[t.cat] = byCat[t.cat] || []).push(t); });

  Object.keys(CATEGORIES).forEach(key => {
    const meta = CATEGORIES[key];
    const terms = byCat[key] || [];
    if (!terms.length) return;

    const colorVar = `var(--cat-${key})`;

    // ---- sticky nav chip ----
    const chip = document.createElement('a');
    chip.className = 'ig-nav-chip';
    chip.href = `#sec-${key}`;
    chip.style.setProperty('--c', colorVar);
    chip.textContent = `${meta.emoji} ${meta.name} (${terms.length})`;
    navEl.appendChild(chip);

    // ---- section ----
    const sec = document.createElement('section');
    sec.className = 'ig-sec';
    sec.id = `sec-${key}`;
    sec.style.setProperty('--c', colorVar);

    const head = document.createElement('div');
    head.className = 'ig-sec-head';
    head.innerHTML =
      `<span class="ig-sec-emoji">${meta.emoji}</span>` +
      `<span class="ig-sec-name"></span>` +
      `<span class="ig-sec-count">${terms.length} מושגים</span>`;
    head.querySelector('.ig-sec-name').textContent = meta.name;
    sec.appendChild(head);

    const grid = document.createElement('div');
    grid.className = 'ig-grid';

    terms.forEach(t => {
      const card = document.createElement('article');
      card.className = 'ig-card';

      const emoji = document.createElement('div');
      emoji.className = 'ig-card-emoji';
      emoji.textContent = t.emoji || meta.emoji;

      const name = document.createElement('h3');
      name.className = 'ig-card-name';
      name.textContent = t.name;

      const kid = document.createElement('p');
      kid.className = 'ig-card-kid';
      kid.innerHTML = t.kid; // trusted: our own data file

      card.append(emoji, name, kid);
      grid.appendChild(card);
    });

    sec.appendChild(grid);
    secWrap.appendChild(sec);
  });

  // ---- print / save-as-PDF ----
  document.getElementById('printBtn')
    .addEventListener('click', () => window.print());

  // ---- back-to-top ----
  const topBtn = document.getElementById('topBtn');
  window.addEventListener('scroll', () => {
    topBtn.hidden = window.scrollY < 600;
  }, { passive: true });
  topBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
})();
