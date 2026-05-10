# -*- coding: utf-8 -*-
"""Program drill-down: history, predictions, error pattern."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.auth import require_password
from utils.data_loader import load_processed, load_predictions, best_model_column
from utils.style import apply_style

st.set_page_config(page_title="כרטיס תוכנית | i24", page_icon="📺", layout="wide")
apply_style()
require_password()

st.title("📺 כרטיס תוכנית")
st.caption("בחרי תוכנית כדי לראות היסטוריה, חיזויים, ושגיאות")

df = load_processed()
preds = load_predictions()
pred_col = best_model_column()

# ---------- Program selector — only programs that have predictions ----------
progs_with_preds = sorted(preds["שם תוכנית_מקור"].dropna().unique())
program = st.selectbox(
    f"בחרי תוכנית-מקור ({len(progs_with_preds)} תוכניות עם חיזויים)",
    options=progs_with_preds,
    index=0,
    help="מוצגות רק תוכניות שיש להן חיזויים בקובץ predictions_all.xlsx",
)

prog_hist = df[df["שם תוכנית_מקור"] == program].sort_values("תאריך שידור").copy()
prog_test = preds[preds["שם תוכנית_מקור"] == program].sort_values("תאריך שידור").copy()

if len(prog_hist) == 0:
    st.warning("אין נתונים לתוכנית זו.")
    st.stop()

# ---------- Summary cards ----------
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("שידורים סה\"כ", len(prog_hist))
with c2:
    st.metric("ר' ממוצע (היסטורי)", f"{prog_hist['רייטינג'].mean():.3f}")
with c3:
    st.metric("ר' מקסימלי", f"{prog_hist['רייטינג'].max():.3f}")
with c4:
    if len(prog_test) > 0:
        mae = (prog_test["רייטינג"] - prog_test[pred_col]).abs().mean()
        st.metric("MAE על מבחן", f"{mae:.3f}")
    else:
        st.metric("MAE על מבחן", "—")

st.divider()

# ---------- Time series: actual + predicted ----------
st.subheader("📈 רייטינג לאורך זמן")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=prog_hist["תאריך שידור"], y=prog_hist["רייטינג"],
    mode="lines+markers", name="אמיתי (היסטורי)",
    line=dict(color="#0066cc"),
    hovertext=prog_hist["שם תוכנית"],
))
if len(prog_test) > 0:
    fig.add_trace(go.Scatter(
        x=prog_test["תאריך שידור"], y=prog_test[pred_col],
        mode="markers", name="חזוי (מבחן)",
        marker=dict(color="orange", size=10, symbol="diamond"),
    ))
# Highlight events
events_in_data = prog_hist[prog_hist["אירוע_מיוחד"].notna() & (prog_hist["אירוע_מיוחד"] != "—")]
if len(events_in_data) > 0:
    fig.add_trace(go.Scatter(
        x=events_in_data["תאריך שידור"], y=events_in_data["רייטינג"],
        mode="markers", name="אירוע מיוחד",
        marker=dict(color="red", size=14, symbol="star", line=dict(color="darkred", width=1)),
        hovertext=events_in_data["אירוע_מיוחד"],
    ))
fig.update_layout(
    height=450,
    xaxis_title="תאריך",
    yaxis_title="רייטינג",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Day-of-week breakdown ----------
left, right = st.columns(2)

with left:
    st.subheader("📅 ממוצע לפי יום שבוע")
    dow_order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    by_dow = prog_hist.groupby("יום שידור", observed=True)["רייטינג"].agg(["mean", "count"]).reindex(dow_order)
    by_dow = by_dow.dropna()
    if len(by_dow) > 0:
        fig2 = px.bar(by_dow, y="mean", labels={"mean": "ר' ממוצע", "יום שידור": "יום"})
        fig2.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

with right:
    st.subheader("⏰ ממוצע לפי שעה")
    by_hr = prog_hist.groupby("שעת התחלה_שעה")["רייטינג"].agg(["mean", "count"])
    if len(by_hr) > 0:
        fig3 = px.bar(by_hr, y="mean", labels={"mean": "ר' ממוצע", "שעת התחלה_שעה": "שעה"})
        fig3.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------- Test predictions table ----------
if len(prog_test) > 0:
    st.subheader("🔍 חיזויים על מבחן (פברואר–אפריל 2026)")
    show_cols = ["שם תוכנית", "תאריך שידור", "יום שידור", "שעת התחלה",
                 "אירוע_מיוחד", "רייטינג", pred_col]
    show_cols = [c for c in show_cols if c in prog_test.columns]
    df_show = prog_test[show_cols].copy()
    df_show["תאריך שידור"] = pd.to_datetime(df_show["תאריך שידור"]).dt.strftime("%Y-%m-%d")
    df_show = df_show.rename(columns={pred_col: "חזוי"})
    df_show["שגיאה"] = (df_show["רייטינג"] - df_show["חזוי"]).round(3)
    st.dataframe(df_show, use_container_width=True)
else:
    st.info("התוכנית אינה כלולה בתקופת המבחן.")
