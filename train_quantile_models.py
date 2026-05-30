# -*- coding: utf-8 -*-
"""Train quantile P10/P90 models + compute conformal offsets.

Outputs `model_quantiles.joblib` — loaded by backend/main.py to produce
calibrated 80% prediction intervals.

Why this exists (DEEP_ANALYSIS.md §F):
- The current CI in backend (`prediction_low/high` = `pred ± 1.28·std_of_slot`)
  achieved only ~56% empirical coverage when checked on test, while claiming 80%.
- True quantile regression gives an honest interval shape (asymmetric where
  reality is asymmetric — i.e. wider above the median because rating spikes are
  upward).
- Conformal calibration then guarantees the interval covers ≥ 80% of new data,
  by adding fixed offsets computed on a held-out calibration slice.

Run: py -3 train_quantile_models.py
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from utils.imputers import SimpleConstantImputer, SimpleMedianImputer

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent
SRC_XLSX = ROOT / "תוכניות_מעובד.xlsx"
OUT = ROOT / "model_quantiles.joblib"

TARGET = "רייטינג מותאם"
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]

NUM_FEATURES = [
    "שעת התחלה_שעה", "משך תוכנית_דק", "reception_pct",
    "חודש", "יום_בחודש", "שבוע_בשנה",
    "lag_program_mean", "lag_program_n",
    "lag_slot_mean", "lag_slot_n",
    "lag_status_slot_mean", "lag_status_slot_n",
    "lag_comp_כאן_11_slot", "lag_comp_קשת_12_slot",
    "lag_comp_רשת_13_slot", "lag_comp_עכשיו_14_slot",
    "lag_competitors_avg_slot",
]
BOOL_FEATURES = ["is_rerun", "יום_ביטחוני", "שבת"]
CAT_FEATURES = ["יום שידור", "חלקי-יום", "סטטוס תוכנית", "תג_ביטחוני"]
ALL_COLS = NUM_FEATURES + BOOL_FEATURES + CAT_FEATURES


# ---------- Feature engineering (mirror of train_and_save_model.py) ----------
def _cum_mean_excl_current(values: pd.Series, group: pd.Series):
    tmp = pd.DataFrame({"v": values, "g": group})
    g = tmp.groupby("g")["v"]
    n = g.cumcount()
    s = g.cumsum()
    mean = (s - tmp["v"]) / n.replace(0, np.nan)
    return mean.values, n.values


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["תאריך שידור", "שעת התחלה"]).reset_index(drop=True)
    d = pd.to_datetime(df["תאריך שידור"])
    df["חודש"] = d.dt.month
    df["יום_בחודש"] = d.dt.day
    df["שבוע_בשנה"] = d.dt.isocalendar().week.astype(int)
    df["_slot"] = df["יום שידור"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    df["_status_slot"] = df["סטטוס תוכנית"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    df["lag_program_mean"], df["lag_program_n"] = _cum_mean_excl_current(df[TARGET], df["שם תוכנית_מקור"])
    df["lag_slot_mean"], df["lag_slot_n"] = _cum_mean_excl_current(df[TARGET], df["_slot"])
    df["lag_status_slot_mean"], df["lag_status_slot_n"] = _cum_mean_excl_current(df[TARGET], df["_status_slot"])
    for ch in COMPETITORS:
        safe = ch.replace(" ", "_")
        m, _ = _cum_mean_excl_current(df[ch], df["_slot"])
        df[f"lag_comp_{safe}_slot"] = m
    comp_cols = [f"lag_comp_{c.replace(' ', '_')}_slot" for c in COMPETITORS]
    df["lag_competitors_avg_slot"] = df[comp_cols].mean(axis=1)
    return df.drop(columns=["_slot", "_status_slot"])


def build_preprocessor():
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleMedianImputer()), ("scale", StandardScaler())]), NUM_FEATURES),
        ("bool", SimpleConstantImputer(0), BOOL_FEATURES),
        ("cat", Pipeline([("imp", SimpleConstantImputer("—")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
         CAT_FEATURES),
    ])


def build_quantile_model(q: float):
    return HistGradientBoostingRegressor(
        loss="quantile", quantile=q,
        max_iter=400, max_depth=6, learning_rate=0.05, random_state=42,
    )


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("📥 Loading data...")
    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    df = add_features(df)
    df = df.dropna(subset=["lag_program_mean", "lag_slot_mean", TARGET]).reset_index(drop=True)
    df = df.sort_values(["תאריך שידור", "שעת התחלה"]).reset_index(drop=True)
    print(f"   {len(df):,} rows after lag-NaN drop")

    # Chronological split for conformal calibration:
    # Last 15% of historical data becomes the calibration set —
    # the most realistic stand-in for "future data the model will face".
    cal_frac = 0.15
    cut = int(len(df) * (1 - cal_frac))
    fit_df = df.iloc[:cut].reset_index(drop=True)
    cal_df = df.iloc[cut:].reset_index(drop=True)
    print(f"   Fit: {len(fit_df):,} rows  (up to {fit_df['תאריך שידור'].iloc[-1].date()})")
    print(f"   Cal: {len(cal_df):,} rows  (from {cal_df['תאריך שידור'].iloc[0].date()})")

    X_fit, y_fit = fit_df[ALL_COLS], fit_df[TARGET].values
    X_cal, y_cal = cal_df[ALL_COLS], cal_df[TARGET].values

    print("\n🤖 Training P10 model...")
    pipe_p10 = Pipeline([("pre", build_preprocessor()),
                         ("model", build_quantile_model(0.10))])
    pipe_p10.fit(X_fit, y_fit)

    print("🤖 Training P90 model...")
    pipe_p90 = Pipeline([("pre", build_preprocessor()),
                         ("model", build_quantile_model(0.90))])
    pipe_p90.fit(X_fit, y_fit)

    # Calibration: compute conformal offsets so that empirical 80% coverage holds.
    # Define gaps:
    #   gap_low  = p10 - y_actual   (positive ⇒ y is BELOW the predicted p10, interval too tight on the bottom)
    #   gap_high = y_actual - p90   (positive ⇒ y is ABOVE the predicted p90, interval too tight on the top)
    # For 80% coverage we want EACH tail (low+high) to contain ≤10% of points.
    # The conformal offset is the 90th-percentile of the corresponding gap on cal.
    p10_cal = pipe_p10.predict(X_cal)
    p90_cal = pipe_p90.predict(X_cal)

    gap_low = p10_cal - y_cal       # take positive parts (y below interval)
    gap_high = y_cal - p90_cal      # take positive parts (y above interval)

    # 90th-percentile of "miss magnitude" on each side
    offset_low = float(max(0.0, np.quantile(gap_low, 0.90)))
    offset_high = float(max(0.0, np.quantile(gap_high, 0.90)))

    # Apply and verify on calibration
    p10_cal_c = p10_cal - offset_low
    p90_cal_c = p90_cal + offset_high
    coverage_raw = float(((y_cal >= p10_cal) & (y_cal <= p90_cal)).mean())
    coverage_calibrated = float(((y_cal >= p10_cal_c) & (y_cal <= p90_cal_c)).mean())
    width_raw = float((p90_cal - p10_cal).mean())
    width_calibrated = float((p90_cal_c - p10_cal_c).mean())

    print(f"\n📊 Conformal calibration result (on cal set):")
    print(f"   Raw coverage:        {coverage_raw:.1%}  (target 80%)")
    print(f"   Calibrated coverage: {coverage_calibrated:.1%}")
    print(f"   Raw mean width:      {width_raw:.3f}")
    print(f"   Calibrated width:    {width_calibrated:.3f}")
    print(f"   offset_low = {offset_low:.3f}   offset_high = {offset_high:.3f}")

    # Save
    print(f"\n💾 Saving to {OUT}...")
    joblib.dump({
        "pipe_p10": pipe_p10,
        "pipe_p90": pipe_p90,
        "offset_low": offset_low,
        "offset_high": offset_high,
        "feature_cols": ALL_COLS,
        "target_name": TARGET,
        "target_kind": "adjusted",
        "cal_coverage_raw": coverage_raw,
        "cal_coverage_calibrated": coverage_calibrated,
        "cal_width_raw": width_raw,
        "cal_width_calibrated": width_calibrated,
        "trained_on_rows": len(fit_df),
        "calibrated_on_rows": len(cal_df),
    }, OUT)
    file_kb = OUT.stat().st_size / 1024
    print(f"   ✓ Saved ({file_kb:.0f} KB)")
    print("\nDone.")


if __name__ == "__main__":
    main()
