"""
train_and_save_kabinet_model.py — מאמן את מודל הייצור של קבינט שישי ושומר
ל-model_kabinet_shishi.joblib.

שלב 101 (2026-10-13):
  - היעד הוא הרייטינג הגולמי, לא המותאם.
  - לפני האימון רץ מבחן walk-forward: לכל שידור מאמנים רק על מה שקדם לו וחוזים
    אותו. מהטעויות האלה נגזרים ה-MAE המדווח ורוחב טווח ה-80%.
  - המודל הסופי מתאמן על כל השידורים.

מקור הדאטה: Supabase אם DATABASE_URL מוגדר (כך זה רץ ב-CI), אחרת
תוכניות_מעובד.xlsx. `--xlsx` כופה את הקובץ המקומי.

הרצה:
    py -3 -X utf8 train_and_save_kabinet_model.py
"""

import argparse
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from kabinet_features import (
    FEATURES, PROGRAM_NAME, TARGET,
    active_events, lag_features, load_security_events, select_live_fridays,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:  # הרצה מקומית קוראת את DATABASE_URL מ-.env; ב-CI הוא משתנה סביבה אמיתי
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
OUT_MODEL = ROOT / 'model_kabinet_shishi.joblib'
OUT_LOG = ROOT / 'retrain_log_kabinet.md'
MIN_TRAIN = 30          # ה-walk-forward מתחיל אחרי 30 שידורים
MIN_SEC_RESIDUALS = 5   # פחות מזה: טווח האירוע הביטחוני נשען על כל הטעויות

ap = argparse.ArgumentParser()
ap.add_argument('--xlsx', action='store_true', help='לקרוא מ-תוכניות_מעובד.xlsx גם אם DATABASE_URL מוגדר')
args = ap.parse_args()


# ---------- 1. טעינה ----------
def load_broadcasts() -> tuple:
    db_url = os.environ.get('DATABASE_URL')
    if db_url and not args.xlsx:
        import psycopg
        with psycopg.connect(db_url) as conn:
            df = pd.read_sql(
                """
                select p.name           as "שם תוכנית",
                       b.broadcast_date as "תאריך שידור",
                       b.day_of_week    as "יום שידור",
                       b.status         as "סטטוס תוכנית",
                       b.actual_rating  as "רייטינג"
                from public.broadcasts b
                join public.programs p on p.id = b.program_id
                where p.name like %s
                """,
                conn, params=(f'%{PROGRAM_NAME}%',),
            )
        return df, 'Supabase'
    return pd.read_excel(ROOT / 'תוכניות_מעובד.xlsx'), 'תוכניות_מעובד.xlsx'


raw, source = load_broadcasts()
df = select_live_fridays(raw)
print(f'מקור: {source} | שידורי-חי של "{PROGRAM_NAME}" בימי שישי: {len(df)} '
      f'({df["תאריך שידור"].min().date()} → {df["תאריך שידור"].max().date()})')

# ---------- 2. פיצ'רים ----------
events = load_security_events()
df['is_security_day'] = df['תאריך שידור'].apply(lambda d: int(bool(active_events(d, events))))
rows = [lag_features(df[TARGET].iloc[:i]) if i > 0 else {} for i in range(len(df))]
df = pd.concat([df, pd.DataFrame(rows, index=df.index)], axis=1)
df_model = df.dropna(subset=['lag_1']).reset_index(drop=True)
X, y = df_model[FEATURES], df_model[TARGET]


def new_model() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_iter=200,
        max_depth=3,
        learning_rate=0.05,
        min_samples_leaf=5,
        l2_regularization=1.0,
        random_state=42,
    )


# ---------- 3. walk-forward: מה היה קורה אילו חזינו כל שבוע מחדש ----------
bt = []
for i in range(MIN_TRAIN, len(df_model)):
    m = new_model().fit(X.iloc[:i], y.iloc[:i])
    bt.append({
        'date': df_model.loc[i, 'תאריך שידור'],
        'actual': float(y.iloc[i]),
        'pred': float(m.predict(X.iloc[[i]])[0]),
        'lag_1': float(X.iloc[i]['lag_1']),
        'is_security_day': int(X.iloc[i]['is_security_day']),
    })
bt = pd.DataFrame(bt)
bt['err'] = bt['pred'] - bt['actual']
routine = bt[bt['is_security_day'] == 0]
security = bt[bt['is_security_day'] == 1]

mae_all = float(bt['err'].abs().mean())
mae_routine = float(routine['err'].abs().mean())
bias_routine = float(routine['err'].mean())
mae_lag1 = float((bt['lag_1'] - bt['actual']).abs().mean())
hw_routine = float(routine['err'].abs().quantile(0.8))
sec_pool = security if len(security) >= MIN_SEC_RESIDUALS else bt
hw_security = max(float(sec_pool['err'].abs().quantile(0.8)), hw_routine)

print(f'walk-forward על {len(bt)} שידורים ({bt["date"].min().date()} → {bt["date"].max().date()}):')
print(f'  MAE כולל {mae_all:.3f} | בשגרה {mae_routine:.3f} (n={len(routine)}, הטיה {bias_routine:+.3f}) '
      f'| באירוע ביטחוני {security["err"].abs().mean():.3f} (n={len(security)})')
print(f'  להשוואה, "כמו בשבוע שעבר": MAE {mae_lag1:.3f}')
print(f'  חצי-רוחב טווח 80%: שגרה ±{hw_routine:.2f} | אירוע ביטחוני ±{hw_security:.2f}')

# ---------- 4. אימון סופי על הכול ----------
hgb = new_model().fit(X, y)

bundle = {
    'pipeline': hgb,
    'feature_cols': FEATURES,
    'model_name': 'HistGradientBoosting-KabinetShishi-raw',
    'expected_test_mae': round(mae_routine, 3),
    'target_name': TARGET,
    'target_kind': 'raw',
    'interval_half_width': {'routine': round(hw_routine, 3), 'security': round(hw_security, 3)},
    'backtest': {
        'n': int(len(bt)),
        'mae_all': round(mae_all, 3),
        'mae_routine': round(mae_routine, 3),
        'bias_routine': round(bias_routine, 3),
        'mae_lag1_baseline': round(mae_lag1, 3),
    },
    'n_train_rows': int(len(df_model)),
    'program_name': PROGRAM_NAME,
    'trained_on': f'{df["תאריך שידור"].min().date()} → {df["תאריך שידור"].max().date()}',
    'data_source': source,
}
joblib.dump(bundle, OUT_MODEL)
print(f'✓ נשמר: {OUT_MODEL.name} ({bundle["n_train_rows"]} שורות אימון, {bundle["trained_on"]})')

# ---------- 5. לוג ----------
if not OUT_LOG.exists():
    OUT_LOG.write_text(
        '# Retrain Log — קבינט שישי\n\n'
        'שורה בכל אימון של `model_kabinet_shishi.joblib`. ה-MAE נמדד ב-walk-forward על רייטינג גולמי.\n\n'
        '| תאריך (UTC) | מקור | שידורים | שידור אחרון | MAE שגרה | MAE "שבוע שעבר" | טווח 80% שגרה |\n'
        '|---|---|---|---|---|---|---|\n',
        encoding='utf-8',
    )
with OUT_LOG.open('a', encoding='utf-8') as f:
    f.write(f'| {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC | {source} | {len(df)} | '
            f'{df["תאריך שידור"].max().date()} | {mae_routine:.3f} | {mae_lag1:.3f} | ±{hw_routine:.2f} |\n')
