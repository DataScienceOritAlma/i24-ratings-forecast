# -*- coding: utf-8 -*-
"""Feature engineering pipeline — turn a raw i24 file into the processed table.

Input: CSV or XLSX with the 15 native i24 columns (the same shape as the
       original `רשימת תוכניות.csv`):
       שם תוכנית · יום שידור · תאריך שידור · שעת התחלה · שעת סיום ·
       משך תוכנית · רייטינג · נתח · צופים 4+ · חשיפה 4+ · משך צפייה ·
       כאן 11 · קשת 12 · רשת 13 · עכשיו 14

Output: same data + 19 engineered columns (the 34-column processed table
        that the model trains on). Identical schema to תוכניות_מעובד.xlsx.

Behavior:
  - If --merge is passed (default), reads existing תוכניות_מעובד.xlsx
    and concats with the new data, deduping by (תאריך שידור, שעת התחלה,
    שם תוכנית).
  - If --replace, ignores the existing processed file.

Usage:
    py -3 -X utf8 process_raw_data.py path/to/new_data.xlsx
    py -3 -X utf8 process_raw_data.py path/to/new_data.csv --no-merge
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
EVENTS_CSV = ROOT / "אירועים_מדויקים.csv"
PROCESSED_XLSX = ROOT / "תוכניות_מעובד.xlsx"
RAW_CSV = ROOT / "רשימת תוכניות.csv"

# Panel reception calibration — observed monthly ramp May 2025 → April 2026.
# For dates past April 2026, we extrapolate linearly (capped at 0.95).
RECEPTION_START_PERIOD = pd.Period("2025-05", freq="M")
RECEPTION_END_PERIOD = pd.Period("2026-04", freq="M")
RECEPTION_START_PCT = 0.65
RECEPTION_END_PCT = 0.90
RECEPTION_CAP = 0.95
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]
NATIVE_15_COLS = [
    "שם תוכנית", "יום שידור", "תאריך שידור", "שעת התחלה", "שעת סיום",
    "משך תוכנית", "רייטינג", "נתח", "צופים 4+", "חשיפה 4+", "משך צפייה",
] + COMPETITORS


# ---------- helpers ----------------------------------------------------------
def reception_pct(date: pd.Timestamp) -> float:
    p = pd.Period(date, freq="M")
    if p <= RECEPTION_START_PERIOD:
        return RECEPTION_START_PCT
    total_steps = (RECEPTION_END_PERIOD - RECEPTION_START_PERIOD).n
    step = (p - RECEPTION_START_PERIOD).n
    frac = step / total_steps
    value = RECEPTION_START_PCT + (RECEPTION_END_PCT - RECEPTION_START_PCT) * frac
    return min(value, RECEPTION_CAP)


def td_to_minutes(s: pd.Series) -> pd.Series:
    return pd.to_timedelta(s.astype(str), errors="coerce").dt.total_seconds() / 60.0


def daypart(h: int) -> str:
    if 6 <= h <= 9:     return "1. בוקר 06–09"
    if 10 <= h <= 13:   return "2. צהריים 10–13"
    if 14 <= h <= 17:   return '3. אחה"צ 14–17'
    if 18 <= h <= 21:   return "4. פריים-טיים 18–21"
    if h >= 22 or h <= 1: return "5. לילה 22–01"
    return "6. לילה מאוחר 02–05"


def status_from_name(name: str) -> str:
    n = str(name)
    if "מיוחד" in n or "מבזק" in n:
        return "מיוחד/מבזק"
    if "לקט" in n:
        return "לקט"
    if "חג" in n:
        return "חג"
    if "ש.ח" in n:
        return "שידור חוזר"
    return "שידור חי"


# ---------- input loading ----------------------------------------------------
def load_raw(path: Path) -> pd.DataFrame:
    """Read CSV or XLSX. CSV may have a banner row above the headers
    (the original i24 format does). XLSX is assumed to have headers on row 1."""
    if path.suffix.lower() == ".csv":
        # First, peek at row 1 — if it doesn't include "שם תוכנית", skip it
        first = pd.read_csv(path, nrows=1, header=None)
        if "שם תוכנית" not in first.iloc[0].astype(str).values:
            df = pd.read_csv(path, skiprows=[0])
        else:
            df = pd.read_csv(path)
    elif path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file extension: {path.suffix}")

    # Sanity check
    missing = [c for c in NATIVE_15_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Input file is missing required column(s): {missing}\n"
            f"Expected the 15 native i24 columns:\n  {NATIVE_15_COLS}"
        )
    return df


# ---------- feature engineering ----------------------------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"], errors="coerce")
    df = df.dropna(subset=["תאריך שידור"]).reset_index(drop=True)

    # Duration features
    for c in ["משך תוכנית", "משך צפייה"]:
        df[c + "_דק"] = td_to_minutes(df[c])

    # Time features — keep only hour (the intermediate "_דק" is dropped at the end)
    _start_minutes = td_to_minutes(df["שעת התחלה"])
    df["שעת התחלה_שעה"] = (_start_minutes // 60).fillna(20).astype(int)

    # Re-run + program-source name
    df["is_rerun"] = df["שם תוכנית"].astype(str).str.contains(r"ש\.ח|לקט", regex=True, na=False)
    df["שם תוכנית_מקור"] = (
        df["שם תוכנית"].astype(str).str.replace(r"\s*ש\.ח\s*$", "", regex=True).str.strip()
    )

    # Competitor-derived features
    df["ממוצע מתחרים"] = df[COMPETITORS].mean(axis=1)
    df["יתרון מול מתחרים"] = df["רייטינג"] - df["ממוצע מתחרים"]
    df["HUT proxy"] = df[COMPETITORS].sum(axis=1) + df["רייטינג"]

    # Status (from program name pattern)
    df["סטטוס תוכנית"] = df["שם תוכנית"].apply(status_from_name)

    # Reception + adjusted rating
    df["reception_pct"] = df["תאריך שידור"].apply(reception_pct)
    df["רייטינג מותאם"] = df["רייטינג"] / df["reception_pct"]

    # Daypart
    df["חלקי-יום"] = df["שעת התחלה_שעה"].apply(daypart)

    return df


# ---------- events tagging ---------------------------------------------------
def load_events() -> pd.DataFrame | None:
    if not EVENTS_CSV.exists():
        return None
    ev = pd.read_csv(EVENTS_CSV)
    ev["תאריך_dt"] = pd.to_datetime(ev["תאריך_התחלה"], errors="coerce")
    ev["תאריך_סיום_dt"] = pd.to_datetime(ev["תאריך_סיום"], errors="coerce")
    ev["סוג"] = ev["קטגוריה"]
    ev["אירוע"] = ev["שם_אירוע"]
    return ev


def tag_events(df: pd.DataFrame, ev: pd.DataFrame | None) -> pd.DataFrame:
    df = df.copy()
    df["תג_עונה"] = "—"
    df["תג_חג"] = "—"
    df["תג_ביטחוני"] = "—"

    if ev is not None:
        sec_kinds = {"ביטחוני", "מדיני"}
        for kind, col_name in [("עונה", "תג_עונה"), ("חג", "תג_חג")]:
            for _, e in ev[ev["סוג"] == kind].iterrows():
                if pd.isna(e["תאריך_dt"]) or pd.isna(e["תאריך_סיום_dt"]):
                    continue
                m = (df["תאריך שידור"] >= e["תאריך_dt"]) & (df["תאריך שידור"] <= e["תאריך_סיום_dt"])
                df.loc[m, col_name] = e["אירוע"]
        for _, e in ev[ev["סוג"].isin(sec_kinds)].iterrows():
            if pd.isna(e["תאריך_dt"]) or pd.isna(e["תאריך_סיום_dt"]):
                continue
            m = (df["תאריך שידור"] >= e["תאריך_dt"]) & (df["תאריך שידור"] <= e["תאריך_סיום_dt"])
            existing = df.loc[m, "תג_ביטחוני"]
            df.loc[m, "תג_ביטחוני"] = existing.where(
                existing == "—", existing + " + " + e["אירוע"]
            ).where(existing != "—", e["אירוע"])

    df["יום_חג"] = df["תג_חג"] != "—"
    df["יום_ביטחוני"] = df["תג_ביטחוני"] != "—"
    df["שבת"] = df["יום שידור"] == "שבת"
    df["אירוע_מיוחד"] = df.apply(
        lambda r: r["תג_ביטחוני"] if r["תג_ביטחוני"] != "—"
        else (r["תג_חג"] if r["תג_חג"] != "—" else "—"),
        axis=1,
    )
    return df


# ---------- merge logic ------------------------------------------------------
def merge_with_existing(new_df: pd.DataFrame) -> pd.DataFrame:
    if not PROCESSED_XLSX.exists():
        print(f"[process] No existing {PROCESSED_XLSX.name} — using new data only")
        return new_df

    print(f"[process] Loading existing {PROCESSED_XLSX.name}...")
    existing = pd.read_excel(PROCESSED_XLSX, sheet_name="נתונים מעובדים")
    existing["תאריך שידור"] = pd.to_datetime(existing["תאריך שידור"])

    combined = pd.concat([existing, new_df], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(
        subset=["תאריך שידור", "שעת התחלה", "שם תוכנית"],
        keep="last",
    ).reset_index(drop=True)
    print(f"[process] Combined {len(existing):,} existing + {len(new_df):,} new "
          f"= {before:,} rows; after dedup = {len(combined):,}")
    return combined


# ---------- main -------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Process raw i24 data into the model's feature schema.")
    ap.add_argument("input", help="Path to the new raw data file (csv or xlsx).")
    ap.add_argument("--no-merge", action="store_true",
                    help="Don't merge with existing processed table; replace it.")
    ap.add_argument("--out", default=str(PROCESSED_XLSX),
                    help=f"Output xlsx path (default: {PROCESSED_XLSX.name})")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[process] ERROR: input file not found: {in_path}", file=sys.stderr)
        return 1

    print(f"[process] Reading {in_path.name}...")
    raw = load_raw(in_path)
    print(f"[process] Loaded {len(raw):,} rows · {len(raw.columns)} columns")

    print("[process] Adding engineered features...")
    feat = add_features(raw)

    ev = load_events()
    print(f"[process] Tagging events from {EVENTS_CSV.name if ev is not None else 'NONE'}...")
    feat = tag_events(feat, ev)

    if not args.no_merge:
        feat = merge_with_existing(feat)

    out_path = Path(args.out)
    print(f"[process] Writing {out_path.name}...")
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        feat.to_excel(xw, sheet_name="נתונים מעובדים", index=False)

    print(f"[process] ✓ Wrote {len(feat):,} rows · {len(feat.columns)} columns "
          f"({out_path.stat().st_size / 1024:.0f} KB)")
    print(f"[process] Date range: {feat['תאריך שידור'].min().date()} → {feat['תאריך שידור'].max().date()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
