# -*- coding: utf-8 -*-
"""Pure prediction logic — no Streamlit, no UI dependencies.

Imported by backend/main.py (FastAPI service). Mirrors utils/predict.py
but stripped of Streamlit decorators.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

DAYS_HE = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]
GLOBAL_MAE = 0.263


def hour_to_daypart(hour: int) -> str:
    if 6 <= hour <= 9: return "1. בוקר 06–09"
    if 10 <= hour <= 13: return "2. צהריים 10–13"
    if 14 <= hour <= 17: return '3. אחה"צ 14–17'
    if 18 <= hour <= 21: return "4. פריים-טיים 18–21"
    if hour >= 22 or hour <= 1: return "5. לילה 22–01"
    return "6. לילה מאוחר 02–05"


def date_to_weekday_he(date) -> str:
    return DAYS_HE[(pd.to_datetime(date).weekday() + 1) % 7]


def estimate_reception_pct(date) -> float:
    d = pd.to_datetime(date)
    start = pd.Timestamp("2025-05-01")
    end = pd.Timestamp("2026-04-30")
    if d <= start: return 0.65
    if d >= end:   return 0.90
    frac = (d - start).days / (end - start).days
    return round(0.65 + 0.25 * frac, 3)


def compute_recent_trend(history_df: pd.DataFrame, program_name: str,
                         lookback_months: int = 6) -> float:
    h = history_df[history_df["שם תוכנית_מקור"] == program_name].copy()
    if len(h) < 5:
        h = history_df.copy()
    h["month"] = pd.to_datetime(h["תאריך שידור"]).dt.to_period("M")
    monthly = h.groupby("month")["רייטינג"].mean().tail(lookback_months + 1)
    if len(monthly) < 3 or monthly.mean() <= 0:
        return 0.0
    slope = np.polyfit(np.arange(len(monthly)), monthly.values, 1)[0]
    return float(max(min(slope / monthly.mean(), 0.05), -0.05))


def compute_slot_uncertainty(history_df: pd.DataFrame, program_name: str,
                             hour: int, weekday_he: str) -> dict:
    h_ps = history_df[
        (history_df["שם תוכנית_מקור"] == program_name) &
        (history_df["שעת התחלה_שעה"] == hour) &
        (history_df["יום שידור"] == weekday_he)
    ]
    if len(h_ps) >= 5:
        std, n, src = float(h_ps["רייטינג"].std()), len(h_ps), "תוכנית × רצועה"
    else:
        h_s = history_df[
            (history_df["שעת התחלה_שעה"] == hour) &
            (history_df["יום שידור"] == weekday_he)
        ]
        if len(h_s) >= 10:
            std, n, src = float(h_s["רייטינג"].std()), len(h_s), "רצועה"
        else:
            std, n, src = GLOBAL_MAE, 0, "default"
    return {
        "p80_half_width": round(std * 1.28, 3),
        "n_used": n,
        "source": src,
    }


def rating_to_viewers(rating: float, hh_per_point: int = 25000,
                     viewers_per_hh: float = 2.3) -> dict:
    hh = int(round(rating * hh_per_point))
    return {"households": hh, "viewers": int(round(hh * viewers_per_hh))}


def compute_lag_features(history_df: pd.DataFrame, program_name: str,
                         target_date, hour: int, status: str, is_rerun: bool,
                         duration_min: int = 30, recent_window_days: int = 90,
                         is_holiday: bool = False, is_security: bool = False,
                         event_tag: str = "—") -> dict:
    target = pd.to_datetime(target_date)
    weekday_he = date_to_weekday_he(target)

    h_full = history_df[history_df["תאריך שידור"] < target].copy()
    cutoff = target - pd.Timedelta(days=recent_window_days)
    h = h_full[h_full["תאריך שידור"] >= cutoff].copy()
    if len(h) < 200:
        h = h_full

    # program lag
    prog = h[h["שם תוכנית_מקור"] == program_name]
    lag_prog_mean = prog["רייטינג"].mean() if len(prog) else h["רייטינג"].mean()
    lag_prog_n = len(prog)

    # slot lag (day × hour)
    slot = h[(h["יום שידור"] == weekday_he) & (h["שעת התחלה_שעה"] == hour)]
    lag_slot_mean = slot["רייטינג"].mean() if len(slot) else h["רייטינג"].mean()
    lag_slot_n = len(slot)

    # status × hour lag
    ss = h[(h["סטטוס תוכנית"] == status) & (h["שעת התחלה_שעה"] == hour)]
    lag_ss_mean = ss["רייטינג"].mean() if len(ss) else h["רייטינג"].mean()
    lag_ss_n = len(ss)

    # competitor lags
    comp = {}
    for ch in COMPETITORS:
        safe = ch.replace(" ", "_")
        if ch in h.columns:
            comp[f"lag_comp_{safe}_slot"] = (
                slot[ch].mean() if len(slot) else h[ch].mean()
            )
        else:
            comp[f"lag_comp_{safe}_slot"] = 0.0
    comp["lag_competitors_avg_slot"] = float(np.mean(list(comp.values())))

    return {
        "שעת התחלה_שעה": hour,
        "משך תוכנית_דק": duration_min,
        "reception_pct": estimate_reception_pct(target),
        "חודש": target.month,
        "יום_בחודש": target.day,
        "שבוע_בשנה": int(target.isocalendar().week),
        "lag_program_mean": lag_prog_mean,
        "lag_program_n": lag_prog_n,
        "lag_slot_mean": lag_slot_mean,
        "lag_slot_n": lag_slot_n,
        "lag_status_slot_mean": lag_ss_mean,
        "lag_status_slot_n": lag_ss_n,
        **comp,
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
