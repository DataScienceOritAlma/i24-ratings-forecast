# -*- coding: utf-8 -*-
"""Verify the event-feature fix (Session-5 bug).

The Supabase retrain path used to fill the event tag columns
(תג_עונה / תג_חג / תג_ביטחוני / יום_חג / יום_ביטחוני / שבת) with constant
defaults, so the model ignored them. tag_events_by_date() now derives them
from אירועים_מדויקים.csv by date.

This script proves the fix on the LOCAL xlsx (no DB needed):
  1. Correctness — derived tags == the tags stored in the xlsx.
  2. Ablation — chronological-split test MAE WITH vs WITHOUT event features.
  3. Permutation importance — event features now score > 0.

Run: py -3 -X utf8 verify_event_fix.py
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline

from retrain_from_supabase import (
    ALL_COLS,
    add_features,
    build_preprocessor,
    tag_events_by_date,
    TARGET,
)

warnings.filterwarnings("ignore")

SRC_XLSX = "תוכניות_מעובד.xlsx"
# Security-event features only — holidays + season were dropped (שלב 57) after an
# ablation showed they contribute ~0; the security signal is the real payload.
EVENT_COLS = ["תג_ביטחוני", "יום_ביטחוני", "שבת"]
TEST_FRAC = 0.20
HP = dict(max_iter=400, max_depth=6, learning_rate=0.05, random_state=42)


def _fit_eval(train, test):
    pipe = Pipeline([("pre", build_preprocessor()), ("model", HistGradientBoostingRegressor(**HP))])
    pipe.fit(train[ALL_COLS], train[TARGET].values)
    pred = pipe.predict(test[ALL_COLS])
    return pipe, mean_absolute_error(test[TARGET].values, pred), r2_score(test[TARGET].values, pred)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    if "שעת התחלה_שעה" not in df.columns:
        df["שעת התחלה_שעה"] = (
            pd.to_datetime(df["שעת התחלה"].astype(str), format="%H:%M:%S", errors="coerce")
            .dt.hour.fillna(20).astype(int)
        )
    print(f"Loaded {len(df):,} rows from {SRC_XLSX}\n")

    # ---- 1. Correctness: derived tags must equal the stored tags ------------
    print("=" * 60)
    print("1) TAG DERIVATION CORRECTNESS (derived vs stored in xlsx)")
    print("=" * 60)
    truth = df[EVENT_COLS].copy()
    derived = tag_events_by_date(df.copy())[EVENT_COLS]
    all_ok = True
    for c in EVENT_COLS:
        a = truth[c].astype(str).values
        b = derived[c].astype(str).values
        n_mismatch = int((a != b).sum())
        all_ok &= n_mismatch == 0
        print(f"  {c:<14} unique={derived[c].nunique():<3} mismatches={n_mismatch}")
    print(f"\n  {'✓ derived tags match the xlsx exactly' if all_ok else '✗ MISMATCH — derivation differs!'}\n")

    # ---- 2. Ablation: WITH vs WITHOUT event features ------------------------
    print("=" * 60)
    print("2) ABLATION — chronological 80/20 split, test MAE")
    print("=" * 60)
    feat = add_features(df.copy())
    feat = feat.dropna(subset=["lag_program_mean", "lag_slot_mean", TARGET]).reset_index(drop=True)
    feat = feat.sort_values("תאריך שידור").reset_index(drop=True)
    cut = int(len(feat) * (1 - TEST_FRAC))
    train, test = feat.iloc[:cut].copy(), feat.iloc[cut:].copy()
    print(f"  train={len(train):,}  test={len(test):,}  cut={test['תאריך שידור'].iloc[0].date()}\n")

    _, mae_with, r2_with = _fit_eval(train, test)

    # Reproduce the bug: collapse event columns to the old constant defaults
    broke_train, broke_test = train.copy(), test.copy()
    for d in (broke_train, broke_test):
        d["תג_ביטחוני"] = "—"
        for c in ["יום_ביטחוני", "שבת"]:
            d[c] = False
    _, mae_without, r2_without = _fit_eval(broke_train, broke_test)

    delta = mae_without - mae_with
    pct = 100 * delta / mae_without
    print(f"  WITHOUT events (the bug):  MAE={mae_without:.4f}  R²={r2_without:.4f}")
    print(f"  WITH events    (fixed)  :  MAE={mae_with:.4f}  R²={r2_with:.4f}")
    print(f"  Δ MAE = {delta:+.4f}   →   {pct:+.1f}% improvement from the fix\n")

    # ---- 3. Permutation importance of event features ------------------------
    print("=" * 60)
    print("3) PERMUTATION IMPORTANCE (test set, MAE drop when shuffled)")
    print("=" * 60)
    pipe, _, _ = _fit_eval(train, test)
    r = permutation_importance(
        pipe, test[ALL_COLS], test[TARGET].values,
        scoring="neg_mean_absolute_error", n_repeats=5, random_state=42,
    )
    imp = pd.Series(r.importances_mean, index=ALL_COLS).sort_values(ascending=False)
    print("\n  Top 8 features overall:")
    for name, val in imp.head(8).items():
        print(f"    {name:<26} {val:.4f}")
    print("\n  Event features specifically:")
    for c in EVENT_COLS:
        flag = "  ← now > 0 ✓" if imp[c] > 0 else ""
        print(f"    {c:<26} {imp[c]:.4f}{flag}")

    print("\nDone.")


if __name__ == "__main__":
    main()
