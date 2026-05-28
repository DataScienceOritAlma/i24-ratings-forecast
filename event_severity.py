# -*- coding: utf-8 -*-
"""LLM event-severity scorer — the first building block of the events agent.

Given an event (name + description) it asks an LLM to rate, 0–10, how much that
event boosts i24's TV-NEWS ratings. A single continuous severity number
generalizes to never-before-seen events, unlike the current one-hot tags which
can't score an event the model never saw in training.

Uses Groq's free OpenAI-compatible API via a plain HTTPS POST (no SDK needed).
Swap GROQ_URL/MODEL for OpenAI/Claude later — the message format is identical.

Usage:
    py -3 -X utf8 event_severity.py            # score the demo events (needs key)
    py -3 -X utf8 event_severity.py --dry-run  # print the prompt only (no key)

Key: put GROQ_API_KEY=gsk_... in .env (free key from https://console.groq.com).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# The rubric is the heart of the prompt: it anchors the 0–10 scale to i24's
# domain (a NEWS channel — security escalations spike viewing, calm holidays
# barely move it). Without an explicit rubric the model invents its own scale.
SYSTEM_PROMPT = """אתה אנליסט מדיה בערוץ החדשות הישראלי i24.
המשימה שלך: בהינתן אירוע, לדרג מ-0 עד 10 כמה הוא מגביר את צפיית החדשות (הרייטינג) בישראל.
זכור: זה ערוץ חדשות — הסלמות ביטחוניות מקפיצות צפייה, חגים רגועים כמעט ולא משפיעים.

טבלת דירוג (שים לב להבחנות הדקות בקצה העליון):
0   = יום רגיל, אין אירוע מיוחד
1-3 = חג קל / אירוע מינורי (ציבור בחופשה, השפעה קלה)
4-6 = חג מרכזי / אירוע מדיני בולט / הסלמה מקומית מוגבלת
7   = אירוע ביטחוני ממוקד / מתקפת טילים נקודתית / רגע לאומי חד-פעמי
8   = מבצע צבאי / הסלמה רחבה עם נפגעים
9   = מבצע אסטרטגי גדול ומתמשך / לחימה פעילה בכמה זירות במקביל
10  = מלחמה כוללת ומתמשכת ברמה הלאומית הגבוהה ביותר — האירוע הקיצוני ביותר

חשוב: היה קמצן עם הציון 10. רוב האירועים הגדולים הם 7-9. שמור 10 רק לאירוע יוצא-דופן באמת.

החזר אך ורק JSON בפורמט: {"severity": <מספר שלם 0-10>, "reasoning": "<משפט קצר אחד בעברית>"}"""

# Few-shot examples grounded in i24's REAL events (from אירועים_מדויקים.csv).
# They teach the model the boundaries of the scale on this exact domain.
FEWSHOT = [
    ("מלחמה כוללת בכל הזירות במקביל",
     "לחימה רחבה ומתמשכת בכמה חזיתות בו-זמנית, מאות הרוגים, מצב חירום לאומי.",
     10, "מלחמה כוללת ומתמשכת — האירוע הקיצוני ביותר."),
    ("מבצע שאגת הארי",
     "מבצע צבאי מתמשך (שבועות) נגד איראן. תקיפות נרחבות בטהראן ובערים נוספות.",
     9, "מבצע אסטרטגי גדול ומתמשך — צפייה מקסימלית לאורך זמן."),
    ("מבצע עם כלביא",
     "מבצע נגד מתקני הגרעין של איראן. מתקפת איראן הנגדית עם הרוגים בישראל.",
     8, "מבצע צבאי עם נפגעים — קפיצת צפייה גדולה."),
    ("מטחים כבדים על מרכז וירושלים",
     "מתקפת טילים נקודתית לכיוון מרכז הארץ, אזעקות ופגיעות.",
     7, "מתקפת טילים ממוקדת — שיא צפייה נקודתי."),
    ("פסח תשפ\"ו", "חג פסח (8 ימים).",
     4, "חג מרכזי — השפעה מתונה על צפיית החדשות."),
    ("חג חנוכה תשפ\"ו", "חג חנוכה (8 ימים).",
     3, "חג קל — השפעה מועטה."),
    ("ללא אירוע", "יום שגרה רגיל ללא אירוע מיוחד.",
     0, "יום רגיל — אין השפעה."),
]

# Events to score in the demo. The first two are NOT in the few-shot — they test
# whether the model generalizes the scale rather than parroting examples.
TEST_EVENTS = [
    ("הסכם הפסקת אש (סיום המלחמה)",
     "חתימת הסכם הפסקת אש שמסיים את המלחמה.", "(לא בדוגמאות — צפוי לרדת מ-10)"),
    ("שחרור 20 חטופים חיים",
     "חמאס שחרר את כל 20 החטופים החיים. רגע לאומי מכונן.", "(לא בדוגמאות — צפוי ~7)"),
    ("פגיעה בזרזיר",
     "מתקפה משולבת של איראן וחזבאללה, פגיעה ישירה בעמק יזרעאל.", "(לא בדוגמאות — צפוי ~7-8)"),
    ("פורים תשפ\"ו", "חג פורים.", "(לא בדוגמאות — צפוי ~2-3)"),
    ("מבצע שאגת הארי",
     "מבצע צבאי מתמשך נגד איראן.", "(בדוגמאות — צפוי 9)"),
]


def _fmt(name: str, description: str) -> str:
    return (f"אירוע: {name}\nתיאור: {description}\n"
            "דרג את עוצמת ההשפעה על רייטינג החדשות (0–10).")


def build_messages(name: str, description: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for ex_name, ex_desc, ex_score, ex_reason in FEWSHOT:
        msgs.append({"role": "user", "content": _fmt(ex_name, ex_desc)})
        msgs.append({"role": "assistant",
                     "content": json.dumps({"severity": ex_score, "reasoning": ex_reason},
                                           ensure_ascii=False)})
    msgs.append({"role": "user", "content": _fmt(name, description)})
    return msgs


def _extract_json(text: str) -> dict:
    """Be forgiving if the model wraps the JSON in prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def score_event(name: str, description: str, api_key: str, model: str = MODEL,
                max_retries: int = 6) -> dict:
    payload = {
        "model": model,
        "messages": build_messages(name, description),
        "temperature": 0.2,  # low → consistent, repeatable scores
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for attempt in range(max_retries):
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 429:  # free-tier rate limit — back off and retry
            wait = float(resp.headers.get("retry-after", 2 ** attempt))
            time.sleep(min(wait, 30))
            continue
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = _extract_json(content)
        return {"severity": int(data["severity"]), "reasoning": data.get("reasoning", "")}
    raise RuntimeError("Groq rate limit: exhausted retries")


def main() -> int:
    ap = argparse.ArgumentParser(description="Score event severity (0–10) with an LLM.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the prompt that would be sent, without calling the API.")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.dry_run:
        print("=== DRY RUN — the exact messages that would be sent to the LLM ===\n")
        for m in build_messages("הסכם הפסקת אש (סיום המלחמה)", "חתימת הסכם הפסקת אש שמסיים את המלחמה."):
            print(f"[{m['role']}]\n{m['content']}\n")
        print(f"(system + {len(FEWSHOT)} few-shot pairs + 1 query · model={args.model})")
        return 0

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY לא מוגדר.\n"
              "1. צרי מפתח חינמי ב-https://console.groq.com\n"
              "2. הוסיפי שורה לקובץ .env:  GROQ_API_KEY=gsk_...\n"
              "3. הריצי שוב.  (או הריצי --dry-run כדי לראות את ה-Prompt בלי מפתח)",
              file=sys.stderr)
        return 1

    print(f"Scoring {len(TEST_EVENTS)} events with {args.model}...\n")
    print(f"{'אירוע':<32} {'severity':>8}   הערה / נימוק")
    print("-" * 80)
    for name, desc, note in TEST_EVENTS:
        try:
            r = score_event(name, desc, api_key, args.model)
            print(f"{name:<32} {r['severity']:>8}   {note}")
            print(f"{'':<32} {'':>8}   → {r['reasoning']}")
        except Exception as e:
            print(f"{name:<32} {'ERROR':>8}   {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
