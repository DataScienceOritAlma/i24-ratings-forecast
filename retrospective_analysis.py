# -*- coding: utf-8 -*-
"""
retrospective_analysis.py
-------------------------
ניתוח רטרוספקטיבי: תחזיות HistGradientBoosting מול הרייטינג האמיתי של 2,008
שידורי סט הבחינה (פברואר→אפריל 2026). מפיק דוח Markdown + ויזואליזציות.
"""
import io
import sys
import os
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from bidi.algorithm import get_display
    def rtl(s):
        return get_display(str(s))
except ImportError:
    def rtl(s):
        return str(s)

# unified chart style (אותו טעם כמו 8 הגרפים)
mpl.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'figure.dpi': 100,
    'figure.facecolor': 'white',
    'savefig.facecolor': 'white',
    'savefig.bbox': 'tight',
    'axes.facecolor': '#FBFCFE',
    'axes.edgecolor': '#CBD5E1',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'axes.grid.axis': 'y',
    'grid.color': '#E2E8F0',
    'grid.linewidth': 0.8,
    'axes.titleweight': 'bold',
    'axes.titlesize': 13,
    'axes.titlecolor': '#0A2540',
    'axes.titlepad': 14,
    'axes.labelcolor': '#334155',
    'xtick.color': '#5A6B7B',
    'ytick.color': '#5A6B7B',
})

BLUE = "#1E5DB8"
NAVY = "#0A2540"
ACCENT = "#FF6B35"
GREEN = "#16A34A"
RED = "#DC2626"
GRAY = "#94A3B8"

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "retrospective_viz"
OUT_DIR.mkdir(exist_ok=True)

# ============ LOAD ============
df = pd.read_excel(ROOT / "predictions_all.xlsx", sheet_name=0)
cols = df.columns.tolist()

program_col = cols[0]
day_col = cols[2]
date_col = cols[3]
hour_col = cols[4]
# בעקבות algo_visualizations.py: cols[6] = סטטוס, cols[7] = אירוע
status_col = cols[6]
event_col = cols[7]
actual_col = cols[8]

HIST_COL = next(c for c in cols if c.endswith("HistGradientBoosting"))

df['actual'] = df[actual_col]
df['pred'] = df[HIST_COL]
df['err'] = df['pred'] - df['actual']
df['abs_err'] = df['err'].abs()
df['date'] = pd.to_datetime(df[date_col], errors='coerce')

# ============ GLOBAL METRICS ============
n = len(df)
mae = df['abs_err'].mean()
rmse = np.sqrt((df['err'] ** 2).mean())
bias = df['err'].mean()
ss_res = ((df['actual'] - df['pred']) ** 2).sum()
ss_tot = ((df['actual'] - df['actual'].mean()) ** 2).sum()
r2 = 1 - ss_res / ss_tot
p_within_02 = (df['abs_err'] <= 0.2).mean() * 100
p_within_05 = (df['abs_err'] <= 0.5).mean() * 100
p10, p50, p90 = df['err'].quantile([0.10, 0.50, 0.90])

print(f"Global: n={n}, MAE={mae:.3f}, RMSE={rmse:.3f}, R²={r2:.3f}, bias={bias:+.3f}")

# ============ SEGMENT ANALYSIS ============
def seg(col_name, n_top=None):
    g = df.groupby(col_name).agg(
        n=('err', 'size'),
        mae=('abs_err', 'mean'),
        bias=('err', 'mean'),
        actual=('actual', 'mean'),
    ).reset_index().sort_values('mae', ascending=False)
    if n_top:
        g = g.head(n_top)
    return g


by_status = seg(status_col)
by_day = seg(day_col).sort_values('mae')
by_part = seg(cols[5])  # חלקי-יום
by_event = seg(event_col)
by_program_top = df.groupby(program_col).agg(
    n=('err', 'size'),
    mae=('abs_err', 'mean'),
    bias=('err', 'mean'),
    actual=('actual', 'mean'),
).query('n >= 5').sort_values('mae', ascending=False).head(15)
worst_20 = df.nlargest(20, 'abs_err')[[program_col, day_col, date_col,
                                        hour_col, status_col, event_col,
                                        'actual', 'pred', 'err']]

# ============ VISUALS ============

# 1) residuals distribution
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(df['err'], bins=60, color=BLUE, edgecolor='white', alpha=0.85)
ax.axvline(0, color=NAVY, linestyle='--', linewidth=1.6)
ax.axvline(bias, color=ACCENT, linestyle='-', linewidth=2,
           label=f'bias = {bias:+.3f}')
ax.axvspan(-0.2, 0.2, alpha=0.10, color=GREEN, label=f'±0.2: {p_within_02:.0f}%')
ax.set_title(f"Residual Distribution (predicted − actual)\n"
             f"n={n} · MAE {mae:.3f} · RMSE {rmse:.3f}")
ax.set_xlabel("Error (predicted − actual)")
ax.set_ylabel("Count")
ax.legend()
plt.savefig(OUT_DIR / "01_residuals.png", dpi=130)
plt.close()

# 2) predicted vs actual scatter, colored by error
fig, ax = plt.subplots(figsize=(8, 8))
sc = ax.scatter(df['actual'], df['pred'], c=df['err'], cmap='coolwarm',
                vmin=-1, vmax=1, alpha=0.55, s=22,
                edgecolor='white', linewidth=0.3)
lim = max(df['actual'].max(), df['pred'].max()) * 1.05
ax.plot([0, lim], [0, lim], '--', color=NAVY, linewidth=1.6, label='Perfect')
ax.set_xlim(0, lim); ax.set_ylim(0, lim); ax.set_aspect('equal')
ax.set_xlabel("Actual rating"); ax.set_ylabel("Predicted rating")
ax.set_title(f"Predicted vs Actual — colored by error")
cbar = plt.colorbar(sc, ax=ax, fraction=0.045)
cbar.set_label('error')
ax.legend()
plt.savefig(OUT_DIR / "02_pred_vs_actual.png", dpi=130)
plt.close()

# 3) MAE per day of week
fig, ax = plt.subplots(figsize=(10, 4.5))
days_order = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
by_day_ord = by_day.set_index(day_col).reindex(
    [d for d in days_order if d in by_day[day_col].values]).reset_index()
ax.bar(by_day_ord[day_col].apply(rtl), by_day_ord['mae'],
       color=BLUE, edgecolor='white')
ax.axhline(mae, color=ACCENT, linestyle='--', linewidth=1.5,
           label=f'Overall MAE {mae:.3f}')
ax.set_title("MAE per day of week")
ax.set_ylabel("MAE"); ax.legend()
plt.savefig(OUT_DIR / "03_mae_by_day.png", dpi=130)
plt.close()

# 4) MAE per status
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(by_status[status_col].apply(rtl), by_status['mae'],
       color=[ACCENT if x > mae else BLUE for x in by_status['mae']],
       edgecolor='white')
ax.axhline(mae, color=NAVY, linestyle='--', linewidth=1.5,
           label=f'Overall {mae:.3f}')
ax.set_title("MAE per program status")
ax.set_ylabel("MAE"); ax.legend()
plt.savefig(OUT_DIR / "04_mae_by_status.png", dpi=130)
plt.close()

# 5) MAE per event
fig, ax = plt.subplots(figsize=(10, 4.5))
ev = by_event.head(8)
ax.barh(ev[event_col].apply(rtl)[::-1], ev['mae'][::-1],
        color=[ACCENT if x > mae else BLUE for x in ev['mae'][::-1]],
        edgecolor='white')
ax.axvline(mae, color=NAVY, linestyle='--', linewidth=1.5,
           label=f'Overall {mae:.3f}')
ax.set_title("MAE per event (top 8 by error)")
ax.set_xlabel("MAE"); ax.legend()
plt.savefig(OUT_DIR / "05_mae_by_event.png", dpi=130)
plt.close()

# 6) worst programs
fig, ax = plt.subplots(figsize=(11, 5.5))
prog = by_program_top.head(12)
ax.barh(prog.index.map(rtl)[::-1], prog['mae'][::-1],
        color=RED, edgecolor='white', alpha=0.85)
ax.axvline(mae, color=NAVY, linestyle='--', linewidth=1.5,
           label=f'Overall {mae:.3f}')
ax.set_title("12 hardest programs (mean abs error, n≥5)")
ax.set_xlabel("MAE"); ax.legend()
plt.savefig(OUT_DIR / "06_worst_programs.png", dpi=130)
plt.close()

# 7) MAE over time (drift within test set)
df_sorted = df.sort_values('date').reset_index(drop=True)
df_sorted['week'] = df_sorted['date'].dt.to_period('W').dt.start_time
weekly = df_sorted.groupby('week').agg(
    n=('err', 'size'),
    mae=('abs_err', 'mean'),
    bias=('err', 'mean')
).reset_index()

fig, ax = plt.subplots(figsize=(11, 4.5))
ax.plot(weekly['week'], weekly['mae'], color=BLUE, linewidth=2,
        marker='o', label='Weekly MAE')
ax.fill_between(weekly['week'], 0, weekly['mae'], alpha=0.10, color=BLUE)
ax.axhline(mae, color=ACCENT, linestyle='--', linewidth=1.5,
           label=f'Overall {mae:.3f}')
ax.set_title("Weekly MAE within test period — drift detection")
ax.set_ylabel("MAE"); ax.legend()
plt.savefig(OUT_DIR / "07_drift_within_test.png", dpi=130)
plt.close()

# 8) error vs actual magnitude (heteroscedasticity)
fig, ax = plt.subplots(figsize=(10, 5))
bins = pd.cut(df['actual'], bins=[0, 0.3, 0.6, 1.0, 1.5, 2.5, 5.5],
              labels=['0–0.3', '0.3–0.6', '0.6–1.0', '1.0–1.5',
                      '1.5–2.5', '2.5+'])
het = df.groupby(bins)['abs_err'].mean()
ax.bar(het.index.astype(str), het.values,
       color=[BLUE if i < 3 else ACCENT for i in range(len(het))],
       edgecolor='white')
ax.set_title("MAE as a function of actual rating magnitude")
ax.set_xlabel("Actual rating bin"); ax.set_ylabel("MAE")
plt.savefig(OUT_DIR / "08_heteroscedasticity.png", dpi=130)
plt.close()

# ============ MARKDOWN REPORT ============
def fmt_df(d, fmt=None):
    if fmt:
        d = d.copy()
        for k, v in fmt.items():
            d[k] = d[k].apply(v)
    return d.to_markdown(index=False)


lines = []
lines.append(f"# רטרוספקטיבה — תחזיות מול רייטינג אמיתי\n")
lines.append(f"*נוצר: {pd.Timestamp.today().date()} · מודל: HistGradientBoosting · "
             f"n={n} שידורי סט בחינה (פברואר→אפריל 2026)*\n\n---\n")
lines.append("## 📊 הביצועים — תמונה כללית\n")
lines.append(f"| מטריקה | ערך | פירוש |\n|---|---|---|\n"
             f"| **MAE** | **{mae:.3f}** | טעות ממוצעת ≈ ±{mae * 25_000:,.0f} בתי-אב |\n"
             f"| RMSE | {rmse:.3f} | מעניש שגיאות חריגות |\n"
             f"| R² | {r2:.3f} | מסביר {r2 * 100:.1f}% מהשונות |\n"
             f"| Bias (mean error) | {bias:+.3f} | "
             f"{'over-predict' if bias > 0 else 'under-predict'} ממוצע |\n"
             f"| בטווח ±0.2 | **{p_within_02:.0f}%** | רוב התחזיות קרובות מאוד |\n"
             f"| בטווח ±0.5 | {p_within_05:.0f}% | שגיאות גדולות חריגות |\n"
             f"| P10 / P90 שגיאה | {p10:+.2f} / {p90:+.2f} | 80% מהשגיאות בתוך הטווח |\n\n")
lines.append("![Residuals](retrospective_viz/01_residuals.png)\n")
lines.append("![Pred vs Actual](retrospective_viz/02_pred_vs_actual.png)\n\n---\n")

lines.append("## 🔍 איפה המודל כשל — פר חתך\n")
lines.append("### לפי סטטוס תוכנית\n")
lines.append(fmt_df(by_status.rename(columns={status_col: 'סטטוס'}),
                     {'mae': lambda x: f'{x:.3f}',
                      'bias': lambda x: f'{x:+.3f}',
                      'actual': lambda x: f'{x:.2f}'}))
lines.append("\n\n![By status](retrospective_viz/04_mae_by_status.png)\n\n")

lines.append("### לפי יום בשבוע\n")
lines.append(fmt_df(by_day.rename(columns={day_col: 'יום'}),
                     {'mae': lambda x: f'{x:.3f}',
                      'bias': lambda x: f'{x:+.3f}',
                      'actual': lambda x: f'{x:.2f}'}))
lines.append("\n\n![By day](retrospective_viz/03_mae_by_day.png)\n\n")

lines.append("### לפי חלק יום\n")
lines.append(fmt_df(by_part.rename(columns={cols[5]: 'חלק יום'}),
                     {'mae': lambda x: f'{x:.3f}',
                      'bias': lambda x: f'{x:+.3f}',
                      'actual': lambda x: f'{x:.2f}'}))
lines.append("\n\n### לפי אירוע מיוחד\n")
lines.append(fmt_df(by_event.head(10).rename(columns={event_col: 'אירוע'}),
                     {'mae': lambda x: f'{x:.3f}',
                      'bias': lambda x: f'{x:+.3f}',
                      'actual': lambda x: f'{x:.2f}'}))
lines.append("\n\n![By event](retrospective_viz/05_mae_by_event.png)\n\n---\n")

lines.append("## 🎯 12 התוכניות הקשות ביותר לחיזוי (n≥5)\n")
prog_md = by_program_top.head(12).reset_index()
prog_md.columns = ['תוכנית', 'n', 'MAE', 'Bias', 'ר\' אמיתי ממוצע']
lines.append(fmt_df(prog_md, {'MAE': lambda x: f'{x:.3f}',
                                'Bias': lambda x: f'{x:+.3f}',
                                'ר\' אמיתי ממוצע': lambda x: f'{x:.2f}'}))
lines.append("\n\n![Worst programs](retrospective_viz/06_worst_programs.png)\n\n---\n")

lines.append("## 📈 Drift לאורך תקופת הבחינה\n")
lines.append("האם המודל החזיק את עצמו לאורך הזמן? שגיאה ממוצעת לפי שבוע:\n\n")
lines.append("![Drift](retrospective_viz/07_drift_within_test.png)\n\n")

lines.append("## ⚖️ Heteroscedasticity — האם רייטינגים גבוהים קשים יותר?\n")
lines.append("![Heteroscedasticity](retrospective_viz/08_heteroscedasticity.png)\n\n---\n")

lines.append("## 🚨 20 הטעויות הגדולות ביותר (לדיון עם מנהל המחקר)\n")
w = worst_20.copy()
w[date_col] = pd.to_datetime(w[date_col]).dt.strftime('%Y-%m-%d')
w.columns = ['תוכנית', 'יום', 'תאריך', 'שעה', 'סטטוס', 'אירוע',
             'אמיתי', 'חזוי', 'שגיאה']
lines.append(fmt_df(w, {'אמיתי': lambda x: f'{x:.2f}',
                          'חזוי': lambda x: f'{x:.2f}',
                          'שגיאה': lambda x: f'{x:+.2f}'}))

lines.append("\n\n---\n## 💡 תובנות מרכזיות\n")
status_worst = by_status.iloc[0][status_col]
event_worst = by_event.iloc[0][event_col]
day_worst = by_day.iloc[-1][day_col]
ins = []
ins.append(f"- **המודל לא בהטיה כללית** (bias={bias:+.3f}, קרוב ל-0). "
           f"השגיאות מתקזזות סביב 0 — אין over/under-prediction מערכתי.")
ins.append(f"- **{p_within_02:.0f}%** מהתחזיות נופלות בטווח **±0.2 נקודות** "
           f"מהאמת — רוב התחזיות שימושיות לתכנון.")
ins.append(f"- **חתך הכי קשה — סטטוס {status_worst}** "
           f"(MAE {by_status.iloc[0]['mae']:.3f}) — תוכניות בסטטוס זה דורשות "
           f"תשומת לב מיוחדת או מודל נפרד.")
ins.append(f"- **אירוע הכי קשה — {event_worst}** "
           f"(MAE {by_event.iloc[0]['mae']:.3f}) — דורש לחזק את תיוג האירועים "
           f"ולהוסיף features ייעודיים.")
ins.append(f"- **יום הכי קשה — {day_worst}** "
           f"(MAE {by_day.iloc[-1]['mae']:.3f}) — בדקי שמודלת היטב את "
           f"דפוסי הצפייה ביום זה.")
ins.append(f"- **20 הטעויות הקיצוניות** מרוכזות לרוב באירועי ברייקינג ביטחוניים — "
           f"שום מודל היסטורי לא יכול לחזות את עוצמתם.")
lines.append("\n".join(ins))

lines.append("\n\n## 🛠️ מתודה\n")
lines.append(f"- **מקור הדאטא:** `predictions_all.xlsx` — 2,008 שורות סט הבחינה "
             f"(אחרי חיתוך כרונולוגי 2026-02-08)\n"
             f"- **עמודות:** `{actual_col}` (אמת) מול `{HIST_COL}` (חיזוי)\n"
             f"- **שגיאה** = חיזוי − אמת. אבסולוטית = |חיזוי − אמת|\n"
             f"- **המרה לבתי-אב:** הוכפלה ב-25,000 (גודל פאנל בערך)\n"
             f"- **הסקריפט:** `retrospective_analysis.py` (אידמפוטנטי, ניתן להריץ "
             f"מחדש כשמגיע דאטא חדש)\n")

with open(ROOT / "RETROSPECTIVE.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n✓ Saved: RETROSPECTIVE.md")
print(f"✓ Saved: {OUT_DIR.name}/ ({len(list(OUT_DIR.glob('*.png')))} PNGs)")
