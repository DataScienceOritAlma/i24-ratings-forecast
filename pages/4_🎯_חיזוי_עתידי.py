# -*- coding: utf-8 -*-
"""Future-prediction page — designed for research managers at i24.

Hero result: predicted rating + estimated viewers.
Decision aids: forecast curve, scenario comparison, CSV export.
"""
from datetime import datetime, time, timedelta
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.auth import require_password
from utils.data_loader import load_processed
from utils.predict import (predict_time_range, get_program_profile,
                            date_to_weekday_he, predict_forecast_curve,
                            predict_scenarios, rating_to_viewers)

st.set_page_config(page_title="חיזוי עתידי | i24", page_icon="🎯", layout="wide")
st.markdown("""
<style>
.main, .block-container, [data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stMetricValue"] { direction: ltr; text-align: right; }
.hero-result {
  background: linear-gradient(135deg, #0066cc 0%, #004499 100%);
  border-radius: 12px; padding: 24px; color: white; text-align: center;
}
.hero-result .number { font-size: 4em; font-weight: bold; line-height: 1; }
.hero-result .label { font-size: 1.1em; opacity: 0.9; margin-top: 8px; }
.scenario-card { padding: 12px; border-radius: 8px; background: #f7fafc; }
</style>
""", unsafe_allow_html=True)

require_password()

st.title("🎯 חיזוי תוכנית עתידית")
st.caption("כלי תכנון למנהל מחקר — בחרי תוכנית, תאריך, ושעות, וקבלי חיזוי מבוסס מודל עם רווח-בטחון, צופים מוערכים, וניתוח תרחישים.")

df = load_processed()

# ==========================================================================
# Section 1: Inputs
# ==========================================================================
with st.container(border=True):
    st.markdown("### 📋 פרטי השידור המתוכנן")

    col1, col2 = st.columns([3, 2])
    with col1:
        existing_progs = sorted(df["שם תוכנית_מקור"].dropna().unique())
        program = st.selectbox(
            "🎬 תוכנית *",
            options=existing_progs,
            index=existing_progs.index("קבינט שישי") if "קבינט שישי" in existing_progs else 0,
        )
    with col2:
        last_date = df["תאריך שידור"].max()
        default_target = last_date + timedelta(days=30)
        target_date = st.date_input(
            "📅 תאריך *",
            value=default_target.date(),
            min_value=(last_date + timedelta(days=1)).date(),
            max_value=(last_date + timedelta(days=365)).date(),
        )

    # Profile preview
    profile = get_program_profile(df, program)
    default_start_h = profile["typical_start_hour"]
    default_start_m = profile["typical_start_minute"]
    default_dur = profile["typical_duration_min"]
    end_total = default_start_h * 60 + default_start_m + default_dur
    default_end_h = (end_total // 60) % 24
    default_end_m = end_total % 60

    # Times + status
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        start_time = st.time_input("🕐 התחלה", value=time(default_start_h, default_start_m), step=300)
    with cc2:
        end_time = st.time_input("🕓 סיום", value=time(default_end_h, default_end_m), step=300)
    with cc3:
        status_options = [f"🤖 {profile['typical_status']}", "שידור חי", "שידור חוזר",
                          "לקט", "מבזק/חדש", "חג"]
        status_choice = st.selectbox("📡 סטטוס", options=status_options, index=0)
        chosen_status = profile["typical_status"] if status_choice.startswith("🤖") else status_choice

    # Event — only 2 options: routine or special event
    event_choice = st.radio(
        "🚨 אירוע מיוחד באותו יום?",
        options=["ללא — שגרה", "⚠️ אירוע מיוחד"],
        horizontal=True,
        index=0,
        help="אירוע מיוחד = חג / ביטחוני / מדיני / ברייקינג / כל אירוע שמעלה צפייה",
    )

    # Computed duration
    def time_to_minutes(t):
        return t.hour * 60 + t.minute
    duration_min = time_to_minutes(end_time) - time_to_minutes(start_time)
    if duration_min <= 0:
        duration_min += 24 * 60

    if duration_min < 5:
        st.error("⚠️ הסיום חייב להיות אחרי ההתחלה.")
    else:
        st.caption(f"⏱️ משך: **{duration_min} דקות** "
                   f"({duration_min // 60}h {duration_min % 60}m) | "
                   f"📺 שודרה {profile['n_airings']} פעמים בעבר | "
                   f"ר' ממוצע היסטורי: {profile['mean_rating']:.2f}")

# Map event flag — single boolean: routine or special event
is_special = event_choice == "⚠️ אירוע מיוחד"
is_holiday = False  # not exposed; merged into "מיוחד"
is_security = is_special
event_tag = "מיוחד" if is_special else "—"

# ==========================================================================
# Section 2: Predict button
# ==========================================================================
predict_clicked = st.button("🚀 חזה רייטינג", type="primary", use_container_width=True,
                            disabled=duration_min < 5)

if predict_clicked:
    with st.spinner("מחשב חיזוי + 4 תרחישים + עקומת חיזוי..."):
        result = predict_time_range(
            history_df=df, program_name=program, target_date=target_date,
            start_hour=start_time.hour, start_min=start_time.minute,
            end_hour=end_time.hour, end_min=end_time.minute,
            status=chosen_status,
            is_holiday=is_holiday, is_security=is_security, event_tag=event_tag,
        )
        scenarios = predict_scenarios(
            df, program, target_date,
            start_time.hour, start_time.minute,
            end_time.hour, end_time.minute,
            chosen_status,
        )
        curve = predict_forecast_curve(
            df, program, target_date,
            start_time.hour, start_time.minute,
            end_time.hour, end_time.minute,
            status=chosen_status, is_holiday=is_holiday, is_security=is_security,
            event_tag=event_tag,
        )

    if result is None:
        st.error("❌ לא ניתן היה לחשב חיזוי.")
    else:
        weekday_he = date_to_weekday_he(target_date)
        date_str = pd.to_datetime(target_date).strftime("%d/%m/%Y")

        # ============ HERO RESULT ============
        st.markdown(
            f"""
            <div class="hero-result">
              <div class="number">{result['prediction']:.2f}</div>
              <div class="label">רייטינג צפוי | ≈ {result['households']:,} בתי-אב | ≈ {result['viewers']:,} צופים</div>
              <div style="margin-top:14px; font-size:0.95em; opacity:0.85;">
                {program} · {weekday_he} {date_str} · {start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')} ({result['duration_min']}m)
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ============ Confidence interval + benchmarks ============
        st.markdown("### 📐 רווח-בטחון ובנצ'מארקים")
        bc1, bc2, bc3, bc4 = st.columns(4)
        with bc1:
            st.metric("⬇️ תרחיש שמרני (P10)", f"{result['ci_low']:.2f}",
                      f"{result['ci_low'] - result['prediction']:+.2f}")
        with bc2:
            st.metric("⬆️ תרחיש אופטימי (P90)", f"{result['ci_high']:.2f}",
                      f"{result['ci_high'] - result['prediction']:+.2f}")
        with bc3:
            st.metric("📊 ר' ממוצע 90 יום", f"{result['recent_mean_90d']:.2f}",
                      f"{result['recent_mean_90d'] - result['prediction']:+.2f} מהחיזוי")
        with bc4:
            st.metric("📚 ר' ממוצע מלא", f"{profile['mean_rating']:.2f}",
                      f"{profile['mean_rating'] - result['prediction']:+.2f} מהחיזוי")

        # Trend banner
        trend_pct = result["monthly_trend"]
        if abs(trend_pct) > 0.5:
            emoji = "📈" if trend_pct > 0 else "📉"
            st.info(
                f"{emoji} **טרנד חודשי: {trend_pct:+.1f}%/חודש** | "
                f"מרחק: {result['months_ahead']:.1f} חודשים | "
                f"מקדם: ×{result['trend_multiplier']:.2f} | "
                f"מקור אי-ודאות: {result['uncertainty']['source']} (n={result['uncertainty']['n']})"
            )

        if result.get("is_cold_start"):
            st.warning("⚠️ Cold-start — אין היסטוריה. הדיוק נמוך משמעותית.")

        st.divider()

        # ============ Forecast curve ============
        st.markdown("### 📈 עקומת חיזוי לחצי שנה קדימה")
        st.caption("איך התחזית מתפתחת ככל שהתאריך רחוק יותר. הטרנד החודשי גורם לעלייה הדרגתית.")

        if not curve.empty:
            fig_c = go.Figure()
            fig_c.add_trace(go.Scatter(
                x=curve["date"], y=curve["ci_high"],
                mode="lines", line=dict(width=0), showlegend=False,
            ))
            fig_c.add_trace(go.Scatter(
                x=curve["date"], y=curve["ci_low"],
                mode="lines", fill="tonexty", fillcolor="rgba(255,165,0,0.2)",
                line=dict(width=0), name="טווח 80%",
            ))
            fig_c.add_trace(go.Scatter(
                x=curve["date"], y=curve["prediction"],
                mode="lines+markers", line=dict(color="#0066cc", width=3),
                marker=dict(size=8), name="חיזוי",
            ))
            fig_c.add_hline(y=profile["mean_rating"], line_dash="dot", line_color="#666",
                            annotation_text=f"ממוצע היסטורי: {profile['mean_rating']:.2f}")
            fig_c.update_layout(height=350, xaxis_title="תאריך עתידי",
                                yaxis_title="רייטינג צפוי", hovermode="x")
            st.plotly_chart(fig_c, use_container_width=True)

        st.divider()

        # ============ Scenario comparison ============
        st.markdown("### 🆚 ניתוח 4 תרחישים")
        st.caption("איך החיזוי משתנה לפי הקשר היום? עוזר לתכנון 'best/worst case'.")

        if scenarios:
            sc_cols = st.columns(len(scenarios))
            for col, sc in zip(sc_cols, scenarios):
                with col:
                    selected = sc["scenario"].split()[1] in event_choice or \
                              (event_choice == "ללא — שגרה" and "שגרה" in sc["scenario"])
                    border_style = "3px solid #0066cc" if selected else "1px solid #ddd"
                    st.markdown(
                        f"""
                        <div class="scenario-card" style="border:{border_style}">
                          <div style="font-size:1.05em; font-weight:bold;">{sc['scenario']}</div>
                          <div style="font-size:2.2em; font-weight:bold; color:#0066cc; margin:8px 0;">
                            {sc['prediction']:.2f}
                          </div>
                          <div style="font-size:0.9em; color:#666;">
                            [{sc['ci_low']:.2f}, {sc['ci_high']:.2f}]<br>
                            {sc['viewers']['viewers']:,} צופים
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.divider()

        # ============ Historical context ============
        st.markdown("### 📚 הקשר היסטורי")
        prog_hist = df[df["שם תוכנית_מקור"] == program].sort_values("תאריך שידור")
        if len(prog_hist) > 0:
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(
                x=prog_hist["תאריך שידור"], y=prog_hist["רייטינג"],
                mode="markers", name="היסטוריה",
                marker=dict(color="#a0aec0", size=5, opacity=0.5),
            ))
            fig_h.add_hline(y=profile["mean_rating"], line_dash="dot", line_color="#666",
                            annotation_text=f"ממוצע מלא: {profile['mean_rating']:.2f}")
            fig_h.add_hline(y=result["recent_mean_90d"], line_dash="dash",
                            line_color="#0066cc",
                            annotation_text=f"90 יום: {result['recent_mean_90d']:.2f}")
            tdate = pd.to_datetime(target_date)
            fig_h.add_trace(go.Scatter(
                x=[tdate, tdate], y=[result["ci_low"], result["ci_high"]],
                mode="lines", line=dict(color="orange", width=8), name="טווח חיזוי",
            ))
            fig_h.add_trace(go.Scatter(
                x=[tdate], y=[result["prediction"]],
                mode="markers",
                marker=dict(color="orange", size=18, symbol="star",
                            line=dict(color="darkorange", width=2)),
                name="חיזוי",
            ))
            fig_h.update_layout(height=380, hovermode="x unified",
                                xaxis_title="תאריך", yaxis_title="רייטינג")
            st.plotly_chart(fig_h, use_container_width=True)

        st.divider()

        # ============ Export ============
        st.markdown("### 💾 ייצוא")
        export_rows = [
            {"שדה": "תוכנית", "ערך": program},
            {"שדה": "תאריך", "ערך": date_str},
            {"שדה": "יום", "ערך": weekday_he},
            {"שדה": "התחלה", "ערך": start_time.strftime("%H:%M")},
            {"שדה": "סיום", "ערך": end_time.strftime("%H:%M")},
            {"שדה": "משך (דק')", "ערך": result["duration_min"]},
            {"שדה": "סטטוס", "ערך": chosen_status},
            {"שדה": "אירוע", "ערך": event_choice},
            {"שדה": "🎯 חיזוי", "ערך": f"{result['prediction']:.3f}"},
            {"שדה": "תרחיש שמרני", "ערך": f"{result['ci_low']:.3f}"},
            {"שדה": "תרחיש אופטימי", "ערך": f"{result['ci_high']:.3f}"},
            {"שדה": "בתי-אב מוערכים", "ערך": f"{result['households']:,}"},
            {"שדה": "צופים מוערכים", "ערך": f"{result['viewers']:,}"},
            {"שדה": "ר' ממוצע 90 יום", "ערך": f"{result['recent_mean_90d']:.3f}"},
            {"שדה": "ר' ממוצע מלא", "ערך": f"{profile['mean_rating']:.3f}"},
            {"שדה": "טרנד חודשי", "ערך": f"{trend_pct:+.1f}%"},
        ]
        export_df = pd.DataFrame(export_rows)
        csv = export_df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ הורד דוח חיזוי (CSV)",
            data=csv, file_name=f"forecast_{program}_{date_str.replace('/', '-')}.csv",
            mime="text/csv", use_container_width=True,
        )

        # Caveats
        with st.expander("⚠️ מגבלות החיזוי"):
            st.warning(f"""
            - **MAE צפוי בשגרה:** ±0.26 (מבוסס test set)
            - **באירועים ביטחוניים בלתי-צפויים:** MAE עד 0.74
            - **כיול בתי-אב/צופים:** מבוסס על ~25K בתי-אב לכל נקודת רייטינג ו-2.3 צופים/בית
            - **טרנד**: limited ל-±5%/חודש על-בסיס 6 חודשים אחרונים
            - **Cold-start:** {"כן" if result.get("is_cold_start") else "לא"} (היסטוריה: {result.get('lag_program_n', 0)} שידורים)
            """)
else:
    st.info("👆 לחצי **חזה רייטינג** — תקבלי חיזוי מרכזי + עקומת חיזוי + 4 תרחישים + ייצוא לCSV.")
