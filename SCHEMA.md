# SCHEMA.md — מסד הנתונים של i24 Ratings Forecast

*v1.0 · 2026-05-21 · שכבת Data של ארכיטקטורת 3 השכבות · מאושר → ניתן ליישום ב-Supabase*

> **מה זה המסמך הזה?**
> זה ה-**blueprint** של שכבת הנתונים. ברגע שהוא ננעל, אני יוצר אותו ב-Supabase ב-SQL פעם אחת.
> זה לא ייכתב שוב — אם בעתיד נשנה (למשל נוסיף טבלה), נעשה זאת ב-migration ייעודי.

---

## 🎯 עקרונות התכנון

1. **Multi-tenancy** — כל לקוח (סוכנות / ערוץ) הוא **organization** עם data משלו. RLS מבטיח שאחד לא רואה את השני.
2. **דאטא מודל = משותף** — קטלוג התוכניות וההיסטוריה (10K שידורי i24) משותף לכולם, כי המודל אומן עליהם. **רק התחזיות הן פר-organization**.
3. **שמירה היסטורית** — כל תחזית נשמרת לתמיד, גם אחרי שמתעדכן הרייטינג האמיתי. זה ה-data שמאפשר לבנות פיצ'ר retrospective חי לכל לקוח.
4. **ID-ים אוניברסליים** — `uuid` בכל מקום (לא `int sequence`). מאפשר לייצר ID-ים גם בצד-הלקוח לפני שמירה.
5. **Timezone-aware** — `timestamptz` בכל מקום (לא `timestamp`). חוסך כאבי-ראש בעתיד.

---

## 📊 6 הטבלאות הראשיות

### 1. `organizations` — לקוחות (multi-tenancy unit)
היחידה הבסיסית. כל סוכנות, ערוץ, או יחידת מחקר מקבלת `organization` משלה.

| עמודה | סוג | הערות |
|---|---|---|
| `id` | uuid PK | מזהה ייחודי |
| `name` | text NOT NULL | "סוכנות מדיה X" / "i24 NEWS" |
| `type` | enum | `agency` / `research` / `channel` / `individual` |
| `created_at` | timestamptz | |

### 2. `profiles` — משתמשים (extends Supabase Auth)
Supabase מנהל את הסיסמאות/טוקנים ב-`auth.users`. אנחנו מוסיפים מטא-דאטא משלנו.

| עמודה | סוג | הערות |
|---|---|---|
| `id` | uuid PK | FK ל-`auth.users(id)` |
| `organization_id` | uuid FK | אילו ארגון המשתמש משתייך |
| `full_name` | text | |
| `role` | enum | `owner` / `member` / `admin` |
| `created_at` | timestamptz | |

### 3. `subscriptions` — מנויים (Stripe sync)
משתקף את ה-subscription של הארגון ב-Stripe. webhook מ-Stripe מעדכן את הטבלה הזאת.

| עמודה | סוג | הערות |
|---|---|---|
| `id` | uuid PK | |
| `organization_id` | uuid FK UNIQUE | ארגון אחד = subscription אחד |
| `stripe_customer_id` | text UNIQUE | |
| `stripe_subscription_id` | text UNIQUE | |
| `status` | enum | `trialing` / `active` / `past_due` / `canceled` / `incomplete` |
| `tier` | enum | `trial` / `pro` / `enterprise` |
| `trial_ends_at` | timestamptz | מתי ה-trial של 14 יום נגמר |
| `current_period_end` | timestamptz | מתי החיוב הבא |
| `created_at`, `updated_at` | timestamptz | |

### 4. `programs` — קטלוג התוכניות (משותף)
כל תוכנית טלוויזיה ייחודית (179 תוכניות נכון להיום). **קריאה ציבורית** — לא פר-ארגון.

| עמודה | סוג | הערות |
|---|---|---|
| `id` | uuid PK | |
| `name` | text UNIQUE | "חדר החדשות איי 24" |
| `source_name` | text | שם בלי "ש.ח" — לזיווג חזרות לתוכנית-מקור |
| `first_aired`, `last_aired` | date | |
| `n_broadcasts` | int | כמה שידורים בהיסטוריה |
| `typical_status`, `typical_day`, `typical_hour` | text | סטטיסטיקות נפוצות לתצוגה |
| `updated_at` | timestamptz | |

### 5. `broadcasts` — שידורים היסטוריים (משותף)
כל שידור שהיה בעבר. **זה הדאטא שעליו המודל אומן**. 10,039 שורות מהקובץ הקיים.

| עמודה | סוג | הערות |
|---|---|---|
| `id` | uuid PK | |
| `program_id` | uuid FK | קישור ל-`programs` |
| `broadcast_date` | date NOT NULL | "2025-05-25" |
| `start_time`, `end_time` | time | "06:00:00" |
| `duration_min` | int | |
| `day_of_week`, `daypart` | text | "ראשון", "פריים-טיים" |
| `status` | text | "שידור חי" / "שידור חוזר" / "לקט" / "מיוחד-מבזק" |
| `event` | text | "—" / "מבצע שאגת הארי" / "חג סוכות" |
| `is_rerun` | bool | |
| `actual_rating` | numeric(5,3) | **הרייטינג בפועל** (אם נמדד) |
| `share` | numeric(5,2) | נתח |
| `viewers_4plus` | int | |
| `hut_proxy` | numeric(5,2) | |
| `reception_pct` | numeric(4,3) | פאנל-נושם החודש |
| `imported_at` | timestamptz | מתי הוספנו את השורה |

**Unique constraint:** `(broadcast_date, start_time, program_id)` — אסור 2 שידורים זהים.

### 6. `predictions` — תחזיות (פר-ארגון, פרטי)
כל תחזית שלקוח ביקש. נשמרת לתמיד. כשהרייטינג האמיתי מתפרסם — מתעדכן השדה `actual_rating` ו-`prediction_error` מחושב אוטומטית.

| עמודה | סוג | הערות |
|---|---|---|
| `id` | uuid PK | |
| `organization_id` | uuid FK | מי שאל |
| `user_id` | uuid FK | איזה משתמש בארגון |
| `program_id` | uuid FK nullable | אם זו תוכנית מהקטלוג |
| `target_date` | date NOT NULL | "מה יהיה הרייטינג ב-2026-06-12?" |
| `target_start_time`, `target_end_time` | time | |
| `scenario` | enum | `routine` / `special_event` |
| `predicted_rating` | numeric(5,3) | |
| `prediction_low`, `prediction_high` | numeric(5,3) | טווח 80% |
| `estimated_households` | int | |
| `estimated_viewers` | int | |
| `model_version` | text | "v1.0_2026-05-20" — אילו מודל הוציא |
| `created_at` | timestamptz | |
| `actual_rating` | numeric(5,3) nullable | מתמלא **אחרי השידור** |
| `actual_recorded_at` | timestamptz nullable | |
| `prediction_error` | numeric(5,3) GENERATED | `predicted_rating - actual_rating` (אוטומטי) |

---

## 🔒 RLS — מי רואה מה (Row-Level Security)

### עקרונות
- **`organizations` / `profiles` / `subscriptions`** — רק חברי-ארגון רואים את הארגון שלהם
- **`programs` / `broadcasts`** — קריאה ציבורית (לכל משתמש מאומת) — זה דאטא קטלוגי, לא רגיש
- **`predictions`** — רק חברי-ארגון רואים את התחזיות של הארגון שלהם
- **כתיבה ל-`subscriptions`** — רק ה-service-role (Stripe webhook), אף לקוח לא יכול לכתוב ישירות

### Helper function
```sql
CREATE OR REPLACE FUNCTION current_user_org()
RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT organization_id FROM profiles WHERE id = auth.uid()
$$;
```

### Policies (תקציר — DDL מלא בקובץ הנפרד)
```
organizations.SELECT: id = current_user_org()
profiles.SELECT:      organization_id = current_user_org()
profiles.UPDATE:      id = auth.uid()  (כל אחד מעדכן את עצמו)
subscriptions.SELECT: organization_id = current_user_org()
programs.SELECT:      auth.role() = 'authenticated'  (פתוח לכולם)
broadcasts.SELECT:    auth.role() = 'authenticated'  (פתוח לכולם)
predictions.SELECT:   organization_id = current_user_org()
predictions.INSERT:   organization_id = current_user_org() AND user_id = auth.uid()
```

---

## 🚀 Indices (מהירות)

```sql
CREATE INDEX idx_broadcasts_date    ON broadcasts(broadcast_date);
CREATE INDEX idx_broadcasts_program ON broadcasts(program_id);
CREATE INDEX idx_broadcasts_status  ON broadcasts(status);
CREATE INDEX idx_programs_name      ON programs(name);
CREATE INDEX idx_predictions_org    ON predictions(organization_id, created_at DESC);
CREATE INDEX idx_predictions_target ON predictions(target_date);
```

---

## 📥 תכנית הגירה — מ-xlsx ל-Postgres

### צעד 1: יצירת הסכמה (פעם אחת)
```bash
# בקונסולת Supabase → SQL Editor → הדבק את `schema.sql` (יעודכן מקובץ זה)
```

### צעד 2: העלאת הדאטא הקיים
סקריפט Python `migrate_to_supabase.py` (אני אכתוב בשלב הבא) קורא מ-`תוכניות_מעובד.xlsx` ו-`אירועים_מדויקים.csv` ומעלה ל-DB:

1. **`programs`** — distinct של 179 שמות-תוכנית ייחודיים
2. **`broadcasts`** — 10,039 שורות, מקושרות ל-`programs.id` לפי שם
3. **`events`** (אופציונלי) — 17 אירועים, או משולב כ-`broadcasts.event` בלבד

### צעד 3: אימות
```sql
SELECT count(*) FROM programs;     -- צפוי: ~179
SELECT count(*) FROM broadcasts;   -- צפוי: 10,039
SELECT min(broadcast_date), max(broadcast_date) FROM broadcasts;
-- צפוי: 2025-05-25 → 2026-04-18
```

### צעד 4: סוף-מאי 2026
כשמגיע אקסל מאי 2026 — סקריפט `import_monthly.py` (יבוא בשלב 2) מעלה רק את השורות החדשות. **לא דורש סכמה חדשה.**

---

## ⏭️ הצעד הבא

1. **אורית פותחת חשבון Supabase** (חינם, ~5 דק') → https://supabase.com
2. **יוצרת פרויקט חדש** ("i24-ratings-forecast", region: West Europe או Frankfurt)
3. **מעבירה לי את 2 ה-keys**: `anon key` (פומבי, אפשר להציג) + `service_role key` (סוד — לא להעלות ל-Git!)
4. **אני יוצר** `schema.sql` (DDL מתוך המסמך הזה) + `migrate_to_supabase.py`
5. **מריצים** במשך 15 דקות → DB עובד עם כל הדאטא + הרשמה ראשונה אפשרית

---

*מסמך אב לשכבת Data · יעודכן רק אם החליטו בכוונה לשנות מבנה · בעלת המוצר: אורית עלמה זיו-נר · מנטור טכני: Claude*
