# i24 — מערכת חיזוי רייטינג

מערכת חיזוי רייטינג טלוויזיה לערוץ i24, מבוססת על ML.
מנבאת רייטינג **לפני** השידור על בסיס היסטוריה, רצועה, אירועים, ותחרות.

---

## 🎯 מה זה

- **דאטה:** 10,039 שידורים, 25/05/2025 → 18/04/2026, 179 תוכניות ייחודיות
- **מודלים:** השוואת **19 מודלים** מ-7 משפחות (ליניאריים, עצים, ensembles, רשתות נוירונים, stacking)
- **מנצח:** `HistGradientBoosting` עם MAE = 0.263, R² = 0.603
- **תקרת ביצועים:** drift של אירועים בלתי-צפויים (שאגת הארי, מתקפה איראנית)

---

## 🖥️ אפליקציית Streamlit

האפליקציה כוללת 3 מסכים מעבר לדף הבית:
1. **📊 חיזויים** — דפדוף בכל החיזויים על מבחן עם סינון לפי תאריך/יום/אירוע/תוכנית
2. **📺 כרטיס תוכנית** — drill-down לתוכנית: היסטוריה, ממוצעים, אירועים שהשפיעו
3. **🔍 השוואת מודלים** — leaderboard, MAE לפי חתך, ראש-בראש בין מודלים

### הרצה לוקאלית

```powershell
# 1. התקנת חבילות
pip install -r requirements.txt

# 2. הגדרת סיסמה (פעם ראשונה)
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# ערכי את הסיסמה בתוך הקובץ

# 3. הרצה
streamlit run app.py
```

האפליקציה תיפתח ב-`http://localhost:8501`. הזיני את הסיסמה כדי להיכנס.

---

## 📁 מבנה הפרוייקט

```
.
├── app.py                              # דף הבית
├── pages/
│   ├── 1_📊_חיזויים.py                  # מסך חיזויים
│   ├── 2_📺_כרטיס_תוכנית.py             # כרטיס תוכנית
│   └── 3_🔍_השוואת_מודלים.py            # השוואת מודלים
├── utils/
│   ├── auth.py                         # password gate
│   └── data_loader.py                  # טעינת נתונים cached
├── .streamlit/
│   ├── config.toml                     # תצורת Streamlit
│   └── secrets.toml.example            # תבנית — העתיקי ל-secrets.toml
│
├── eda_script.py                       # EDA + יצירת אקסל מעובד
├── model_train.py                      # V1 — 4 מודלים
├── model_train_advanced.py             # V2 — tuning + hybrid
├── model_train_timeseries.py           # מודלי TS
├── model_train_all.py                  # V3 — 19 מודלים
│
├── תוכניות_מעובד.xlsx                  # דאטה מעובד
├── predictions_all.xlsx                # חיזויי 19 מודלים
├── אירועים_מדויקים.csv                 # 17 אירועים מתויגים
│
├── EDA_REPORT.md                       # דוח EDA
├── MODEL_REPORT.md / V2 / TS / ALL    # דוחות מודלינג
├── MODEL_FAQ.md                        # שאלות-ותשובות
├── WORK_LOG.md                         # לוג כרונולוגי
├── Plan.md                             # תוכנית פעילה
└── CLAUDE.md                           # הנחיות עבודה
```

---

## 🔐 אבטחה

- כל גישה לאפליקציה מוגנת בסיסמה (בקובץ `.streamlit/secrets.toml`)
- `secrets.toml` נמצא ב-`.gitignore` — **לא נכנס לריפו**
- הריפו פרטי כדי להגן על נתוני i24

---

## 🚀 פריסה ל-Streamlit Community Cloud

ראה הוראות מפורטות ב-[`DEPLOY.md`](DEPLOY.md).

---

## 📊 תוצאות מודלינג (Top 5)

| מודל | MAE | R² |
|---|---|---|
| 🏆 HistGradientBoosting | 0.263 | 0.603 |
| LightGBM | 0.265 | 0.598 |
| GradientBoosting | 0.270 | 0.579 |
| CatBoost | 0.271 | 0.576 |
| ExtraTrees | 0.272 | 0.579 |

המודל הנאיבי (ממוצע גלובלי) משיג MAE=0.422 — שיפור של **37.8%**.

---

*הפרוייקט פותח כפרוייקט לימודי-מקצועי לתפקיד data scientist.*
