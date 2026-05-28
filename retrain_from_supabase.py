# -*- coding: utf-8 -*-
"""Automated bi-weekly retraining from Supabase.

Run by .github/workflows/retrain.yml. Can also be invoked manually:
    py -3 -X utf8 retrain_from_supabase.py

What it does:
  1. Pulls broadcasts + programs from Supabase via DATABASE_URL
  2. Derives רייטינג מותאם = רייטינג / reception_pct
  3. Computes chronological 80/20 split + reports test MAE/R² (no leakage)
  4. Re-fits on FULL data (the production pattern) and saves model_saved.joblib
  5. Appends one line to retrain_log.md so we have an audit trail

Fails fast if DATABASE_URL is missing or returns no rows.
"""
from __future__ import annotations

import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psycopg
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from utils.imputers import SimpleMedianImputer, SimpleConstantImputer

try:  # local runs read DATABASE_URL from .env; CI injects it as a real env var
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
OUT_MODEL = ROOT / "model_saved.joblib"
OUT_LOG = ROOT / "retrain_log.md"
EVENTS_CSV = ROOT / "אירועים_מדויקים.csv"
TARGET = "רייטינג מותאם"
TEST_FRAC = 0.20
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]


# ---------- Feature engineering (mirror of train_and_save_model.py) ----------
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
        if ch in df.columns:
            mean_arr, _ = _cum_mean_excl_current(df[ch], df["_slot"])
            df[f"lag_comp_{col_safe}_slot"] = mean_arr
        else:
            df[f"lag_comp_{col_safe}_slot"] = 0.0

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
    "lag_comp_כאן_11_slot", "lag_comp_קשת_12_slot",
    "lag_comp_רשת_13_slot", "lag_comp_עכשיו_14_slot",
    "lag_competitors_avg_slot",
]
# Holidays + season dropped (2026-05-28): ablation showed ~0 contribution and
# the holiday rating signal in the data is contested/unreliable. Security events
# stay — they're worth ~10.6% of MAE. See WORK_LOG שלב 57.
PRE_AIRING_FEATURES_BOOL = ["is_rerun", "יום_ביטחוני", "שבת"]
PRE_AIRING_FEATURES_CAT = ["יום שידור", "חלקי-יום", "סטטוס תוכנית", "תג_ביטחוני"]
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


def tag_events_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """Derive event tags (season / holiday / security) from the curated events
    file by matching each broadcast date to event start–end ranges.

    Mirrors eda_script.tag_events so the Supabase-trained model sees the SAME
    multi-category event features as the CSV-trained model. Without this the
    tag columns collapse to a single constant value and the model ignores them
    (security/holiday signal worth ~8% of MAE).
    """
    if not EVENTS_CSV.exists():
        raise RuntimeError(f"{EVENTS_CSV.name} not found — cannot tag events.")
    ev = pd.read_csv(EVENTS_CSV)
    ev["_start"] = pd.to_datetime(ev["תאריך_התחלה"], errors="coerce")
    ev["_end"] = pd.to_datetime(ev["תאריך_סיום"], errors="coerce")

    dates = pd.to_datetime(df["תאריך שידור"])
    sec_kinds = {"ביטחוני", "מדיני"}

    df["תג_עונה"] = "—"
    df["תג_חג"] = "—"
    df["תג_ביטחוני"] = "—"
    # LLM-scored security intensity (0–10; max if events overlap). NOT a model
    # feature — adding it hurt MAE (0.30→0.41) because semantic intensity ≠
    # per-broadcast rating impact (duration confound; see compare_severity.py,
    # WORK_LOG שלב 59). Kept for the explanation/chatbot layer.
    df["severity"] = 0.0
    for _, e in ev.iterrows():
        if pd.isna(e["_start"]) or pd.isna(e["_end"]):
            continue
        m = (dates >= e["_start"]) & (dates <= e["_end"])
        if not m.any():
            continue
        kind, name = e["קטגוריה"], e["שם_אירוע"]
        if kind == "עונה":
            df.loc[m, "תג_עונה"] = name
        elif kind == "חג":
            df.loc[m, "תג_חג"] = name
        elif kind in sec_kinds:
            cur = df.loc[m, "תג_ביטחוני"]
            df.loc[m, "תג_ביטחוני"] = (
                cur.where(cur == "—", cur + " + " + name).where(cur != "—", name)
            )
            sev = float(e["severity"]) if "severity" in ev.columns and pd.notna(e["severity"]) else 0.0
            df.loc[m, "severity"] = np.maximum(df.loc[m, "severity"], sev)

    df["יום_חג"] = df["תג_חג"] != "—"
    df["יום_ביטחוני"] = df["תג_ביטחוני"] != "—"
    df["שבת"] = df["יום שידור"].astype(str) == "שבת"
    return df


def _daypart(hour: int) -> str:
    if 6 <= hour <= 9:   return "1. בוקר 06–09"
    if 10 <= hour <= 13: return "2. צהריים 10–13"
    if 14 <= hour <= 17: return '3. אחה"צ 14–17'
    if 18 <= hour <= 21: return "4. פריים-טיים 18–21"
    if hour >= 22 or hour <= 1: return "5. לילה 22–01"
    return "6. לילה מאוחר 02–05"


def load_from_supabase() -> pd.DataFrame:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set — cannot retrain from Supabase.")
    print("[retrain] Loading from Supabase...")
    with psycopg.connect(db_url) as conn:
        df = pd.read_sql(
            """
            select
                p.name           as "שם תוכנית",
                p.source_name    as "שם תוכנית_מקור",
                b.broadcast_date as "תאריך שידור",
                b.start_time     as "שעת התחלה",
                b.day_of_week    as "יום שידור",
                b.daypart        as "חלקי-יום",
                b.status         as "סטטוס תוכנית",
                b.duration_min   as "משך תוכנית_דק",
                b.event          as "אירוע_מיוחד",
                b.is_rerun,
                b.actual_rating  as "רייטינג",
                b.reception_pct
            from public.broadcasts b
            join public.programs p on p.id = b.program_id
            where b.actual_rating is not null
              and b.reception_pct is not null
            """,
            conn,
        )
    if len(df) == 0:
        raise RuntimeError("Supabase returned 0 broadcasts — aborting.")

    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    # Hour-of-start
    df["שעת התחלה_שעה"] = (
        pd.to_datetime(df["שעת התחלה"].astype(str), format="%H:%M:%S", errors="coerce")
        .dt.hour.fillna(20).astype(int)
    )
    # Daypart if missing
    if df["חלקי-יום"].isna().any():
        df["חלקי-יום"] = df.apply(
            lambda r: r["חלקי-יום"] if isinstance(r["חלקי-יום"], str) else _daypart(int(r["שעת התחלה_שעה"])),
            axis=1,
        )
    # Adjusted rating
    df["רייטינג מותאם"] = pd.to_numeric(df["רייטינג"], errors="coerce") / pd.to_numeric(df["reception_pct"], errors="coerce")
    df["משך תוכנית_דק"] = pd.to_numeric(df["משך תוכנית_דק"], errors="coerce")
    # Event tags — derived from the curated events file by date (NOT constant
    # defaults). This is the fix for the bug where security/holiday features
    # were collapsing to a single category and the model ignored them.
    df = tag_events_by_date(df)
    # Competitor columns: not in Supabase yet → 0
    for ch in COMPETITORS:
        if ch not in df.columns:
            df[ch] = 0.0
    return df


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    df = load_from_supabase()
    n_raw = len(df)
    print(f"[retrain] Loaded {n_raw:,} rows")

    df = add_features(df)
    df = df.dropna(subset=["lag_program_mean", "lag_slot_mean", TARGET]).reset_index(drop=True)
    print(f"[retrain] After lag-NaN drop: {len(df):,}")

    # Chronological split for evaluation
    df = df.sort_values("תאריך שידור").reset_index(drop=True)
    cut = int(len(df) * (1 - TEST_FRAC))
    train, test = df.iloc[:cut], df.iloc[cut:]
    cut_date = test["תאריך שידור"].iloc[0]
    print(f"[retrain] Train: {len(train):,}  ·  Test: {len(test):,}  ·  cut: {cut_date.date()}")

    # Train on train, evaluate on test
    model = HistGradientBoostingRegressor(
        max_iter=400, max_depth=6, learning_rate=0.05, random_state=42,
    )
    pipe_eval = Pipeline([("pre", build_preprocessor()), ("model", model)])
    pipe_eval.fit(train[ALL_COLS], train[TARGET].values)
    test_pred = pipe_eval.predict(test[ALL_COLS])
    test_mae = mean_absolute_error(test[TARGET].values, test_pred)
    test_r2 = r2_score(test[TARGET].values, test_pred)
    print(f"[retrain] Test MAE = {test_mae:.4f}  ·  R² = {test_r2:.4f}")

    # Re-fit on FULL data for production
    print("[retrain] Re-fitting on full dataset for production...")
    model_prod = HistGradientBoostingRegressor(
        max_iter=400, max_depth=6, learning_rate=0.05, random_state=42,
    )
    pipe_prod = Pipeline([("pre", build_preprocessor()), ("model", model_prod)])
    pipe_prod.fit(df[ALL_COLS], df[TARGET].values)

    # Save with metadata
    print(f"[retrain] Saving model → {OUT_MODEL.name}")
    joblib.dump({
        "pipeline": pipe_prod,
        "feature_cols": ALL_COLS,
        "num_cols": PRE_AIRING_FEATURES_NUM,
        "bool_cols": PRE_AIRING_FEATURES_BOOL,
        "cat_cols": PRE_AIRING_FEATURES_CAT,
        "model_name": "HistGradientBoosting",
        "target_name": TARGET,
        "target_kind": "adjusted",
        "expected_test_mae": round(float(test_mae), 4),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_train_rows": int(len(df)),
    }, OUT_MODEL)
    size_kb = OUT_MODEL.stat().st_size / 1024
    print(f"[retrain] ✓ Saved ({size_kb:.0f} KB)")

    # Append to log
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log_line = (
        f"| {today} | {len(df):,} | {cut_date.date()} | "
        f"{test_mae:.4f} | {test_r2:.4f} | {size_kb:.0f} |\n"
    )
    write_header = not OUT_LOG.exists()
    with open(OUT_LOG, "a", encoding="utf-8") as f:
        if write_header:
            f.write("# Retrain Log\n\n")
            f.write("היסטוריית retraining אוטומטי של המודל. שורה בכל הרצה.\n\n")
            f.write("| תאריך (UTC) | שורות | חיתוך test | Test MAE | Test R² | גודל KB |\n")
            f.write("|---|---|---|---|---|---|\n")
        f.write(log_line)
    print(f"[retrain] ✓ Appended to {OUT_LOG.name}")

    print("\n[retrain] Done.")


if __name__ == "__main__":
    main()
