# -*- coding: utf-8 -*-
"""מריץ את schema.sql ב-Supabase. צעד 1/2 לפני migrate_to_supabase.py."""
import io
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()
DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL:
    sys.exit("ERROR: DATABASE_URL לא ב-.env")

print("→ מתחבר ל-Supabase...")
with psycopg.connect(DB_URL, autocommit=True) as conn:
    print("✓ מחובר")
    sql = Path("schema.sql").read_text(encoding='utf-8')
    print("→ מריץ schema.sql (6 טבלאות + RLS + indices)...")
    with conn.cursor() as cur:
        cur.execute(sql)
        # אימות נפרד (לא דרך השאילתה האחרונה של schema.sql)
        cur.execute(
            "select count(*) from information_schema.tables "
            "where table_schema='public' and table_name in "
            "('organizations','profiles','subscriptions','programs','broadcasts','predictions')"
        )
        n = cur.fetchone()[0]
        print(f"✓ {n}/6 טבלאות קיימות ב-public")

print("\n✅ schema.sql בוצע. כעת אפשר להריץ migrate_to_supabase.py")
