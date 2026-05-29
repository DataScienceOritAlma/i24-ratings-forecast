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

SYSTEM = """אתה מסווג חדשות עבור ערוץ החדשות i24. בהינתן כותרת/ידיעה, החלט אם מדובר
באירוע ביטחוני או מדיני משמעותי שעשוי להשפיע על צפיית החדשות בישראל (הסלמה, מבצע,
מתקפה, פיגוע, הסכם מדיני גדול, וכו'). אירועי שגרה (מזג אוויר, ספורט, בידור) אינם נחשבים.

החזר אך ורק JSON בפורמט:
{"is_security_event": true/false, "name": "שם קצר לאירוע או null", "category": "ביטחוני/מדיני/—", "reasoning": "משפט קצר אחד בעברית"}"""


def classify(headline: str, date: str | None = None) -> dict:
    user = (f"תאריך: {date}\n" if date else "") + f"ידיעה: {headline}\n\nסווג."
    return chat_json([{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": user}])


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    samples = [
        "מתקפת טילים נרחבת מאיראן על מרכז הארץ, אזעקות בכל גוש דן",
        "צה\"ל פתח במבצע קרקעי רחב בדרום לבנון",
        "מזג אוויר נעים צפוי בסוף השבוע, טמפרטורות נעימות",
        "מכבי תל אביב ניצחה בגביע אירופה בכדורסל",
        "נחתם הסכם הפסקת אש בין ישראל לחיזבאללה",
    ]
    for s in samples:
        r = classify(s, date="2026-06-01")
        mark = "🚨" if r.get("is_security_event") else "—"
        print(f"\n{mark}  {s[:55]}")
        print(f"     → {r}")
