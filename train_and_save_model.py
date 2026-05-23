# -*- coding: utf-8 -*-
"""Train HistGradientBoosting (V3 winner) and save the full pipeline to disk.

Output: model_saved.joblib — full sklearn Pipeline (preprocessor + model)

Run: py -3 train_and_save_model.py
The Streamlit prediction page loads this file at runtime (no retraining needed).
"""
from __future__ import annotations

import os
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# Import imputers from shared module so joblib pickle works cross-script
from utils.imputers import SimpleMedianImputer, SimpleConstantImputer

warnings.filterwarnings("ignore")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_XLSX = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")
OUT_MODEL = os.path.join(DATA_DIR, "model_saved.joblib")

TARGET = "רייטינג מותאם"
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]


# ---------- Feature engineering ----------------------------------------------
def _cum_mean_excl_current(values: pd.Series, group: pd.Series):
    df_tmp = pd.DataFrame({"v": values, "g": group})
    grp = df_tmp.groupby("g")["v"]
    n = grp.cumcount()
    s = grp.cumsum()
    mean = (s - df_tmp["v"]) / n.replace(0, np.nan)
    return mean.values, n.values


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["תאריך שידור", "שעת התחלה"]).reset_index(drop=True)

    d = pd.to_datetime(df["תאריך שידור"])
    df["חודש"] = d.dt.month
    df["יום_בחודש"] = d.dt.day
    df["שבוע_בשנה"] = d.dt.isocalendar().week.astype(int)

    df["_slot"] = df["יום שידור"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    df["_status_slot"] = df["סטטוס תוכנית"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)

    df["lag_program_mean"], df["lag_program_n"] = \
        _cum_mean_excl_current(df[TARGET], df["שם תוכנית_מקור"])
    df["lag_slot_mean"], df["lag_slot_n"] = \
        _cum_mean_excl_current(df[TARGET], df["_slot"])
    df["lag_status_slot_mean"], df["lag_status_slot_n"] = \
        _cum_mean_excl_current(df[TARGET], df["_status_slot"])

    for ch in COMPETITORS:
        col_safe = ch.replace(" ", "_")
        mean_arr, _ = _cum_mean_excl_current(df[ch], df["_slot"])
        df[f"lag_comp_{col_safe}_slot"] = mean_arr

    comp_lag_cols = [f"lag_comp_{c.replace(' ', '_')}_slot" for c in COMPETITORS]
    df["lag_competitors_avg_slot"] = df[comp_lag_cols].mean(axis=1)

    df = df.drop(columns=["_slot", "_status_slot"])
    return df


PRE_AIRING_FEATURES_NUM = [
    "שעת התחלה_שעה", "משך תוכנית_דק", "reception_pct",
    "חודש", "יום_בחודש", "שבוע_בשנה",
    "lag_program_mean", "lag_program_n",
    "lag_slot_mean", "lag_slot_n",
    "lag_status_slot_mean", "lag_status_slot_n",
    "lag_comp_כאן_11_slot",
    "lag_comp_קשת_12_slot",
    "lag_comp_רשת_13_slot",
    "lag_comp_עכשיו_14_slot",
    "lag_competitors_avg_slot",
]

PRE_AIRING_FEATURES_BOOL = ["is_rerun", "יום_חג", "יום_ביטחוני", "שבת"]
PRE_AIRING_FEATURES_CAT = ["יום שידור", "חלקי-יום", "סטטוס תוכנית",
                            "תג_עונה", "תג_חג", "תג_ביטחוני"]
ALL_COLS = PRE_AIRING_FEATURES_NUM + PRE_AIRING_FEATURES_BOOL + PRE_AIRING_FEATURES_CAT


def build_preprocessor():
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleMedianImputer()), ("scale", StandardScaler())]),
         PRE_AIRING_FEATURES_NUM),
        ("bool", SimpleConstantImputer(0), PRE_AIRING_FEATURES_BOOL),
        ("cat", Pipeline([("imp", SimpleConstantImputer("—")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
         PRE_AIRING_FEATURES_CAT),
    ])


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading data...")
    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    print(f"  {len(df):,} rows loaded")

    print("Engineering features...")
    df = add_features(df)
    df = df.dropna(subset=["lag_program_mean", "lag_slot_mean"]).reset_index(drop=True)
    print(f"  {len(df):,} rows after lag-NaN drop")

    print("Training HistGradientBoosting on FULL data...")
    model = HistGradientBoostingRegressor(
        max_iter=400, max_depth=6, learning_rate=0.05, random_state=42,
    )
    pipe = Pipeline([("pre", build_preprocessor()), ("model", model)])
    pipe.fit(df[ALL_COLS], df[TARGET].values)

    # Quick sanity check on the same train data
    train_pred = pipe.predict(df[ALL_COLS])
    mae_train = np.mean(np.abs(df[TARGET].values - train_pred))
    print(f"  Train MAE (same data): {mae_train:.4f}")

    # Save
    print(f"Saving model to {OUT_MODEL}...")
    joblib.dump({
        "pipeline": pipe,
        "feature_cols": ALL_COLS,
        "num_cols": PRE_AIRING_FEATURES_NUM,
        "bool_cols": PRE_AIRING_FEATURES_BOOL,
        "cat_cols": PRE_AIRING_FEATURES_CAT,
        "model_name": "HistGradientBoosting",
        "target_name": TARGET,
        "target_kind": "adjusted",  # raw / adjusted
        "expected_test_mae": 0.300,
    }, OUT_MODEL)

    file_kb = os.path.getsize(OUT_MODEL) / 1024
    print(f"  ✓ Saved ({file_kb:.0f} KB)")
    print("\nDone!")


if __name__ == "__main__":
    main()
