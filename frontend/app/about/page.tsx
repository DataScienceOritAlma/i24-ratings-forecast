"use client";

// /about — Single source of truth for the navbar is now the real React <NavBar/>.
// The page body (hero, stats, models, tech, etc.) is rendered via dangerouslySetInnerHTML
// from the same content that used to live in public/index.html — we did NOT rewrite
// the content (that would be a big port with risk of drift); we just lifted the navbar
// into the React tree so it can't visually diverge from /dashboard /chat /etc.

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/NavBar";

// Body content of the original static page — everything between the old appbar and </body>.
// Kept here verbatim (light theme already applied via overrides) so we don't risk drift.
const BODY_HTML = `
<div class="scroll-progress" id="scrollProgress"></div>

<header class="hero">
  <div class="hero-bg"></div>
  <div class="container">
    <h1 class="hero-title">
      חיזוי רייטינג של תוכניות i24<br>
      <span class="hero-accent">באמצעות 19 מודלי מכונה לומדת</span>
    </h1>
    <p class="hero-subtitle">
      פרוייקט End-to-End — מ-EDA ועד מודל פרודקטיבי באוויר.<br>
      תכנון אסטרטגי של ערוץ — תוכניות עבודה, תחזית הכנסות, החלטות לוז.
    </p>
    <div class="hero-cta">
      <a href="/dashboard" class="btn btn-primary">🚀 לאפליקציה</a>
      <a href="/infographic" class="btn btn-secondary">🔮 מקסם למדע</a>
      <a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast" target="_blank" rel="noopener" class="btn btn-secondary">📂 GitHub</a>
    </div>
    <div class="hero-kpis">
      <div class="kpi"><span class="kpi-num">0.263</span><span class="kpi-lbl">MAE — המודל הזוכה</span></div>
      <div class="kpi"><span class="kpi-num">0.603</span><span class="kpi-lbl">R² · 60% מוסבר</span></div>
      <div class="kpi"><span class="kpi-num">19</span><span class="kpi-lbl">מודלים בהשוואה</span></div>
      <div class="kpi"><span class="kpi-num">10K</span><span class="kpi-lbl">שורות · שנה שלמה</span></div>
    </div>
  </div>
</header>

<section id="stats" class="section section-stats">
  <div class="container">
    <h2 class="section-title">📊 הפרוייקט במספרים</h2>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-value" data-target="10039">0</div><div class="stat-label">שורות דאטה</div><div class="stat-sub">2025-05-25 → 2026-04-18</div></div>
      <div class="stat-card"><div class="stat-value" data-target="179">0</div><div class="stat-label">תוכניות שונות</div><div class="stat-sub">חדשות, אירוח, מגזינים</div></div>
      <div class="stat-card"><div class="stat-value" data-target="19">0</div><div class="stat-label">מודלים שאומנו</div><div class="stat-sub">מ-Naive עד Stacking</div></div>
      <div class="stat-card stat-highlight"><div class="stat-value">0.263</div><div class="stat-label">MAE (זוכה)</div><div class="stat-sub">HistGradientBoosting</div></div>
      <div class="stat-card"><div class="stat-value">0.603</div><div class="stat-label">R² (זוכה)</div><div class="stat-sub">60% מההסבר</div></div>
      <div class="stat-card"><div class="stat-value" data-target="34">0</div><div class="stat-label">פיצ'רים</div><div class="stat-sub">15 גולמיים + 19 מהונדסים</div></div>
    </div>
  </div>
</section>

<section id="about" class="section">
  <div class="container">
    <h2 class="section-title">🎯 על הפרוייקט</h2>
    <div class="about-grid">
      <div class="about-card"><h3>הבעיה</h3><p>i24 NEWS משדר 24/7 עם עשרות תוכניות בלוז משתנה. ההחלטות האסטרטגיות שלהם — איזו תוכנית לחזק, מתי להוסיף, מה לבטל — תלויות בחיזוי הרייטינג של חודשים קדימה.</p></div>
      <div class="about-card"><h3>הפתרון</h3><p>מודל HistGradientBoosting שמאומן על שנת דאטה מלאה ומספק חיזוי לכל תוכנית בכל שעה, יום או חודש — עם רווח-בטחון, ויזואליזציה אינטראקטיבית, והשוואת תרחישים.</p></div>
      <div class="about-card"><h3>ההשפעה</h3><p>מנהל המחקר של i24: "כל הארגון תלוי בנתונים האלה — תחזית הכנסות, הוצאות, תוכניות עבודה ושינויי לוז". האפליקציה הופכת את ההחלטות לנתונים-מבוססים.</p></div>
    </div>
  </div>
</section>

<section id="models" class="section section-models">
  <div class="container">
    <h2 class="section-title">🏆 השוואת 19 מודלים — Top 8</h2>
    <p class="section-sub">MAE על סט הבחינה (חיתוך כרונולוגי 80/20). נמוך = טוב.</p>
    <div class="leaderboard" id="leaderboard"></div>
    <div class="viz-grid">
      <figure class="viz-card"><img src="/viz/04_model_leaderboard.png" alt="Model leaderboard"><figcaption>השוואת 19 מודלים — כל אחד אומן ונבחן באותם תנאים</figcaption></figure>
      <figure class="viz-card"><img src="/viz/03_pred_vs_actual.png" alt="Predicted vs Actual"><figcaption>חיזוי vs אמיתי — HistGradientBoosting, 500 שורות test</figcaption></figure>
      <figure class="viz-card"><img src="/viz/02_chronological_split.png" alt="Train/Test Split"><figcaption>פיצול כרונולוגי — אימון על העבר, בחינה על העתיד</figcaption></figure>
      <figure class="viz-card"><img src="/viz/08_error_by_status.png" alt="Errors by status"><figcaption>שגיאות פר סטטוס — שידור חי קשה יותר לחיזוי</figcaption></figure>
    </div>
  </div>
</section>

<section id="algorithms" class="section">
  <div class="container">
    <h2 class="section-title">🧠 איך זה עובד</h2>
    <div class="algo-grid">
      <figure class="algo-card"><img src="/viz/06_boosting.png" alt="Gradient Boosting"><figcaption><strong>Gradient Boosting</strong> — כל עץ מתקן את הטעויות של הקודמים. ככל שמוסיפים עצים, המודל מדויק יותר.</figcaption></figure>
      <figure class="algo-card"><img src="/viz/05_random_forest.png" alt="Random Forest"><figcaption><strong>Random Forest</strong> — חוכמת ההמון של 100+ עצים. כל עץ "פרוע" לבד, אבל יחד הם יציבים.</figcaption></figure>
      <figure class="algo-card"><img src="/viz/07_histogram_binning.png" alt="Histogram Binning"><figcaption><strong>Histogram Binning</strong> — הקסם של HistGB. מחלק את הדאטה ל-256 סלים → מהיר פי 10.</figcaption></figure>
      <figure class="algo-card"><img src="/viz/01_bias_variance.png" alt="Bias-Variance"><figcaption><strong>Bias-Variance Tradeoff</strong> — לא פשוט מדי, לא מורכב מדי. המודל הזוכה מאוזן.</figcaption></figure>
    </div>
  </div>
</section>

<section id="tech" class="section section-tech">
  <div class="container">
    <h2 class="section-title">⚙️ Tech Stack</h2>
    <div class="tech-grid">
      <div class="tech-cat"><h4>Data &amp; ML</h4><ul><li>Python 3.11</li><li>pandas, NumPy</li><li>scikit-learn 1.6</li><li>XGBoost, LightGBM, CatBoost</li><li>statsmodels</li></ul></div>
      <div class="tech-cat"><h4>App &amp; UI</h4><ul><li>Next.js 15 (React 19)</li><li>Tailwind CSS</li><li>Heebo Font · RTL</li><li>FastAPI (ML API)</li></ul></div>
      <div class="tech-cat"><h4>Deployment</h4><ul><li>Vercel (Frontend)</li><li>Render (FastAPI Backend)</li><li>Supabase (Postgres + Auth)</li><li>joblib · Git + GitHub CI</li></ul></div>
      <div class="tech-cat"><h4>Process</h4><ul><li>EDA → 5 שכבות מודלים</li><li>Time-aware CV</li><li>פיצול כרונולוגי 80/20</li><li>תיעוד ברציפות (CLAUDE.md, WORK_LOG.md)</li></ul></div>
    </div>
  </div>
</section>

<section id="links" class="section section-links">
  <div class="container">
    <h2 class="section-title">🔗 קישורים מהירים</h2>
    <div class="links-grid">
      <a href="/dashboard" class="link-card"><div class="link-icon">🚀</div><div class="link-title">האפליקציה החיה</div><div class="link-sub">חיזוי רייטינג בזמן אמת</div></a>
      <a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast" target="_blank" rel="noopener" class="link-card"><div class="link-icon">📂</div><div class="link-title">קוד מקור</div><div class="link-sub">GitHub Public Repo</div></a>
      <a href="/infographic" class="link-card"><div class="link-icon">🔮</div><div class="link-title">מקסם למדע — דאטה סיינס בציורים</div><div class="link-sub">23 מושגים בציור אחד · לחיצה פותחת הסבר מלא בשלוש רמות</div></a>
      <a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast/blob/main/MODEL_FAQ.md" target="_blank" rel="noopener" class="link-card"><div class="link-icon">❓</div><div class="link-title">MODEL FAQ</div><div class="link-sub">למה בחרנו HistGradientBoosting</div></a>
      <a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast/blob/main/DATA_DEEP_DIVE.md" target="_blank" rel="noopener" class="link-card"><div class="link-icon">🔬</div><div class="link-title">העמקה בדאטה</div><div class="link-sub">30 שורות מנותחות ידנית</div></a>
      <a href="https://github.com/DataScienceOritAlma/i24-ratings-forecast/blob/main/ALGORITHMS_VISUAL.md" target="_blank" rel="noopener" class="link-card"><div class="link-icon">🎨</div><div class="link-title">ויזואליזציה</div><div class="link-sub">8 תרשימים שמסבירים את האלגוריתמים</div></a>
    </div>
  </div>
</section>

<footer class="footer">
  <div class="container">
    <p>נבנה ע"י <strong>אורית עלמה זיו-נר</strong> · 2026 · Data Science Portfolio</p>
    <p class="footer-sub">Next.js · Tailwind · Vercel</p>
  </div>
</footer>
`;

// Theme overrides identical to the ones we had inline in public/index.html — keep the body light
// and the tech section non-dark, matching the app aesthetic. Scoped under #about-shell.
const SCOPED_CSS = `
#about-shell{background:#F1F5F9}
#about-shell .hero{min-height:auto;padding:48px 0 40px;background:#F1F5F9;color:#1A202C}
#about-shell .hero-bg{display:none}
#about-shell .hero-title{font-size:clamp(1.5rem,3.2vw,2.2rem);margin-bottom:14px;color:#1A202C;font-weight:900}
#about-shell .hero-accent{background:linear-gradient(135deg,#1E5DB8,#FF6B35);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
#about-shell .hero-subtitle{color:#5A6B7B;font-size:1rem;margin-bottom:24px;max-width:640px;font-weight:400}
#about-shell .hero-cta{margin-bottom:22px;gap:10px}
#about-shell .btn{padding:10px 22px;font-size:.95rem;font-weight:700;border-radius:10px;border:1px solid #E2E8F0}
#about-shell .btn-primary{background:#1E5DB8;color:#fff;border-color:#1E5DB8}
#about-shell .btn-primary:hover{background:#0A2540;color:#fff;box-shadow:0 6px 16px rgba(30,93,184,.25);transform:translateY(-1px)}
#about-shell .btn-secondary{background:#fff;color:#0A2540;border-color:#E2E8F0}
#about-shell .btn-secondary:hover{background:#fff;color:#1E5DB8;border-color:#1E5DB8;transform:translateY(-1px)}
#about-shell .hero-kpis{margin-top:14px;gap:12px}
#about-shell .kpi{background:#fff;border:1px solid #E2E8F0;box-shadow:0 1px 3px rgba(10,37,64,.04);backdrop-filter:none;-webkit-backdrop-filter:none;border-radius:14px;padding:14px 18px;min-width:140px}
#about-shell .kpi:hover{background:#fff;transform:translateY(-2px);box-shadow:0 4px 16px rgba(10,37,64,.08)}
#about-shell .kpi-num{background:none;-webkit-text-fill-color:initial;color:#1E5DB8;font-size:1.7rem}
#about-shell .kpi-lbl{color:#5A6B7B}
#about-shell .section-tech{background:#fff;color:#1A202C;border-top:1px solid #E2E8F0;border-bottom:1px solid #E2E8F0}
#about-shell .section-tech .section-title{color:#1A202C}
#about-shell .section-tech .tech-cat{background:#F1F5F9;border:1px solid #E2E8F0}
#about-shell .section-tech .tech-cat:hover{background:#fff;border-color:#1E5DB8;transform:translateY(-2px);box-shadow:0 4px 16px rgba(10,37,64,.08)}
#about-shell .section-tech .tech-cat h4{color:#1E5DB8}
#about-shell .section-tech .tech-cat li{color:#1A202C;border-bottom:1px solid #E2E8F0}
#about-shell .section-tech .tech-cat li:last-child{border-bottom:none}
`;

export default function AboutPage() {
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setEmail(data.session?.user.email ?? null);
    });

    // Load the static page's CSS so the section/card classes still style correctly.
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/style.css";
    document.head.appendChild(link);

    // Inject scoped overrides (light theme).
    const style = document.createElement("style");
    style.textContent = SCOPED_CSS;
    document.head.appendChild(style);

    // Load the static page's JS for counter animation + leaderboard fills.
    const script = document.createElement("script");
    script.src = "/script.js";
    script.async = false;
    document.body.appendChild(script);

    return () => {
      link.remove();
      style.remove();
      script.remove();
    };
  }, []);

  return (
    <main className="min-h-screen bg-slate-100">
      <NavBar email={email} title="אודות" />
      <div id="about-shell" dangerouslySetInnerHTML={{ __html: BODY_HTML }} />
    </main>
  );
}
