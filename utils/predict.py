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


def compute_recent_trend(history_df: pd.DataFrame, program_name: str,
                          lookback_months: int = 3) -> float:
    """Compute month-over-month rating growth in recent months.
    Returns mean MoM growth rate (e.g., 0.05 = 5% per month)."""
    h = history_df[history_df["שם תוכנית_מקור"] == program_name].copy()
    if len(h) < 5:
        h = history_df.copy()  # fall back to global trend
    h["month"] = pd.to_datetime(h["תאריך שידור"]).dt.to_period("M")
    monthly = h.groupby("month")["רייטינג"].mean().tail(lookback_months + 1)
    if len(monthly) < 2:
        return 0.0
    pct_changes = monthly.pct_change().dropna()
    if len(pct_changes) == 0:
        return 0.0
    trend = float(pct_changes.mean())
    return max(min(trend, 0.20), -0.20)  # clamp to [-20%, +20%] / month


def compute_lag_features(history_df: pd.DataFrame,
                         program_name: str,
                         target_date,
                         hour: int,
                         status: str,
                         is_rerun: bool,
                         recent_window_days: int = 90,
                         duration_min: int = 30,
                         is_holiday: bool = False,
                         is_security: bool = False,
                         event_tag: str = "—") -> dict:
    """Compute lag features for a hypothetical future row.

    Uses ONLY the last `recent_window_days` of history (default 90) to make
    predictions track recent trends rather than the multi-year mean.
    """
    target_date = pd.to_datetime(target_date)
    weekday_he = date_to_weekday_he(target_date)

    # All history strictly before target_date
    h_full = history_df[history_df["תאריך שידור"] < target_date].copy()
    # Recent window
    cutoff = target_date - pd.Timedelta(days=recent_window_days)
    h = h_full[h_full["תאריך שידור"] >= cutoff].copy()
    # If recent window has too few rows, fall back to fuller history
    if len(h) < 200:
        h = h_full

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
        "משך תוכנית_דק": duration_min,
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
        "יום_חג": is_holiday,
        "יום_ביטחוני": is_security,
        "שבת": weekday_he == "שבת",
        "יום שידור": weekday_he,
        "חלקי-יום": hour_to_daypart(hour),
        "סטטוס תוכנית": status,
        "תג_עונה": "—",
        "תג_חג": event_tag if is_holiday else "—",
        "תג_ביטחוני": event_tag if is_security else "—",
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
                  is_special_event: bool = False,
                  apply_trend_correction: bool = True) -> dict:
    """Predict for a daypart (range). Runs model per hour + applies trend correction.

    Trend correction: if last 3 months show monthly growth of X%, the prediction
    for a date N months ahead is multiplied by (1 + X)^N.
    This corrects for the model's tendency to under-predict when historical
    averages are dominated by lower-rating early periods.
    """
    hours = daypart_to_hours(daypart)
    profile = get_program_profile(history_df, program_name)

    if status is None:
        status = profile["typical_status"]
    if is_rerun is None:
        is_rerun = status in ["ש.ח", "לקט"]

    # ---- Compute trend correction factor ----
    target_date = pd.to_datetime(target_date)
    last_data_date = history_df["תאריך שידור"].max()
    months_ahead = max(0, (target_date - last_data_date).days / 30.0)
    monthly_trend = compute_recent_trend(history_df, program_name, lookback_months=3)
    trend_multiplier = (1.0 + monthly_trend) ** months_ahead if apply_trend_correction else 1.0
    # Clamp to reasonable range
    trend_multiplier = max(0.5, min(2.5, trend_multiplier))

    # ---- Recent baseline for sanity check ----
    h_recent = history_df[
        (history_df["שם תוכנית_מקור"] == program_name) &
        (history_df["תאריך שידור"] >= last_data_date - pd.Timedelta(days=90))
    ]
    recent_mean = float(h_recent["רייטינג"].mean()) if len(h_recent) > 0 else profile["mean_rating"]

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
            # Apply trend correction
            corrected_point = r["point"] * trend_multiplier
            corrected_low = r["ci_low"] * trend_multiplier
            corrected_high = r["ci_high"] * trend_multiplier
            predictions.append({
                "hour": hour,
                "point": round(corrected_point, 3),
                "ci_low": round(corrected_low, 3),
                "ci_high": round(corrected_high, 3),
                "raw_point": r["point"],  # before trend correction
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
        "monthly_trend": round(monthly_trend * 100, 1),  # as percentage
        "trend_multiplier": round(trend_multiplier, 3),
        "months_ahead": round(months_ahead, 1),
        "recent_mean_90d": round(recent_mean, 3),
    }


def time_range_to_hour_weights(start_hour: int, start_min: int,
                                 end_hour: int, end_min: int) -> list:
    """Decompose a time range into (hour, minutes_in_that_hour) pairs.
    Handles wrap-around past midnight."""
    if (end_hour, end_min) <= (start_hour, start_min):
        end_hour += 24

    weights = []
    cur_h, cur_m = start_hour, start_min
    while (cur_h, cur_m) < (end_hour, end_min):
        next_boundary = (cur_h + 1, 0)
        if next_boundary <= (end_hour, end_min):
            mins_in_hour = (next_boundary[0] * 60) - (cur_h * 60 + cur_m)
            weights.append((cur_h % 24, mins_in_hour))
            cur_h, cur_m = next_boundary
        else:
            mins_in_hour = (end_hour * 60 + end_min) - (cur_h * 60 + cur_m)
            weights.append((cur_h % 24, mins_in_hour))
            break
    return weights


def predict_time_range(history_df: pd.DataFrame,
                        program_name: str,
                        target_date,
                        start_hour: int, start_min: int,
                        end_hour: int, end_min: int,
                        status: Optional[str] = None,
                        is_rerun: Optional[bool] = None,
                        is_holiday: bool = False,
                        is_security: bool = False,
                        event_tag: str = "—",
                        apply_trend_correction: bool = True) -> dict:
    """Predict for an exact time range (e.g., 19:50–22:00).
    Decomposes into hours, predicts each, returns weighted-average + range."""
    hour_weights = time_range_to_hour_weights(start_hour, start_min, end_hour, end_min)
    if not hour_weights:
        return None

    profile = get_program_profile(history_df, program_name)
    if status is None:
        status = profile["typical_status"]
    if is_rerun is None:
        is_rerun = status in ["ש.ח", "לקט"]

    duration_min = sum(w for _, w in hour_weights)

    # Trend correction setup
    target_date = pd.to_datetime(target_date)
    last_data_date = history_df["תאריך שידור"].max()
    months_ahead = max(0, (target_date - last_data_date).days / 30.0)
    monthly_trend = compute_recent_trend(history_df, program_name, lookback_months=3)
    trend_multiplier = (1.0 + monthly_trend) ** months_ahead if apply_trend_correction else 1.0
    trend_multiplier = max(0.5, min(2.5, trend_multiplier))

    # Recent baseline
    h_recent = history_df[
        (history_df["שם תוכנית_מקור"] == program_name) &
        (history_df["תאריך שידור"] >= last_data_date - pd.Timedelta(days=90))
    ]
    recent_mean = float(h_recent["רייטינג"].mean()) if len(h_recent) > 0 else profile["mean_rating"]

    # Predict for each hour in range
    predictions = []
    for (hr, mins) in hour_weights:
        try:
            r = predict_with_uncertainty(
                history_df=history_df,
                program_name=program_name,
                target_date=target_date,
                hour=hr,
                status=status,
                is_rerun=is_rerun,
                duration_min=duration_min,
                is_holiday=is_holiday,
                is_security=is_security,
                event_tag=event_tag,
            )
            predictions.append({
                "hour": hr,
                "minutes": mins,
                "weight": mins / duration_min,
                "point": round(r["point"] * trend_multiplier, 3),
                "ci_low": round(r["ci_low"] * trend_multiplier, 3),
                "ci_high": round(r["ci_high"] * trend_multiplier, 3),
                "raw_point": r["point"],
            })
        except Exception:
            pass

    if not predictions:
        return None

    # Weighted average across the time range
    weighted_pred = sum(p["point"] * p["weight"] for p in predictions)
    weighted_low = sum(p["ci_low"] * p["weight"] for p in predictions)
    weighted_high = sum(p["ci_high"] * p["weight"] for p in predictions)
    points = [p["point"] for p in predictions]

    return {
        "weighted_avg": round(weighted_pred, 3),
        "median": round(float(np.median(points)), 3),
        "min": round(float(min(points)), 3),
        "max": round(float(max(points)), 3),
        "ci_low": round(weighted_low, 3),
        "ci_high": round(weighted_high, 3),
        "predictions": predictions,
        "duration_min": duration_min,
        "n_hours": len(predictions),
        "profile": profile,
        "monthly_trend": round(monthly_trend * 100, 1),
        "trend_multiplier": round(trend_multiplier, 3),
        "months_ahead": round(months_ahead, 1),
        "recent_mean_90d": round(recent_mean, 3),
        "is_holiday": is_holiday,
        "is_security": is_security,
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
