# -*- coding: utf-8 -*-
"""i24 Ratings Forecast — main app (home page).

Run locally:
    streamlit run app.py

Data is uploaded by the user at runtime — no data is bundled with the deployment.
"""
import streamlit as st

from utils.auth import require_password
from utils.data_loader import (
    is_data_loaded, render_upload_panel,
    get_processed, get_predictions, get_metrics,
)

st.set_page_config(
    page_title="i24 חיזוי רייטינג",
    page_icon="📺",
    layout="wide",
)

# Hebrew RTL CSS
st.markdown("""
<style>
.main, .block-container, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
.stMarkdown, .stMetric, .stDataFrame, .stTable { direction: rtl; }
[data-testid="stMetricValue"] { direction: ltr; text-align: right; }
h1, h2, h3, h4 { direction: rtl; text-align: right; }
.stButton > button { direction: rtl; }
</style>
""", unsafe_allow_html=True)

require_password()

# ---------- Header ----------
st.title("📺 i24 — מערכת חיזוי רייטינג")
st.caption("חיזוי רייטינג לפני שידור | מבוסס על 9,746 שורות, 19 מודלים שנבדקו")

# ---------- Upload gate ----------
if not is_data_loaded():
    render_upload_panel()
    st.divider()
    st.subheader("🎯 על הפרוייקט")
    st.markdown("""
    מערכת חיזוי שמנבאת את **רייטינג** התוכנית **לפני** שהיא משודרת.

    **שלבים שהושלמו:**
    - ✅ EDA מלא + 19 פיצ'רים מהונדסים
    - ✅ תיוג מדויק של 17 אירועים (חגים, ביטחוני, עונות)
    - ✅ השוואה של **19 מודלים** מ-7 משפחות
    - ✅ ניתוח שגיאות לפי תוכנית, יום, חלק-יום, אירוע

    **המודל המוביל:** `HistGradientBoosting` עם MAE = 0.263, R² = 0.603
    """)
    st.stop()

# ---------- Data loaded — show full app ----------
df = get_processed()
preds = get_predictions()
summary = get_metrics()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("שורות בדאטה", f"{len(df):,}")
with c2:
    st.metric("תוכניות ייחודיות", df["שם תוכנית_מקור"].nunique())
with c3:
    if summary is not None and len(summary):
        best_mae = summary["MAE"].min()
        st.metric("MAE של המודל המוביל", f"{best_mae:.3f}")
    else:
        st.metric("MAE של המודל המוביל", "—")
with c4:
    if summary is not None and len(summary):
        best_r2 = summary.loc[summary["MAE"].idxmin(), "R²"]
        st.metric("R² של המודל המוביל", f"{best_r2:.3f}")
    else:
        st.metric("R² של המודל המוביל", "—")

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
    if summary is not None and len(summary):
        top10 = summary.nsmallest(10, "MAE")[["MAE", "RMSE", "R²"]]
        st.dataframe(top10, use_container_width=True)
    else:
        st.info("העלי את `predictions_all.xlsx` עם גליון 'סיכום מטריקות' לראות leaderboard")

st.divider()

# ---------- Navigation hint ----------
st.subheader("🧭 ניווט")
st.markdown("""
השתמשו בתפריט הצד כדי לעבור בין המסכים:

- **📊 חיזויים** — דפדוף בכל החיזויים על מבחן (פברואר–אפריל 2026)
- **📺 כרטיס תוכנית** — drill-down לתוכנית בודדת: היסטוריה, חיזויים, אירועים
- **🔍 השוואת מודלים** — איך כל מודל ביצע, איפה כל אחד נכשל
""")

# ---------- Reset data option ----------
with st.sidebar:
    st.divider()
    if st.button("🔄 טען נתונים מחדש"):
        for key in ["df_processed", "df_predictions", "df_metrics", "df_events"]:
            st.session_state.pop(key, None)
        st.rerun()

st.divider()
st.caption("פותח באמצעות Streamlit | מודלים: scikit-learn + LightGBM + XGBoost + CatBoost")
