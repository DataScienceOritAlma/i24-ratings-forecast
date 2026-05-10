# -*- coding: utf-8 -*-
"""Future-prediction page — analyst form for predicting a program's rating
on a hypothetical future date."""
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.auth import require_password
from utils.data_loader import load_processed
from utils.predict import (predict_with_uncertainty, date_to_weekday_he,
                            estimate_reception_pct, hour_to_daypart)

st.set_page_config(page_title="חיזוי עתידי | i24", page_icon="🎯", layout="wide")

st.markdown("""
<style>
.main, .block-container, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stMetricValue"] { direction: ltr; text-align: right; }
</style>
""", unsafe_allow_html=True)

require_password()

st.title("🎯 חיזוי תוכנית עתידית")
st.caption("בחר תוכנית, תאריך, ושעה — ותקבל חיזוי רייטינג עם רווח-בטחון.")

df = load_processed()

# ---------- Form ----------
st.markdown("### 📋 פרטי השידור המתוכנן")

col1, col2 = st.columns(2)

with col1:
    # Existing or new program?
    program_mode = st.radio(
        "התוכנית",
        options=["תוכנית קיימת (יש לה היסטוריה)", "תוכנית חדשה (אין לה היסטוריה)"],
        horizontal=True,
    )
    if program_mode == "תוכנית קיימת (יש לה היסטוריה)":
        existing_progs = sorted(df["שם תוכנית_מקור"].dropna().unique())
        program = st.selectbox("שם התוכנית", options=existing_progs, index=0)
    else:
        program = st.text_input("שם תוכנית חדשה (לא היה בעבר)", value="תוכנית חדשה")
        st.caption("⚠️ Cold-start: בלי היסטוריה הדיוק יורד. נשתמש בממוצע גלובלי.")

    # Target date — default 1 month from latest data
    last_date = df["תאריך שידור"].max()
    default_target = last_date + timedelta(days=30)
    target_date = st.date_input(
        "תאריך השידור המתוכנן",
        value=default_target.date(),
        min_value=(last_date + timedelta(days=1)).date(),
        max_value=(last_date + timedelta(days=180)).date(),
    )
    weekday_he = date_to_weekday_he(target_date)
    st.caption(f"יום בשבוע: **{weekday_he}**")

with col2:
    hour = st.number_input("שעת התחלה (0-23)", min_value=0, max_value=23, value=20)
    daypart = hour_to_daypart(hour)
    st.caption(f"חלק-יום: **{daypart}**")

    status = st.selectbox(
        "סטטוס תוכנית",
        options=["חי", "ש.ח", "לקט", "מיוחד-מבזק", "חג"],
        index=0,
    )
    is_rerun = status in ["ש.ח", "לקט"]

    reception = estimate_reception_pct(target_date)
    st.caption(f"reception_pct מוערך: **{reception:.2f}** (פאנל-נושם)")

st.divider()

# ---------- Predict ----------
if st.button("🚀 חזה רייטינג", type="primary", use_container_width=True):
    with st.spinner("מחשב חיזוי..."):
        result = predict_with_uncertainty(
            history_df=df,
            program_name=program,
            target_date=target_date,
            hour=hour,
            status=status,
            is_rerun=is_rerun,
        )

    # ---------- Display result ----------
    st.markdown("## 📊 התוצאה")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🎯 רייטינג צפוי", f"{result['point']:.3f}",
                  help="חיזוי המודל HistGradientBoosting")
    with c2:
        st.metric("⬇️ גבול תחתון", f"{result['ci_low']:.3f}",
                  help="הקצה הנמוך של רווח-הבטחון")
    with c3:
        st.metric("⬆️ גבול עליון", f"{result['ci_high']:.3f}",
                  help="הקצה הגבוה של רווח-הבטחון")

    # Visualization
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["חיזוי"],
        y=[result["point"]],
        error_y=dict(
            type="data",
            symmetric=False,
            array=[result["ci_high"] - result["point"]],
            arrayminus=[result["point"] - result["ci_low"]],
        ),
        marker_color="#0066cc",
        width=0.3,
    ))
    fig.update_layout(
        height=350,
        yaxis_title="רייטינג צפוי",
        showlegend=False,
        title=f"חיזוי ל-{program} | {weekday_he} {pd.to_datetime(target_date).strftime('%d/%m/%Y')} | {hour:02d}:00",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------- Diagnostics ----------
    st.markdown("### 🔍 פירוט")

    cd1, cd2 = st.columns(2)
    with cd1:
        st.markdown("**📈 ביטחון בחיזוי:**")
        if result["is_cold_start"]:
            st.warning("⚠️ **Cold-start** — לתוכנית הזו אין היסטוריית שידורים. הדיוק נמוך משמעותית.")
        else:
            st.info(f"📺 התוכנית '{program}' שודרה **{result['lag_program_n']}** פעמים בעבר.")
        st.write(f"**מספר שידורים דומים בעבר ברצועה:** {result['slot_n']}")
        st.write(f"**סטיית תקן ברצועה:** ±{result['slot_std']:.3f}")

    with cd2:
        st.markdown("**🎓 איך נחושב החיזוי:**")
        st.write("""
        - **שלב 1:** המערכת חישבה את ההיסטוריה של התוכנית והרצועה
        - **שלב 2:** המודל (HistGradientBoosting) רץ על המאפיינים
        - **שלב 3:** רווח-הבטחון נגזר מהשונות ההיסטורית באותה רצועה
        """)
        feats = result["features_used"]
        st.write(f"**lag_program_mean:** {feats['lag_program_mean']:.3f}")
        st.write(f"**lag_slot_mean:** {feats['lag_slot_mean']:.3f}")
        st.write(f"**lag_status_slot_mean:** {feats['lag_status_slot_mean']:.3f}")

    st.divider()

    # ---------- Historical context ----------
    st.markdown("### 📚 הקשר היסטורי")

    if not result["is_cold_start"]:
        prog_hist = df[df["שם תוכנית_מקור"] == program].sort_values("תאריך שידור")
        if len(prog_hist) > 0:
            fig2 = px.line(prog_hist, x="תאריך שידור", y="רייטינג",
                           title=f"היסטוריית רייטינג של '{program}'",
                           markers=True, height=300)
            # Add prediction point
            fig2.add_trace(go.Scatter(
                x=[pd.to_datetime(target_date)],
                y=[result["point"]],
                mode="markers",
                marker=dict(color="orange", size=15, symbol="star"),
                name="חיזוי עתידי",
            ))
            fig2.add_shape(
                type="line",
                x0=pd.to_datetime(target_date), x1=pd.to_datetime(target_date),
                y0=result["ci_low"], y1=result["ci_high"],
                line=dict(color="orange", width=4),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ---------- Caveats ----------
    st.markdown("### ⚠️ מה המודל לא יודע")
    st.warning("""
    **מגבלות החיזוי:**
    - **אירועים בלתי-צפויים** — שום מודל לא יחזה רייטינג של מהדורה במהלך מבצע צבאי שטרם החל.
      תקרת הביצועים של המודל היא MAE=0.74 באירועים כאלה (לעומת 0.19 בשגרה).
    - **תוכניות חדשות** (cold-start) — בלי היסטוריה החיזוי הוא הימור מבוסס-ממוצעים.
    - **רחוק יותר מחודש** — ככל שהתאריך רחוק יותר, drift דמוגרפי / מתחרים מקטין דיוק.
    """)
