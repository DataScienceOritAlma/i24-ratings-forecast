# -*- coding: utf-8 -*-
"""Score every security event in אירועים_מדויקים.csv with the LLM and persist a
`severity` column (0–10). Non-security rows (חג/עונה) get 0.

Run once after adding new events to the curated file:
    py -3 -X utf8 score_events_severity.py            # score + write back
    py -3 -X utf8 score_events_severity.py --dry-run  # print, don't write

Frozen on disk so the feature pipeline is deterministic — re-run only when new
events are added. Needs GROQ_API_KEY in .env.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd

from event_severity import score_event, MODEL

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EVENTS_CSV = Path(__file__).resolve().parent / "אירועים_מדויקים.csv"
SECURITY_KINDS = {"ביטחוני", "מדיני"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print scores without writing the CSV.")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("GROQ_API_KEY לא מוגדר ב-.env", file=sys.stderr)
        return 1

    df = pd.read_csv(EVENTS_CSV)
    severities = []
    for _, r in df.iterrows():
        if r["קטגוריה"] in SECURITY_KINDS:
            res = score_event(str(r["שם_אירוע"]), str(r.get("תיאור", "")), key, MODEL)
            sev = res["severity"]
            print(f"  {sev:>2}  {r['שם_אירוע'][:45]:<45}  → {res['reasoning']}")
            time.sleep(2)  # stay under the free-tier rate limit
        else:
            sev = 0
            print(f"  {sev:>2}  {r['שם_אירוע'][:45]:<45}  (לא-ביטחוני)")
        severities.append(sev)

    df["severity"] = severities
    if args.dry_run:
        print("\n[dry-run] לא נכתב.")
        return 0

    # utf-8 WITHOUT BOM — the tagging code reads columns by name ("קטגוריה" etc.)
    df.to_csv(EVENTS_CSV, index=False, encoding="utf-8")
    print(f"\n✓ נכתב {EVENTS_CSV.name} עם עמודת severity ({len(df)} שורות)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
