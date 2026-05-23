# Auto-Retrain — Bi-weekly Model Refresh

מערכת אוטומטית שמאמנת את המודל מחדש פעם בשבועיים על דאטה טריה מ-Supabase, ומעלה אותו ל-production.

---

## איך זה עובד

```
GitHub Actions cron (1 ו-15 לחודש, 04:00 UTC = 07:00 ישראל)
       ↓
טוען broadcasts + programs מ-Supabase
       ↓
מחשב רייטינג מותאם = רייטינג / reception_pct
       ↓
מאמן HistGradientBoosting · מודד test MAE על פיצול 80/20 כרונולוגי
       ↓
שומר model_saved.joblib + מוסיף שורה ל-retrain_log.md
       ↓
git commit + push (אוטומטי, בשם github-actions[bot])
       ↓
Render רואה push → מבנה מחדש → המודל החי מתעדכן
```

**זמן ריצה צפוי:** 5-7 דקות עד שה-Render מסיים build.

---

## קבצים

- **`retrain_from_supabase.py`** — הסקריפט שמתאמן ושומר. מתשתל ב-CI וגם נריץ ידנית.
- **`.github/workflows/retrain.yml`** — תזמון cron + הרשאות commit.
- **`retrain_log.md`** — היסטוריית כל הריצות (נוצר אוטומטית בריצה הראשונה).

---

## הפעלה ראשונית — דבר אחד שצריך לעשות פעם אחת

ה-CI צריך לדעת איך להתחבר ל-Supabase. תוסיף את `DATABASE_URL` כ-secret ברפו:

1. ב-GitHub → **Settings** של הריפו → בתפריט שמאל **Secrets and variables → Actions**
2. **New repository secret**
3. שם: `DATABASE_URL`
4. ערך: אותה שורה שיש לך ב-`.env` המקומי (`postgresql://...`)
5. **Add secret**

זהו. מהרגע הזה ה-cron ירוץ אוטומטית.

---

## הפעלה ידנית (אופציונלי)

אם רוצים לאמן עכשיו (לדוגמה, כי הוספת דאטה חדשה ל-Supabase ולא רוצים לחכות עד 1 בחודש הבא):

1. GitHub → **Actions** → **Bi-weekly model retrain**
2. כפתור ימני **Run workflow** → **Run workflow**
3. הריצה תופיע ברשימה תוך כ-30 שניות, אורכת ~5 דק'

---

## מגבלה ידועה — שלמות דאטה ב-Supabase

נכון לרגע זה, ה-Supabase מכיל את **הנתונים הבסיסיים** (רייטינג, reception_pct, יום, סטטוס) אבל **חסרים**:
- רייטינג של מתחרים (`כאן 11`, `קשת 12`, ...)
- תגיות עונה / חג / ביטחוני
- משך תוכנית בדקות

כשהאוטו-retrain רץ על Supabase, ה-features החסרים מקבלים defaults (0 או "—"), ובגלל זה **test MAE עלול להיות ~0.338 במקום ~0.300** מה-xlsx המלא.

**זה לא קריטי** — עדיין מודל טרי שווה יותר ממודל ישן בלי המגמה האחרונה. אבל **כצעד עתידי**, שווה לסנכרן את העמודות החסרות ל-Supabase.

---

## מה לעקוב אחריו

אחרי כל ריצת cron:
1. **GitHub Actions tab** — לראות אם הריצה הצליחה
2. **`retrain_log.md`** — שורה חדשה עם תאריך, מספר שורות, ו-MAE
3. **Render dashboard** — בוודאות שהדפלוי האוטומטי עבר

אם MAE מתחיל לטפס באופן עקבי לאורך כמה ריצות — זה סימן ל-drift אמיתי בנתונים, וצריך לבחון את הפיצ'רים מחדש.
