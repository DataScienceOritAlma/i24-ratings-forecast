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
                          lookback_months: int = 6) -> float:
    """Compute moderate month-over-month rating growth in recent months.

    Uses 6-month lookback for stability. Returns linear (not compounded)
    monthly growth, capped to ±5%/month — realistic for TV ratings.
    Compounding 20%/month for 6 months is unrealistic; 5%/mo over 6 mo = 35%
    cumulative which is the upper-bound for real-world rating growth.
    """
    h = history_df[history_df["שם תוכנית_מקור"] == program_name].copy()
    if len(h) < 5:
        h = history_df.copy()
    h["month"] = pd.to_datetime(h["תאריך שידור"]).dt.to_period("M")
    monthly = h.groupby("month")["רייטינג"].mean().tail(lookback_months + 1)
    if len(monthly) < 3:
        return 0.0
    # Linear regression slope as % of mean (more robust than pct_change mean)
    y = monthly.values
    x = np.arange(len(y))
    if y.mean() <= 0:
        return 0.0
    slope = np.polyfit(x, y, 1)[0]
    monthly_growth = slope / y.mean()
    # Cap to ±5%/month — realistic for TV ratings
    return float(max(min(monthly_growth, 0.05), -0.05))


def compute_slot_uncertainty(history_df: pd.DataFrame, program_name: str,
                              hour: int, weekday_he: str) -> dict:
    """Estimate prediction uncertainty from slot residuals.

    Returns expected MAE and 80% prediction interval based on actual variance
    in the program × slot combination. Falls back to global slot std if too
    few historical points.
    """
    GLOBAL_MAE = 0.263  # from MODEL_REPORT_ALL test set

    # Try program × slot first
    h_ps = history_df[
        (history_df["שם תוכנית_מקור"] == program_name) &
        (history_df["שעת התחלה_שעה"] == hour) &
        (history_df["יום שידור"] == weekday_he)
    ]
    if len(h_ps) >= 5:
        std = float(h_ps["רייטינג"].std())
        n = len(h_ps)
        source = "תוכנית × רצועה"
    else:
        # Fall back to slot only
        h_s = history_df[
            (history_df["שעת התחלה_שעה"] == hour) &
            (history_df["יום שידור"] == weekday_he)
        ]
        if len(h_s) >= 10:
            std = float(h_s["רייטינג"].std())
            n = len(h_s)
            source = "רצועה (יום × שעה)"
        else:
            std = GLOBAL_MAE
            n = 0
            source = "ברירת מחדל גלובלית"

    return {
        "expected_mae": round(max(GLOBAL_MAE, std * 0.8), 3),
        "p80_half_width": round(std * 1.28, 3),  # 80% PI for normal
        "p95_half_width": round(std * 1.96, 3),
        "n": n,
        "source": source,
    }


def rating_to_viewers(rating: float, hh_per_point: int = 25000,
                      viewers_per_hh: float = 2.3) -> dict:
    """Convert rating point to estimated households + viewers.
    Based on Israeli TV norms:
      - 1 rating point ≈ 25,000 households (out of ~2.5M TV households)
      - Avg 2.3 viewers per watching household
    """
    households = int(round(rating * hh_per_point))
    viewers = int(round(households * viewers_per_hh))
    return {"households": households, "viewers": viewers}


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


def _parse_time_str(time_str) -> tuple:
    """Parse '19:50:00' or '19:50' or 19 → (hour, minute)."""
    s = str(time_str)
    if ":" in s:
        parts = s.split(":")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    try:
        return int(float(s)), 0
    except Exception:
        return 20, 0


def get_program_profile(history_df: pd.DataFrame, program_name: str) -> dict:
    """Get the historical profile of a program. Returns FULL start time (HH:MM)
    and median duration so UI can show real values, not just hour buckets."""
    h = history_df[history_df["שם תוכנית_מקור"] == program_name]
    if len(h) == 0:
        return {
            "exists": False,
            "n_airings": 0,
            "mean_rating": float(history_df["רייטינג"].mean()),
            "median_rating": float(history_df["רייטינג"].median()),
            "typical_day": "ראשון",
            "typical_start_hour": 20,
            "typical_start_minute": 0,
            "typical_duration_min": 60,
            "typical_status": "חי",
            "rating_std": 0.3,
        }

    # Use only LIVE broadcasts for "typical" start time (reruns/lakat
    # dominate the mode but aren't the program's main slot).
    # Status values: "שידור חי", "שידור חוזר", "לקט", "מבזק/חדש", "חג"
    h_live = h[h["סטטוס תוכנית"].astype(str).str.contains("חי", na=False)]
    h_for_typical = h_live if len(h_live) >= 3 else h

    # Typical start time — mode of full HH:MM string from live broadcasts
    if "שעת התחלה" in h_for_typical.columns:
        mode_time = h_for_typical["שעת התחלה"].mode()
        ts = str(mode_time.iloc[0]) if len(mode_time) else "20:00:00"
        start_h, start_m = _parse_time_str(ts)
    else:
        start_h, start_m = 20, 0

    # Typical duration — also from live broadcasts
    if "משך תוכנית_דק" in h_for_typical.columns:
        typical_dur = int(h_for_typical["משך תוכנית_דק"].median())
    else:
        typical_dur = 60

    return {
        "exists": True,
        "n_airings": len(h),
        "mean_rating": float(h["רייטינג"].mean()),
        "median_rating": float(h["רייטינג"].median()),
        "min_rating": float(h["רייטינג"].min()),
        "max_rating": float(h["רייטינג"].max()),
        "rating_std": float(h["רייטינג"].std()),
        "typical_day": h["יום שידור"].mode().iloc[0] if len(h["יום שידור"].mode()) else "ראשון",
        "typical_start_hour": start_h,
        "typical_start_minute": start_m,
        "typical_duration_min": typical_dur,
        "typical_status": h["סטטוס תוכנית"].mode().iloc[0] if len(h["סטטוס תוכנית"].mode()) else "חי",
        "days_distribution": h["יום שידור"].value_counts().to_dict(),
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
        is_rerun = "חוזר" in str(status) or "לקט" in str(status)

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
    """Predict for the entire program (start–end is the duration).

    The model was trained with one prediction per broadcast — using the START
    hour as the hour feature and the full duration. We do the same here:
    ONE prediction per broadcast, NOT one per hour.
    """
    # Compute total duration
    if (end_hour, end_min) <= (start_hour, start_min):
        duration_min = (end_hour + 24) * 60 + end_min - (start_hour * 60 + start_min)
    else:
        duration_min = (end_hour * 60 + end_min) - (start_hour * 60 + start_min)
    duration_min = max(5, duration_min)

    profile = get_program_profile(history_df, program_name)
    if status is None:
        status = profile["typical_status"]
    if is_rerun is None:
        is_rerun = "חוזר" in str(status) or "לקט" in str(status)

    # Trend correction
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

    # Single prediction using the START hour + full duration
    try:
        r = predict_with_uncertainty(
            history_df=history_df,
            program_name=program_name,
            target_date=target_date,
            hour=start_hour,
            status=status,
            is_rerun=is_rerun,
            duration_min=duration_min,
            is_holiday=is_holiday,
            is_security=is_security,
            event_tag=event_tag,
        )
    except Exception as e:
        return None

    point = r["point"] * trend_multiplier

    # ---- Better CI based on slot variance (replaces arbitrary ±std) ----
    weekday_he = date_to_weekday_he(target_date)
    uncertainty = compute_slot_uncertainty(history_df, program_name, start_hour, weekday_he)

    # Special events have wider uncertainty
    p80_half = uncertainty["p80_half_width"]
    if is_security:
        p80_half = max(p80_half, 0.6)  # security events are unpredictable
    elif is_holiday:
        p80_half = max(p80_half, 0.4)

    ci_low_v = max(0.0, point - p80_half)
    ci_high_v = point + p80_half

    # Viewer estimates for hero metric
    viewers = rating_to_viewers(point)

    return {
        "prediction": round(point, 3),
        "ci_low": round(ci_low_v, 3),
        "ci_high": round(ci_high_v, 3),
        "raw_prediction": round(r["point"], 3),
        "duration_min": duration_min,
        "start_time": f"{start_hour:02d}:{start_min:02d}",
        "end_time": f"{end_hour:02d}:{end_min:02d}",
        "profile": profile,
        "monthly_trend": round(monthly_trend * 100, 1),
        "trend_multiplier": round(trend_multiplier, 3),
        "months_ahead": round(months_ahead, 1),
        "recent_mean_90d": round(recent_mean, 3),
        "is_holiday": is_holiday,
        "is_security": is_security,
        "lag_program_n": r.get("lag_program_n", 0),
        "is_cold_start": r.get("is_cold_start", False),
        "uncertainty": uncertainty,
        "households": viewers["households"],
        "viewers": viewers["viewers"],
    }


def predict_forecast_curve(history_df: pd.DataFrame, program_name: str,
                            base_date, start_hour: int, start_min: int,
                            end_hour: int, end_min: int,
                            **kwargs) -> pd.DataFrame:
    """Generate forecast curve for the next 6 months.
    Returns DataFrame with columns: date, prediction, ci_low, ci_high."""
    base_date = pd.to_datetime(base_date)
    weekday_he = date_to_weekday_he(base_date)

    rows = []
    for days in [7, 14, 30, 60, 90, 120, 180]:
        future = base_date + pd.Timedelta(days=days)
        # Adjust to same weekday
        delta = (future.weekday() - base_date.weekday()) % 7
        future_aligned = future - pd.Timedelta(days=delta)
        try:
            r = predict_time_range(
                history_df=history_df,
                program_name=program_name,
                target_date=future_aligned,
                start_hour=start_hour, start_min=start_min,
                end_hour=end_hour, end_min=end_min,
                **kwargs,
            )
            if r:
                rows.append({
                    "date": future_aligned,
                    "days_ahead": days,
                    "prediction": r["prediction"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                })
        except Exception:
            pass
    return pd.DataFrame(rows)


def predict_scenarios(history_df: pd.DataFrame, program_name: str,
                       target_date, start_hour: int, start_min: int,
                       end_hour: int, end_min: int,
                       status: Optional[str] = None) -> list:
    """Generate predictions for 2 scenarios: routine vs special event."""
    scenarios = [
        {"name": "🟢 שגרה", "is_holiday": False, "is_security": False, "tag": "—"},
        {"name": "⚠️ אירוע מיוחד", "is_holiday": False, "is_security": True, "tag": "מיוחד"},
    ]
    results = []
    for s in scenarios:
        try:
            r = predict_time_range(
                history_df=history_df,
                program_name=program_name,
                target_date=target_date,
                start_hour=start_hour, start_min=start_min,
                end_hour=end_hour, end_min=end_min,
                status=status,
                is_holiday=s["is_holiday"], is_security=s["is_security"],
                event_tag=s["tag"],
            )
            if r:
                results.append({
                    "scenario": s["name"],
                    "prediction": r["prediction"],
                    "ci_low": r["ci_low"],
                    "ci_high": r["ci_high"],
                    "viewers": r["viewers"],
                })
        except Exception:
            pass
    return results


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
