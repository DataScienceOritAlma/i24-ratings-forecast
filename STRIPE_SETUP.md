# Stripe Setup — מדריך הקמה

המדריך הזה מסביר איך להפעיל את שלב 4 — Stripe Subscriptions. **משך**: ~15 דקות.

> **הערה:** כל ההגדרה למטה היא ב-**Test Mode** — לא מחויב בכרטיס אמיתי. כשתעברי ל-Live מאוחר יותר, אותו תהליך עם מפתחות אמיתיים.

---

## 1. הרשמה ל-Stripe (3 דק')
1. https://stripe.com → **Sign in / Sign up**
2. הרשמה חינמית — לא דורש כרטיס אשראי בשלב הזה
3. אישור מייל

## 2. השגת המפתחות (1 דק')
1. ב-Stripe Dashboard, ודאי **שאת ב-Test mode** (טוגל ימני-עליון "Test mode" דלוק)
2. Developers → **API keys**
3. תראי 2 מפתחות:
   - **Publishable key:** `pk_test_...` (לא נחוץ ל-MVP — צד-שרת בלבד עכשיו)
   - **Secret key:** `sk_test_...` — **לחיצי "Reveal" + העתקי**

## 3. יצירת מוצר ומחיר (3 דק')
1. **Products → Add product**
2. **Name:** `i24 Pro`
3. **Description:** `תחזיות רייטינג ללא הגבלה לתוכניות i24 וערוצים ישראליים`
4. **Pricing:**
   - **Pricing model:** Standard pricing
   - **Price:** `990.00`
   - **Currency:** `ILS (₪)`
   - **Billing period:** `Monthly`
   - **Save product**
5. אחרי שמירה, גללי למטה ל-"Pricing" וצלמי את ה-**Price ID** — משהו כמו `price_1AbCd...`

## 4. עדכון `.env` במחשב (1 דק')
פתחי את `.env` (בתיקיית הפרויקט הראשית), הוסיפי בסוף:
```bash
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxx       # מצעד 2
STRIPE_PRICE_PRO_MONTHLY=price_xxxxxxxxxxxxxx     # מצעד 3
# STRIPE_WEBHOOK_SECRET — נמלא בצעד 5
```

## 5. Webhook (לדרך הסנכרון של ה-DB עם Stripe — 5 דק')

ה-webhook הוא איך Stripe מודיע לנו "חיוב הצליח / מנוי חודש / בוטל". בלעדיו ה-DB לא יסונכרן.

### בפיתוח לוקאלי
1. התקיני את Stripe CLI: https://stripe.com/docs/stripe-cli (גרסת Windows: `winget install --id Stripe.StripeCLI` או הורדה ידנית)
2. ב-Terminal:
   ```powershell
   stripe login
   stripe listen --forward-to localhost:8000/stripe/webhook
   ```
3. ה-CLI יציג: `Ready! Your webhook signing secret is whsec_...` — **העתיקי**
4. הוסיפי ל-`.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxx
   ```
5. השאירי את `stripe listen` רץ ברקע בזמן שעובדים על המנויים

### בפרודקשן (אחרי פריסה ל-Render)
1. Stripe Dashboard → Developers → **Webhooks** → Add endpoint
2. **Endpoint URL:** `https://i24-ratings-api.onrender.com/stripe/webhook`
3. **Events to send:**
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. אחרי שמירה — תקבלי `whsec_...` חדש — הוסיפי אותו ל-Environment variables ב-Render

## 6. הפעלה מחדש של ה-Backend
```powershell
# אם רץ עכשיו — Ctrl+C
cd backend
py -3 -m uvicorn main:app --reload --port 8000
```

ב-startup תראי: `[startup] ✓ Stripe configured (live: False)`

## 7. בדיקה
1. נכנסי ל-`http://localhost:3000/account`
2. לחיצי **🚀 שדרוג ל-Pro · ₪990/חודש**
3. תועברי ל-Stripe Checkout (כתובת `checkout.stripe.com/...`)
4. **כרטיס לבדיקה:**
   - Number: `4242 4242 4242 4242`
   - Expiry: כל תאריך עתידי (למשל `12/30`)
   - CVC: כל 3 ספרות (למשל `123`)
   - ZIP: כל קוד-מיקוד
5. **Pay** — תועברי בחזרה ל-`/account?success=1`
6. אם stripe listen רץ — הסטטוס יתעדכן תוך 2-3 שניות (Refresh)
7. תראי **"✅ Pro · Trial"** במקום כפתור השדרוג

## טיפים
- כל הכרטיסים בבדיקה: https://stripe.com/docs/testing#cards
- לסימולציה של דחייה: `4000 0000 0000 0002`
- לסימולציה של פג תוקף: `4000 0000 0000 0069`
- כדי לראות את החיוב — Stripe Dashboard → Payments

## מה הלאה
- כשנפרוס ל-Render, נצטרך לעדכן ב-Environment שם את 3 משתני Stripe + URL חדש ל-webhook
- מעבר ל-Live: יוצרים מוצר זהה ב-Live mode, מעדכנים את ה-keys, ועוסק פטור מוציא חשבונית (תלוי ב-iCount/Greeninvoice integration שניטמע בשלב 5)
