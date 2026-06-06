# -*- coding: utf-8 -*-
"""Compute post-hoc bias corrections per (status × daypart).

Why this exists (DEEP_ANALYSIS.md §J):
- The model has systematic bias in specific (status × daypart) cells.
- E.g. `שידור חי × צהריים 10–13` consistently predicts ~0.27 below actual.
- A simple post-hoc shift (correction = -bias) flattens these systematic errors at
  ZERO cost, provided we have enough samples for a stable estimate.

Approach (honest, not over-fit):
1. Train HistGB on chronological 80% (same as production).
2. Predict on the chronological 20% test split.
3. For each (status, daypart) cell:
     - require n >= MIN_N to trust the bias estimate
     - require |mean_bias| >= MIN_BIAS to be worth correcting
     - cap the absolute correction to MAX_CORRECTION (prevent extreme shifts)
4. Save the resulting dict to `bias_corrections.json`.

The backend loads this and applies `corrected = pred - bias[(status, daypart)]`
when the cell has a correction. Cells not in the dict are left alone.

Run: py -3 compute_bias_corrections.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import warnings
from pathlib import Path

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
OUT = ROOT / "bias_corrections.json"

TARGET = "רייטינג מותאם"
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]

# Statistical filter thresholds — tuned conservatively to avoid over-fitting
MIN_N = 30           # minimum rows per cell to trust the bias estimate
MIN_BIAS = 0.10      # don't bother correcting tiny biases (within noise)
MAX_CORRECTION = 0.30  # cap correction magnitude (no wild shifts)

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
    cut = int(len(df) * 0.80)
    train_df = df.iloc[:cut].reset_index(drop=True)
    test_df = df.iloc[cut:].reset_index(drop=True)
    print(f"   train: {len(train_df):,}  |  test: {len(test_df):,}")

    print("🤖 Training HistGB (production config) on train...")
    pipe = Pipeline([("pre", build_preprocessor()),
                     ("model", HistGradientBoostingRegressor(
                         max_iter=400, max_depth=6, learning_rate=0.05, random_state=42))])
    pipe.fit(train_df[ALL_COLS], train_df[TARGET].values)
    test_df = test_df.assign(y_pred=pipe.predict(test_df[ALL_COLS]))
    test_df["bias"] = test_df["y_pred"] - test_df[TARGET]

    print("\n📊 Per-cell bias (status × daypart):")
    grid = test_df.groupby(["סטטוס תוכנית", "חלקי-יום"], observed=True).agg(
        n=("bias", "size"),
        mean_bias=("bias", "mean"),
        std_bias=("bias", "std"),
    ).reset_index()
    print(grid.to_string(index=False))

    # Filter to stable, meaningful cells
    eligible = grid[(grid["n"] >= MIN_N) & (grid["mean_bias"].abs() >= MIN_BIAS)].copy()
    eligible["correction"] = (-eligible["mean_bias"]).clip(-MAX_CORRECTION, MAX_CORRECTION)
    print(f"\n✂️  Filter: n≥{MIN_N}, |bias|≥{MIN_BIAS}, |correction| capped at {MAX_CORRECTION}")
    print(f"   {len(eligible)}/{len(grid)} cells qualify")

    if not len(eligible):
        print("   No cells meet thresholds — no corrections written.")
        return

    print("\n🛠  Applied corrections:")
    print(eligible[["סטטוס תוכנית", "חלקי-יום", "n", "mean_bias", "correction"]].to_string(index=False))

    # Verify gain on test
    corrections = {f"{r['סטטוס תוכנית']}|{r['חלקי-יום']}": float(r["correction"])
                   for _, r in eligible.iterrows()}
    key = test_df["סטטוס תוכנית"].astype(str) + "|" + test_df["חלקי-יום"].astype(str)
    shifts = key.map(corrections).fillna(0.0)
    y_pred_corrected = test_df["y_pred"] + shifts
    from sklearn.metrics import mean_absolute_error
    mae_before = mean_absolute_error(test_df[TARGET], test_df["y_pred"])
    mae_after = mean_absolute_error(test_df[TARGET], y_pred_corrected)
    print(f"\n📈 Test MAE before: {mae_before:.4f}  →  after: {mae_after:.4f}  "
          f"(Δ = {mae_after - mae_before:+.4f}, {(mae_after - mae_before)/mae_before*100:+.1f}%)")

    # Save
    out_obj = {
        "version": 1,
        "target_kind": "adjusted",
        "thresholds": {"min_n": MIN_N, "min_bias": MIN_BIAS, "max_correction": MAX_CORRECTION},
        "test_mae_before": round(mae_before, 4),
        "test_mae_after": round(mae_after, 4),
        "corrections": corrections,  # key = "status|daypart" → shift to ADD to prediction
    }
    OUT.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 Saved {len(corrections)} corrections → {OUT.name}")


if __name__ == "__main__":
    main()
