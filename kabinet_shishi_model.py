"""
kabinet_shishi_model.py — מודל פשוט לתוכנית אחת: 'קבינט שישי'.

פישוט מדעת: מתוך 232 שורות בדאטה, יש רק 50 שידורים חיים (סטטוס='שידור חי').
כל השאר שידורים חוזרים/לקטים ואינם מנבאים תוכן חדש.

מטרה: לבדוק אם מודל ייעודי לתוכנית-אחת מנצח את המודל הכללי בייצור (MAE=0.300).

Y = 'רייטינג מותאם' (כפי שהוחלט בפרוייקט)
פיצול: כרונולוגי 80/20
"""

import sys
import io
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROGRAM_NAME = 'קבינט שישי'
TARGET = 'רייטינג מותאם'

# ---------- 1. טעינה וסינון ----------
df_all = pd.read_excel('תוכניות_מעובד.xlsx')
mask = (
    df_all['שם תוכנית'].astype(str).str.contains(PROGRAM_NAME, na=False) &
    (df_all['סטטוס תוכנית'] == 'שידור חי')
)
df = df_all[mask].copy()
df['תאריך שידור'] = pd.to_datetime(df['תאריך שידור'])
df = df.sort_values('תאריך שידור').reset_index(drop=True)

# ---------- 1.5 העשרה מ-אירועים_מדויקים.csv ----------
# רק אירועים ביטחוניים — חגים/עונות הוסרו מהמודל בשלב 57
events = pd.read_csv('אירועים_מדויקים.csv')
events = events[events['קטגוריה'] == 'ביטחוני'].copy()
events['תאריך_התחלה'] = pd.to_datetime(events['תאריך_התחלה'])
events['תאריך_סיום'] = pd.to_datetime(events['תאריך_סיום'])

def event_context(broadcast_date):
    """מחזיר (days_since_start, severity) של האירוע הפעיל ביום השידור.
    אם אין אירוע פעיל — (NaN, 0). אם כמה אירועים חופפים — האחרון שהתחיל."""
    active = events[(events['תאריך_התחלה'] <= broadcast_date) &
                    (events['תאריך_סיום'] >= broadcast_date)]
    if active.empty:
        return (np.nan, 0)
    latest = active.sort_values('תאריך_התחלה').iloc[-1]
    return ((broadcast_date - latest['תאריך_התחלה']).days, int(latest['severity']))

ctx = df['תאריך שידור'].apply(event_context)
df['days_since_event_start'] = ctx.apply(lambda t: t[0])
df['event_severity'] = ctx.apply(lambda t: t[1])
df['in_event'] = df['days_since_event_start'].notna().astype(int)
# broadcasts_in_current_event: מונה שידורים של קבינט שישי מתחילת האירוע (כולל הנוכחי)
# חושב פר שידור לפי תאריך התחלה של האירוע הפעיל, אם קיים
def broadcasts_so_far(idx):
    row = df.loc[idx]
    if pd.isna(row['days_since_event_start']):
        return 0
    event_start = row['תאריך שידור'] - pd.Timedelta(days=int(row['days_since_event_start']))
    return int(((df['תאריך שידור'] >= event_start) & (df['תאריך שידור'] <= row['תאריך שידור'])).sum())

df['broadcasts_in_current_event'] = [broadcasts_so_far(i) for i in df.index]

print(f'שידורים חיים של "{PROGRAM_NAME}": {len(df)}')
print(f'טווח: {df["תאריך שידור"].min().date()} → {df["תאריך שידור"].max().date()}')
print(f'{TARGET}: mean={df[TARGET].mean():.3f}, std={df[TARGET].std():.3f}, min={df[TARGET].min():.3f}, max={df[TARGET].max():.3f}')
print()

# ---------- 2. פיצ'רים ----------
# lag features (על הרייטינג המותאם) — קורים לפני השידור, אין דליפה
df['lag_1'] = df[TARGET].shift(1)
df['lag_2'] = df[TARGET].shift(2)
df['ema_4'] = df[TARGET].shift(1).ewm(span=4, adjust=False).mean()
df['rolling_mean_4'] = df[TARGET].shift(1).rolling(4, min_periods=1).mean()

# פיצ'רי-זמן
df['month'] = df['תאריך שידור'].dt.month
df['week_of_year'] = df['תאריך שידור'].dt.isocalendar().week.astype(int)
df['weeks_since_start'] = ((df['תאריך שידור'] - df['תאריך שידור'].min()).dt.days // 7)

# אירועים
df['is_security_day'] = df['יום_ביטחוני'].fillna(0).astype(int)
# תג ביטחוני — יש 4 ערכים; ניצור flags בסיסיים
df['sec_level'] = df['תג_ביטחוני'].astype(str)
sec_dummies = pd.get_dummies(df['sec_level'], prefix='sec').astype(int)
df = pd.concat([df, sec_dummies], axis=1)

# משך תוכנית
df['duration_min'] = df['משך תוכנית_דק']

FEATURES = (
    ['lag_1', 'lag_2', 'ema_4', 'rolling_mean_4',
     'month', 'week_of_year', 'weeks_since_start',
     'is_security_day', 'duration_min',
     'days_since_event_start', 'event_severity', 'in_event',
     'broadcasts_in_current_event']
    + list(sec_dummies.columns)
)

# משתמשים רק בשורות שיש להן lag_2 (מפילים 2 שורות ראשונות)
df_model = df.dropna(subset=['lag_2']).reset_index(drop=True)
print(f'שורות אחרי בניית lag: {len(df_model)}')
print()

# ---------- 3. פיצול כרונולוגי ----------
split = int(len(df_model) * 0.8)
train = df_model.iloc[:split]
test = df_model.iloc[split:]
print(f'Train: {len(train)} ({train["תאריך שידור"].min().date()} → {train["תאריך שידור"].max().date()})')
print(f'Test : {len(test)} ({test["תאריך שידור"].min().date()} → {test["תאריך שידור"].max().date()})')
print()

X_train, y_train = train[FEATURES].fillna(0), train[TARGET]
X_test, y_test = test[FEATURES].fillna(0), test[TARGET]

# ---------- 4. Baselines + מודלים ----------
results = []

# baseline 1: mean של train
pred_mean = np.full(len(test), y_train.mean())
results.append(('Baseline: ממוצע train', pred_mean))

# baseline 2: last value (lag_1)
pred_last = test['lag_1'].fillna(y_train.mean()).values
results.append(('Baseline: השבוע שעבר (lag_1)', pred_last))

# baseline 3: EMA_4
pred_ema = test['ema_4'].fillna(y_train.mean()).values
results.append(('Baseline: EMA(4)', pred_ema))

# מודל 1: Ridge
ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)
pred_ridge = ridge.predict(X_test)
results.append(('Ridge', pred_ridge))

# מודל 2: HistGB (עם רגולריזציה כי הדאטה קטן)
hgb = HistGradientBoostingRegressor(
    max_iter=200,
    max_depth=3,
    learning_rate=0.05,
    min_samples_leaf=5,
    l2_regularization=1.0,
    random_state=42,
)
hgb.fit(X_train, y_train)
pred_hgb = hgb.predict(X_test)
results.append(('HistGradientBoosting (מכוונן קטן)', pred_hgb))

# ---------- 5. דיווח ----------
print('=' * 72)
print(f'{"מודל":<40} {"MAE":>8} {"R²":>8}')
print('-' * 72)
for name, pred in results:
    mae = mean_absolute_error(y_test, pred)
    r2 = r2_score(y_test, pred)
    print(f'{name:<40} {mae:>8.3f} {r2:>8.3f}')
print('=' * 72)
print()

# חשיפת פיצ'רי-אירוע בtest — הצצה לאיך המבחן נראה
print("=== פיצ'רי אירוע ב-test ===")
print(test[['תאריך שידור', TARGET, 'days_since_event_start', 'event_severity', 'broadcasts_in_current_event']].to_string(index=False))
print()
print('לשם השוואה: המודל הכללי בייצור (HistGB על 179 תוכניות) — MAE=0.300 על test כללי.')
print(f'MAE ממוצע של Y ב-test של קבינט שישי: {y_test.mean():.3f} (mean baseline)')
print(f'טווח Y ב-test: [{y_test.min():.3f}, {y_test.max():.3f}]')

# תחזיות מפורטות
print()
print('=== תחזיות פר שידור (test) ===')
report = test[['תאריך שידור', TARGET]].copy()
report['ridge'] = pred_ridge
report['hgb'] = pred_hgb
report['ema_4'] = pred_ema
report['last_week'] = pred_last
report['תאריך שידור'] = report['תאריך שידור'].dt.date
print(report.to_string(index=False))
