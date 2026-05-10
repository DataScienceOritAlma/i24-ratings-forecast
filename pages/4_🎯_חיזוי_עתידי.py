# -*- coding: utf-8 -*-
"""Future-prediction page — minimal mandatory fields, smart defaults from history."""
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.auth import require_password
from utils.data_loader import load_processed
from utils.predict import (predict_range, get_program_profile,
                            date_to_weekday_he, hour_to_daypart,
                            estimate_reception_pct, daypart_to_hours)

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
st.caption("בחר תוכנית ותאריך — וקבל חיזוי רייטינג מבוסס ההיסטוריה והרצועה הטיפוסית של התוכנית.")

df = load_processed()

# ==========================================================================
# Section 1: Mandatory inputs
# ==========================================================================
st.markdown("### 📋 פרטי החיזוי")

col1, col2 = st.columns([3, 2])

with col1:
    existing_progs = sorted(df["שם תוכנית_מקור"].dropna().unique())
    program = st.selectbox(
        "🎬 שם התוכנית *",
        options=existing_progs,
        index=existing_progs.index("קבינט שישי") if "קבינט שישי" in existing_progs else 0,
        help="בחר תוכנית קיימת מההיסטוריה",
    )

with col2:
    last_date = df["תאריך שידור"].max()
    default_target = last_date + timedelta(days=30)
    target_date = st.date_input(
        "📅 תאריך השידור המתוכנן *",
        value=default_target.date(),
        min_value=(last_date + timedelta(days=1)).date(),
        max_value=(last_date + timedelta(days=365)).date(),
    )

# ==========================================================================
# Section 2: Program profile preview (auto-shown when program selected)
# ==========================================================================
profile = get_program_profile(df, program)

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
        st.metric("שעה טיפוסית", f"{profile['typical_hour']:02d}:00")

    st.caption(f"💡 ברירות מחדל אוטומטיות מבוססות על {profile['n_airings']} שידורים היסטוריים. "
               f"תוכל לשנות אותן באפשרויות המתקדמות למטה.")

# ==========================================================================
# Section 3: Optional advanced settings (collapsible)
# ==========================================================================
with st.expander("⚙️ אפשרויות מתקדמות (אופציונלי)", expanded=False):
    st.markdown("השאירי כפי שזה כדי להשתמש בברירות-מחדל הטיפוסיות לתוכנית, או שני לפי הצורך:")

    ac1, ac2 = st.columns(2)
    with ac1:
        # Daypart override
        daypart_options = [
            f"🤖 אוטומטי ({profile['typical_daypart']})",
            "1. בוקר 06–09",
            "2. צהריים 10–13",
            '3. אחה"צ 14–17',
            "4. פריים-טיים 18–21",
            "5. לילה 22–01",
            "6. לילה מאוחר 02–05",
        ]
        daypart_choice = st.selectbox(
            "⏰ חלק היום",
            options=daypart_options,
            index=0,
            help="טווח שעות במקום שעה מדוייקת",
        )
        if daypart_choice.startswith("🤖"):
            chosen_daypart = profile["typical_daypart"]
        else:
            chosen_daypart = daypart_choice

        # Status override
        status_options = [
            f"🤖 אוטומטי ({profile['typical_status']})",
            "חי", "ש.ח", "לקט", "מיוחד-מבזק", "חג",
        ]
        status_choice = st.selectbox("📡 סטטוס שידור", options=status_options, index=0)
        if status_choice.startswith("🤖"):
            chosen_status = profile["typical_status"]
        else:
            chosen_status = status_choice

    with ac2:
        # Special event flag
        is_special = st.checkbox(
            "🚨 שידור באירוע מיוחד?",
            value=False,
            help="חג, יום ביטחוני, או אירוע אקטואלי — משנה את הציפיות",
        )
        if is_special:
            event_type = st.selectbox(
                "סוג האירוע",
                options=["חג", "אירוע ביטחוני", "אירוע מדיני", "אחר"],
            )

        # Comparison scenario
        compare_mode = st.checkbox(
            "🆚 השווה ל-2 תרחישים",
            value=False,
            help="תקבל גם תרחיש 'best case' ו'worst case'",
        )

# ==========================================================================
# Section 4: Predict button + result
# ==========================================================================
st.divider()

if st.button("🚀 חזה רייטינג", type="primary", use_container_width=True):
    with st.spinner("מחשב חיזוי..."):
        result = predict_range(
            history_df=df,
            program_name=program,
            target_date=target_date,
            daypart=chosen_daypart,
            status=chosen_status,
            is_special_event=is_special,
        )

    if result is None:
        st.error("❌ לא ניתן היה לחשב חיזוי. בדקי את הפרמטרים.")
    else:
        weekday_he = date_to_weekday_he(target_date)
        date_str = pd.to_datetime(target_date).strftime("%d/%m/%Y")

        # Main result card
        st.markdown(f"## 📊 חיזוי ל-*{program}*")
        st.caption(f"{weekday_he} {date_str} | {chosen_daypart} | סטטוס: {chosen_status}")

        # 3 hero metrics
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.metric("🎯 הערכה מרכזית (מדיאן)", f"{result['median']:.2f}",
                      delta=f"{result['median'] - profile['mean_rating']:.2f} מהממוצע ההיסטורי",
                      help="חיזוי המדיאן ברצועה")
        with rc2:
            st.metric("⬇️ תרחיש שמרני", f"{result['ci_low']:.2f}",
                      help="הקצה הנמוך של הצפי")
        with rc3:
            st.metric("⬆️ תרחיש אופטימי", f"{result['ci_high']:.2f}",
                      help="הקצה הגבוה של הצפי")

        st.divider()

        # ----- Visualization: range vs historical -----
        gc1, gc2 = st.columns([2, 1])

        with gc1:
            # Historical context graph
            prog_hist = df[df["שם תוכנית_מקור"] == program].sort_values("תאריך שידור")
            if len(prog_hist) > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=prog_hist["תאריך שידור"], y=prog_hist["רייטינג"],
                    mode="markers", name="היסטוריה",
                    marker=dict(color="#a0aec0", size=5, opacity=0.5),
                ))
                # Historical mean line
                fig.add_hline(
                    y=profile["mean_rating"],
                    line_dash="dot", line_color="#666",
                    annotation_text=f"ממוצע היסטורי: {profile['mean_rating']:.2f}",
                )
                # Prediction range as a band on the right
                tdate = pd.to_datetime(target_date)
                fig.add_trace(go.Scatter(
                    x=[tdate, tdate], y=[result["ci_low"], result["ci_high"]],
                    mode="lines", line=dict(color="orange", width=8),
                    name="טווח חיזוי",
                ))
                fig.add_trace(go.Scatter(
                    x=[tdate], y=[result["median"]],
                    mode="markers", marker=dict(color="orange", size=18, symbol="star",
                                                 line=dict(color="darkorange", width=2)),
                    name="חיזוי (מדיאן)",
                ))
                fig.update_layout(
                    title="היסטוריה + חיזוי",
                    xaxis_title="תאריך", yaxis_title="רייטינג",
                    height=400, hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)

        with gc2:
            st.markdown("**💡 איך לקרוא את החיזוי:**")
            st.markdown(f"""
            - **מדיאן** הוא ההערכה הסבירה ביותר
            - **הטווח** מבטא אי-ודאות סטטיסטית בתוך הרצועה
            - **לא לוקח בחשבון:** אירועים בלתי-צפויים שיכולים לגרום לזינוקים פי 3-5
            """)
            mean_diff = result["median"] - profile["mean_rating"]
            if abs(mean_diff) < 0.1:
                st.info("📊 החיזוי קרוב לממוצע ההיסטורי של התוכנית — תרחיש שגרתי")
            elif mean_diff > 0.1:
                st.success(f"📈 החיזוי גבוה מהממוצע ב-{mean_diff:.2f}")
            else:
                st.warning(f"📉 החיזוי נמוך מהממוצע ב-{abs(mean_diff):.2f}")

        # ----- Per-hour breakdown (within the daypart) -----
        st.divider()
        with st.expander("🔍 פירוט לכל שעה ברצועה"):
            details = pd.DataFrame(result["predictions"])
            details["שעה"] = details["hour"].apply(lambda h: f"{h:02d}:00")
            details = details[["שעה", "point", "ci_low", "ci_high"]]
            details.columns = ["שעה", "חיזוי", "תרחיש שמרני", "תרחיש אופטימי"]
            st.dataframe(details, use_container_width=True, hide_index=True)

            fig2 = px.bar(
                details, x="שעה", y="חיזוי",
                error_y=details["תרחיש אופטימי"] - details["חיזוי"],
                error_y_minus=details["חיזוי"] - details["תרחיש שמרני"],
                title="חיזוי לכל שעה בתוך הרצועה",
                height=300,
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ----- Caveats (in collapsible) -----
        with st.expander("⚠️ מה המודל לא יודע"):
            st.warning("""
            **מגבלות החיזוי:**
            - **אירועים בלתי-צפויים** — שום מודל לא יחזה רייטינג של מהדורה במהלך מבצע צבאי שטרם החל.
              MAE של המודל באירועים כאלה: 0.74 (לעומת 0.19 בשגרה).
            - **שינויי לוח-שידורים** — אם תוכנית עוברת רצועה משמעותית, ההיסטוריה ברצועה החדשה לא רלוונטית.
            - **דרייפט עתידי** — ככל שהתאריך רחוק יותר, הדיוק יורד.
            - **MAE צפוי באירועים שגרתיים: ±0.26**
            """)
else:
    st.info("👆 לחץ **חזה רייטינג** כדי לקבל את התחזית. רק התוכנית והתאריך נדרשים — השאר אופציונלי.")
