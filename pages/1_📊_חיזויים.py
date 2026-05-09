# -*- coding: utf-8 -*-
"""Predictions browser — filter by date, day, time, event, program."""
import streamlit as st
import pandas as pd
import plotly.express as px

from utils.auth import require_password
from utils.data_loader import load_predictions, best_model_column

st.set_page_config(page_title="חיזויים | i24", page_icon="📊", layout="wide")
st.markdown("""
<style>
.main, .block-container, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stMetricValue"] { direction: ltr; text-align: right; }
</style>
""", unsafe_allow_html=True)

require_password()

st.title("📊 חיזויים — דפדוף וסינון")
st.caption("חיזויי המודל המוביל (HistGradientBoosting) על תקופת המבחן")

preds = load_predictions()
pred_col = best_model_column()

# ---------- Sidebar filters ----------
st.sidebar.header("מסננים")

dates = pd.to_datetime(preds["תאריך שידור"])
min_d, max_d = dates.min().date(), dates.max().date()
date_range = st.sidebar.date_input("טווח תאריכים", value=(min_d, max_d),
                                    min_value=min_d, max_value=max_d)

days = st.sidebar.multiselect("יום שבוע",
                               options=sorted(preds["יום שידור"].dropna().unique()),
                               default=None)

dayparts = st.sidebar.multiselect("חלקי-יום",
                                   options=sorted(preds["חלקי-יום"].dropna().unique()),
                                   default=None)

events = st.sidebar.multiselect("אירוע מיוחד",
                                 options=sorted(preds["אירוע_מיוחד"].dropna().unique()),
                                 default=None)

programs = st.sidebar.multiselect("שם תוכנית (מקור)",
                                   options=sorted(preds["שם תוכנית_מקור"].dropna().unique()),
                                   default=None)

# ---------- Apply filters ----------
filtered = preds.copy()
if isinstance(date_range, tuple) and len(date_range) == 2:
    d1, d2 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[(filtered["תאריך שידור"] >= d1) & (filtered["תאריך שידור"] <= d2)]
if days:
    filtered = filtered[filtered["יום שידור"].isin(days)]
if dayparts:
    filtered = filtered[filtered["חלקי-יום"].isin(dayparts)]
if events:
    filtered = filtered[filtered["אירוע_מיוחד"].isin(events)]
if programs:
    filtered = filtered[filtered["שם תוכנית_מקור"].isin(programs)]

# ---------- Summary metrics ----------
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("שורות נבחרות", f"{len(filtered):,}")
with c2:
    if len(filtered) > 0:
        mae = (filtered["רייטינג"] - filtered[pred_col]).abs().mean()
        st.metric("MAE על הסלקציה", f"{mae:.3f}")
with c3:
    if len(filtered) > 0:
        st.metric("ר' ממוצע (אמיתי)", f"{filtered['רייטינג'].mean():.3f}")
with c4:
    if len(filtered) > 0:
        st.metric("ר' ממוצע (חזוי)", f"{filtered[pred_col].mean():.3f}")

st.divider()

# ---------- Visualization: actual vs predicted scatter ----------
if len(filtered) > 0:
    st.subheader("📈 חזוי מול אמיתי")
    fig = px.scatter(
        filtered, x=pred_col, y="רייטינג",
        color="אירוע_מיוחד" if "אירוע_מיוחד" in filtered else None,
        hover_data=["שם תוכנית", "תאריך שידור", "יום שידור", "שעת התחלה"],
        labels={pred_col: "חזוי", "רייטינג": "אמיתי"},
        height=500,
    )
    # Diagonal y=x reference line
    max_val = max(filtered["רייטינג"].max(), filtered[pred_col].max())
    fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                  line=dict(color="gray", dash="dash"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("אין נתונים להצגה — נסי לשנות מסננים.")

st.divider()

# ---------- Table ----------
st.subheader("📋 טבלת חיזויים")
display_cols = ["שם תוכנית", "יום שידור", "תאריך שידור", "שעת התחלה",
                "חלקי-יום", "סטטוס תוכנית", "אירוע_מיוחד",
                "רייטינג", pred_col]
display_cols = [c for c in display_cols if c in filtered.columns]
df_show = filtered[display_cols].copy()
if "תאריך שידור" in df_show:
    df_show["תאריך שידור"] = pd.to_datetime(df_show["תאריך שידור"]).dt.strftime("%Y-%m-%d")
df_show = df_show.rename(columns={pred_col: "חזוי"})
df_show["שגיאה"] = (df_show["רייטינג"] - df_show["חזוי"]).round(3)
st.dataframe(df_show, use_container_width=True, height=500)

st.caption(f"מודל בשימוש: {pred_col}")
