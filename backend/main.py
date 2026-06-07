# -*- coding: utf-8 -*-
"""i24 Ratings Forecast API — FastAPI service.

Loads HistGradientBoosting pipeline from model_saved.joblib, fetches broadcast
history from Supabase on startup, and serves /predict + /health.
"""
from __future__ import annotations

import io
import os
import re
import sys

# Force UTF-8 stdout/stderr — startup prints use ✓/⚠️/—; on Windows the default
# is cp1255 (Hebrew) which crashes on these. Must run before any print().
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from datetime import date as date_t, time as time_t, timedelta, datetime
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
import psycopg
import requests
import stripe
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Make `utils.imputers` importable (required by joblib pickle resolution)
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from utils.imputers import SimpleMedianImputer, SimpleConstantImputer  # noqa: F401, E402

from prediction_logic import (  # noqa: E402
    compute_lag_features,
    compute_recent_trend,
    compute_slot_uncertainty,
    date_to_weekday_he,
    estimate_reception_pct,
    rating_to_viewers,
)

load_dotenv(ROOT / ".env")

# Optional LLM layer (explanation + chatbot). Degrades gracefully: if the import
# fails or GROQ_API_KEY is unset, the API still serves predictions without it.
try:
    from llm_client import chat_json  # noqa: E402
    from explain import explain_prediction  # noqa: E402
    _LLM_OK = True
except Exception:
    _LLM_OK = False


def _llm_ready() -> bool:
    return _LLM_OK and bool(os.environ.get("GROQ_API_KEY"))


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

# Conformal-calibrated quantile models for honest 80% prediction intervals.
# See DEEP_ANALYSIS.md §F and train_quantile_models.py. If the file is missing,
# /predict gracefully falls back to the std-of-slot interval.
QUANTILE_PATH = ROOT / "model_quantiles.joblib"
_QUANTILE_OBJ = None
if QUANTILE_PATH.exists():
    try:
        _QUANTILE_OBJ = joblib.load(QUANTILE_PATH)
        print(f"[startup] ✓ Quantile bundle loaded "
              f"(calibrated coverage={_QUANTILE_OBJ['cal_coverage_calibrated']:.1%}, "
              f"offsets [-{_QUANTILE_OBJ['offset_low']:.3f}, +{_QUANTILE_OBJ['offset_high']:.3f}])")
    except Exception as e:
        print(f"[startup] ⚠️  Failed to load quantile bundle: {e} → fallback to std interval")
        _QUANTILE_OBJ = None
else:
    print("[startup] ⚠️  model_quantiles.joblib not found → fallback to std interval")

# Post-hoc bias corrections per (status × daypart) — DEEP_ANALYSIS §J + שלב 80.
# See compute_bias_corrections.py. Keys are "status|daypart"; value is added to prediction.
import json as _json  # local alias to avoid touching the top imports
BIAS_PATH = ROOT / "bias_corrections.json"
_BIAS_CORRECTIONS: dict = {}
if BIAS_PATH.exists():
    try:
        _obj = _json.loads(BIAS_PATH.read_text(encoding="utf-8"))
        _BIAS_CORRECTIONS = _obj.get("corrections", {})
        print(f"[startup] ✓ Bias corrections loaded: {len(_BIAS_CORRECTIONS)} cells "
              f"(test MAE {_obj.get('test_mae_before')} → {_obj.get('test_mae_after')})")
    except Exception as e:
        print(f"[startup] ⚠️  Failed to load bias_corrections.json: {e}")
        _BIAS_CORRECTIONS = {}
else:
    print("[startup] ⚠️  bias_corrections.json not found → no bias correction applied")


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
    # Derive adjusted rating from raw + reception_pct (the model trains on this)
    if "רייטינג מותאם" not in df.columns and "רייטינג" in df.columns and "reception_pct" in df.columns:
        rp = pd.to_numeric(df["reception_pct"], errors="coerce")
        rr = pd.to_numeric(df["רייטינג"], errors="coerce")
        df["רייטינג מותאם"] = (rr / rp).where(rp > 0)
    print(f"[startup] ✓ history rows: {len(df):,}")
    return df


HISTORY_DF = _load_history()
# Sorted by length DESC so longest-match-wins in extraction
PROGRAM_CATALOG = sorted(
    HISTORY_DF["שם תוכנית"].dropna().astype(str).unique().tolist(),
    key=len,
    reverse=True,
)
print(f"[startup] ✓ catalog: {len(PROGRAM_CATALOG)} unique programs")

# ============================================================
# Stripe (optional — only configured if STRIPE_SECRET_KEY set)
# ============================================================
STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_PRO = os.environ.get("STRIPE_PRICE_PRO_MONTHLY", "")

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET
    print(f"[startup] ✓ Stripe configured (live: {not STRIPE_SECRET.startswith('sk_test_')})")
else:
    print("[startup] ⚠️  Stripe not configured (STRIPE_SECRET_KEY missing) — checkout disabled")


def _require_stripe():
    if not STRIPE_SECRET or not STRIPE_PRICE_PRO:
        raise HTTPException(
            status_code=503,
            detail=(
                "Stripe לא מוגדר. הוסיפי ב-.env: STRIPE_SECRET_KEY, "
                "STRIPE_PRICE_PRO_MONTHLY, STRIPE_WEBHOOK_SECRET. "
                "ראה STRIPE_SETUP.md."
            ),
        )


# ============================================================
# Auth — verify a Supabase JWT by asking Supabase itself.
# Avoids any local crypto / JWT-secret config (works with the new
# asymmetric-key Supabase projects too). Returns the user object on success.
# ============================================================
SUPABASE_URL = (
    os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    or os.environ.get("SUPABASE_URL")
    or "https://bfnmaogcxdgnaxwjdtny.supabase.co"
)
# The PUBLISHABLE (=anon) key is meant to be exposed publicly — it's bundled into
# the Vercel frontend already. Hardcoding it as the ultimate fallback prevents a
# Render env-var misconfiguration from silently 401-ing every user.
_DEFAULT_SUPABASE_KEY = "sb_publishable_7RMhqEoPZs73M1ZSbP0Uww_YLE9Nv76"
SUPABASE_KEY = (
    os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY")
    or _DEFAULT_SUPABASE_KEY
)
print(f"[startup] ✓ Supabase config: url={SUPABASE_URL}, key={'<env-var>' if SUPABASE_KEY != _DEFAULT_SUPABASE_KEY else '<hardcoded fallback>'}")
# Local-dev escape hatch — never set REQUIRE_AUTH=false in production
_AUTH_REQUIRED = os.environ.get("REQUIRE_AUTH", "true").lower() != "false"


def require_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency: verifies the caller's Supabase JWT and returns the user.

    Raises 401 if the token is missing or rejected by Supabase.
    Set REQUIRE_AUTH=false to bypass for local development.
    """
    if not _AUTH_REQUIRED:
        return {"id": "dev", "email": "dev@local"}

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    try:
        r = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_KEY},
            timeout=5,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {e}")

    if r.status_code != 200:
        # Surface the real reason for easier diagnosis — distinguishes "expired user
        # token" (the user needs to re-login) from "server-side apikey misconfigured"
        # (we have a deploy issue). Truncated to avoid leaking secrets.
        try:
            reason = r.json().get("msg") or r.json().get("message") or r.text[:120]
        except Exception:
            reason = r.text[:120]
        raise HTTPException(status_code=401, detail=f"Auth check failed ({r.status_code}): {reason}")

    return r.json()


# ============================================================
# NL helpers (mock GenAI — heuristic Hebrew parser)
# ============================================================
HE_DAYS = {
    "ראשון": 6, "שני": 0, "שלישי": 1, "רביעי": 2, "חמישי": 3, "שישי": 4, "שבת": 5,
}


def _next_weekday(target_weekday: int) -> date_t:
    today = date_t.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def extract_date_he(text: str) -> Optional[date_t]:
    t = text.strip()
    today = date_t.today()
    if "מחר" in t:
        return today + timedelta(days=1)
    if "היום" in t:
        return today
    if "שבוע" in t or "שבוע הבא" in t:
        return today + timedelta(days=7)
    if "חודש" in t:
        return today + timedelta(days=30)
    for day_name, wd in HE_DAYS.items():
        if day_name in t and ("הקרוב" in t or "הבא" in t or "ב" + day_name in t):
            return _next_weekday(wd)
    # explicit date: dd/mm/yyyy or dd-mm-yyyy or yyyy-mm-dd
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", t)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        if y < 100:
            y += 2000
        try:
            return date_t(y, mo, d)
        except ValueError:
            pass
    return None


def extract_program(text: str) -> Optional[str]:
    for name in PROGRAM_CATALOG:
        if name in text:
            return name
    # Try source_name match (program without "ש.ח" suffix)
    if "שם תוכנית_מקור" in HISTORY_DF.columns:
        for name in sorted(
            HISTORY_DF["שם תוכנית_מקור"].dropna().astype(str).unique(),
            key=len, reverse=True,
        ):
            if name and len(name) >= 4 and name in text:
                return name
    return None


def detect_scenario(text: str) -> str:
    # "special_event" is the canonical key for a SECURITY event (the only event
    # type the model still uses — holidays were dropped in שלב 57, so "חג" no
    # longer triggers it).
    if any(w in text for w in ["אירוע", "מבזק", "ברייקינג", "פיגוע", "מבצע",
                               "מלחמה", "הסלמה", "טילים"]):
        return "special_event"
    return "routine"


def llm_extract(q: str):
    """LLM-based intent parsing for /ask (replaces regex when GROQ is available).

    Returns (program_name, target_date, scenario) or None on any failure, so the
    caller can fall back to the regex extractors.
    """
    if not _llm_ready():
        return None
    try:
        programs = sorted(HISTORY_DF["שם תוכנית_מקור"].dropna().unique().tolist())
        today = date_t.today().isoformat()
        system = (
            "חלץ מהשאלה בעברית והחזר JSON עם המפתחות: "
            "program_name (התאמה מדויקת לאחד מהשמות ברשימה, או null), "
            f"target_date (פורמט YYYY-MM-DD; היום הוא {today}), "
            "scenario ('special_event' אם מוזכר אירוע/מלחמה/הסלמה/מבצע, אחרת 'routine').\n"
            f"רשימת התוכניות: {programs}"
        )
        r = chat_json([{"role": "system", "content": system},
                       {"role": "user", "content": q}])
        prog = r.get("program_name") or None
        td = pd.to_datetime(r.get("target_date"), errors="coerce")
        target = td.date() if pd.notna(td) else None
        scenario = r.get("scenario") if r.get("scenario") in ("routine", "special_event") else "routine"
        return prog, target, scenario
    except Exception:
        return None


# ============================================================
# FastAPI app
# ============================================================
app = FastAPI(
    title="i24 Ratings Forecast API",
    description="שירות חיזוי רייטינג של תוכניות i24 — מבוסס HistGradientBoosting",
    version="1.0.0",
)

# CORS — tightened. Allow localhost for dev + any vercel.app subdomain (production
# + preview deploys). Add a custom domain via env var EXTRA_CORS_ORIGINS=https://foo.com
_extra = [o.strip() for o in os.environ.get("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", *_extra],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Rate limiting — protects /predict and /ask from abuse (even authenticated users).
# 30/minute is comfortable for human usage but rules out spam. /health is exempt.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler — CORSMiddleware does NOT add headers to uncaught
# Python exceptions (the response is built by Starlette below the middleware
# stack). Without this handler, every 500 turns into a "Failed to fetch" in the
# browser because the response has no Access-Control-Allow-Origin header, so
# the user never sees the real error. We log a traceback server-side and echo
# the exception message back to the caller with proper CORS headers attached.
@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    import traceback as _tb
    _tb.print_exc()  # goes to Render logs

    origin = request.headers.get("origin", "")
    cors_headers: dict = {}
    if origin == "http://localhost:3000" or origin == "http://127.0.0.1:3000" \
       or re.match(r"^https://.*\.vercel\.app$", origin):
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
        headers=cors_headers,
    )

# Security headers — defense in depth (HSTS, no-sniff, frame-deny, referrer-policy).
# These are *response* headers; nothing to configure on the client.
@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ============================================================
# Schemas
# ============================================================
class PredictRequest(BaseModel):
    program_name: str = Field(..., description="שם תוכנית (כפי שמופיע בקטלוג)")
    target_date: date_t = Field(..., description="תאריך שידור צפוי (YYYY-MM-DD)")
    start_time: time_t = Field(..., description="שעת התחלה (HH:MM:SS)")
    end_time: Optional[time_t] = Field(None, description="שעת סיום (אופציונלי)")
    scenario: str = Field("routine", description="routine | special_event (=security event)")
    status: str = Field("שידור חי", description="סטטוס תוכנית")


class PredictResponse(BaseModel):
    predicted_rating: float          # adjusted rating (panel-corrected, business KPI)
    prediction_low: float            # 80% CI lower bound (adjusted scale)
    prediction_high: float           # 80% CI upper bound (adjusted scale)
    predicted_rating_raw: float      # derived: adjusted × estimated reception_pct
    reception_pct_used: float        # extrapolated panel reception for target_date
    estimated_households: int
    estimated_viewers: int
    model: str
    target_kind: str = "adjusted"
    confidence_pct: int = 80
    uncertainty_source: str
    # Cold-start signals (DEEP_ANALYSIS §C): a program with <5 prior broadcasts has
    # ~1.4× higher MAE than veterans. UI should show a warning badge so the user knows
    # the interval is wide because of low signal, not because the answer is "extreme".
    cold_start: bool = False
    n_historical_broadcasts: int = 0
    reliability: str = "high"           # "high" | "medium" | "cold_start"
    metadata: dict
    explanation: Optional[str] = None   # LLM natural-language explanation (null if GROQ key unset)


class AskRequest(BaseModel):
    question: str = Field(..., description="שאלה בעברית חופשית")


class AskResponse(BaseModel):
    question: str
    answer: str               # explanation in Hebrew
    extracted: dict           # {program_name, target_date, scenario, ...}
    prediction: Optional[PredictResponse] = None
    confidence: str           # "high" | "medium" | "low" — how sure we are we parsed correctly


class CheckoutRequest(BaseModel):
    user_id: str
    organization_id: str
    email: str
    return_url: str = Field(..., description="URL לחזרה אחרי תשלום (success or cancel)")


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


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


@app.post("/ask", response_model=AskResponse)
@limiter.limit("30/minute")
def ask(request: Request, req: AskRequest = Body(...), user: dict = Depends(require_user)):
    q = req.question.strip()
    parsed = llm_extract(q)            # LLM parsing if GROQ available
    if parsed and parsed[0]:
        program, target, scenario = parsed
        target = target or (date_t.today() + timedelta(days=7))
    else:                             # graceful fallback to the regex extractors
        program = extract_program(q)
        target = extract_date_he(q) or (date_t.today() + timedelta(days=7))
        scenario = detect_scenario(q)

    # Confidence based on what we managed to extract
    if program and any(kw in q for kw in ["מחר", "היום", "שבוע", "ראשון", "שני", "שלישי",
                                          "רביעי", "חמישי", "שישי", "שבת"]):
        confidence = "high"
    elif program:
        confidence = "medium"
    else:
        confidence = "low"

    extracted = {
        "program_name": program,
        "target_date": str(target),
        "scenario": scenario,
    }

    if not program:
        return AskResponse(
            question=q,
            answer=(
                "לא הצלחתי לזהות איזו תוכנית שאלת עליה. נסי לנסח עם שם תוכנית "
                "ספציפי, למשל: 'מה הצפי לקבינט שישי ביום שישי הבא?'"
            ),
            extracted=extracted,
            confidence="low",
        )

    # Build prediction internally
    pred_req = PredictRequest(
        program_name=program,
        target_date=target,
        start_time=time_t(19, 50),
        end_time=time_t(22, 0),
        scenario=scenario,  # type: ignore[arg-type]
        status="שידור חי",
    )
    pred = predict(request, pred_req, user=user)

    weekday_he_name = {
        0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת", 6: "ראשון"
    }[target.weekday()]
    scenario_he = "אירוע ביטחוני" if scenario == "special_event" else "שגרה"

    answer = (
        f"📊 תחזית לתוכנית **{program}** ב{weekday_he_name} {target.strftime('%d/%m/%Y')} "
        f"({scenario_he}):\n\n"
        f"רייטינג מותאם: **{pred.predicted_rating:.2f}**  "
        f"(גולמי משוער: {pred.predicted_rating_raw:.2f})\n"
        f"טווח 80%: {pred.prediction_low:.2f} – {pred.prediction_high:.2f}\n"
        f"בתי-אב מוערכים: {pred.estimated_households:,}\n"
        f"צופים מוערכים: {pred.estimated_viewers:,}\n\n"
        f"מקור אי-הוודאות: {pred.uncertainty_source}. "
        f"המודל: {pred.model}."
    )

    return AskResponse(
        question=q,
        answer=answer,
        extracted=extracted,
        prediction=pred,
        confidence=confidence,
    )


@app.post("/checkout/create-session", response_model=CheckoutResponse)
def create_checkout_session(req: CheckoutRequest):
    _require_stripe()

    db_url = os.environ.get("DATABASE_URL")
    customer_id: Optional[str] = None
    if db_url:
        with psycopg.connect(db_url) as conn, conn.cursor() as cur:
            cur.execute(
                "select stripe_customer_id from public.subscriptions where organization_id=%s",
                (req.organization_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                customer_id = row[0]

    if not customer_id:
        customer = stripe.Customer.create(
            email=req.email,
            metadata={"organization_id": req.organization_id, "user_id": req.user_id},
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": STRIPE_PRICE_PRO, "quantity": 1}],
        success_url=f"{req.return_url}?success=1&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.return_url}?canceled=1",
        subscription_data={
            "trial_period_days": 14,
            "metadata": {
                "organization_id": req.organization_id,
                "user_id": req.user_id,
            },
        },
        metadata={
            "organization_id": req.organization_id,
            "user_id": req.user_id,
        },
    )
    return CheckoutResponse(checkout_url=session.url, session_id=session.id)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe events. Set webhook URL in Stripe dashboard.
    Local dev: `stripe listen --forward-to localhost:8000/stripe/webhook`
    """
    _require_stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {e}")

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return {"received": True, "warning": "DATABASE_URL not set, not syncing"}

    etype = event["type"]
    data = event["data"]["object"]
    print(f"[stripe-webhook] {etype}")

    if etype in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        sub = data
        org_id = (sub.get("metadata") or {}).get("organization_id")
        user_id = (sub.get("metadata") or {}).get("user_id")

        # Get the price's nickname to infer tier (default 'pro')
        tier = "pro"
        try:
            price_id = sub["items"]["data"][0]["price"]["id"]
            if "enterprise" in (sub["items"]["data"][0]["price"].get("nickname") or "").lower():
                tier = "enterprise"
            elif price_id != STRIPE_PRICE_PRO:
                tier = "enterprise"
        except (KeyError, IndexError):
            pass

        if etype == "customer.subscription.deleted":
            status = "canceled"
        else:
            status = sub["status"]  # trialing / active / past_due / etc

        if org_id:
            with psycopg.connect(db_url, autocommit=True) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.subscriptions
                        (organization_id, stripe_customer_id, stripe_subscription_id,
                         status, tier, trial_ends_at, current_period_end)
                    values (%s, %s, %s, %s, %s,
                            to_timestamp(%s), to_timestamp(%s))
                    on conflict (organization_id) do update set
                        stripe_customer_id     = excluded.stripe_customer_id,
                        stripe_subscription_id = excluded.stripe_subscription_id,
                        status                 = excluded.status,
                        tier                   = excluded.tier,
                        trial_ends_at          = excluded.trial_ends_at,
                        current_period_end     = excluded.current_period_end,
                        updated_at             = now()
                    """,
                    (
                        org_id,
                        sub.get("customer"),
                        sub.get("id"),
                        status,
                        tier,
                        sub.get("trial_end"),
                        sub.get("current_period_end"),
                    ),
                )

    return {"received": True}


@app.post("/predict", response_model=PredictResponse)
@limiter.limit("30/minute")
def predict(request: Request, req: PredictRequest = Body(...), user: dict = Depends(require_user)):
    h = req.start_time.hour
    # "special_event" now means a SECURITY event. Holidays were dropped from the
    # model (שלב 57); this fires the strong יום_ביטחוני signal (≈+39% on a
    # typical prime-time program).
    is_security = req.scenario == "special_event"
    is_holiday = False

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

    # Post-hoc bias correction (שלב 80 / DEEP_ANALYSIS §J). Applied BEFORE quantile
    # intervals so the [low, high] band re-centers around the corrected prediction.
    bias_key = f"{req.status}|{feats.get('חלקי-יום', '')}"
    bias_shift = float(_BIAS_CORRECTIONS.get(bias_key, 0.0))
    if bias_shift != 0.0:
        pred = max(0.0, pred + bias_shift)

    weekday_he = date_to_weekday_he(req.target_date)
    uncert = compute_slot_uncertainty(HISTORY_DF, req.program_name, h, weekday_he)

    # Prediction interval — prefer conformal-calibrated quantile models (~80% empirical
    # coverage, validated). Falls back to symmetric std-of-slot if the bundle is missing.
    # The same bias_shift is applied to P10/P90 so the band stays centered on the corrected
    # prediction — if the model under-predicts the median by 0.27, it likely also under-
    # predicts the tails by the same amount.
    if _QUANTILE_OBJ is not None:
        try:
            p10_raw = float(_QUANTILE_OBJ["pipe_p10"].predict(feature_row)[0])
            p90_raw = float(_QUANTILE_OBJ["pipe_p90"].predict(feature_row)[0])
            low = max(0.0, p10_raw - _QUANTILE_OBJ["offset_low"] + bias_shift)
            high = max(low, p90_raw + _QUANTILE_OBJ["offset_high"] + bias_shift)
            interval_method = "conformal_quantile"
        except Exception:
            low = max(0.0, pred - uncert["p80_half_width"])
            high = pred + uncert["p80_half_width"]
            interval_method = "slot_std_fallback"
    else:
        low = max(0.0, pred - uncert["p80_half_width"])
        high = pred + uncert["p80_half_width"]
        interval_method = "slot_std"

    # Project back to "raw rating" scale for households/viewers calibration.
    # The viewer-conversion ratio (hh_per_point=25000) was calibrated on raw, panel-measured ratings.
    reception_pct = estimate_reception_pct(req.target_date)
    pred_raw = pred * reception_pct
    viewers = rating_to_viewers(pred_raw)

    # LLM explanation is the slowest step (Groq round-trip + retries can hit 30s+).
    # Two safeguards: env-var gate (LLM_EXPLAIN_PREDICTIONS=false skips entirely),
    # and a hard 1.5s wall-clock cap via ThreadPoolExecutor so a slow Groq never
    # blocks the user — they get the prediction and the explanation is just omitted.
    explanation = None
    if _llm_ready() and os.environ.get("LLM_EXPLAIN_PREDICTIONS", "true").lower() != "false":
        import concurrent.futures
        timeout_sec = float(os.environ.get("LLM_EXPLAIN_TIMEOUT_SEC", "1.5"))
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(
                    explain_prediction,
                    program=req.program_name, weekday=weekday_he, hour=h, predicted=pred,
                    program_avg=float(feats["lag_program_mean"]),
                    slot_avg=float(feats["lag_slot_mean"]), is_security=is_security,
                )
                explanation = future.result(timeout=timeout_sec)
        except (concurrent.futures.TimeoutError, Exception):
            explanation = None  # slow Groq, error, anything → no explanation, fast response

    # Reliability classification by historical-broadcast count (DEEP_ANALYSIS §C):
    #   n<5   → cold_start  (~36% higher MAE — show explicit warning)
    #   5-19  → medium      (warming up — quiet hint, not a warning)
    #   20+   → high        (no badge)
    n_hist = int(feats.get("lag_program_n", 0) or 0)
    if n_hist < 5:
        reliability = "cold_start"
    elif n_hist < 20:
        reliability = "medium"
    else:
        reliability = "high"

    return PredictResponse(
        predicted_rating=round(pred, 3),                       # adjusted (model target)
        prediction_low=round(low, 3),
        prediction_high=round(high, 3),
        predicted_rating_raw=round(pred_raw, 3),               # derived raw
        reception_pct_used=reception_pct,
        estimated_households=viewers["households"],
        estimated_viewers=viewers["viewers"],
        model=MODEL_NAME,
        target_kind=_MODEL_OBJ.get("target_kind", "adjusted"),
        confidence_pct=80,
        uncertainty_source=interval_method,
        cold_start=(reliability == "cold_start"),
        n_historical_broadcasts=n_hist,
        reliability=reliability,
        metadata={
            "weekday": weekday_he,
            "hour": h,
            "scenario": req.scenario,
            "days_ahead": days_ahead,
            "interval_method": interval_method,
            "slot_std_basis_n": uncert["n_used"],
            "slot_std_source": uncert["source"],
            "bias_correction_applied": round(bias_shift, 3),
        },
        explanation=explanation,
    )
