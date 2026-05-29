# -*- coding: utf-8 -*-
"""LLM agent: a free-text Hebrew question → a real rating prediction + explanation.

This is an *agent* (not just an LLM): the LLM has a tool — the trained rating
model. Flow:
  1. LLM parses the question into {program_name, target_date, hour, scenario}
     (grounded: it must pick a program from the real catalog).
  2. The actual model predicts (compute_lag_features + model_saved.joblib).
  3. explain_prediction() phrases the answer in Hebrew from the real numbers.

Run a demo:  py -3 -X utf8 chat_agent.py
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
from prediction_logic import compute_lag_features  # noqa: E402

from llm_client import chat_json  # noqa: E402
from explain import explain_prediction  # noqa: E402

_MODEL = joblib.load("model_saved.joblib")
PIPE, COLS = _MODEL["pipeline"], _MODEL["feature_cols"]

HIST = pd.read_excel("תוכניות_מעובד.xlsx", sheet_name="נתונים מעובדים")
HIST["תאריך שידור"] = pd.to_datetime(HIST["תאריך שידור"])
if "שעת התחלה_שעה" not in HIST.columns:
    HIST["שעת התחלה_שעה"] = (
        pd.to_datetime(HIST["שעת התחלה"].astype(str), format="%H:%M:%S", errors="coerce")
        .dt.hour.fillna(20).astype(int)
    )
PROGRAMS = sorted(HIST["שם תוכנית_מקור"].dropna().unique().tolist())


def parse_question(question: str, today: str) -> dict:
    system = (
        "אתה מפענח שאלות בעברית על תחזית רייטינג. חלץ מהשאלה והחזר JSON עם המפתחות:\n"
        "- program_name: שם התוכנית. חייב להיות התאמה מדויקת לאחד מהשמות ברשימה (או null אם אין):\n"
        f"{PROGRAMS}\n"
        f"- target_date: בפורמט YYYY-MM-DD. היום הוא {today}; פענח ביטויים כמו 'שישי הבא'.\n"
        "- hour: שעת השידור כמספר 0-23 (אם לא צוין, השתמש ב-20).\n"
        "- scenario: 'special_event' אם מוזכר אירוע/מלחמה/הסלמה/מבצע, אחרת 'routine'."
    )
    return chat_json([{"role": "system", "content": system},
                      {"role": "user", "content": question}])


def answer(question: str) -> str:
    today = datetime.date.today().isoformat()
    p = parse_question(question, today)
    program = p.get("program_name")
    if not program:
        return "לא זיהיתי על איזו תוכנית מדובר. נסי לציין שם תוכנית מהקטלוג."

    hour = int(p.get("hour") or 20)
    is_security = p.get("scenario") == "special_event"
    feats = compute_lag_features(
        HIST, program, p["target_date"], hour,
        status="שידור חי", is_rerun=False, is_security=is_security,
    )
    pred = float(PIPE.predict(pd.DataFrame([feats])[COLS])[0])
    expl = explain_prediction(
        program=program, weekday=feats["יום שידור"], hour=hour, predicted=pred,
        program_avg=feats["lag_program_mean"], slot_avg=feats["lag_slot_mean"],
        is_security=is_security,
    )
    return f"תחזית רייטינג מותאם ל\"{program}\" ({feats['יום שידור']}, {p['target_date']}): {pred:.2f}\n{expl}"


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    questions = [
        "מה הרייטינג הצפוי לחדר החדשות ביום שישי הקרוב בשמונה בערב?",
        "מה צפוי למהדורה המרכזית אם תפרוץ הסלמה ביטחונית בשבוע הבא?",
    ]
    for q in questions:
        print(f"\n❓ {q}")
        print("🤖 " + answer(q))
