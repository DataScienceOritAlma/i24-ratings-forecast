# -*- coding: utf-8 -*-
"""Compute lag features for a hypothetical future row, then predict.

The trained pipeline expects all engineered features. For a future row
(program_name, target_date, hour, status, etc.), we compute the lag features
from history (everything that happened before target_date).
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(DATA_DIR, "model_saved.joblib")

DAYS_HE = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]


def hour_to_daypart(hour: int) -> str:
    if 6 <= hour <= 9: return "1. בוקר 06–09"
    if 10 <= hour <= 13: return "2. צהריים 10–13"
    if 14 <= hour <= 17: return '3. אחה"צ 14–17'
    if 18 <= hour <= 21: return "4. פריים-טיים 18–21"
    if hour >= 22 or hour <= 1: return "5. לילה 22–01"
    return "6. לילה מאוחר 02–05"


def date_to_weekday_he(date) -> str:
    """Map date to Hebrew day name (Sunday = 0)."""
    return DAYS_HE[(pd.to_datetime(date).weekday() + 1) % 7]


def estimate_reception_pct(date) -> float:
    """Linear ramp from 65% (May 2025) to 90% (Apr 2026)."""
    d = pd.to_datetime(date)
    start = pd.Timestamp("2025-05-01")
    end = pd.Timestamp("2026-04-30")
    if d <= start:
        return 0.65
    if d >= end:
        return 0.90  # also use 0.90 for future dates beyond data
    frac = (d - start).days / (end - start).days
    return round(0.65 + 0.25 * frac, 3)


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


def compute_lag_features(history_df: pd.DataFrame,
                         program_name: str,
                         target_date,
                         hour: int,
                         status: str,
                         is_rerun: bool) -> dict:
    """Compute lag features as if we're predicting for a hypothetical row
    on target_date, using all history strictly before target_date.

    Returns a dict of all features needed by the saved pipeline.
    """
    target_date = pd.to_datetime(target_date)
    weekday_he = date_to_weekday_he(target_date)

    # All history strictly before target_date
    h = history_df[history_df["תאריך שידור"] < target_date].copy()

    # ---- Program lag (this exact program's history) ----
    prog_hist = h[h["שם תוכנית_מקור"] == program_name]
    if len(prog_hist) > 0:
        lag_program_mean = prog_hist["רייטינג"].mean()
        lag_program_n = len(prog_hist)
    else:
        # Cold start: program never aired before
        lag_program_mean = h["רייטינג"].mean()  # global fallback
        lag_program_n = 0

    # ---- Slot lag (day × hour) ----
    slot_hist = h[(h["יום שידור"] == weekday_he) & (h["שעת התחלה_שעה"] == hour)]
    if len(slot_hist) > 0:
        lag_slot_mean = slot_hist["רייטינג"].mean()
        lag_slot_n = len(slot_hist)
    else:
        lag_slot_mean = h["רייטינג"].mean()
        lag_slot_n = 0

    # ---- Status × slot lag ----
    ss_hist = h[(h["סטטוס תוכנית"] == status) & (h["שעת התחלה_שעה"] == hour)]
    if len(ss_hist) > 0:
        lag_status_slot_mean = ss_hist["רייטינג"].mean()
        lag_status_slot_n = len(ss_hist)
    else:
        lag_status_slot_mean = h["רייטינג"].mean()
        lag_status_slot_n = 0

    # ---- Competitor lags by slot ----
    comp_lags = {}
    for ch in COMPETITORS:
        col_safe = ch.replace(" ", "_")
        if len(slot_hist) > 0 and ch in h.columns:
            comp_lags[f"lag_comp_{col_safe}_slot"] = slot_hist[ch].mean()
        else:
            comp_lags[f"lag_comp_{col_safe}_slot"] = h[ch].mean() if ch in h.columns else 0.0
    comp_lags["lag_competitors_avg_slot"] = float(np.mean(list(comp_lags.values())))

    # ---- Date features ----
    feats = {
        "שעת התחלה_שעה": hour,
        "משך תוכנית_דק": 30,
        "reception_pct": estimate_reception_pct(target_date),
        "חודש": target_date.month,
        "יום_בחודש": target_date.day,
        "שבוע_בשנה": int(target_date.isocalendar().week),
        "lag_program_mean": lag_program_mean,
        "lag_program_n": lag_program_n,
        "lag_slot_mean": lag_slot_mean,
        "lag_slot_n": lag_slot_n,
        "lag_status_slot_mean": lag_status_slot_mean,
        "lag_status_slot_n": lag_status_slot_n,
        **comp_lags,
        "is_rerun": is_rerun,
        "יום_חג": False,
        "יום_ביטחוני": False,
        "שבת": weekday_he == "שבת",
        "יום שידור": weekday_he,
        "חלקי-יום": hour_to_daypart(hour),
        "סטטוס תוכנית": status,
        "תג_עונה": "—",
        "תג_חג": "—",
        "תג_ביטחוני": "—",
    }
    return feats


def get_program_profile(history_df: pd.DataFrame, program_name: str) -> dict:
    """Get the historical profile of a program — typical day, hour, status,
    and rating distribution. Used for smart defaults in the prediction UI."""
    h = history_df[history_df["שם תוכנית_מקור"] == program_name]
    if len(h) == 0:
        return {
            "exists": False,
            "n_airings": 0,
            "mean_rating": history_df["רייטינג"].mean(),
            "median_rating": history_df["רייטינג"].median(),
            "typical_day": "ראשון",
            "typical_hour": 20,
            "typical_status": "חי",
            "typical_daypart": hour_to_daypart(20),
            "rating_std": 0.3,
        }

    return {
        "exists": True,
        "n_airings": len(h),
        "mean_rating": float(h["רייטינג"].mean()),
        "median_rating": float(h["רייטינג"].median()),
        "min_rating": float(h["רייטינג"].min()),
        "max_rating": float(h["רייטינג"].max()),
        "rating_std": float(h["רייטינג"].std()),
        "typical_day": h["יום שידור"].mode().iloc[0] if len(h["יום שידור"].mode()) else "ראשון",
        "typical_hour": int(h["שעת התחלה_שעה"].mode().iloc[0]) if len(h["שעת התחלה_שעה"].mode()) else 20,
        "typical_status": h["סטטוס תוכנית"].mode().iloc[0] if len(h["סטטוס תוכנית"].mode()) else "חי",
        "typical_daypart": h["חלקי-יום"].mode().iloc[0] if len(h["חלקי-יום"].mode()) else hour_to_daypart(20),
        "days_distribution": h["יום שידור"].value_counts().to_dict(),
        "hours_distribution": h["שעת התחלה_שעה"].value_counts().to_dict(),
    }


def daypart_to_hours(daypart: str) -> list:
    """Map a daypart label to representative hours (for range prediction)."""
    mapping = {
        "1. בוקר 06–09": [6, 7, 8, 9],
        "2. צהריים 10–13": [10, 11, 12, 13],
        '3. אחה"צ 14–17': [14, 15, 16, 17],
        "4. פריים-טיים 18–21": [18, 19, 20, 21],
        "5. לילה 22–01": [22, 23, 0, 1],
        "6. לילה מאוחר 02–05": [2, 3, 4, 5],
    }
    return mapping.get(daypart, [20])


def predict_range(history_df: pd.DataFrame,
                  program_name: str,
                  target_date,
                  daypart: str,
                  status: Optional[str] = None,
                  is_rerun: Optional[bool] = None,
                  is_special_event: bool = False) -> dict:
    """Predict for a daypart (range) — runs the model for each hour in the
    daypart and returns the min/median/max as the prediction range."""
    hours = daypart_to_hours(daypart)
    profile = get_program_profile(history_df, program_name)

    # Smart defaults
    if status is None:
        status = profile["typical_status"]
    if is_rerun is None:
        is_rerun = status in ["ש.ח", "לקט"]

    predictions = []
    for hour in hours:
        try:
            r = predict_with_uncertainty(
                history_df=history_df,
                program_name=program_name,
                target_date=target_date,
                hour=hour,
                status=status,
                is_rerun=is_rerun,
            )
            predictions.append({
                "hour": hour,
                "point": r["point"],
                "ci_low": r["ci_low"],
                "ci_high": r["ci_high"],
            })
        except Exception:
            pass

    if not predictions:
        return None

    points = [p["point"] for p in predictions]
    return {
        "predictions": predictions,
        "median": round(float(np.median(points)), 3),
        "min": round(float(min(points)), 3),
        "max": round(float(max(points)), 3),
        "ci_low": round(min(p["ci_low"] for p in predictions), 3),
        "ci_high": round(max(p["ci_high"] for p in predictions), 3),
        "n_hours": len(predictions),
        "profile": profile,
    }


def predict_with_uncertainty(history_df: pd.DataFrame, **kwargs) -> dict:
    """Predict with a confidence interval estimated from per-slot historical std.

    kwargs match compute_lag_features signature.
    """
    bundle = load_model()
    pipe = bundle["pipeline"]
    feature_cols = bundle["feature_cols"]

    feats = compute_lag_features(history_df, **kwargs)
    row_df = pd.DataFrame([feats])[feature_cols]

    # Point prediction
    point = float(pipe.predict(row_df)[0])

    # Confidence interval: std of similar slots in history
    target_date = pd.to_datetime(kwargs["target_date"])
    weekday_he = date_to_weekday_he(target_date)
    hour = kwargs["hour"]
    h = history_df[history_df["תאריך שידור"] < target_date]
    slot_hist = h[(h["יום שידור"] == weekday_he) & (h["שעת התחלה_שעה"] == hour)]
    if len(slot_hist) >= 5:
        slot_std = float(slot_hist["רייטינג"].std())
    else:
        slot_std = 0.3  # fallback uncertainty

    ci_low = max(0.0, point - 1.0 * slot_std)
    ci_high = point + 1.0 * slot_std

    return {
        "point": round(point, 3),
        "ci_low": round(ci_low, 3),
        "ci_high": round(ci_high, 3),
        "slot_n": len(slot_hist),
        "slot_std": round(slot_std, 3),
        "lag_program_n": feats["lag_program_n"],
        "is_cold_start": feats["lag_program_n"] == 0,
        "features_used": feats,
    }
