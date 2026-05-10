# -*- coding: utf-8 -*-
"""i24 Ratings Forecast — main app (home page).

Run locally:
    streamlit run app.py
"""
import streamlit as st

from utils.auth import require_password
from utils.data_loader import load_processed, load_predictions, load_metrics_summary
from utils.style import apply_style

st.set_page_config(
    page_title="i24 חיזוי רייטינג",
    page_icon="📺",
    layout="wide",
)

apply_style()
require_password()

# ---------- Header ----------
st.title("📺 i24 — מערכת חיזוי רייטינג")
st.caption("חיזוי רייטינג לפני שידור | מבוסס על 9,746 שורות, 19 מודלים שנבדקו")

# ---------- Quick stats ----------
df = load_processed()
preds = load_predictions()
summary = load_metrics_summary()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("שורות בדאטה", f"{len(df):,}")
with c2:
    st.metric("תוכניות ייחודיות", df["שם תוכנית_מקור"].nunique())
with c3:
    best_mae = summary["MAE"].min()
    st.metric("MAE של המודל המוביל", f"{best_mae:.3f}")
with c4:
    best_r2 = summary.loc[summary["MAE"].idxmin(), "R²"]
    st.metric("R² של המודל המוביל", f"{best_r2:.3f}")

st.divider()

# ---------- Two columns: project summary + model leaderboard ----------
left, right = st.columns([1, 1])

with left:
    st.subheader("🎯 על הפרוייקט")
    st.markdown("""
    מערכת חיזוי שמנבאת את **רייטינג** התוכנית **לפני** שהיא משודרת.

    **שלבים שהושלמו:**
    - ✅ EDA מלא + 19 פיצ'רים מהונדסים
    - ✅ תיוג מדויק של 17 אירועים (חגים, ביטחוני, עונות)
    - ✅ השוואה של **19 מודלים** מ-7 משפחות
    - ✅ ניתוח שגיאות לפי תוכנית, יום, חלק-יום, אירוע

    **המודל המוביל:** `HistGradientBoosting` עם MAE = 0.263, R² = 0.603

    **תקרת ביצועים:** drift של אירועים בלתי-צפויים (מבצע שאגת הארי, מתקפה איראנית).
    """)

with right:
    st.subheader("🏆 דירוג המודלים (Top 10)")
    top10 = summary.nsmallest(10, "MAE")[["MAE", "RMSE", "R²"]]
    st.dataframe(top10, use_container_width=True)

st.divider()

# ---------- Navigation hint ----------
st.subheader("🧭 ניווט")
st.markdown("""
השתמשו בתפריט הצד כדי לעבור בין המסכים:

- **📊 חיזויים** — דפדוף בכל החיזויים על מבחן (פברואר–אפריל 2026)
- **📺 כרטיס תוכנית** — drill-down לתוכנית בודדת: היסטוריה, חיזויים, אירועים
- **🔍 השוואת מודלים** — איך כל מודל ביצע, איפה כל אחד נכשל
""")

st.divider()
st.caption("פותח באמצעות Streamlit | מודלים: scikit-learn + LightGBM + XGBoost + CatBoost")
