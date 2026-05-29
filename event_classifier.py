# -*- coding: utf-8 -*-
"""Classify a news item as a security/political event relevant to i24 ratings.

The "reads the news" agent's core: given a headline (and date), the LLM decides
whether it's a security/political event that could move TV-news viewing, and
returns a structured row ready to append to אירועים_מדויקים.csv.

Live news ingestion (WebSearch / a news API) is a separate integration step;
this module is the classification brain and is tested on sample headlines.

Run a demo:  py -3 -X utf8 event_classifier.py
"""
from __future__ import annotations

import sys

from llm_client import chat_json

SYSTEM = """אתה מסווג חדשות עבור ערוץ החדשות i24. החלט אם הכותרת מתארת
**אירוע ביטחוני/מדיני בזמן אמת** שמקפיץ צפייה בחדשות — אירוע מתפתח כעת:
מבצע צבאי, מתקפה, מטח טילים, פיגוע, חטיפה או שחרור חטופים, הכרזת מלחמה או הפסקת אש.

אל תסווג כאירוע (החזר false):
- ניתוח, פרשנות, דוח, ראיון, עדות, סיכום של אירוע שהסתיים מזמן
- דיון/מחלוקת פוליטית שגרתית
- חדשות שאינן ביטחוניות (ספורט, מזג אוויר, כלכלה, תרבות)

החזר אך ורק JSON בפורמט:
{"is_security_event": true/false, "name": "שם קצר לאירוע או null", "category": "ביטחוני/מדיני/—", "reasoning": "משפט קצר אחד בעברית"}"""


def classify(headline: str, date: str | None = None) -> dict:
    # NOTE: Groq's content filter rejects graphic security headlines (war crimes,
    # sexual violence) with HTTP 400 — common in real security news. Callers must
    # catch the exception and skip (news_agent does); the human review backstops it.
    user = (f"תאריך: {date}\n" if date else "") + f"ידיעה: {headline}\n\nסווג."
    return chat_json([{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": user}])


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    samples = [
        ("מתקפת טילים נרחבת מאיראן על מרכז הארץ, אזעקות בכל גוש דן", "צפוי: כן"),
        ("צה\"ל פתח במבצע קרקעי רחב בדרום לבנון", "צפוי: כן"),
        ("נחתם הסכם הפסקת אש בין ישראל לחיזבאללה", "צפוי: כן (מדיני בזמן אמת)"),
        ("דוח האו\"ם: צה\"ל אחראי לפשעי מלחמה בעזה", "צפוי: לא (דוח)"),
        ("המג\"דים מספרים בראיון מה באמת קרה בלבנון", "צפוי: לא (ראיון)"),
        ("מזג אוויר נעים צפוי בסוף השבוע", "צפוי: לא"),
        ("מכבי תל אביב ניצחה בכדורסל", "צפוי: לא"),
    ]
    for s, expected in samples:
        try:
            r = classify(s, date="2026-06-01")
        except Exception as e:
            print(f"\n⚠️  {s[:52]}   [{expected}]\n     → שגיאה: {e}")
            continue
        mark = "🚨" if r.get("is_security_event") else "—"
        print(f"\n{mark}  {s[:52]}   [{expected}]")
        print(f"     → {r}")
