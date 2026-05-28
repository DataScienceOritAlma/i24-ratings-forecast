# -*- coding: utf-8 -*-
"""Decide the event encoding: one-hot tag vs LLM severity vs both.

Trains HistGradientBoosting on a chronological 80/20 split of the xlsx under
three feature configs and reports test MAE/R². Severity is derived on the fly
via retrain_from_supabase.tag_events_by_date (reads severity from the curated CSV).

Run: py -3 -X utf8 compare_severity.py
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from utils.imputers import SimpleMedianImputer, SimpleConstantImputer
from retrain_from_supabase import (
    add_features, tag_events_by_date, TARGET, PRE_AIRING_FEATURES_NUM,
)

warnings.filterwarnings("ignore")
HP = dict(max_iter=400, max_depth=6, learning_rate=0.05, random_state=42)
BASE_CAT = ["יום שידור", "חלקי-יום", "סטטוס תוכנית"]
BOOL = ["is_rerun", "יום_ביטחוני", "שבת"]


def preproc(num, cat):
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleMedianImputer()), ("scale", StandardScaler())]), num),
        ("bool", SimpleConstantImputer(0), BOOL),
        ("cat", Pipeline([("imp", SimpleConstantImputer("—")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat),
    ])


def evaluate(train, test, num, cat):
    pipe = Pipeline([("pre", preproc(num, cat)), ("m", HistGradientBoostingRegressor(**HP))])
    allc = num + BOOL + cat
    pipe.fit(train[allc], train[TARGET].values)
    p = pipe.predict(test[allc])
    return mean_absolute_error(test[TARGET].values, p), r2_score(test[TARGET].values, p)


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    df = pd.read_excel("תוכניות_מעובד.xlsx", sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    if "שעת התחלה_שעה" not in df.columns:
        df["שעת התחלה_שעה"] = (pd.to_datetime(df["שעת התחלה"].astype(str),
            format="%H:%M:%S", errors="coerce").dt.hour.fillna(20).astype(int))
    df = tag_events_by_date(df)        # adds תג_ביטחוני, יום_ביטחוני, שבת, severity
    print("severity distribution:", dict(pd.cut(df["severity"], [-1,0,7,8,9,10]).value_counts().sort_index()))

    feat = add_features(df).dropna(subset=["lag_program_mean", "lag_slot_mean", TARGET]).reset_index(drop=True)
    feat = feat.sort_values("תאריך שידור").reset_index(drop=True)
    cut = int(len(feat) * 0.8)
    train, test = feat.iloc[:cut].copy(), feat.iloc[cut:].copy()
    print(f"train={len(train):,} test={len(test):,} cut={test['תאריך שידור'].iloc[0].date()}\n")

    configs = {
        "(a) one-hot תג_ביטחוני [current]": (PRE_AIRING_FEATURES_NUM, BASE_CAT + ["תג_ביטחוני"]),
        "(b) severity (drop one-hot)":      (PRE_AIRING_FEATURES_NUM + ["severity"], BASE_CAT),
        "(c) severity + one-hot (both)":    (PRE_AIRING_FEATURES_NUM + ["severity"], BASE_CAT + ["תג_ביטחוני"]),
    }
    print(f"{'config':<38} {'MAE':>8} {'R²':>8}")
    print("-" * 56)
    for name, (num, cat) in configs.items():
        mae, r2 = evaluate(train, test, num, cat)
        print(f"{name:<38} {mae:>8.4f} {r2:>8.4f}")


if __name__ == "__main__":
    main()
