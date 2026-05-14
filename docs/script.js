// ============================================
// i24 Ratings Forecast — Vanilla JS
// No frameworks, no dependencies
// ============================================

(function() {
  'use strict';

  // ===== Model leaderboard data =====
  const MODELS = [
    { rank: 1, name: 'HistGradientBoosting', mae: 0.263, class: 'gold' },
    { rank: 2, name: 'LightGBM',             mae: 0.265, class: 'silver' },
    { rank: 3, name: 'GradientBoosting',     mae: 0.270, class: 'bronze' },
    { rank: 4, name: 'CatBoost',             mae: 0.271, class: '' },
    { rank: 5, name: 'ExtraTrees',           mae: 0.272, class: '' },
    { rank: 6, name: 'Stacking (RF+XGB+LGB+Ridge)', mae: 0.272, class: '' },
    { rank: 7, name: 'RandomForest tuned',   mae: 0.280, class: '' },
    { rank: 8, name: 'XGBoost',              mae: 0.280, class: '' },
  ];

  // ===== Render leaderboard =====
  function renderLeaderboard() {
    const container = document.getElementById('leaderboard');
    if (!container) return;

    const maxMae = Math.max(...MODELS.map(m => m.mae));
    const minMae = Math.min(...MODELS.map(m => m.mae));

    const html = MODELS.map(m => {
      // Width: lower MAE = wider bar
      const widthPct = 100 - ((m.mae - minMae) / (maxMae - minMae)) * 40;
      return `
        <div class="bar-row ${m.class}">
          <div class="bar-rank">#${m.rank}</div>
          <div class="bar-name">${m.name}</div>
          <div class="bar-track">
            <div class="bar-fill" data-width="${widthPct}">MAE: ${m.mae.toFixed(3)}</div>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = html;
  }

  // ===== Animate bars when leaderboard is in view =====
  function animateBars() {
    const bars = document.querySelectorAll('.bar-fill');
    bars.forEach(bar => {
      const width = bar.getAttribute('data-width');
      requestAnimationFrame(() => {
        bar.style.width = width + '%';
      });
    });
  }

  // ===== Count-up animation for stats =====
  function animateCounter(el) {
    const target = parseInt(el.getAttribute('data-target'), 10);
    if (!target || isNaN(target)) return;

    const duration = 1500;
    const startTime = performance.now();

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(eased * target);
      el.textContent = current.toLocaleString('he-IL');

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = target.toLocaleString('he-IL');
      }
    }

    requestAnimationFrame(update);
  }

  // ===== IntersectionObserver for animations =====
  function setupObservers() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;

        // Animate stat counters
        if (entry.target.classList.contains('stat-value')) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }

        // Animate leaderboard bars
        if (entry.target.id === 'leaderboard') {
          animateBars();
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    // Observe stat counters with data-target
    document.querySelectorAll('.stat-value[data-target]').forEach(el => {
      observer.observe(el);
    });

    // Observe leaderboard
    const leaderboard = document.getElementById('leaderboard');
    if (leaderboard) observer.observe(leaderboard);
  }

  // ===== Smooth scroll for nav links (extra robust beyond CSS) =====
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
      link.addEventListener('click', (e) => {
        const href = link.getAttribute('href');
        if (href === '#') return;
        const target = document.querySelector(href);
        if (!target) return;
        e.preventDefault();
        const top = target.getBoundingClientRect().top + window.pageYOffset - 80;
        window.scrollTo({ top, behavior: 'smooth' });
      });
    });
  }

  // ===== Init =====
  function init() {
    renderLeaderboard();
    setupObservers();
    setupSmoothScroll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
