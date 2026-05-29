# -*- coding: utf-8 -*-
"""Natural-language (Hebrew) explanation for a rating prediction.

The LLM is given ONLY the numbers the model actually used (program/slot
averages, the security flag, the prediction). It must phrase them in plain
Hebrew without inventing anything — it is a renderer of facts, not a source of
new facts. This is the safe way to add a GenAI layer: no hallucinated data.

Run a demo:  py -3 -X utf8 explain.py
"""
from __future__ import annotations

import sys

from llm_client import chat

SYSTEM = """אתה אנליסט שמסביר תחזיות רייטינג של ערוץ החדשות i24 למנהלים, בעברית פשוטה.
תקבל תחזית ואת המספרים שעליהם היא מבוססת. נסח הסבר קצר (משפט-שניים), ענייני וברור.
חוקים נוקשים:
- השתמש אך ורק במספרים שניתנו לך. אל תמציא נתונים, אחוזים או עובדות חדשות.
- אם יש אירוע ביטחוני, ציין שהוא מעלה את הצפי.
- בלי שבחים ובלי מליצות. רק ההסבר."""


def explain_prediction(program: str, weekday: str, hour: int, predicted: float,
                       program_avg: float, slot_avg: float, is_security: bool,
                       trend_pct: float | None = None) -> str:
    facts = [
        f"תוכנית: {program}",
        f"יום: {weekday}, שעה: {hour}:00",
        f"תחזית רייטינג מותאם: {predicted:.2f}",
        f"ממוצע התוכנית בתקופה האחרונה: {program_avg:.2f}",
        f"ממוצע הרצועה (יום+שעה): {slot_avg:.2f}",
        f"אירוע ביטחוני פעיל: {'כן' if is_security else 'לא'}",
    ]
    if trend_pct is not None:
        facts.append(f"מגמת התוכנית: {trend_pct:+.0%} לחודש")
    user = "\n".join(facts) + "\n\nכתוב הסבר קצר בעברית למה זו התחזית."
    return chat([{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": user}]).strip()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    demos = [
        dict(program="חדר החדשות", weekday="שישי", hour=20, predicted=0.62,
             program_avg=0.55, slot_avg=0.58, is_security=False),
        dict(program="מהדורת חדשות", weekday="שלישי", hour=20, predicted=2.15,
             program_avg=1.50, slot_avg=1.10, is_security=True),
    ]
    for d in demos:
        print(f"\n[{d['program']} · {d['weekday']} · ביטחוני={d['is_security']}] → תחזית {d['predicted']}")
        print("  " + explain_prediction(**d))
