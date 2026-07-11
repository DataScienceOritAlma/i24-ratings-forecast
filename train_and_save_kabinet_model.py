"""
train_and_save_kabinet_model.py — מאמן על כל 48 השורות (בלי train/test split) ושומר
ל-model_kabinet_shishi.joblib עם כל המטא-דאטה שה-backend צריך.

הרעיון: kabinet_shishi_model.py משמש להערכה (עם split); הסקריפט הזה
לייצור-בפועל — מאמן על כל מה שיש, שומר, ומכניס לbackend.
"""

import io
import sys
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROGRAM_NAME = 'קבינט שישי'
TARGET = 'רייטינג מותאם'

# ---------- 1. טעינה ----------
df_all = pd.read_excel('תוכניות_מעובד.xlsx')
mask = (
    df_all['שם תוכנית'].astype(str).str.contains(PROGRAM_NAME, na=False) &
    (df_all['סטטוס תוכנית'] == 'שידור חי')
)
df = df_all[mask].copy()
df['תאריך שידור'] = pd.to_datetime(df['תאריך שידור'])
df = df.sort_values('תאריך שידור').reset_index(drop=True)
print(f'שידורים חיים של "{PROGRAM_NAME}": {len(df)}')

# ---------- 2. פיצ'רים ----------
df['lag_1'] = df[TARGET].shift(1)
df['lag_2'] = df[TARGET].shift(2)
df['ema_4'] = df[TARGET].shift(1).ewm(span=4, adjust=False).mean()
df['rolling_mean_4'] = df[TARGET].shift(1).rolling(4, min_periods=1).mean()

df['month'] = df['תאריך שידור'].dt.month
df['week_of_year'] = df['תאריך שידור'].dt.isocalendar().week.astype(int)
START_DATE = df['תאריך שידור'].min()
df['weeks_since_start'] = ((df['תאריך שידור'] - START_DATE).dt.days // 7)

df['is_security_day'] = df['יום_ביטחוני'].fillna(0).astype(int)
sec_levels_all = sorted(df['תג_ביטחוני'].astype(str).unique().tolist())
sec_dummies = pd.get_dummies(df['תג_ביטחוני'].astype(str), prefix='sec').astype(int)
df = pd.concat([df, sec_dummies], axis=1)

df['duration_min'] = df['משך תוכנית_דק']

FEATURES = (
    ['lag_1', 'lag_2', 'ema_4', 'rolling_mean_4',
     'month', 'week_of_year', 'weeks_since_start',
     'is_security_day', 'duration_min']
    + list(sec_dummies.columns)
)
print(f'{len(FEATURES)} פיצ\'רים: {FEATURES}')
print(f'רמות תג_ביטחוני שנצפו באימון: {sec_levels_all}')

# משתמשים רק בשורות עם lag_2
df_model = df.dropna(subset=['lag_2']).reset_index(drop=True)
X = df_model[FEATURES].fillna(0)
y = df_model[TARGET]
print(f'אימון על {len(df_model)} שורות (כולל כל ה-test מ-kabinet_shishi_model.py).')

# ---------- 3. אימון ----------
hgb = HistGradientBoostingRegressor(
    max_iter=200,
    max_depth=3,
    learning_rate=0.05,
    min_samples_leaf=5,
    l2_regularization=1.0,
    random_state=42,
)
hgb.fit(X, y)

# תחזית in-sample לצורך sanity
pred = hgb.predict(X)
mae_in = float(np.mean(np.abs(y - pred)))
print(f'in-sample MAE: {mae_in:.3f} (referenced expected_test_mae=0.717 מהניסוי)')

# ---------- 4. היסטוריה שהbackend צריך לחישוב lag ----------
# 4 השידורים האחרונים של קבינט שישי (חי), עם רייטינג מותאם + תאריך.
# ה-backend ישתמש בהם כדי לחשב lag_1, lag_2, ema_4, rolling_mean_4 לתחזית העתידית.
recent_history = df[['תאריך שידור', TARGET]].tail(6).reset_index(drop=True)
recent_history['תאריך שידור'] = recent_history['תאריך שידור'].dt.strftime('%Y-%m-%d')

# ממוצע ו-std של רייטינג מותאם לחישוב רווח-ביטחון 80% פשוט (זמנית עד שנאמן quantile חדש)
y_mean = float(y.mean())
y_std = float(y.std())

# ---------- 5. שמירה ----------
bundle = {
    'pipeline': hgb,
    'feature_cols': FEATURES,
    'model_name': 'HistGradientBoosting-KabinetShishi',
    'expected_test_mae': 0.717,
    'target_name': TARGET,
    'target_kind': 'adjusted',
    'in_sample_mae': mae_in,
    'sec_levels': sec_levels_all,
    'start_date': START_DATE.strftime('%Y-%m-%d'),
    'recent_history': recent_history.to_dict('records'),
    'y_mean': y_mean,
    'y_std': y_std,
    'n_train_rows': len(df_model),
    'program_name': PROGRAM_NAME,
    'trained_on': f'{df["תאריך שידור"].min().date()} → {df["תאריך שידור"].max().date()}',
    'notes': (
        'מודל ייעודי לתוכנית קבינט שישי בלבד — רק שידורים חיים (סטטוס=\'שידור חי\'). '
        'פיצ\'רים: lag_1/2, EMA4, rolling4, month, week_of_year, weeks_since_start, '
        'is_security_day, duration_min, sec_* one-hot של תג_ביטחוני. '
        'ה-backend צריך להזין lag_* מתוך recent_history + הפיצ\'רים החדשים.'
    ),
}
joblib.dump(bundle, 'model_kabinet_shishi.joblib')
print()
print(f'✓ נשמר: model_kabinet_shishi.joblib')
print(f'  Model: {bundle["model_name"]}')
print(f'  Features: {len(FEATURES)}')
print(f'  Expected test MAE: {bundle["expected_test_mae"]}')
print(f'  Y stats: mean={y_mean:.3f}, std={y_std:.3f}')
print(f'  Recent history rows: {len(recent_history)}')
