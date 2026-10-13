# -*- coding: utf-8 -*-
"""kabinet_features.py — הגדרות משותפות לאימון ולהגשה של מודל קבינט שישי.

גם `train_and_save_kabinet_model.py` וגם `backend/main.py` מייבאים מכאן, כדי
שהפיצ'רים בזמן חיזוי יחושבו בדיוק כמו באימון.

שלב 101 (2026-10-13): היעד הוא הרייטינג הגולמי (מה ש-i24 מדווחת), והפיצ'רים
צומצמו לארבעה. ראה WORK_LOG.md.
"""
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
EVENTS_CSV = ROOT / "אירועים_מדויקים.csv"

PROGRAM_NAME = "קבינט שישי"
TARGET = "רייטינג"
LIVE_STATUS = "שידור חי"
BROADCAST_DAY = "שישי"
FEATURES = ["lag_1", "ema_4", "rolling_mean_4", "is_security_day"]

# ימי שישי שהם חג או ערב חג: בתאריכים האלה התוכנית לא שודרה במתכונת הרגילה
# (22.5.2026 מהדורת חג; 11.9, 25.9 ו-2.10.2026 לא שודרה). חול המועד אינו ברשימה,
# כי בו התוכנית שודרה כרגיל (3.4.2026). יש להאריך את הרשימה פעם בשנה.
HOLIDAY_FRIDAYS = {
    date(2026, 5, 22): "שבועות",
    date(2026, 9, 11): "ערב ראש השנה",
    date(2026, 9, 25): "ערב סוכות",
    date(2026, 10, 2): "ערב שמחת תורה",
    date(2027, 6, 11): "שבועות",
    date(2027, 10, 1): "ערב ראש השנה",
    date(2027, 10, 15): "ערב סוכות",
    date(2027, 10, 22): "ערב שמחת תורה",
}


def load_security_events() -> pd.DataFrame:
    ev = pd.read_csv(EVENTS_CSV)
    ev = ev[ev["קטגוריה"] == "ביטחוני"].copy()
    ev["תאריך_התחלה"] = pd.to_datetime(ev["תאריך_התחלה"])
    ev["תאריך_סיום"] = pd.to_datetime(ev["תאריך_סיום"])
    return ev


def active_events(target_date, events: pd.DataFrame) -> list:
    """שמות האירועים הביטחוניים שפעילים בתאריך (רשימה ריקה אם אין)."""
    ts = pd.Timestamp(target_date)
    hit = events[(events["תאריך_התחלה"] <= ts) & (events["תאריך_סיום"] >= ts)]
    return hit.sort_values("תאריך_התחלה")["שם_אירוע"].tolist()


def select_live_fridays(df: pd.DataFrame) -> pd.DataFrame:
    """שידורי-חי רגילים של התוכנית: השם המדויק, יום שישי, שורה אחת לתאריך.
    מהדורות חג, 'מוקדמת', לקטים ושידורים חוזרים נשארים בחוץ."""
    mask = (
        (df["שם תוכנית"].astype(str).str.strip() == PROGRAM_NAME)
        & (df["סטטוס תוכנית"] == LIVE_STATUS)
        & (df["יום שידור"] == BROADCAST_DAY)
    )
    out = df[mask].copy()
    out["תאריך שידור"] = pd.to_datetime(out["תאריך שידור"])
    out[TARGET] = pd.to_numeric(out[TARGET], errors="coerce")
    out = out.dropna(subset=[TARGET]).sort_values("תאריך שידור")
    return out.drop_duplicates("תאריך שידור", keep="last").reset_index(drop=True)


def lag_features(past: pd.Series) -> dict:
    """פיצ'רי היסטוריה לשידור הבא, מתוך הרייטינג של כל השידורים שקדמו לו."""
    return {
        "lag_1": float(past.iloc[-1]),
        "ema_4": float(past.ewm(span=4, adjust=False).mean().iloc[-1]),
        "rolling_mean_4": float(past.tail(4).mean()),
    }
