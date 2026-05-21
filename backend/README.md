# Backend — FastAPI ML Service

שירות חיזוי רייטינג חי, מבוסס HistGradientBoosting. שכבת ה-Backend של ארכיטקטורת 3-השכבות.

## 📁 קבצים
- `main.py` — FastAPI app (`/health`, `/predict`)
- `prediction_logic.py` — חישוב lag features ואי-ודאות
- `requirements.txt` — תלויות (FastAPI, sklearn, pandas, psycopg)
- `render.yaml` — תצורת פריסה ל-Render.com

## 🧪 הרצה מקומית
```powershell
cd backend
py -3 -m pip install -r requirements.txt
py -3 -m uvicorn main:app --reload --port 8000
```
- בריאות: http://localhost:8000/health
- תיעוד אינטראקטיבי: http://localhost:8000/docs
- חיזוי: POST http://localhost:8000/predict

### דוגמה לקריאה
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "program_name": "קבינט שישי",
    "target_date": "2026-06-12",
    "start_time": "19:50:00",
    "end_time": "22:00:00",
    "scenario": "routine",
    "status": "שידור חי"
  }'
```

## ☁️ פריסה ל-Render

### צעד 1: הרשמה (~3 דק')
1. https://render.com → **Sign in with GitHub**
2. אישור — Render יראה את הריפו `i24-ratings-forecast`

### צעד 2: יצירת השירות (~1 דק')
1. **Dashboard → "New +" → "Web Service"**
2. **Connect Repository:** `DataScienceOritAlma/i24-ratings-forecast`
3. Render יזהה אוטומטית את `backend/render.yaml` — אישור

### צעד 3: משתני סביבה
1. בעמוד השירות → **Environment** (תפריט שמאל)
2. **Add Environment Variable:**
   - Key: `DATABASE_URL`
   - Value: אותו ערך כמו ב-`.env` המקומי (Session Pooler עם הסיסמה)
3. **Save Changes** → Render יבנה אוטומטית

### צעד 4: ממתינים לבנייה
- בנייה ראשונה: ~5-7 דק' (התקנת sklearn + pandas)
- כתובת חיה: `https://i24-ratings-api.onrender.com`
- בדיקה: `https://i24-ratings-api.onrender.com/health`

### הערה על Free tier
- 750 שעות/חודש
- **השירות נרדם אחרי 15 דק' חוסר-פעילות** ⚠️
- בקריאה ראשונה אחרי השינה: 30-60 שניות "התעוררות"
- בייצור: לעבור ל-Starter ($7/חודש, לא נרדם)

## 🔐 אבטחה (TODO לפני Launch)
- [ ] להוסיף JWT verification (מבדיקת token של Supabase Auth)
- [ ] לצמצם CORS לדומיינים ספציפיים (לא `*`)
- [ ] rate limiting (פר-משתמש, פר-IP)
- [ ] לשמור כל חיזוי ב-`predictions` table (RLS דרך service-role)
