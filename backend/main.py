# -*- coding: utf-8 -*-
"""i24 Ratings Forecast API — FastAPI service.

Loads HistGradientBoosting pipeline from model_saved.joblib, fetches broadcast
history from Supabase on startup, and serves /predict + /health.
"""
from __future__ import annotations

import os
import sys
from datetime import date as date_t, time as time_t
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Make `utils.imputers` importable (required by joblib pickle resolution)
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from utils.imputers import SimpleMedianImputer, SimpleConstantImputer  # noqa: F401, E402

from prediction_logic import (  # noqa: E402
    compute_lag_features,
    compute_recent_trend,
    compute_slot_uncertainty,
    date_to_weekday_he,
    rating_to_viewers,
)

load_dotenv(ROOT / ".env")


# ============================================================
# Startup — load model + history once
# ============================================================
MODEL_PATH = ROOT / "model_saved.joblib"
print(f"[startup] Loading model from {MODEL_PATH}...")
_MODEL_OBJ = joblib.load(MODEL_PATH)
PIPELINE = _MODEL_OBJ["pipeline"]
FEATURE_COLS = _MODEL_OBJ["feature_cols"]
MODEL_NAME = _MODEL_OBJ["model_name"]
EXPECTED_MAE = _MODEL_OBJ["expected_test_mae"]
print(f"[startup] ✓ {MODEL_NAME}, expected MAE = {EXPECTED_MAE}")


def _load_history() -> pd.DataFrame:
    """Load broadcasts from Supabase (or fall back to local xlsx)."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        print("[startup] Loading history from Supabase...")
        with psycopg.connect(db_url) as conn:
            df = pd.read_sql(
                """
                select
                    p.name              as "שם תוכנית",
                    p.source_name       as "שם תוכנית_מקור",
                    b.broadcast_date    as "תאריך שידור",
                    b.start_time        as "שעת התחלה",
                    b.day_of_week       as "יום שידור",
                    b.daypart           as "חלקי-יום",
                    b.status            as "סטטוס תוכנית",
                    b.event             as "אירוע_מיוחד",
                    b.is_rerun,
                    b.actual_rating     as "רייטינג",
                    b.share             as "נתח",
                    b.reception_pct
                from public.broadcasts b
                join public.programs p on p.id = b.program_id
                """,
                conn,
            )
    else:
        print("[startup] DATABASE_URL not set → xlsx fallback")
        df = pd.read_excel(
            ROOT / "תוכניות_מעובד.xlsx", sheet_name="נתונים מעובדים"
        )

    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    # שעת התחלה_שעה (hour as int)
    if "שעת התחלה" in df.columns:
        df["שעת התחלה_שעה"] = (
            pd.to_datetime(df["שעת התחלה"].astype(str),
                           format="%H:%M:%S", errors="coerce").dt.hour
        )
        df["שעת התחלה_שעה"] = df["שעת התחלה_שעה"].fillna(20).astype(int)
    # Competitor columns: empty in Supabase for now → fill with 0
    for ch in ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]:
        if ch not in df.columns:
            df[ch] = 0.0
    print(f"[startup] ✓ history rows: {len(df):,}")
    return df


HISTORY_DF = _load_history()


# ============================================================
# FastAPI app
# ============================================================
app = FastAPI(
    title="i24 Ratings Forecast API",
    description="שירות חיזוי רייטינג של תוכניות i24 — מבוסס HistGradientBoosting",
    version="1.0.0",
)

# CORS — open in dev; tighten to specific origin once frontend has a domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Schemas
# ============================================================
class PredictRequest(BaseModel):
    program_name: str = Field(..., description="שם תוכנית (כפי שמופיע בקטלוג)")
    target_date: date_t = Field(..., description="תאריך שידור צפוי (YYYY-MM-DD)")
    start_time: time_t = Field(..., description="שעת התחלה (HH:MM:SS)")
    end_time: Optional[time_t] = Field(None, description="שעת סיום (אופציונלי)")
    scenario: str = Field("routine", description="routine | special_event")
    status: str = Field("שידור חי", description="סטטוס תוכנית")


class PredictResponse(BaseModel):
    predicted_rating: float
    prediction_low: float
    prediction_high: float
    estimated_households: int
    estimated_viewers: int
    model: str
    confidence_pct: int = 80
    uncertainty_source: str
    metadata: dict


# ============================================================
# Endpoints
# ============================================================
@app.get("/")
def root():
    return {
        "service": "i24-ratings-forecast",
        "version": app.version,
        "model": MODEL_NAME,
        "history_rows": len(HISTORY_DF),
        "endpoints": ["/health", "/predict (POST)", "/docs"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "history_rows": len(HISTORY_DF),
        "expected_mae": EXPECTED_MAE,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    h = req.start_time.hour
    is_holiday = req.scenario == "special_event"
    is_security = False  # not enriched in v1

    feats = compute_lag_features(
        history_df=HISTORY_DF,
        program_name=req.program_name,
        target_date=req.target_date,
        hour=h,
        status=req.status,
        is_rerun=(req.status == "שידור חוזר"),
        is_holiday=is_holiday,
        is_security=is_security,
    )

    # Duration
    if req.end_time:
        dur = (req.end_time.hour - req.start_time.hour) * 60 + \
              (req.end_time.minute - req.start_time.minute)
        if dur < 0:
            dur += 24 * 60
        feats["משך תוכנית_דק"] = dur

    feature_row = pd.DataFrame([feats])[FEATURE_COLS]

    try:
        pred = float(PIPELINE.predict(feature_row)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    # Trend adjustment for far-future dates (capped to ±5%/mo, max 6 months)
    last_known = HISTORY_DF["תאריך שידור"].max()
    days_ahead = (pd.to_datetime(req.target_date) - last_known).days
    if days_ahead > 0:
        trend = compute_recent_trend(HISTORY_DF, req.program_name)
        months_ahead = min(days_ahead / 30, 6)
        pred *= (1 + trend) ** months_ahead

    pred = max(0.0, pred)

    weekday_he = date_to_weekday_he(req.target_date)
    uncert = compute_slot_uncertainty(HISTORY_DF, req.program_name, h, weekday_he)
    viewers = rating_to_viewers(pred)

    return PredictResponse(
        predicted_rating=round(pred, 3),
        prediction_low=round(max(0, pred - uncert["p80_half_width"]), 3),
        prediction_high=round(pred + uncert["p80_half_width"], 3),
        estimated_households=viewers["households"],
        estimated_viewers=viewers["viewers"],
        model=MODEL_NAME,
        confidence_pct=80,
        uncertainty_source=uncert["source"],
        metadata={
            "weekday": weekday_he,
            "hour": h,
            "scenario": req.scenario,
            "days_ahead": days_ahead,
            "n_uncertainty_basis": uncert["n_used"],
        },
    )
