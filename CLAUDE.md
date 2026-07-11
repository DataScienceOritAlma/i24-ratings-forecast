# CLAUDE.md — הנחיות לעבודה עם Claude בפרוייקט I24

## 📱 הודעות מהנייד — לקרוא קודם

**בתחילת כל שיחה חדשה בפרויקט הזה, קראי את הקובץ:**
`C:\Users\user\OneDrive\Claude Mobile Inbox\i24.md`

אם יש שם הוראות חדשות (מעל הקו האופקי, או שלא סומנו ✅) — תזכירי לי ותציעי לטפל בהן לפני שאנחנו ממשיכים למשימה שביקשתי בשיחה.

אם הקובץ ריק או שכל ההוראות סומנו ✅ — אל תזכירי אותו.

הקובץ יושב ב-OneDrive ומסונכרן לנייד — אני עורכת אותו בדרך באפליקציית OneDrive, וההוראות מחכות לי כשאחזור ל-VS Code.

---


## מה הפרוייקט

**המטרה (לפי מנהל המחקר של i24):**  
ניבוי רייטינג של תוכניות, עם אופק של **סוף שנה / כמה חודשים קדימה**, לתכנון אסטרטגי של הארגון.

**הערך העסקי:** תוכניות עבודה · תחזית הכנסות · תחזית הוצאות · שינויי לוז.  
*"כל הארגון תלוי בנתונים האלה."*

**אבולוציה עתידית:** מתוכנית-בודדת → רצועות (פריים) → חישובי trade-off פרסומות.

### דאטה ומידול
- נתונים: 10,039 שורות × 15 עמודות, טווח 2025-05-25 → 2026-04-18, 179 תוכניות
- שפה: Python, pandas, scikit-learn, openpyxl
- סביבה: Windows 10, PowerShell, Python 3

## קבצים מרכזיים

### דאטה
- `רשימת תוכניות.csv` — הדאטה הגולמי הראשי
- `תוכניות_מעובד.xlsx` — הדאטה המעובד עם 34 עמודות (15 מקוריות + 19 מהונדסות)
- `אירועים_מדויקים.csv` — 17 אירועים עם תאריכים מדויקים

### קוד
- `eda_script.py` — EDA + יצוא אקסל מעובד
- `model_train.py` — V1, 4 מודלים (Baseline, Ridge, RF, XGB)
- `model_train_advanced.py` — V2, tuning + hybrid + competitor lags
- `model_train_timeseries.py` — מודלי TS קלאסיים (SARIMAX, Additive)
- `model_train_all.py` — **V3, 19 מודלים** + ניתוח שגיאות מעמיק
- `retrospective_analysis.py` — ניתוח רטרוספקטיבי: HistGB מול אמת על 1,957 שורות test. מפיק `RETROSPECTIVE.md` + `retrospective_viz/`
- **`deep_analysis.py`** (שלב 75, 2026-05-30) — חקירה בעומק ברמת senior-DS: 10 ניתוחים (permutation importance, PDP/2D, cold-start, per-program profile, Mixture-of-Experts, quantile + conformal calibration, residual diagnostics + PSI, error clustering, counterfactual, bias heatmap). אידמפוטנטי. מפיק `DEEP_ANALYSIS.md` + `deep_viz/` + `deep_artifacts/`. ממצאי-מפתח: MoE גרוע יותר בכל סטטוס (-2 עד -20%, סוגר הדיון); quantile coverage 56% מכוילים-קונפורמלית ל-76% עם offsets `[-0.05,+0.26]`; counterfactual מאשר ש-event-feature מנוצל חלקית (+0.19 ממוצע מול קפיצות אמיתיות של +0.5+); PSI על פיצ'רי-זמן הוא false-alarm של הפיצול הכרונולוגי.
- **`deep_analysis_v2.py`** (שלב 81, 2026-06-06) — חלק שני של החקירה: 6 ניתוחים נוספים (Learning curve, Bootstrap MAE CI, Calibration plot, Local explanation, STL seasonality, Anomaly detection). מצרף סעיפים K-P ל-`DEEP_ANALYSIS.md` (אידמפוטנטי). ממצאי-מפתח: דאטה עדכני שווה הרבה (5% אחרונים שיפרו 0.014, יותר מ-1170 שורות לפניהן) — monthly retrain הכרחי לא קוסמטיקה; MAE = 0.30 ± 0.008 (CI 95% [0.286, 0.316]); 56% מהtest מסומן כanomaly וMAE עליהן פי 1.63 גרוע. דורש statsmodels.
- **`error_analysis_20cases.py`** (שלב 95, 2026-06-07) — הכנה למפגש מנטור 6. בוחר 20 מקרים מ-test (10 הצלחות + 10 פספוסים) מפוזרים לרוחב 3 רצועות אמת (נמוך ≤0.6 / בינוני 0.6-1.5 / גבוה >1.5), עם פונקציית `diversify` שמונעת חזרה על אותו (סטטוס, אירוע). מפיק `ניתוח_שגיאות_20_מקרים.xlsx` — 3 גליונות: 20 מקרים למילוי ידני (4 עמודות "למה" ריקות לזווית התקשורתית), סיכום ביצועי מודל פר רצועה, הוראות. ממצא מרכזי: MAE פר רצועה 0.164/0.346/**0.864**, הטיה ברצועה הגבוהה **−0.793** (HistGB מתכווץ למרכז בקפיצות אירוע ביטחוני).
- **`enrich_20cases_context.py`** (שלב 96, 2026-06-08) — מעשיר כל אחד מ-20 המקרים בהקשר היסטורי: ממוצע רייטינג של אותה תוכנית באימון, ממוצע באותו חלקי-יום, מספר הופעות, וטופ-2 שידורים אחרים באותו יום (לזיהוי מי "לקח" את הקהל). פיצול כרונולוגי מ-2026-02-08. מפיק `הקשר_20_מקרים.xlsx`.
- **`build_mentor_prep_docx.js`** (שלב 96, 2026-06-08; הורחב שלב 97, 2026-06-13) — docx-js: בונה את `סיכום_הכנה_מפגש_מנטור_6.docx` — מסמך Word RTL מפורט עם 8 פרקים, 6 טבלאות (ביצועי-רצועות, 20-מקרים, **4-משפחות-טעות**, תרחישים, המלצה-3-מדרגות, סיכום-מקרה-1). פרק 4.5 החדש מציג את 4 משפחות-הטעות שזוהו אחרי תיוג ה-20 ואת המסר שהן מובילות אליו. מבוסס על `ניתוח_שגיאות_20_מקרים.xlsx` + `_cases_data.json`. דורש `npm install docx`. הריצה ב-`node build_mentor_prep_docx.js`.
- **`fill_20cases_answers.py`** (שלב 97, 2026-06-13) — ממלא את 4 עמודות "למה" לכל 20 המקרים ב-`ניתוח_שגיאות_20_מקרים.xlsx` (בסגנון מקרה 1 מהמסמך), מוסיף עמודת "משפחת-טעות" עם צביעת רקע, ויוצר גליון רביעי "פיזור משפחות". 4 משפחות: A=הגזמה (אירוע מת/שעה משנית, ×4), B=החמצה (יום-1 של אירוע חדש, ×5), C=מדויק (×10), D=אנומליה (case 8 בלבד). אידמפוטנטי.
- **`regen_cases_json.py`** (שלב 97) — משחזר את `_cases_data.json` מ-`ניתוח_שגיאות_20_מקרים.xlsx`. נחוץ כי הקובץ נמחק אחרי build קודם, ו-`build_mentor_prep_docx.js` תלוי בו.
- **`kabinet_shishi_model.py`** (שלב 98, 2026-07-11) — פישוט טכני: מודל ייעודי לתוכנית **קבינט שישי** בלבד. מסנן ל-50 שידורים חיים (מתוך 232 שכוללים גם 160 חזרות ו-22 לקטים), בונה פיצ'רי-lag/EMA/rolling + אירועים ביטחוניים (`days_since_event_start`, `event_severity`, `in_event`, `broadcasts_in_current_event` מ-`אירועים_מדויקים.csv`), פיצול כרונולוגי 80/20 (38/10), משווה 3 baselines + Ridge + HistGB. **תוצאות:** HistGB מכוונן-קטן MAE=0.717 (R²=0.19); ב-MAE/mean = 14.6% לעומת 22.4% במודל הכללי — יחסית טוב יותר. **פיצ'רי אירוע לא עזרו:** HistGB התעלם (min_samples_leaf=5 חוסם splits עם 4 שורות "in event" באימון); Ridge החמיר ל-0.851→1.085 (overshoot ל-8.20 מול אמת 6.18 במרץ 2026). התקרה = **חוסר-דאטה של המשטר החדש** (מבצע שאגת הארי התחיל 2026-02-28, train מסתיים 2026-02-06 → אפס דוגמאות אימון של קבינט-שישי-בתוך-אירוע-רמה-9), לא בחירת מודל.
- **`compare_general_vs_kabinet.py`** (שלב 98, 2026-07-11) — משווה את המודל הכללי (`model_saved.joblib`, MAE=0.300 כללי) מול המודל הייעודי על אותן 10 שורות test של קבינט שישי. **תוצאה:** ייעודי 0.717 מול כללי 1.179 — **המודל הייעודי מנצח ב-39.2%** ו-8/10 שידורים. הכללי כשל שיטתי בקצוות (2026-03-06: חזה 3.49 מול אמת 5.78). בסיס להחלטה להחליף בייצור.
- **`train_and_save_kabinet_model.py`** (שלב 98, 2026-07-11) — גרסת-ייצור של המודל: אימון על **כל 48 השורות** (בלי train/test split), שמירה ל-`model_kabinet_shishi.joblib`. Bundle: pipeline (HistGB), 16 feature_cols, sec_levels (7 רמות תג_ביטחוני שנצפו), start_date=2025-05-30, y_std=1.061 (לרווחי-ביטחון), recent_history (6 שידורים אחרונים). In-sample MAE=0.147; ה-`expected_test_mae=0.717` מגיע מהניסוי עם ה-split.
- **`model_kabinet_shishi.joblib`** (16KB) — המודל בייצור מ-2026-07-11. **החליף את `model_saved.joblib`** ב-backend/main.py. נטען עם `sec_levels`, `start_date`, `y_std` כמטא-דאטה.

### תוצאות
- `predictions.xlsx` — חיזויי V1 (4 מודלים)
- `predictions_v2.xlsx` — חיזויי V2 (5 מודלים, רייטינג + נתח)
- `predictions_ts.xlsx` — חיזויים יומיים TS
- `predictions_all.xlsx` — **חיזויי V3 (19 מודלים) + best_model_for_row + 5 גליונות**

### תיעוד (לעדכן תמיד!)
- `CLAUDE.md` — **המסמך הזה** — הנחיות לעבודה
- `Plan.md` — תוכנית העבודה הפעילה
- `WORK_LOG.md` — לוג כרונולוגי של כל השלבים
- `MODEL_FAQ.md` — שאלות-ותשובות על בחירת המודלים (לראיון)
- `README.md` — סקירה כללית באנגלית/עברית של הפרוייקט
- `DEPLOY.md` — הוראות פריסה ל-GitHub + Streamlit Cloud
- `MENTOR_PREP.md` — הכנה למפגשי מנטור 3-6 + שאלות לשאול
- `PRODUCT_VISION.md` — חזון מוצר B2B + GitHub strategy + דאטה נוסף
- **`PRODUCT_SPEC.md`** — **North Star v1.0 (2026-05-20):** ספק מוצר מפורט — לקוח-יעד (סוכנויות → ערוצים), תמחור Trial+Pro+Enterprise (+ setup fee), MVP כולל GenAI, ארכיטקטורת 3-שכבות, רוד-מאפ 10-12 שבועות, חוסמים (i24 פתוח · עוסק ✅)
- **`PRD.md`** — **מסמך דרישות מוצר v1.1 (2026-05-28):** פרסונות (מנהל חדשות / דסק תכנות), use cases, יכולות נוכחיות, באגים שנסגרו מול פתוחים, רודמאפ (כולל severity שנבדק ונדחה כפיצ'ר). מסלול ג׳ של המנטור
- **`SCHEMA.md`** — תכנון שכבת Data: 6 טבלאות (organizations, profiles, subscriptions, programs, broadcasts, predictions), RLS, indices, תכנית הגירה xlsx→Postgres
- **`schema.sql`** — DDL להרצה ישירה ב-Supabase SQL Editor (6 טבלאות + indices + RLS policies + triggers, אידמפוטנטי)
- **`setup_db.py`** — מריץ את `schema.sql` ב-Supabase דרך psycopg (אלטרנטיבה ל-SQL Editor)

### Frontend (Next.js — שלב 3, 2026-05-21)
- `frontend/app/layout.tsx` — RTL/Hebrew · Heebo font · metadata (title template, OG, Twitter, keywords, robots)
- `frontend/app/page.tsx` — דף נחיתה שיווקי (hero + features + pricing + CTA)
- `frontend/app/login/page.tsx` — מסך התחברות/הרשמה (Supabase Auth, signin/signup tabs)
- `frontend/app/dashboard/page.tsx` — טופס חיזוי + תוצאה (KPI strip, confidence bar, date shortcuts, recent-5)
- `frontend/app/chat/page.tsx`, `history/page.tsx`, `analytics/page.tsx`, `account/page.tsx` — 4 מסכי-אזור-מחובר
- `frontend/app/robots.ts` + `sitemap.ts` — SEO scaffolding (חוסם נתיבים מאחורי auth)
- `frontend/components/NavBar.tsx` — הסרגל העליון של האזור-המחובר (גרדיאנט כהה, כפתורי-גלולה)
- `frontend/public/index.html` + `infographic.html` — דפי הוויטרינה הסטטיים (Vanilla JS). **שלב 72:** נושאים `appbar` סטטי **זהה ויזואלית** ל-NavBar; ניווט same-tab משני הכיוונים (אין יותר `target="_blank"`). סרגל **מודע-לחיבור**: סקריפט module טוען Supabase מ-CDN, קורא session מ-localStorage המשותף, ומחליף "התחברות"→מייל+"יציאה" (מוגן `try/catch`). זו הדרך לאחד את הסרגל בלי פורט React (גישת ה-iframe/ראוטים נכשלה, שלבים 70-71)
- `frontend/lib/supabase.ts` — Supabase JS client
- `frontend/lib/api.ts` — קליינט ל-Backend FastAPI
- `frontend/tailwind.config.ts` — מותג: brand-primary #1E5DB8, brand-accent #FF6B35
- `frontend/next.config.ts` — rewrites: `/about` → `/index.html`, `/infographic` → `/infographic.html` (כתובות נקיות בלי `.html`, מגישות את הקבצים הסטטיים כמו שהם — לא ראוטים של React)
- הרצה: `cd frontend && npm install && npm run dev` → http://localhost:3000

### Backend (FastAPI ML Service — שלב 2, 2026-05-21)
- `backend/main.py` — FastAPI app: `/health`, `/predict`, `/docs`. **שלב 98 (2026-07-11):** טוען `model_kabinet_shishi.joblib` (במקום `model_saved.joblib`); quantile+bias יצאו זמנית (לא תואמים לפיצ'רים החדשים); היסטוריה מ-Supabase נשארה אבל מסוננת פעם אחת ל-`KABINET_HISTORY` (50 שידורי-חי) לחישוב lag_1/2/EMA4/rolling4. `אירועים_מדויקים.csv` נטען ב-startup. פונקציה חדשה `_derive_security_tag(target_date, scenario)` ממפה תאריך + scenario ל-תג_ביטחוני שתואם לרמות באימון (`routine`→שגרה; `special_event`→לפי CSV, או תג הכי חמור אם אין אירוע פעיל = סימולציית תרחיש-הסלמה). `_compute_kabinet_features` בונה 16 פיצ'רים. Interval: `pred ± 1.28 * y_std` (`interval_method='y_std_kabinet'`). Metadata חדשה מחזירה את `lag_1`, `lag_2`, `ema_4`, `sec_tag_used`. dev-toggles: `REQUIRE_AUTH=false` עוקף JWT verify, `LLM_EXPLAIN_PREDICTIONS=false` מדלג על Groq. **שלב 92:** `_unhandled_exception_handler` גלובלי (CORS headers ל-uncaught exceptions). **שלב 94:** אסור להוסיף `from __future__ import annotations` (שובר את Pydantic 2.10 model_rebuild).
- `backend/prediction_logic.py` — חישוב lag features, slot uncertainty, trend (פורט מ-utils/predict.py בלי תלות ב-Streamlit)
- `backend/requirements.txt` — FastAPI · uvicorn · sklearn · pandas · psycopg · dotenv
- `backend/render.yaml` — תצורת פריסה אוטומטית ל-Render.com

### Stripe Subscriptions (שלב 4, 2026-05-21)
- `backend/main.py` endpoints: `POST /checkout/create-session` (Subscription mode, 14-day trial), `POST /stripe/webhook` (HMAC verified, syncs `subscriptions` table)
- `frontend/app/account/page.tsx` — קורא subscription status מ-Supabase, מציג Pro/Free, מפעיל Checkout
- `STRIPE_SETUP.md` — מדריך הקמה (~15 דק'): Test account → product → keys → Stripe CLI → webhook
- Stripe מותנה ב-3 env vars: `STRIPE_SECRET_KEY` · `STRIPE_PRICE_PRO_MONTHLY` · `STRIPE_WEBHOOK_SECRET`. בלעדיהם — 503 ברור (לא קורס)
- `backend/README.md` — הרצה מקומית + מדריך פריסה
- הרצה מקומית: `cd backend && py -3 -m uvicorn main:app --reload`
- **`migrate_to_supabase.py`** — מעלה תוכניות+שידורים מ-`תוכניות_מעובד.xlsx` ל-Postgres דרך psycopg ישיר. Type-aware: datetime.time, uuid.UUID, NaN→None. דורש `.env` עם DATABASE_URL
- **`.env.example`** — תבנית למשתני סביבה (Project URL + Publishable key כבר מוטמעים; secrets ב-`.env` המקומי בלבד)
- `GLOSSARY.md` — **מילון מושגים מקיף** — DS/ML + אלגוריתמים, מוסבר בשלוש רמות (ילד/טכני/פרוייקט)
- `DATA_DEEP_DIVE.md` + `sample_30_rows.xlsx` — ניתוח ידני של 30 שורות מ-test, השוואת 6 מודלים, זיהוי דפוסים
- `ALGORITHMS_VISUAL.md` + `viz/01-08*.png` — 8 תרשימים שמסבירים אלגוריתמים על הדאטה האמיתי
- `data_deep_dive.py`, `algo_visualizations.py` — סקריפטי הניתוח/ויזואליזציה
- `eda_to_docx.py` — ממיר Markdown→Word גנרי (RTL, מיתוג i24). `py -3 eda_to_docx.py [SRC.md] [OUT.docx]`; ברירת מחדל: `EDA_REPORT.md`→`EDA_REPORT.docx`
- `EDA_REPORT.docx`, `WORK_LOG.docx` — פלטי Word

### דף נחיתה (Vanilla JS, GitHub Pages, 2026-05-14)
- `docs/index.html` — HTML semantic, RTL, 7 sections
- `docs/style.css` — Heebo + Grid + CSS variables, fully responsive
- `docs/script.js` — IntersectionObserver, count-up, leaderboard bars
- `docs/infographic.{html,css}` — **דאטה סיינס בציורים + מילון משולב** (דף המושגים היחיד): 23 איורי SVG; לחיצה על כרטיס פותחת modal עם הציור בגדול + הסבר 3 רמות (פשוט/טכני/בפרוייקט). סטטי, כולל `@media print`. החליף את glossary.* + journey.* שנמחקו (2026-05-18, צמצום דפים לפי בקשת המשתמשת)
- `docs/{favicon.svg,favicon-32.png,icon-180.png,og-cover.png}` — נכסי שיתוף (Open Graph + favicon), נוצרים ע"י `make_share_assets.py` (matplotlib + bidi RTL)
- `docs/viz/` — 8 PNG-ים
- `docs/README.md` — הוראות פריסה ל-GitHub Pages

### אפליקציה (Streamlit, נוסף 2026-05-09, פרוס באוויר 2026-05-10)
- `app.py` — דף הבית
- `pages/1_📊_חיזויים.py`, `pages/2_📺_כרטיס_תוכנית.py`, `pages/3_🔍_השוואת_מודלים.py`, **`pages/4_🎯_חיזוי_עתידי.py`** (חדש 2026-05-10)
- `utils/auth.py` — password gate
- `utils/data_loader.py` — טעינות cached
- **`utils/predict.py`** (חדש) — חיזוי בזמן אמת על קלט עתידי
- **`utils/imputers.py`** (חדש) — imputers משותפים (פתרון pickle cross-script)
- **`utils/style.py`** (חדש) — מערכת עיצוב מאוחדת (Heebo, גרדיאנטים, hover)
- **`train_and_save_model.py`** — מאמן את HistGradientBoosting ושומר ל-joblib. **TARGET = `רייטינג מותאם`** (panel-adjusted, ראה שלב 52)
- **`model_saved.joblib`** (1.2MB) — הצנרת המאומנת. מטא-דאטה כולל `target_name`, `target_kind="adjusted"`, `expected_test_mae=0.300`
- **`train_quantile_models.py`** (שלב 77, 2026-05-30) — מאמן P10/P90 (HistGB עם loss=quantile), 85/15 split כרונולוגי לחיתוך-קליברציה, מחשב conformal offsets כ-90th-pctile של פערים בכל קצה. מפיק `model_quantiles.joblib`.
- **`model_quantiles.joblib`** (2.4MB) — `pipe_p10`, `pipe_p90`, `offset_low=0.054`, `offset_high=0.328`. כיסוי מכויל 79.9% (יעד 80%). נטען ב-backend (שלב 78) להפקת `prediction_low/high`.
- **`compute_bias_corrections.py`** (שלב 80, 2026-05-30) — מחשב bias ממוצע פר (status × daypart) על test, מסנן n≥30 & |bias|≥0.10 & cap ב-±0.30. מפיק `bias_corrections.json`.
- **`bias_corrections.json`** — 7 תיקוני הטיה יציבים. backend מחיל אותם על pred + רווח quantile (שלב 80). שיפור MAE על test: 0.3010 → 0.2993.
- `model_train_all_v4_adjusted.py` + `MODEL_REPORT_ALL_v4_adjusted.md` — השוואת 19 המודלים על Y המותאם
- `predictions_all_v4_adjusted.xlsx` — חיזויי V4 על test set

### Auto-retrain (שלב 53-54, 2026-05-23)
- **`retrain_from_supabase.py`** — נטען בו ב-CI. מאמן מ-Supabase, מודד test MAE, שומר `model_saved.joblib` ומוסיף שורה ל-`retrain_log.md`. **שלב 55:** `tag_events_by_date()` גוזר תגי אירועים מ-`אירועים_מדויקים.csv` לפי תאריך (תיקון הבאג שבו התגים אבדו לברירות-מחדל קבועות). טוען `.env` ומושך גם `duration_min`.
- **`verify_event_fix.py`** (שלב 55) — מוכיח את תיקון האירועים: תיוג נכון (0 אי-התאמות מול xlsx) + ablation (שיפור 9.6% ב-MAE: 0.333→0.301) + permutation importance. הרצה מקומית, ללא DB.
- **`process_raw_data.py`** (שלב 54) — מקבל קובץ גולמי מ-i24 (15 עמודות), מוסיף 19 עמודות מהונדסות, ממזג עם הדאטה הקיים ועושה dedup. אומת מספרית מול eda_script.py.
- **`.github/workflows/retrain.yml`** — cron `0 4 1 * *` (חודשי, 1 לחודש 07:00 ישראל) + workflow_dispatch. דורש secret `DATABASE_URL` ב-GitHub repo.
- **`.github/workflows/keepalive.yml`** (שלב 61) — cron `*/10 * * * *`: ping ל-`/health` (Render) ול-Streamlit כדי למנוע Cold Start. חלופה עצמאית ל-UptimeRobot.
- **`.claude/skills/process-i24-data/`** — סקיל מקומי (לא ב-git) שמנחה אותי בזרימה החודשית של בליעת דאטה חדשה.
- **`RETRAIN.md`** — מדריך תפעולי: זרימה חודשית מקבצי i24 גולמיים → סקריפט → Supabase → retrain → deploy.
- `.streamlit/config.toml` — תצורה
- `.streamlit/secrets.toml.example` — תבנית לסיסמה (הקובץ האמיתי ב-gitignore)
- `requirements.txt` — תלויות לפריסה (כולל joblib==1.4.2)

### סוכן אירועים — LLM (שלב 56+59, 2026-05-28)
- **`event_severity.py`** — נותן ציון severity (0–10) לאירוע דרך Groq (HTTPS ישיר, בלי SDK). system prompt עם טבלת דירוג + few-shot מהאירועים האמיתיים. `--dry-run`, retry-on-429. דורש `GROQ_API_KEY` ב-`.env`.
- **`score_events_severity.py`** — מדרג את כל האירועים הביטחוניים ושומר עמודת `severity` ב-`אירועים_מדויקים.csv`.
- **`compare_severity.py`** — סקריפט ההשוואה one-hot↔severity.
- ⚠️ **severity אינו פיצ'ר במודל** (שלב 59): ניסוי הראה שהוא מזיק (MAE 0.30→0.41) כי עוצמה סמנטית ≠ השפעה per-broadcast (אפקט משך). נשמר לשכבת הסבר/צ'אטבוט עתידית, לא לחיזוי הרייטינג.

### שכבת LLM — agents (שלב 62, 2026-05-29)
- **`llm_client.py`** — קליינט Groq משותף (`chat`/`chat_json`, retry-on-429, JSON). בסיס לכל פיצ'רי ה-LLM.
- **`explain.py`** — `explain_prediction(...)`: הסבר עברי קצר לתחזית, מבוסס-עובדות בלבד (ללא הזיות).
- **`event_classifier.py`** — `classify(headline, date)`: ידיעת חדשות → JSON של אירוע ביטחוני. בסיס לסוכן שמתחזק את `אירועים_מדויקים.csv`.
- **`chat_agent.py`** — סוכן: שאלה חופשית → LLM מפרסר → המודל חוזה → `explain` עונה. נבדק מול Groq.
- **חיווט לאפליקציה (שלב 63):** `backend/main.py` — `/predict` מחזיר `explanation`, `/ask` משתמש ב-`llm_extract` (LLM) עם נפילה לרגקס. הכל **graceful** — בלי `GROQ_API_KEY` האפליקציה עובדת כרגיל. הדשבורד מציג בלוק "💡 הסבר". **דרוש:** `GROQ_API_KEY` ב-Environment של Render להפעלה חיה.
- **`news_agent.py`** (שלב 64) — סוכן חדשות אוטונומי: מושך RSS (ברירת מחדל ynet, `xml.etree`) → מסווג ב-`event_classifier` → מציע אירועים ל-`אירועים_מדויקים.csv`. Human-in-the-loop: dry-run כברירת מחדל, `--apply` כותב.

### 🌐 Live URLs
- **GitHub:** https://github.com/DataScienceOritAlma/i24-ratings-forecast (ציבורי)
- **Streamlit:** https://i24-ratings-orit.streamlit.app (סיסמה: `i24-2026-orit`)

## כללי עבודה

### תיעוד — חובה בכל שינוי
1. **`WORK_LOG.md`** — לעדכן בכל שלב שמסתיים, עם תאריך, מה נעשה, ותוצאות מספריות
2. **`Plan.md`** — לעדכן כשמשלימים משימות (לסמן ✅) או כשמשתנה הכיוון
3. **`CLAUDE.md`** — לעדכן כשמתווספים קבצים חדשים, החלטות ארכיטקטורה, או כלים חדשים

### שפה
- כל הקבצים בעברית (חוץ מקוד Python)
- תיעוד קצר וממוקד — לא רומן, רק מה שצריך לדעת

### הרצת קוד
```powershell
cd "D:\Users\user\Desktop\Claude\projects\פרוייקט I24"
py -3 eda_script.py
py -3 model_train.py
py -3 model_train_advanced.py
py -3 model_train_timeseries.py
py -3 model_train_all.py            # V3 — 19 מודלים, ~60 שניות
```

### חבילות מותקנות
`pandas`, `numpy`, `openpyxl`, `scikit-learn`, `xgboost`, `lightgbm`, `catboost`, `statsmodels`

## סטטוס נוכחי (מעודכן 2026-05-10)
- שלב EDA: **הושלם ✅**
- שלב מידול (5 שכבות + V3 19 מודלים): **הושלם ✅**
- נקודת החלטה: **הושלמה ✅** — עברנו לפיתוח אפליקציה
- שלב אפליקציה: **הושלם ✅** — 4 מסכים פעילים
- שלב פריסה: **הושלם ✅** — חי באוויר ב-Streamlit Cloud
- שלב עיצוב: **הושלם ✅** — מערכת עיצוב מאוחדת

## תוצאות מידול (לעיון מהיר)

**V4 — Y = `רייטינג מותאם` (בייצור היום)**
| מודל | MAE | R² |
|---|---|---|
| **🏆 HistGradientBoosting (V4)** | **0.300** | **0.617** |
| LightGBM | 0.305 | 0.617 |
| GradientBoosting | 0.302 | 0.603 |
| XGBoost / CatBoost | 0.310 | 0.59-0.61 |
| Stacking | 0.312 | 0.578 |

**V3 — Y = `רייטינג` (גולמי, היסטורי)**
| מודל | MAE | R² |
|---|---|---|
| **HistGradientBoosting** | **0.263** | **0.603** |
| LightGBM | 0.265 | 0.598 |
| GradientBoosting | 0.270 | 0.579 |

> ⚠️ MAE לא ישיר להשוואה: סקאלת `מותאם` גדולה ב-1.3x מ-`גולמי`. ב-MAE/mean יחסית, V4 ב-53.1% לעומת V3 ב-59.7% (V4 טוב ב-11%).

## החלטות ארכיטקטורה שכבר התקבלו
- **Y = `רייטינג מותאם`** (panel-adjusted, ה-KPI העסקי, ראה שלב 52)
- פיצול **כרונולוגי** 80/20 (חיתוך 2026-02-08) — לא רנדומלי
- **אין leakage**: עמודות שנמדדות אחרי שידור הוצאו מה-features
- Lag features מחושבים רק מהיסטוריה שקדמה לכל שורה (על `רייטינג מותאם`)
- מודל יחיד עדיף על Hybrid (overfitting על דאטה קטן של אירועים)
- תקרת הביצועים = drift של אירועים בלתי-צפויים, לא בחירת מודל
- `reception_pct` עתידי מוערך בקירוב ליניארי (0.65 → 0.95), כדי לגזור raw מ-adjusted
- **אין פיצ'רי חגים/עונות** (הוסרו 2026-05-28, שלב 57): ablation הראה תרומה ~0 ואות הרייטינג בחגים שנוי-במחלוקת/לא-אמין (דומיין i24 אומר נמוך, הדאטה מראה גבוה). אירועי ביטחון (`תג_ביטחוני`,`יום_ביטחוני`) נשארו — שווים ~10.6% מ-MAE
