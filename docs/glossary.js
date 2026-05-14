// ============================================
// Glossary — interactive vanilla JS
// ============================================

(function() {
  'use strict';

  let activeCat = 'all';
  let searchQuery = '';
  const expanded = new Set();

  const $ = (id) => document.getElementById(id);
  const grid = $('grid');
  const empty = $('empty');
  const stats = $('stats');
  const search = $('search');
  const filters = $('filters');
  const topBtn = $('topBtn');

  // ===== Build category chips =====
  function buildFilters() {
    const counts = {};
    TERMS.forEach(t => { counts[t.cat] = (counts[t.cat] || 0) + 1; });

    Object.entries(CATEGORIES).forEach(([key, cat]) => {
      const btn = document.createElement('button');
      btn.className = 'g-chip';
      btn.dataset.cat = key;
      btn.innerHTML = `${cat.emoji} ${cat.name} <span class="g-chip-count">${counts[key] || 0}</span>`;
      filters.appendChild(btn);
    });

    filters.addEventListener('click', (e) => {
      const chip = e.target.closest('.g-chip');
      if (!chip) return;
      activeCat = chip.dataset.cat;
      filters.querySelectorAll('.g-chip').forEach(c => c.classList.toggle('active', c === chip));
      render();
    });
  }

  // ===== Filter logic =====
  function matchesSearch(term) {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return [term.name, term.kid, term.tech, term.where]
      .some(s => s.toLowerCase().includes(q));
  }

  function highlight(text) {
    if (!searchQuery) return text;
    const q = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`(${q})`, 'gi'), '<mark>$1</mark>');
  }

  // ===== Render =====
  function render() {
    const filtered = TERMS.filter(t =>
      (activeCat === 'all' || t.cat === activeCat) && matchesSearch(t)
    );

    stats.innerHTML = `<strong>${filtered.length}</strong> מושגים`;

    if (filtered.length === 0) {
      grid.hidden = true;
      empty.hidden = false;
      return;
    }
    grid.hidden = false;
    empty.hidden = true;

    grid.innerHTML = filtered.map((t, i) => {
      const id = `term-${TERMS.indexOf(t)}`;
      const isOpen = expanded.has(id);
      return `
        <article class="g-card ${isOpen ? 'expanded' : ''}" data-cat="${t.cat}" data-id="${id}" style="animation-delay: ${Math.min(i * 30, 600)}ms">
          <span class="g-card-bar"></span>
          <header class="g-card-head">
            <span class="g-card-emoji">${t.emoji}</span>
            <div class="g-card-info">
              <div class="g-card-name">${highlight(t.name)}</div>
              <span class="g-card-cat">${CATEGORIES[t.cat].emoji} ${CATEGORIES[t.cat].name}</span>
            </div>
            <button class="g-card-toggle" aria-label="${isOpen ? 'סגור' : 'פתח'}" aria-expanded="${isOpen}">+</button>
          </header>
          <div class="g-card-body">
            <div class="g-card-content">
              <div class="g-level g-level-kid">
                <div class="g-level-header"><span class="icon">🧒</span> הסבר לילד</div>
                <div class="g-level-text">${highlight(t.kid)}</div>
              </div>
              <div class="g-level g-level-tech">
                <div class="g-level-header"><span class="icon">📘</span> הסבר טכני</div>
                <div class="g-level-text">${highlight(t.tech)}</div>
              </div>
              <div class="g-level g-level-where">
                <div class="g-level-header"><span class="icon">🔍</span> איפה השתמשנו</div>
                <div class="g-level-text">${highlight(t.where)}</div>
              </div>
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  // ===== Click handlers =====
  grid.addEventListener('click', (e) => {
    const card = e.target.closest('.g-card');
    if (!card) return;
    const id = card.dataset.id;
    if (expanded.has(id)) {
      expanded.delete(id);
      card.classList.remove('expanded');
      const btn = card.querySelector('.g-card-toggle');
      if (btn) { btn.textContent = '+'; btn.setAttribute('aria-expanded', 'false'); }
    } else {
      expanded.add(id);
      card.classList.add('expanded');
      const btn = card.querySelector('.g-card-toggle');
      if (btn) { btn.textContent = '+'; btn.setAttribute('aria-expanded', 'true'); }
    }
  });

  // ===== Search =====
  let searchTimer;
  search.addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = e.target.value.trim();
      render();
    }, 150);
  });

  // ===== Expand / Collapse all =====
  $('expandAll').addEventListener('click', () => {
    document.querySelectorAll('.g-card').forEach(card => {
      expanded.add(card.dataset.id);
      card.classList.add('expanded');
    });
  });

  $('collapseAll').addEventListener('click', () => {
    expanded.clear();
    document.querySelectorAll('.g-card').forEach(card => card.classList.remove('expanded'));
  });

  // ===== Back to top =====
  $('topBtn').addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  window.addEventListener('scroll', () => {
    topBtn.hidden = window.scrollY < 400;
  }, { passive: true });

  // ===== Init =====
  buildFilters();
  render();
})();
