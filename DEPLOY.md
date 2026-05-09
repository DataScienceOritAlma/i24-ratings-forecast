# 🚀 הוראות פריסה — צעד-אחר-צעד

מסמך זה מסביר איך להעלות את הפרוייקט לריפו פרטי ב-GitHub ולהפעיל אותו על Streamlit Community Cloud עם URL לשיתוף.

---

## שלב 1: יצירת ריפו פרטי ב-GitHub

### אופציה A: דרך אתר GitHub (מומלץ — הכי פשוט)

1. כנסי ל-https://github.com/new
2. **Repository name:** `i24-ratings-forecast` (או כל שם שתבחרי)
3. **Description:** `i24 TV ratings forecast — Streamlit app`
4. **Privacy:** סמני **🔒 Private** (חשוב!)
5. **כן/לא** ל-`Add a README file` — סמני **לא** (יש לנו כבר)
6. **כן/לא** ל-`Add .gitignore` — סמני **לא** (יש לנו כבר)
7. לחצי **Create repository**

GitHub יציג לך עמוד עם הוראות. תעתיקי את ה-URL של הריפו (משהו כמו `https://github.com/YOUR_USERNAME/i24-ratings-forecast.git`).

### אופציה B: דרך GitHub CLI (אם רוצה אוטומציה)

```powershell
# התקנה חד-פעמית
winget install GitHub.cli

# התחברות
gh auth login

# יצירת ריפו פרטי + push בפעולה אחת
cd "D:\Users\user\Desktop\Claude\projects\פרוייקט I24"
gh repo create i24-ratings-forecast --private --source=. --push
```

---

## שלב 2: דחיפת הקוד לריפו

לאחר שיש לך URL של ריפו ריק (אופציה A), הריצי בטרמינל:

```powershell
cd "D:\Users\user\Desktop\Claude\projects\פרוייקט I24"

# קישור הריפו המקומי לריפו ב-GitHub
git remote add origin https://github.com/YOUR_USERNAME/i24-ratings-forecast.git

# שינוי שם ענף ראשי ל-main (אם צריך)
git branch -M main

# push ראשון
git push -u origin main
```

תתבקשי להזין שם משתמש וסיסמה/PAT (Personal Access Token).
**שימי לב:** GitHub כבר לא מקבל סיסמת חשבון לפעולות git — צריך PAT.
ליצירת PAT: https://github.com/settings/tokens (`Generate new token (classic)` → סמני `repo`).

---

## שלב 3: פריסה ל-Streamlit Community Cloud

Streamlit Community Cloud **תומך בריפואים פרטיים** באופן חינמי, ובלבד שמתחברים עם GitHub.

1. כנסי ל-https://share.streamlit.io
2. **Sign in with GitHub** — אשרי הרשאות לקרוא מהריפו הפרטי שלך
3. לחצי **New app**
4. **Repository:** בחרי `YOUR_USERNAME/i24-ratings-forecast`
5. **Branch:** `main`
6. **Main file path:** `app.py`
7. **App URL:** Streamlit יציע URL כמו `i24-ratings-forecast.streamlit.app` — שני אם רוצה
8. לחצי **Advanced settings** ← זה הצעד הקריטי:
   - תחת **Secrets** הזיני:
     ```toml
     APP_PASSWORD = "הסיסמה-שתשלחי-לאנשים"
     ```
   - בחרי Python version: 3.11 (יציב)
9. לחצי **Deploy**

הפריסה לוקחת ~3-5 דקות. תקבלי URL כמו:
```
https://i24-ratings-forecast.streamlit.app
```

---

## שלב 4: שיתוף

### למי שרוצה לתת גישה
שלחי לה(ם):
- **URL:** `https://i24-ratings-forecast.streamlit.app`
- **סיסמה:** [הסיסמה שהגדרת ב-Secrets]

הם יקלידו את הסיסמה במסך הראשון וייכנסו.

### חשוב לזכור
- הסיסמה היא **שכבת הגנה יחידה**. אל תפיצי אותה ברבים.
- אם רוצה להחליף סיסמה: עדכני ב-Streamlit Cloud → Secrets, האפליקציה תתחיל מחדש אוטומטית.
- אם רוצה לבטל גישה לכולם בבת-אחת: שני סיסמה.

---

## שלב 5: עדכוני קוד

כל פעם שתשני קוד וב-`git push` — Streamlit Cloud יבחין אוטומטית ויעלה גרסה חדשה תוך 1-2 דקות.

```powershell
git add .
git commit -m "תיאור השינוי"
git push
```

---

## בעיות נפוצות

### ה-build נכשל ב-Streamlit Cloud
- בדקי את הלוג ב-Streamlit Cloud (כפתור "Manage app" → "Logs")
- בעיה נפוצה: גרסה לא תואמת ב-`requirements.txt`. נסי להוריד את `==X.Y.Z` ולתת ל-pip לבחור.

### האפליקציה מבקשת סיסמה שוב כל ניווט
- זה רק במצב development (`streamlit run` לוקאלי). בענן ה-session state נשמר.

### Streamlit Cloud לא מצליח לטעון את האקסל
- וידאי שהקובץ קומיט לריפו (`git ls-files | grep .xlsx`).
- אם הקובץ גדול מ-100MB — GitHub יחסום אותו, צריך Git LFS.

### רוצה להוסיף עוד אנשים עם הרשאות שונות
- כעת יש סיסמה אחת לכולם.
- אם רוצה auth אמיתי (למשל login עם Google), שדרגי ל-`streamlit_authenticator` או Streamlit Teams.

---

## חלופה אם Streamlit Community Cloud לא מתאים

- **Render** (https://render.com) — חינמי ל-free tier, תומך ב-private repos.
- **Railway** (https://railway.app) — קל לפריסה.
- **HuggingFace Spaces** — חינמי, תומך ב-Streamlit, יכול להיות פרטי.
- **Streamlit Teams** — בתשלום, מציע auth מתקדם.
