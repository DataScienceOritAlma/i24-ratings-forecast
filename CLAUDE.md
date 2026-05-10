# CLAUDE.md — הנחיות לעבודה עם Claude בפרוייקט I24

## מה הפרוייקט
חיזוי רייטינג טלוויזיה לערוץ i24 — מודל forecast שמנבא רייטינג לפני שידור.
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

### אפליקציה (Streamlit, נוסף 2026-05-09)
- `app.py` — דף הבית
- `pages/1_📊_חיזויים.py`, `pages/2_📺_כרטיס_תוכנית.py`, `pages/3_🔍_השוואת_מודלים.py`
- `utils/auth.py` — password gate
- `utils/data_loader.py` — טעינות cached
- `.streamlit/config.toml` — תצורה
- `.streamlit/secrets.toml.example` — תבנית לסיסמה (הקובץ האמיתי ב-gitignore)
- `requirements.txt` — תלויות לפריסה

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

## סטטוס נוכחי (מעודכן 2026-05-09)
- שלב EDA: **הושלם ✅**
- שלב מידול (5 שכבות): **הושלם ✅**
- נקודת החלטה: **הושלמה ✅** — עברנו לפיתוח אפליקציה
- שלב אפליקציה: **בתכנון**

## תוצאות מידול (לעיון מהיר)
| מודל | MAE | R² |
|---|---|---|
| נאיבי גלובלי | 0.422 | -0.046 |
| Baseline ממוצע-רצועה | 0.305 | 0.435 |
| Ridge | 0.372 | 0.471 |
| Lasso | 0.288 | 0.486 |
| RandomForest tuned (V2) | 0.280 | 0.566 |
| XGBoost | 0.280 | 0.558 |
| ExtraTrees | 0.272 | 0.579 |
| Stacking (RF+XGB+LGB+Ridge) | 0.272 | 0.566 |
| CatBoost | 0.271 | 0.576 |
| GradientBoosting (sklearn) | 0.270 | 0.579 |
| LightGBM | 0.265 | 0.598 |
| **🏆 HistGradientBoosting (V3)** | **0.263** | **0.603** |
| MLP (64×32) | 0.328 | 0.468 |
| KNN / SVR / DecisionTree | 0.294–0.298 | 0.47–0.48 |
| SARIMAX / Additive TS | 0.379–0.397 | שלילי |

## החלטות ארכיטקטורה שכבר התקבלו
- פיצול **כרונולוגי** 80/20 (חיתוך 2026-02-08) — לא רנדומלי
- **אין leakage**: עמודות שנמדדות אחרי שידור הוצאו מה-features
- Lag features מחושבים רק מהיסטוריה שקדמה לכל שורה
- מודל יחיד עדיף על Hybrid (overfitting על דאטה קטן של אירועים)
- תקרת הביצועים = drift של אירועים בלתי-צפויים, לא בחירת מודל
