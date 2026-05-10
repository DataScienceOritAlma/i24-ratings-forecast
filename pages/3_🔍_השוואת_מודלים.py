# -*- coding: utf-8 -*-
"""Model comparison: leaderboard, MAE per segment, head-to-head."""
import streamlit as st
import pandas as pd
import plotly.express as px

from utils.auth import require_password
from utils.data_loader import load_predictions, load_metrics_summary
from utils.style import apply_style

st.set_page_config(page_title="השוואת מודלים | i24", page_icon="🔍", layout="wide")
apply_style()
require_password()

st.title("🔍 השוואת מודלים")
st.caption("כל 19 המודלים שאומנו — דירוג, ניתוח שגיאות לפי חתך, ראש-בראש")

preds = load_predictions()
summary = load_metrics_summary()

# ---------- Leaderboard ----------
st.subheader("🏆 דירוג כללי")

leaderboard = summary.copy().sort_values("MAE")
leaderboard["MAE"] = leaderboard["MAE"].round(4)
leaderboard["RMSE"] = leaderboard["RMSE"].round(4)
leaderboard["R²"] = leaderboard["R²"].round(4)

c1, c2 = st.columns([2, 1])
with c1:
    st.dataframe(leaderboard, use_container_width=True, height=500)
with c2:
    fig = px.bar(leaderboard.reset_index(), x="MAE", y="מודל", orientation="h",
                 height=500, title="MAE לכל מודל")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------- Find prediction columns dynamically ----------
pred_cols = [c for c in preds.columns if c.startswith("חזוי_")]
model_names = [c.replace("חזוי_", "") for c in pred_cols]

# ---------- MAE per segment ----------
st.subheader("📊 MAE לפי חתך")
seg_choice = st.radio("חתך", ["יום שידור", "חלקי-יום", "אירוע_מיוחד", "סטטוס תוכנית"], horizontal=True)

selected_models = st.multiselect(
    "בחרי מודלים להצגה",
    options=model_names,
    default=["13_HistGradientBoosting", "15_LightGBM", "10_RandomForest_tuned",
             "01_Slot_Mean", "00_Naive_GlobalMean"],
)

if selected_models and seg_choice in preds.columns:
    rows = []
    for name in selected_models:
        col = f"חזוי_{name}"
        if col not in preds.columns:
            continue
        for seg, grp in preds.groupby(seg_choice, dropna=False):
            mae = (grp["רייטינג"] - grp[col]).abs().mean()
            rows.append({seg_choice: str(seg), "מודל": name, "MAE": mae, "n": len(grp)})
    seg_df = pd.DataFrame(rows)

    fig2 = px.bar(seg_df, x=seg_choice, y="MAE", color="מודל",
                  barmode="group", height=500,
                  title=f"MAE לפי {seg_choice}")
    st.plotly_chart(fig2, use_container_width=True)

    # Table
    pivot = seg_df.pivot(index=seg_choice, columns="מודל", values="MAE").round(3)
    st.dataframe(pivot, use_container_width=True)

st.divider()

# ---------- Head-to-head ----------
st.subheader("⚔️ ראש-בראש: מודל A מול מודל B")
c1, c2 = st.columns(2)
with c1:
    model_a = st.selectbox("מודל A", model_names,
                           index=model_names.index("13_HistGradientBoosting") if "13_HistGradientBoosting" in model_names else 0)
with c2:
    model_b = st.selectbox("מודל B", model_names,
                           index=model_names.index("00_Naive_GlobalMean") if "00_Naive_GlobalMean" in model_names else 1)

col_a, col_b = f"חזוי_{model_a}", f"חזוי_{model_b}"
err_a = (preds["רייטינג"] - preds[col_a]).abs()
err_b = (preds["רייטינג"] - preds[col_b]).abs()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric(f"MAE {model_a}", f"{err_a.mean():.3f}")
with c2:
    st.metric(f"MAE {model_b}", f"{err_b.mean():.3f}")
with c3:
    delta = err_b.mean() - err_a.mean()
    st.metric("יתרון של A (ערך חיובי = A טוב יותר)", f"{delta:+.3f}")

# Where does A beat B and vice versa?
diff_df = preds.copy()
diff_df["err_A"] = err_a
diff_df["err_B"] = err_b
diff_df["יתרון_A"] = err_b - err_a  # positive = A wins

st.write("**10 השורות שבהן A ניצח את B בהפרש הגדול ביותר:**")
top_a = diff_df.nlargest(10, "יתרון_A")[
    ["שם תוכנית", "תאריך שידור", "יום שידור", "אירוע_מיוחד",
     "רייטינג", col_a, col_b, "יתרון_A"]
].copy()
top_a["תאריך שידור"] = pd.to_datetime(top_a["תאריך שידור"]).dt.strftime("%Y-%m-%d")
st.dataframe(top_a, use_container_width=True)

st.write("**10 השורות שבהן B ניצח את A:**")
top_b = diff_df.nsmallest(10, "יתרון_A")[
    ["שם תוכנית", "תאריך שידור", "יום שידור", "אירוע_מיוחד",
     "רייטינג", col_a, col_b, "יתרון_A"]
].copy()
top_b["תאריך שידור"] = pd.to_datetime(top_b["תאריך שידור"]).dt.strftime("%Y-%m-%d")
st.dataframe(top_b, use_container_width=True)
