# -*- coding: utf-8 -*-
"""News-reading agent: pull a news RSS feed, classify each headline with the LLM,
and propose new security events for אירועים_מדויקים.csv.

This is the autonomous version of the events workflow (could run on a schedule,
like retrain/keepalive) — it uses RSS, not a tool only Claude has. Human-in-the-
loop by design: it PROPOSES (dry-run) and only writes with --apply.

    py -3 -X utf8 news_agent.py                 # propose only (safe)
    py -3 -X utf8 news_agent.py --apply          # append new events to the CSV
    py -3 -X utf8 news_agent.py --feed <url> --limit 10

Needs GROQ_API_KEY in .env (for classification).
"""
from __future__ import annotations

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from event_classifier import classify

DEFAULT_FEED = "https://www.ynet.co.il/Integration/StoryRss2.xml"
EVENTS_CSV = Path(__file__).resolve().parent / "אירועים_מדויקים.csv"


def fetch_headlines(url: str, limit: int) -> list[tuple[str, str | None]]:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for item in root.iter("item"):
        title = item.findtext("title")
        if title and title.strip():
            items.append((title.strip(), item.findtext("pubDate")))
        if len(items) >= limit:
            break
    return items


def _to_date(pub: str | None) -> str:
    d = pd.to_datetime(pub, errors="coerce") if pub else None
    return (d.date().isoformat() if d is not None and pd.notna(d)
            else pd.Timestamp.today().date().isoformat())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default=DEFAULT_FEED)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--apply", action="store_true",
                    help="append the proposed (new) security events to the CSV")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        headlines = fetch_headlines(args.feed, args.limit)
    except Exception as e:
        print(f"[news_agent] לא הצלחתי למשוך את הפיד ({args.feed}):\n  {e}", file=sys.stderr)
        return 1
    if not headlines:
        print("[news_agent] הפיד לא החזיר כותרות.", file=sys.stderr)
        return 1

    print(f"[news_agent] נמשכו {len(headlines)} כותרות מ-{args.feed}\n")
    proposals = []
    for title, pub in headlines:
        try:
            r = classify(title, date=_to_date(pub))
        except Exception as e:
            print(f"  ⚠️  כשל בסיווג: {e}")
            continue
        if r.get("is_security_event"):
            d = _to_date(pub)
            proposals.append({
                "קטגוריה": r.get("category", "ביטחוני"),
                "שם_אירוע": r.get("name") or title[:40],
                "תאריך_התחלה": d, "תאריך_סיום": d,
                "תיאור": title, "מקור": "news_agent", "severity": "",
            })
            print(f"  🚨 {title[:60]}\n       → {r.get('name')} ({r.get('category')})")
        else:
            print(f"  —  {title[:60]}")
        time.sleep(1.5)  # stay under the free-tier rate limit

    print(f"\n[news_agent] {len(proposals)} אירועים ביטחוניים אותרו.")
    if not proposals:
        return 0

    existing = pd.read_csv(EVENTS_CSV)
    known = set(existing["שם_אירוע"].astype(str))
    fresh = [p for p in proposals if p["שם_אירוע"] not in known]
    print(f"[news_agent] מתוכם {len(fresh)} חדשים (לא קיימים כבר ב-CSV).")

    if not args.apply:
        print("\n(הרצת הצעה בלבד — להוספה בפועל הריצי עם --apply. כדאי לעבור עליהם קודם.)")
        return 0

    if fresh:
        out = pd.concat([existing, pd.DataFrame(fresh)], ignore_index=True)
        out.to_csv(EVENTS_CSV, index=False, encoding="utf-8")
        print(f"✓ נוספו {len(fresh)} אירועים ל-{EVENTS_CSV.name}. מומלץ להריץ score_events_severity.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
