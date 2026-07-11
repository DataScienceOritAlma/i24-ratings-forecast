"""
compare_general_vs_kabinet.py — מי טוב יותר לחזות קבינט שישי?

משווה את המודל הכללי (model_saved.joblib, MAE כללי=0.300, אומן על 179 תוכניות)
מול המודל הייעודי (kabinet_shishi_model.py, MAE=0.717, אומן על 38 שידורים)
— על אותן 10 שורות test של קבינט שישי, פיצול כרונולוגי זהה.
"""

import sys
import io
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
warnings.filterwarnings('ignore')

# ---- imports מהפרוייקט ----
sys.path.insert(0, '.')
from utils.imputers import SimpleMedianImputer, SimpleConstantImputer  # noqa

TARGET = 'רייטינג מותאם'
PROGRAM_NAME = 'קבינט שישי'

# ---------- טעינת הדאטה ----------
df_all = pd.read_excel('תוכניות_מעובד.xlsx')
mask_kab = (
    df_all['שם תוכנית'].astype(str).str.contains(PROGRAM_NAME, na=False) &
    (df_all['סטטוס תוכנית'] == 'שידור חי')
)
df_kab = df_all[mask_kab].copy()
df_kab['תאריך שידור'] = pd.to_datetime(df_kab['תאריך שידור'])
df_kab = df_kab.sort_values('תאריך שידור').reset_index(drop=True)

# בונים אותם lag features כמו במודל הייעודי (כדי לזהות אותן שורות test)
df_kab['lag_1'] = df_kab[TARGET].shift(1)
df_kab['lag_2'] = df_kab[TARGET].shift(2)
df_kab_model = df_kab.dropna(subset=['lag_2']).reset_index(drop=True)
split = int(len(df_kab_model) * 0.8)
test_kab = df_kab_model.iloc[split:].copy()

print(f'Test set: {len(test_kab)} שידורי קבינט שישי')
print(f'טווח test: {test_kab["תאריך שידור"].min().date()} → {test_kab["תאריך שידור"].max().date()}')
print()

# ---------- 1. המודל הייעודי (משחזרים MAE=0.717) ----------
# נבנה את הפיצ'רים ונאמן שוב HistGB כמו ב-kabinet_shishi_model.py
df_kab['ema_4'] = df_kab[TARGET].shift(1).ewm(span=4, adjust=False).mean()
df_kab['rolling_mean_4'] = df_kab[TARGET].shift(1).rolling(4, min_periods=1).mean()
df_kab['month'] = df_kab['תאריך שידור'].dt.month
df_kab['week_of_year'] = df_kab['תאריך שידור'].dt.isocalendar().week.astype(int)
df_kab['weeks_since_start'] = ((df_kab['תאריך שידור'] - df_kab['תאריך שידור'].min()).dt.days // 7)
df_kab['is_security_day'] = df_kab['יום_ביטחוני'].fillna(0).astype(int)
sec_dummies = pd.get_dummies(df_kab['תג_ביטחוני'].astype(str), prefix='sec').astype(int)
df_kab = pd.concat([df_kab, sec_dummies], axis=1)
df_kab['duration_min'] = df_kab['משך תוכנית_דק']

KAB_FEATURES = (
    ['lag_1', 'lag_2', 'ema_4', 'rolling_mean_4',
     'month', 'week_of_year', 'weeks_since_start',
     'is_security_day', 'duration_min']
    + list(sec_dummies.columns)
)

df_kab_final = df_kab.dropna(subset=['lag_2']).reset_index(drop=True)
train_kab_final = df_kab_final.iloc[:split]
test_kab_final = df_kab_final.iloc[split:]

X_tr = train_kab_final[KAB_FEATURES].fillna(0)
y_tr = train_kab_final[TARGET]
X_te = test_kab_final[KAB_FEATURES].fillna(0)
y_te = test_kab_final[TARGET].values

hgb = HistGradientBoostingRegressor(
    max_iter=200, max_depth=3, learning_rate=0.05,
    min_samples_leaf=5, l2_regularization=1.0, random_state=42,
)
hgb.fit(X_tr, y_tr)
pred_kabinet_specialist = hgb.predict(X_te)
mae_kab = mean_absolute_error(y_te, pred_kabinet_specialist)

# ---------- 2. המודל הכללי (model_saved.joblib) ----------
print('טוענת model_saved.joblib...')
obj = joblib.load('model_saved.joblib')
PIPELINE = obj['pipeline']
FEATURE_COLS = obj['feature_cols']
print(f'Model: {obj["model_name"]}')
print(f'expected_test_mae: {obj["expected_test_mae"]}')
print(f'Feature cols ({len(FEATURE_COLS)}):')
for i, c in enumerate(FEATURE_COLS):
    print(f'  {i+1}. {c}')
print()

# יוצרים את אותן features על שורות ה-test.
# הגישה: מתוך df_all הכללי, מסננים לאותם תאריכי שידור של test_kab.
# הפיצ'רים כבר מוכנים ב-xlsx (הוא הפלט של eda_script.py) — פשוט נלקח את השורות המתאימות.
test_dates = test_kab['תאריך שידור'].tolist()
mask_test_in_all = (
    df_all['שם תוכנית'].astype(str).str.contains(PROGRAM_NAME, na=False) &
    (df_all['סטטוס תוכנית'] == 'שידור חי') &
    (pd.to_datetime(df_all['תאריך שידור']).isin(test_dates))
)
test_general_rows = df_all[mask_test_in_all].copy().sort_values('תאריך שידור').reset_index(drop=True)
print(f'שורות תואמות ב-df_all: {len(test_general_rows)}')

# בודקת אילו features חסרות
missing = [c for c in FEATURE_COLS if c not in test_general_rows.columns]
print(f'Features חסרות בקובץ: {missing}')

# צריך להשלים lag features כמו ה-backend עושה (compute_lag_features).
# פשוט יותר: נקרא לפונקציה מ-prediction_logic ישירות.
sys.path.insert(0, 'backend')
from prediction_logic import compute_lag_features, date_to_weekday_he

# HISTORY: כל השורות עד לפני test — כי compute_lag_features צריך היסטוריה
# כדי לחשב lag_program_mean, lag_slot_mean וכו'.
# בדיוק כמו הפיצול הכרונולוגי: history = train_kab_final (2025-06-13 → 2026-02-06)
history_cutoff = test_kab['תאריך שידור'].min()
history_general = df_all[pd.to_datetime(df_all['תאריך שידור']) < history_cutoff].copy()
history_general['תאריך שידור'] = pd.to_datetime(history_general['תאריך שידור'])
if 'רייטינג מותאם' not in history_general.columns:
    rp = pd.to_numeric(history_general['reception_pct'], errors='coerce')
    rr = pd.to_numeric(history_general['רייטינג'], errors='coerce')
    history_general['רייטינג מותאם'] = (rr / rp).where(rp > 0)

# hour מ-שעת התחלה
history_general['שעת התחלה_שעה'] = pd.to_datetime(
    history_general['שעת התחלה'].astype(str), format='%H:%M:%S', errors='coerce'
).dt.hour.fillna(20).astype(int)
for ch in ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]:
    if ch not in history_general.columns:
        history_general[ch] = 0.0

preds_general = []
for _, row in test_general_rows.iterrows():
    target_date = pd.to_datetime(row['תאריך שידור']).date()
    # מזג'ר שעה
    hour = pd.to_datetime(str(row['שעת התחלה']), format='%H:%M:%S', errors='coerce').hour
    if pd.isna(hour):
        hour = 20
    hour = int(hour)
    is_security = int(row.get('יום_ביטחוני', 0) or 0) == 1

    feats = compute_lag_features(
        history_df=history_general,
        program_name=PROGRAM_NAME,
        target_date=target_date,
        hour=hour,
        status='שידור חי',
        is_rerun=False,
        is_holiday=False,
        is_security=is_security,
    )
    feats['משך תוכנית_דק'] = row.get('משך תוכנית_דק', 60)
    feature_row = pd.DataFrame([feats])[FEATURE_COLS]
    pred = float(PIPELINE.predict(feature_row)[0])
    pred = max(0.0, pred)
    preds_general.append(pred)

preds_general = np.array(preds_general)
mae_general = mean_absolute_error(y_te, preds_general)

# ---------- 3. השוואה ----------
print()
print('=' * 72)
print(f'{"מודל":<40} {"MAE":>8} {"R²":>8}')
print('-' * 72)
print(f'{"המודל הייעודי (kabinet only)":<40} {mae_kab:>8.3f} {r2_score(y_te, pred_kabinet_specialist):>8.3f}')
print(f'{"המודל הכללי (model_saved.joblib)":<40} {mae_general:>8.3f} {r2_score(y_te, preds_general):>8.3f}')
print('=' * 72)
print()

diff = mae_general - mae_kab
if diff > 0.02:
    winner = f'המודל הייעודי מנצח בהפרש {diff:.3f} (טוב יותר ב-{100*diff/mae_general:.1f}%)'
elif diff < -0.02:
    winner = f'המודל הכללי מנצח בהפרש {-diff:.3f} (טוב יותר ב-{100*(-diff)/mae_kab:.1f}%)'
else:
    winner = 'תיקו (הפרש קטן מ-0.02 — לא מובהק על 10 שורות)'
print(f'✅ {winner}')

# ---------- 4. פירוט פר שורה ----------
print()
print('=== תחזיות פר שידור ===')
report = pd.DataFrame({
    'תאריך': [d.date() for d in test_kab['תאריך שידור']],
    'אמת': y_te,
    'ייעודי': pred_kabinet_specialist,
    'כללי': preds_general,
    'שגיאה_ייעודי': np.abs(y_te - pred_kabinet_specialist),
    'שגיאה_כללי': np.abs(y_te - preds_general),
})
print(report.to_string(index=False))
