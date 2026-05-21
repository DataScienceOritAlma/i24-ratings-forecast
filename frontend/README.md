# Frontend — i24 Ratings Forecast

Next.js 15 + TypeScript + Tailwind + Supabase Auth. שכבת ה-Frontend של ארכיטקטורת 3-השכבות.

## 📁 קבצים עיקריים
- `app/layout.tsx` — RTL/עברית · Heebo font · global styles
- `app/page.tsx` — מסך התחברות/הרשמה (Supabase Auth)
- `app/dashboard/page.tsx` — לוח החיזוי: טופס + תוצאה
- `lib/supabase.ts` — Supabase client
- `lib/api.ts` — קריאות ל-Backend (`/predict`)

## 🧪 הרצה מקומית

### צעד 1: התקנה (פעם אחת, ~2 דק')
```powershell
cd frontend
npm install
```

### צעד 2: env vars
הקובץ `.env.local` כבר נוצר עם הערכים הנכונים.

### צעד 3: ודאי שה-Backend רץ
בטרמינל נפרד:
```powershell
cd backend
py -3 -m uvicorn main:app --reload --port 8000
```

### צעד 4: הרץ את ה-Frontend
```powershell
npm run dev
```
→ פתחי http://localhost:3000

## 🔐 זרימה
1. נרשמת/מתחברת ב-`/` (Supabase Auth — email + סיסמה)
2. הסכמה שולחת מייל אישור (פותרים בהגדרות Supabase: Auth → Email → אפשר לבטל confirmation בפיתוח)
3. אחרי התחברות מוצלחת → `/dashboard`
4. מילוי טופס + לחיצה על "חשב תחזית" → קריאה ל-FastAPI → תוצאה

## ☁️ פריסה ל-Vercel (בעתיד)
```powershell
npx vercel
```
- מתחבר אוטומטית ל-GitHub
- צריך להגדיר env vars ב-Vercel dashboard (אותם כמו `.env.local`)
- אבל לשנות `NEXT_PUBLIC_API_URL` לכתובת ה-Render בפרודקשן

## 📌 TODO לפני Launch
- [ ] לחבר את הדשבורד לטבלת `predictions` (שמירת היסטוריה)
- [ ] לחבר ארגון ל-Auth (יצירת `organizations` row אוטומטית בהרשמה)
- [ ] להוסיף מסך היסטוריית-תחזיות
- [ ] להוסיף מסך חשבון + שדרוג ל-Pro (Stripe — שלב 4)
- [ ] להוסיף Auth callback page (אחרי email confirmation)
