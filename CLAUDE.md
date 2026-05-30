# CLAUDE.md — הנחיות לעבודה עם Claude בפרוייקט I24

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
- `backend/main.py` — FastAPI app: `/health`, `/predict`, `/docs`. טוען model_saved.joblib + היסטוריה מ-Supabase ב-startup. **תרחיש `scenario`:** `routine` או `special_event` (=אירוע ביטחוני; מדליק `is_security`, ≈+39%). חגים אינם תרחיש (הוסרו, שלב 57)
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
