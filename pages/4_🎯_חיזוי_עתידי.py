# -*- coding: utf-8 -*-
"""Future-prediction page — exact time range + event selector.

User specifies start/end times (HH:MM) and optional special event;
the model returns a weighted-average prediction with a range.
"""
from datetime import datetime, time, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.auth import require_password
from utils.data_loader import load_processed
from utils.predict import (predict_time_range, get_program_profile,
                            date_to_weekday_he, hour_to_daypart)

st.set_page_config(page_title="חיזוי עתידי | i24", page_icon="🎯", layout="wide")
st.markdown("""
<style>
.main, .block-container, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stMetricValue"] { direction: ltr; text-align: right; }
.stExpander { border: 1px solid #e0e0e0; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

require_password()

st.title("🎯 חיזוי תוכנית עתידית")
st.caption("בחר תוכנית, תאריך, וטווח שעות מדוייק. רק 2 שדות חובה (תוכנית + תאריך) — השאר עם ברירות-מחדל חכמות.")

df = load_processed()

# ==========================================================================
# Section 1: Mandatory inputs (program + date)
# ==========================================================================
st.markdown("### 📋 פרטי החיזוי")

col1, col2 = st.columns([3, 2])

with col1:
    existing_progs = sorted(df["שם תוכנית_מקור"].dropna().unique())
    program = st.selectbox(
        "🎬 שם התוכנית *",
        options=existing_progs,
        index=existing_progs.index("קבינט שישי") if "קבינט שישי" in existing_progs else 0,
    )

with col2:
    last_date = df["תאריך שידור"].max()
    default_target = last_date + timedelta(days=30)
    target_date = st.date_input(
        "📅 תאריך השידור *",
        value=default_target.date(),
        min_value=(last_date + timedelta(days=1)).date(),
        max_value=(last_date + timedelta(days=365)).date(),
    )

# ---- Program profile preview ----
profile = get_program_profile(df, program)

# Compute typical start/end time from history
prog_hist = df[df["שם תוכנית_מקור"] == program]
typical_start_h = profile["typical_hour"]
# Estimate end time from typical duration in history
if "משך תוכנית_דק" in prog_hist.columns and len(prog_hist) > 0:
    typical_dur = int(prog_hist["משך תוכנית_דק"].median())
else:
    typical_dur = 60
typical_end_h = (typical_start_h + (typical_dur // 60)) % 24
typical_end_m = typical_dur % 60

with st.container(border=True):
    st.markdown(f"#### 📺 פרופיל היסטורי של *{program}*")
    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1:
        st.metric("שידורים בעבר", f"{profile['n_airings']:,}")
    with pc2:
        st.metric("רייטינג ממוצע", f"{profile['mean_rating']:.2f}")
    with pc3:
        st.metric("יום נפוץ", profile["typical_day"])
    with pc4:
        st.metric("שעה טיפוסית", f"{typical_start_h:02d}:00")

# ==========================================================================
# Section 2: Optional — exact time range
# ==========================================================================
st.markdown("### ⏰ שעת השידור (אופציונלי)")
st.caption(f"💡 ברירת-מחדל מבוססת על הזמן הטיפוסי של *{program}*. שני אם השידור מתוכנן בשעה שונה.")

tc1, tc2 = st.columns(2)
with tc1:
    start_time = st.time_input(
        "🕐 שעת התחלה",
        value=time(typical_start_h, 0),
        step=300,  # 5-minute increments
    )
with tc2:
    end_time = st.time_input(
        "🕓 שעת סיום",
        value=time(typical_end_h, typical_end_m),
        step=300,
    )

# Validate / show duration
def time_to_minutes(t):
    return t.hour * 60 + t.minute

duration_min = time_to_minutes(end_time) - time_to_minutes(start_time)
if duration_min <= 0:
    duration_min += 24 * 60  # wraps past midnight

if duration_min < 5:
    st.error("⚠️ הסיום חייב להיות אחרי ההתחלה. הגדירי טווח ארוך יותר.")
elif duration_min > 6 * 60:
    st.warning(f"⚠️ הטווח שלך ({duration_min} דק') ארוך מ-6 שעות — בטוח?")
else:
    st.caption(f"⏱️ משך מחושב: **{duration_min} דקות** "
               f"({duration_min // 60}h {duration_min % 60}m)")

# ==========================================================================
# Section 3: Optional — status + special event
# ==========================================================================
st.markdown("### ⚙️ אפשרויות נוספות (אופציונלי)")

ec1, ec2 = st.columns(2)

with ec1:
    status_options = [
        f"🤖 אוטומטי ({profile['typical_status']})",
        "חי", "ש.ח", "לקט", "מיוחד-מבזק", "חג",
    ]
    status_choice = st.selectbox("📡 סטטוס שידור", options=status_options, index=0)
    chosen_status = profile["typical_status"] if status_choice.startswith("🤖") else status_choice

with ec2:
    event_choice = st.selectbox(
        "🚨 אירוע מיוחד באותו יום?",
        options=[
            "ללא — שגרה",
            "🕊️ חג",
            "⚠️ אירוע ביטחוני",
            "🌍 אירוע מדיני",
            "⚽ אירוע ספורט",
            "📰 ברייקינג / מבזק",
        ],
        index=0,
    )

# Map event choice to flags
is_holiday = event_choice == "🕊️ חג"
is_security = event_choice in ["⚠️ אירוע ביטחוני", "🌍 אירוע מדיני", "📰 ברייקינג / מבזק"]
event_tag_map = {
    "🕊️ חג": "חג",
    "⚠️ אירוע ביטחוני": "ביטחוני",
    "🌍 אירוע מדיני": "מדיני",
    "📰 ברייקינג / מבזק": "ברייקינג",
}
event_tag = event_tag_map.get(event_choice, "—")

# ==========================================================================
# Section 4: Predict
# ==========================================================================
st.divider()

if duration_min < 5:
    st.button("🚀 חזה רייטינג", disabled=True, use_container_width=True)
elif st.button("🚀 חזה רייטינג", type="primary", use_container_width=True):
    with st.spinner("מחשב חיזוי..."):
        result = predict_time_range(
            history_df=df,
            program_name=program,
            target_date=target_date,
            start_hour=start_time.hour, start_min=start_time.minute,
            end_hour=end_time.hour, end_min=end_time.minute,
            status=chosen_status,
            is_holiday=is_holiday,
            is_security=is_security,
            event_tag=event_tag,
        )

    if result is None:
        st.error("❌ לא ניתן היה לחשב חיזוי. בדקי את הפרמטרים.")
    else:
        weekday_he = date_to_weekday_he(target_date)
        date_str = pd.to_datetime(target_date).strftime("%d/%m/%Y")

        st.markdown(f"## 📊 חיזוי ל-*{program}*")
        st.caption(
            f"{weekday_he} {date_str} | "
            f"{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')} ({result['duration_min']} דק') | "
            f"סטטוס: {chosen_status} | "
            f"אירוע: {event_choice}"
        )

        # Trend banner
        trend_pct = result["monthly_trend"]
        if abs(trend_pct) > 1:
            trend_emoji = "📈" if trend_pct > 0 else "📉"
            trend_label = "עולה" if trend_pct > 0 else "יורד"
            st.info(
                f"{trend_emoji} **טרנד חודשי {trend_label}: {abs(trend_pct):.1f}%/חודש** | "
                f"מרחק: {result['months_ahead']} חודשים | "
                f"מקדם תיקון: ×{result['trend_multiplier']}"
            )

        # 3 hero metrics
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            delta = result["weighted_avg"] - result["recent_mean_90d"]
            st.metric("🎯 חיזוי משוקלל",
                      f"{result['weighted_avg']:.2f}",
                      delta=f"{delta:+.2f} מ-90 ימים אחרונים",
                      help="ממוצע משוקלל לפי דקות בכל שעה בטווח")
        with rc2:
            st.metric("⬇️ תרחיש שמרני", f"{result['ci_low']:.2f}")
        with rc3:
            st.metric("⬆️ תרחיש אופטימי", f"{result['ci_high']:.2f}")

        st.caption(f"🔵 **ממוצע 90 ימים אחרונים** של {program}: **{result['recent_mean_90d']:.2f}** "
                   f"(לעומת ממוצע מלא: {profile['mean_rating']:.2f})")

        st.divider()

        # ----- Per-hour breakdown -----
        st.markdown("### 🕐 חלוקה לפי שעות בתוך הטווח")
        details = pd.DataFrame(result["predictions"])
        details["שעה"] = details["hour"].apply(lambda h: f"{h:02d}:00")
        details["דקות"] = details["minutes"]
        details["משקל"] = (details["weight"] * 100).round(0).astype(int).astype(str) + "%"
        details_display = details[["שעה", "דקות", "משקל", "point", "ci_low", "ci_high"]].copy()
        details_display.columns = ["שעה", "דקות בשעה זו", "משקל", "חיזוי", "שמרני", "אופטימי"]
        st.dataframe(details_display, use_container_width=True, hide_index=True)

        # Bar chart per hour with weights
        fig = px.bar(
            details, x="שעה", y="point",
            error_y=details["ci_high"] - details["point"],
            error_y_minus=details["point"] - details["ci_low"],
            text="weight",
            title="חיזוי לכל שעה בטווח (גובה = חיזוי, טקסט = משקל בממוצע)",
            height=350,
        )
        fig.update_traces(texttemplate="%{text:.0%}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ----- Historical context graph -----
        st.markdown("### 📈 הקשר היסטורי")
        prog_hist = df[df["שם תוכנית_מקור"] == program].sort_values("תאריך שידור")
        if len(prog_hist) > 0:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=prog_hist["תאריך שידור"], y=prog_hist["רייטינג"],
                mode="markers", name="היסטוריה",
                marker=dict(color="#a0aec0", size=5, opacity=0.5),
            ))
            fig2.add_hline(y=profile["mean_rating"], line_dash="dot", line_color="#666",
                           annotation_text=f"ממוצע מלא: {profile['mean_rating']:.2f}")
            fig2.add_hline(y=result["recent_mean_90d"], line_dash="dash", line_color="#0066cc",
                           annotation_text=f"ממוצע 90 יום: {result['recent_mean_90d']:.2f}")
            tdate = pd.to_datetime(target_date)
            fig2.add_trace(go.Scatter(
                x=[tdate, tdate], y=[result["ci_low"], result["ci_high"]],
                mode="lines", line=dict(color="orange", width=8), name="טווח חיזוי",
            ))
            fig2.add_trace(go.Scatter(
                x=[tdate], y=[result["weighted_avg"]],
                mode="markers",
                marker=dict(color="orange", size=18, symbol="star",
                            line=dict(color="darkorange", width=2)),
                name="חיזוי משוקלל",
            ))
            fig2.update_layout(height=400, hovermode="x unified",
                               xaxis_title="תאריך", yaxis_title="רייטינג")
            st.plotly_chart(fig2, use_container_width=True)

        with st.expander("⚠️ מה המודל לא יודע"):
            st.warning("""
            - **אירועים בלתי-צפויים** — מבצעים צבאיים, ברייקינג קיצוני: MAE עד 0.74
            - **שינויי לוח** — אם תוכנית עברה רצועה, ההיסטוריה ברצועה החדשה לא רלוונטית
            - **MAE צפוי בשגרה: ±0.26**
            """)
else:
    st.info("👆 לחצי **חזה רייטינג** כדי לקבל את התחזית.")
