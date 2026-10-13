# Auto-Retrain — Monthly Model Refresh

מערכת אוטומטית שמאמנת את המודל מחדש פעם בחודש על דאטה טריה מ-Supabase, ומעלה אותו ל-production.

---

## הזרימה המלאה — חודש טיפוסי

```
1. את מקבלת מ-i24 קובץ חדש עם נתוני החודש (CSV או XLSX, 15 עמודות)
       ↓
2. אומרת לי "יש לי דאטה חדשה" + מצביעה על הקובץ
       ↓
3. אני מריץ את הסקיל process-i24-data:
   - מוסיף 19 עמודות מהונדסות
   - ממזג עם הדאטה הקיים (dedup אוטומטי), או מחליף אותו אם הקובץ מכיל את כל הטווח
   - מעלה ל-Supabase (UPSERT)
   - מאמן מחדש את מודל קבינט שישי (`train_and_save_kabinet_model.py`)
       ↓
4. ה-cron של GitHub Actions ירוץ ב-1 לחודש הבא — או נריץ ידנית
       ↓
5. שני המודלים מתאמנים מחדש על כל הדאטה: הכללי, ומודל קבינט שישי שבייצור
       ↓
6. Render רואה את ה-commit החדש → בונה מחדש → המודל החי מתעדכן
```

**זמן ידני בחודש: ~5 דקות שלך.** את נותנת לי קובץ, אני עושה את כל השאר.

---

## תזמון

- **cron:** 1 לכל חודש ב-04:00 UTC (07:00 ישראל)
- **טריגר ידני:** GitHub → Actions → "Monthly model retrain" → Run workflow

---

## קבצים

| קובץ | תפקיד |
|---|---|
| **`process_raw_data.py`** | מקבל xlsx/csv גולמי מ-i24, מוסיף 19 עמודות מהונדסות, ממזג עם הדאטה הקיים |
| **`.claude/skills/process-i24-data/SKILL.md`** | הוראות איך אני (Claude) מפעיל את הסקריפט עבורך |
| **`retrain_from_supabase.py`** | מאמן את המודל הכללי מ-Supabase, שומר model_saved.joblib, מעדכן retrain_log.md |
| **`train_and_save_kabinet_model.py`** | מאמן את מודל קבינט שישי (**זה שבייצור**), שומר model_kabinet_shishi.joblib, מעדכן retrain_log_kabinet.md |
| **`.github/workflows/retrain.yml`** | ה-cron החודשי + workflow_dispatch לטריגר ידני. מריץ את שני האימונים |
| **`retrain_log.md`** / **`retrain_log_kabinet.md`** | היסטוריית הריצות של כל מודל (נוצרים אוטומטית) |
| **`migrate_to_supabase.py`** | מעלה את הדאטה המעובד ל-Supabase (UPSERT — בטוח לחזור) |

---

## הפעלה ראשונית — דבר אחד שצריך לעשות פעם אחת

ה-CI צריך לדעת איך להתחבר ל-Supabase. תוסיפי את `DATABASE_URL` כ-secret ברפו:

1. https://github.com/DataScienceOritAlma/i24-ratings-forecast/settings/secrets/actions
2. **New repository secret**
3. שם: `DATABASE_URL`
4. ערך: אותה שורה שיש לך ב-`.env` המקומי (`postgresql://...`)
5. **Add secret**

מהרגע הזה ה-cron ירוץ אוטומטית בכל 1 לחודש.

---

## דרישות לקובץ הגולמי מ-i24

15 עמודות, בכל סדר:

```
שם תוכנית · יום שידור · תאריך שידור · שעת התחלה · שעת סיום ·
משך תוכנית · רייטינג · נתח · צופים 4+ · חשיפה 4+ · משך צפייה ·
כאן 11 · קשת 12 · רשת 13 · עכשיו 14
```

CSV או XLSX עם שורת כותרת מעל (פורמט i24 מקורי) — נתמך אוטומטית.

קובץ שמכיל את **כל הטווח** מההתחלה (ולא רק את החודש החדש) מעבדים עם `--no-merge`, כדי ששורות ש-i24 תיקנה או שינתה להן שם לא יישארו בכפילות.

---

## מה לעקוב אחריו אחרי כל ריצה

1. **GitHub Actions tab** — הריצה הצליחה?
2. **`retrain_log.md`** ו-**`retrain_log_kabinet.md`** — שורה חדשה בכל אחד. אם "שידור אחרון" ב-`retrain_log_kabinet.md` לא מתקדם מחודש לחודש, הדאטה החדש לא הגיע ל-Supabase
3. **Render dashboard** — הדפלוי האוטומטי עבר?

אם **MAE מתחיל לטפס** באופן עקבי לאורך כמה ריצות — זה סימן ל-drift אמיתי בנתונים. כדאי לחקור איזה תוכניות התרחקו מהמודל.
