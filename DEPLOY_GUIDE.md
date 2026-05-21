# Deploy Guide — i24 Ratings Forecast

מדריך פריסה מלא של 3 השכבות לענן. **סך זמן: ~30 דקות.**

> **תנאים מקדימים:** חשבון GitHub פעיל (יש), Supabase (יש ✅), DATABASE_URL ב-`.env` (יש ✅).

---

## 1. Backend ל-Render.com (~10 דק')

### א. הרשמה
1. https://render.com → **Sign in with GitHub** (אישור הרשאות)
2. Render יראה את הריפו `i24-ratings-forecast`

### ב. יצירת השירות
1. Dashboard → **New + → Web Service**
2. **Connect Repository:** `DataScienceOritAlma/i24-ratings-forecast`
3. Render יזהה את `backend/render.yaml` — אישור
4. שם: `i24-ratings-api` (או כל שם). Plan: **Free**. Region: **Frankfurt**

### ג. משתני סביבה
ב-Service → Environment → Add:
```
DATABASE_URL = <אותו ערך מ-.env המקומי, כולל הסיסמה>
```
**Save** → Render יתחיל בנייה אוטומטית (~5-7 דק' בפעם הראשונה).

### ד. ודאי
- Build הצליח: לוגים מציגים `[startup] ✓ Model: HistGradientBoosting`
- כתובת חיה: `https://i24-ratings-api.onrender.com`
- בדיקה: `https://i24-ratings-api.onrender.com/health` → JSON עם `"status":"ok"`

### הערה על Free tier
- 750 שעות/חודש (מספיק)
- **נרדם אחרי 15 דק' חוסר פעילות**. קריאה ראשונה אחרי שינה: 30-60 שניות
- ב-Launch: לשדרג ל-Starter ($7/חודש, לא נרדם)

---

## 2. Frontend ל-Vercel (~10 דק')

### א. הרשמה
1. https://vercel.com → **Sign in with GitHub** (אישור)
2. Vercel יראה את הריפו

### ב. Import Project
1. Dashboard → **Add New → Project**
2. בחרי `i24-ratings-forecast`
3. **Root Directory:** `frontend` (חשוב! לחיצי על "Edit" וקבעי את זה)
4. Framework Preset: Next.js (יזוהה אוטומטית)
5. **Region:** Frankfurt (fra1) — כבר ב-`vercel.json`

### ג. משתני סביבה
לפני "Deploy" → גללי ל-**Environment Variables**:
```
NEXT_PUBLIC_SUPABASE_URL = https://bfnmaogcxdgnaxwjdtny.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = sb_publishable_7RMhqEoPZs73M1ZSbP0Uww_YLE9Nv76
NEXT_PUBLIC_API_URL = https://i24-ratings-api.onrender.com
```
(החליפי `i24-ratings-api` בשם השירות שיצרת ב-Render)

### ד. Deploy
לחיצי **Deploy** → תוך ~2 דק' תקבלי URL כמו `i24-ratings-forecast-xxxx.vercel.app`.

### ה. דומיין מותאם (אופציונלי, עתידי)
Vercel → Settings → Domains → Add custom domain (למשל `i24.orit-alma.com`).

---

## 3. CORS — לאפשר ל-Vercel לדבר עם Render (~2 דק')

`backend/main.py` כרגע מאפשר `*` — פתוח לפיתוח. בייצור, צמצמי לדומיין הספציפי של Vercel:

ב-Render → Service → Environment → Add:
```
CORS_ORIGIN = https://i24-ratings-forecast-xxxx.vercel.app
```
ועדכני את הקוד ב-`backend/main.py`:
```python
allow_origins=[os.environ.get("CORS_ORIGIN", "*")],
```
(אם כבר עשית את זה לפני הפריסה — אז ה-`*` בקובץ; להשאיר ככה עד ש-domain יציב.)

---

## 4. Stripe Webhook לפרודקשן (~5 דק')

אם פתחת חשבון Stripe (ראה STRIPE_SETUP.md):
1. Stripe Dashboard → Developers → **Webhooks → Add endpoint**
2. **Endpoint URL:** `https://i24-ratings-api.onrender.com/stripe/webhook`
3. **Events to send:**
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. אחרי שמירה — `whsec_...` חדש (שונה מה-CLI הלוקאלי)
5. Render → Environment → עדכני את `STRIPE_WEBHOOK_SECRET`

---

## 5. בדיקת קצה-לקצה

- [ ] http://your-vercel-url — דף התחברות עולה
- [ ] הרשמה עם מייל חדש → נכנסת לדשבורד
- [ ] דשבורד → חישוב תחזית → רואים תוצאה
- [ ] היסטוריה → התחזית נראית
- [ ] אנליטיקה → מספרים נכונים
- [ ] חשבון → רואה ארגון + שם + Trial
- [ ] צ'אט → שאלה בעברית → תשובה

אם הכל ✅ — **את חיה!** 🚀

---

## תקלות נפוצות

**"Failed to fetch" בדשבורד**
→ Backend נרדם (Render free tier). קריאה ראשונה לוקחת 30-60 שניות. רענני אחרי דקה.

**Build נכשל ב-Render**
→ ודאי שיש לך `DATABASE_URL` ב-Environment. ראי לוגים.

**Build נכשל ב-Vercel**
→ ודאי שה-Root Directory הוא `frontend`. בדקי שכל 3 משתני NEXT_PUBLIC_ קיימים.

**Stripe webhook לא מסונכרן**
→ Stripe Dashboard → Webhooks → לחיצי על השורה → Event log → תראי כשלים אם יש.

---

*נבנה ע&quot;י אורית עלמה זיו-נר · 2026*
