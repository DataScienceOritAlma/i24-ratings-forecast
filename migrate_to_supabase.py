# -*- coding: utf-8 -*-
"""
migrate_to_supabase.py
----------------------
מעלה את `תוכניות_מעובד.xlsx` ל-Supabase Postgres.

הרצה ראשונה:
    py -3 -m pip install pandas openpyxl sqlalchemy "psycopg[binary]" python-dotenv
    py -3 migrate_to_supabase.py

דרישות מקדימות:
    1. רצת קודם את `schema.sql` ב-Supabase SQL Editor (יצרת את 6 הטבלאות)
    2. יש לך `.env` בתיקייה הזאת עם DATABASE_URL מלא
    3. הקובץ `תוכניות_מעובד.xlsx` קיים בתיקייה (10,039 שורות)

מה הסקריפט עושה:
    1. טוען את ה-xlsx (פעם אחת)
    2. מוצא 179 תוכניות ייחודיות → מעלה ל-`programs`
    3. מעבד 10,039 שידורים → מעלה ל-`broadcasts` עם FK ל-programs
    4. מאמת ספירות

אידמפוטנטי: אם רצת פעם אחת ואת רצה שוב — יזרוק שגיאת UNIQUE.
לניקוי לפני הרצה חוזרת: `TRUNCATE broadcasts, programs CASCADE;` ב-SQL Editor.
"""
import io
import os
import sys
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ---- Load env ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARN: python-dotenv not installed. Install: pip install python-dotenv")

DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL or 'REPLACE_ME' in DB_URL or 'YOUR_DB_PASSWORD' in DB_URL:
    sys.exit("ERROR: DATABASE_URL לא מוגדר נכון ב-.env. ראה .env.example.")

# Force psycopg3 driver (modern, maintained)
if DB_URL.startswith('postgresql://'):
    DB_URL = DB_URL.replace('postgresql://', 'postgresql+psycopg://', 1)

ROOT = Path(__file__).parent
SRC = ROOT / "תוכניות_מעובד.xlsx"
if not SRC.exists():
    sys.exit(f"ERROR: {SRC.name} לא נמצא")

print(f"→ Connecting to Supabase Postgres...")
engine = create_engine(DB_URL, pool_pre_ping=True)

# סנטיטי-צ'ק לחיבור
with engine.connect() as conn:
    n = conn.execute(text("select count(*) from public.programs")).scalar()
    if n > 0:
        sys.exit(f"⚠️  כבר יש {n} programs בטבלה. לניקוי: TRUNCATE broadcasts, programs CASCADE;")

# ---- Load xlsx ----
print(f"→ Loading {SRC.name}...")
df = pd.read_excel(SRC)
print(f"   loaded {len(df):,} rows × {df.shape[1]} columns")

# מיפוי עמודות לפי שם (לא לפי אינדקס — ראה memory: עמודות תוכניות_מעובד.xlsx)
def col(name):
    for c in df.columns:
        if c == name:
            return c
    raise KeyError(f"column not found: {name}")

C_NAME       = col('שם תוכנית')
C_DAY        = col('יום שידור')
C_DATE       = col('תאריך שידור')
C_START      = col('שעת התחלה')
C_END        = col('שעת סיום')
C_DUR        = col('משך תוכנית')
C_RATING     = col('רייטינג')
C_RECEPTION  = col('reception_pct')
C_SHARE      = col('נתח')
C_VIEWERS    = col('צופים 4+')
C_STATUS     = col('סטטוס תוכנית')
C_SOURCE     = col('שם תוכנית_מקור')
C_DAYPART    = col('חלקי-יום')
C_EVENT      = col('אירוע_מיוחד')
C_HUT        = col('HUT proxy')
C_ISRERUN    = col('is_rerun')

# ---- helpers ----
def parse_duration_min(v):
    """'00:11:29' → 11.48 דקות"""
    if pd.isna(v):
        return None
    s = str(v)
    m = re.match(r'(\d+):(\d+):(\d+)', s)
    if not m:
        return None
    h, mi, se = int(m[1]), int(m[2]), int(m[3])
    return round(h * 60 + mi + se / 60, 2)

def clean_time(v):
    """דרישות הטבלה: HH:MM:SS"""
    if pd.isna(v):
        return None
    s = str(v)
    if re.match(r'\d+:\d+:\d+', s):
        return s
    return None

# ---- 1. programs ----
print("\n1️⃣  Programs...")
programs = (
    df[[C_NAME, C_SOURCE]]
    .dropna(subset=[C_NAME])
    .groupby(C_NAME, as_index=False)
    .first()
    .rename(columns={C_NAME: 'name', C_SOURCE: 'source_name'})
)

# סטטיסטיקות פר תוכנית
stats = (
    df.groupby(C_NAME).agg(
        n_broadcasts=(C_NAME, 'size'),
        first_aired=(C_DATE, 'min'),
        last_aired=(C_DATE, 'max'),
    ).reset_index().rename(columns={C_NAME: 'name'})
)
stats['first_aired'] = pd.to_datetime(stats['first_aired'], errors='coerce').dt.date
stats['last_aired'] = pd.to_datetime(stats['last_aired'], errors='coerce').dt.date

programs = programs.merge(stats, on='name', how='left')

programs.to_sql('programs', engine, schema='public',
                if_exists='append', index=False, method='multi', chunksize=200)
print(f"   ✓ {len(programs)} programs inserted")

# ---- lookup IDs ----
with engine.connect() as conn:
    id_map = pd.read_sql(
        "select id, name from public.programs", conn
    ).set_index('name')['id'].to_dict()

# ---- 2. broadcasts ----
print("\n2️⃣  Broadcasts...")

broadcasts = pd.DataFrame({
    'program_id':     df[C_NAME].map(id_map),
    'broadcast_date': pd.to_datetime(df[C_DATE], errors='coerce').dt.date,
    'start_time':     df[C_START].apply(clean_time),
    'end_time':       df[C_END].apply(clean_time),
    'duration_min':   df[C_DUR].apply(parse_duration_min),
    'day_of_week':    df[C_DAY],
    'daypart':        df[C_DAYPART],
    'status':         df[C_STATUS],
    'event':          df[C_EVENT],
    'is_rerun':       df[C_ISRERUN].fillna(False).astype(bool),
    'actual_rating':  pd.to_numeric(df[C_RATING], errors='coerce'),
    'share':          pd.to_numeric(df[C_SHARE], errors='coerce'),
    'viewers_4plus':  pd.to_numeric(df[C_VIEWERS], errors='coerce').astype('Int64'),
    'hut_proxy':      pd.to_numeric(df[C_HUT], errors='coerce'),
    'reception_pct':  pd.to_numeric(df[C_RECEPTION], errors='coerce'),
})

# הסרת שורות חסרות-קריטית
before = len(broadcasts)
broadcasts = broadcasts.dropna(subset=['program_id', 'broadcast_date', 'start_time'])
dropped = before - len(broadcasts)
if dropped:
    print(f"   ⚠️  הוסרו {dropped} שורות חסרות (program/date/time)")

# duplicate guard (אנחנו לא רוצים לפול על UNIQUE constraint)
broadcasts = broadcasts.drop_duplicates(
    subset=['broadcast_date', 'start_time', 'program_id'], keep='first'
)

broadcasts.to_sql('broadcasts', engine, schema='public',
                  if_exists='append', index=False, method='multi', chunksize=500)
print(f"   ✓ {len(broadcasts):,} broadcasts inserted")

# ---- 3. verify ----
print("\n3️⃣  Verification...")
with engine.connect() as conn:
    n_progs = conn.execute(text("select count(*) from public.programs")).scalar()
    n_bcst = conn.execute(text("select count(*) from public.broadcasts")).scalar()
    d_min, d_max = conn.execute(text(
        "select min(broadcast_date), max(broadcast_date) from public.broadcasts"
    )).first()
    avg_rating = conn.execute(text(
        "select round(avg(actual_rating)::numeric, 3) from public.broadcasts"
    )).scalar()

print(f"   programs:     {n_progs}")
print(f"   broadcasts:   {n_bcst:,}")
print(f"   date range:   {d_min} → {d_max}")
print(f"   avg rating:   {avg_rating}  (צפוי ~0.441)")

print("\n✅ Migration complete! בדקי ב-Supabase → Table Editor.")
