# i24 Ratings Forecast — Landing Page

דף נחיתה סטטי לפרוייקט, כתוב ב-**Vanilla JavaScript** (ללא frameworks).

## פריסה ל-GitHub Pages

1. Push את התיקייה `docs/` לריפו ב-GitHub.
2. בריפו: **Settings → Pages**.
3. **Source:** `Deploy from a branch`.
4. **Branch:** `main`, **Folder:** `/docs`.
5. שמור. תוך 1-2 דקות הדף יהיה זמין ב:
   `https://datascienceoritalma.github.io/i24-ratings-forecast/`

## מבנה הקבצים

```
docs/
├── index.html       # מבנה הדף + תוכן
├── style.css        # עיצוב מאוחד עם Heebo + RTL
├── script.js        # אנימציות leaderboard + count-up + smooth scroll
├── infographic.html # דאטה סיינס בציורים + מילון משולב — 23 SVG, לחיצה→modal 3 רמות
├── infographic.css  # עיצוב הציורים + modal + helpers ל-SVG + הדפסה/PDF
├── viz/             # 8 תרשימי PNG מ-algo_visualizations.py
│   ├── 01_bias_variance.png
│   ├── 02_chronological_split.png
│   └── ...
└── README.md        # קובץ זה
```

## טכנולוגיות

- **HTML5** — semantic markup, RTL
- **CSS3** — Grid, Flexbox, gradients, CSS variables, backdrop-filter
- **Vanilla JS** — IntersectionObserver, requestAnimationFrame
- **Heebo Font** — Google Fonts
- **0 dependencies, 0 build step**

## פיתוח מקומי

לפתיחה מקומית:
```powershell
# Python pre-installed on most systems
cd docs
py -3 -m http.server 8000
```
ואז: `http://localhost:8000`
