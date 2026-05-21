# -*- coding: utf-8 -*-
"""
migrate_to_supabase.py
----------------------
מעלה את `תוכניות_מעובד.xlsx` ל-Supabase Postgres דרך psycopg ישיר.

דרישות:
    py -3 -m pip install pandas openpyxl "psycopg[binary]" python-dotenv

הרצה:
    py -3 migrate_to_supabase.py

מה הסקריפט עושה:
    1. טוען את ה-xlsx
    2. מעלה 179 תוכניות → `programs`
    3. מעלה 10K שידורים → `broadcasts` עם FK ל-programs
    4. מאמת ספירות

אידמפוטנטי: אם הטבלאות לא ריקות — הסקריפט יזרוק אזהרה ויעצור.
לאיפוס: TRUNCATE broadcasts, programs CASCADE; ב-Supabase SQL Editor.
"""
import io
import os
import re
import sys
import datetime as dt
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.types.json import Jsonb  # noqa: F401  (loads psycopg types)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL or 'REPLACE_ME' in DB_URL or 'YOUR_DB_PASSWORD' in DB_URL:
    sys.exit("ERROR: DATABASE_URL לא מוגדר נכון ב-.env")

ROOT = Path(__file__).parent
SRC = ROOT / "תוכניות_מעובד.xlsx"
if not SRC.exists():
    sys.exit(f"ERROR: {SRC.name} לא נמצא")


# ---------- helpers ----------
def parse_time(v):
    """'06:11:29' → datetime.time(6, 11, 29). Handles 24+ hours."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    m = re.match(r'(\d+):(\d+):(\d+)', s)
    if not m:
        return None
    h = int(m[1]) % 24  # 24:00 → 00:00
    return dt.time(h, int(m[2]), int(m[3]))


def parse_duration_min(v):
    """'00:11:29' → 11.48 דקות"""
    if pd.isna(v):
        return None
    m = re.match(r'(\d+):(\d+):(\d+)', str(v))
    if not m:
        return None
    return round(int(m[1]) * 60 + int(m[2]) + int(m[3]) / 60, 2)


def parse_date(v):
    if pd.isna(v):
        return None
    d = pd.to_datetime(v, errors='coerce')
    return None if pd.isna(d) else d.date()


def clean(v):
    """NaN/None → None לדאטא־בייס."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    return v


# ---------- load ----------
print(f"→ מתחבר ל-Supabase Postgres...")
conn = psycopg.connect(DB_URL)
print(f"✓ מחובר")

# בדיקה: האם כבר יש דאטא?
with conn.cursor() as cur:
    cur.execute("select count(*) from public.programs")
    n_existing = cur.fetchone()[0]
if n_existing > 0:
    conn.close()
    sys.exit(f"⚠️  כבר יש {n_existing} programs. לאיפוס: TRUNCATE broadcasts, programs CASCADE;")

print(f"→ טוען {SRC.name}...")
df = pd.read_excel(SRC)
print(f"   {len(df):,} שורות × {df.shape[1]} עמודות")


# ---------- column mapping (by name, not index) ----------
def col(name):
    if name not in df.columns:
        raise KeyError(f"missing column: {name}")
    return name

C_NAME      = col('שם תוכנית')
C_DAY       = col('יום שידור')
C_DATE      = col('תאריך שידור')
C_START     = col('שעת התחלה')
C_END       = col('שעת סיום')
C_DUR       = col('משך תוכנית')
C_RATING    = col('רייטינג')
C_RECEPTION = col('reception_pct')
C_SHARE     = col('נתח')
C_VIEWERS   = col('צופים 4+')
C_STATUS    = col('סטטוס תוכנית')
C_SOURCE    = col('שם תוכנית_מקור')
C_DAYPART   = col('חלקי-יום')
C_EVENT     = col('אירוע_מיוחד')
C_HUT       = col('HUT proxy')
C_ISRERUN   = col('is_rerun')


# ---------- 1. programs ----------
print("\n1️⃣  Programs...")
prog_df = (
    df[[C_NAME, C_SOURCE]]
    .dropna(subset=[C_NAME])
    .groupby(C_NAME, as_index=False)
    .first()
)

# סטטיסטיקות
stats = df.groupby(C_NAME).agg(
    n_broadcasts=(C_NAME, 'size'),
    first_aired=(C_DATE, 'min'),
    last_aired=(C_DATE, 'max'),
).reset_index()

prog_df = prog_df.merge(stats, on=C_NAME, how='left')

records = []
for _, r in prog_df.iterrows():
    records.append((
        clean(r[C_NAME]),
        clean(r[C_SOURCE]),
        parse_date(r['first_aired']),
        parse_date(r['last_aired']),
        int(r['n_broadcasts']) if pd.notna(r['n_broadcasts']) else 0,
    ))

with conn.cursor() as cur:
    cur.executemany(
        "insert into public.programs (name, source_name, first_aired, last_aired, n_broadcasts) "
        "values (%s, %s, %s, %s, %s)",
        records,
    )
conn.commit()
print(f"   ✓ {len(records)} programs inserted")


# ---------- lookup IDs ----------
with conn.cursor() as cur:
    cur.execute("select id, name from public.programs")
    id_map = {name: pid for pid, name in cur.fetchall()}


# ---------- 2. broadcasts ----------
print("\n2️⃣  Broadcasts...")

records = []
dropped = 0
seen = set()  # למניעת כפילויות UNIQUE
for _, r in df.iterrows():
    prog_id = id_map.get(r[C_NAME])
    d = parse_date(r[C_DATE])
    t = parse_time(r[C_START])
    if prog_id is None or d is None or t is None:
        dropped += 1
        continue

    key = (d, t, prog_id)
    if key in seen:
        dropped += 1
        continue
    seen.add(key)

    rating = pd.to_numeric(r[C_RATING], errors='coerce')
    share  = pd.to_numeric(r[C_SHARE], errors='coerce')
    view   = pd.to_numeric(r[C_VIEWERS], errors='coerce')
    hut    = pd.to_numeric(r[C_HUT], errors='coerce')
    rec    = pd.to_numeric(r[C_RECEPTION], errors='coerce')

    records.append((
        prog_id,                              # program_id (uuid)
        d,                                    # broadcast_date
        t,                                    # start_time
        parse_time(r[C_END]),                 # end_time
        parse_duration_min(r[C_DUR]),         # duration_min
        clean(r[C_DAY]),                      # day_of_week
        clean(r[C_DAYPART]),                  # daypart
        clean(r[C_STATUS]),                   # status
        clean(r[C_EVENT]),                    # event
        bool(r[C_ISRERUN]) if pd.notna(r[C_ISRERUN]) else False,
        float(rating) if pd.notna(rating) else None,
        float(share) if pd.notna(share) else None,
        int(round(view)) if pd.notna(view) else None,
        float(hut) if pd.notna(hut) else None,
        float(rec) if pd.notna(rec) else None,
    ))

if dropped:
    print(f"   ⚠️  הוסרו {dropped} שורות (חסרות / כפילויות)")

with conn.cursor() as cur:
    cur.executemany("""
        insert into public.broadcasts (
            program_id, broadcast_date, start_time, end_time, duration_min,
            day_of_week, daypart, status, event, is_rerun,
            actual_rating, share, viewers_4plus, hut_proxy, reception_pct
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, records)
conn.commit()
print(f"   ✓ {len(records):,} broadcasts inserted")


# ---------- 3. verify ----------
print("\n3️⃣  אימות...")
with conn.cursor() as cur:
    cur.execute("select count(*) from public.programs")
    n_p = cur.fetchone()[0]
    cur.execute("select count(*) from public.broadcasts")
    n_b = cur.fetchone()[0]
    cur.execute(
        "select min(broadcast_date), max(broadcast_date), "
        "round(avg(actual_rating)::numeric, 3) from public.broadcasts"
    )
    d_min, d_max, avg = cur.fetchone()

print(f"   programs:   {n_p}")
print(f"   broadcasts: {n_b:,}")
print(f"   date range: {d_min} → {d_max}")
print(f"   avg rating: {avg}   (צפוי ~0.441)")

conn.close()
print("\n✅ Migration complete! בדקי ב-Supabase → Table Editor.")
