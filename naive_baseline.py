# -*- coding: utf-8 -*-
"""i24 ratings — מודל בסיסי נאיבי + פיצול כרונולוגי.

המטרה: לבסס קו-בסיס אבסולוטי (absolute floor). כל מודל מתוחכם חייב לנצח
את ה-naive הזה — אחרת אין הצדקה לסיבוכיות.

מתודולוגיה:
  1. טוענים את `תוכניות_מעובד.xlsx` (10,039 שורות).
  2. ממיינים לפי תאריך עולה ועושים פיצול כרונולוגי 80/20.
  3. מאמנים מודל נאיבי: y_pred = ממוצע הרייטינג ב-train (קבוע!).
  4. מודדים MAE, RMSE, R² על ה-test.
  5. כותבים דוח Markdown.

פלט:
  - NAIVE_REPORT.md
"""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_XLSX = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")
OUT_MD = os.path.join(DATA_DIR, "NAIVE_REPORT.md")

TARGET = "רייטינג"
TEST_FRAC = 0.20  # 80/20


def main() -> None:
    # 1. Load
    print("Loading data...")
    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    n = len(df)
    print(f"  Loaded {n:,} rows")

    # 2. Chronological split
    print("Chronological split (80/20)...")
    df = df.sort_values("תאריך שידור").reset_index(drop=True)
    cutoff_idx = int(n * (1 - TEST_FRAC))
    cutoff_date = df.iloc[cutoff_idx]["תאריך שידור"]
    train = df.iloc[:cutoff_idx].copy()
    test = df.iloc[cutoff_idx:].copy()
    print(f"  Cutoff date: {cutoff_date.date()}")
    print(f"  Train: {len(train):,} rows  ({train['תאריך שידור'].min().date()} - {train['תאריך שידור'].max().date()})")
    print(f"  Test:  {len(test):,} rows  ({test['תאריך שידור'].min().date()} - {test['תאריך שידור'].max().date()})")

    # 3. Train naive model — global mean of train
    print("Training naive model (global mean of train)...")
    train_mean = train[TARGET].mean()
    print(f"  Predicted constant: {train_mean:.4f}")

    # 4. Predict & evaluate
    y_true = test[TARGET].values
    y_pred = np.full_like(y_true, train_mean, dtype=float)

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    print(f"\nMetrics on test:")
    print(f"  MAE  = {mae:.4f}")
    print(f"  RMSE = {rmse:.4f}")
    print(f"  R^2  = {r2:.4f}")

    # 5. Sanity comparators
    zero_mae = float(np.mean(np.abs(y_true)))                       # predict 0
    test_mean = float(y_true.mean())
    test_mean_mae = float(np.mean(np.abs(y_true - test_mean)))      # oracle: predict test mean

    # 6. Write report
    print(f"\nWriting {OUT_MD}...")
    lines = []
    lines.append(f"# מודל נאיבי + פיצול כרונולוגי\n")
    lines.append(f"*נוצר ב-{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append(f"## 1. הגדרת הבעיה\n")
    lines.append(f"- **משתנה מטרה (Y):** `{TARGET}`")
    lines.append(f"- **רשומות סה\"כ:** {n:,}")
    lines.append(f"- **חלוקה:** כרונולוגית 80/20 (לא random!) — חיוני לסדרות זמן.\n")

    lines.append(f"## 2. הפיצול\n")
    lines.append(f"| | n | תאריך התחלה | תאריך סיום |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| Train | {len(train):,} | {train['תאריך שידור'].min().date()} | {train['תאריך שידור'].max().date()} |")
    lines.append(f"| Test  | {len(test):,} | {test['תאריך שידור'].min().date()} | {test['תאריך שידור'].max().date()} |")
    lines.append(f"\n**תאריך חיתוך:** {cutoff_date.date()}\n")
    lines.append(f"**למה כרונולוגית?** ב-time series אסור לאמן על העתיד ולחזות את העבר. "
                 f"random split היה יוצר ‘leakage’ — המודל ‘רואה’ דוגמאות מ-2026-04 בזמן האימון, "
                 f"ואז מאמת על 2025-09. זה אופטימיות שווא.\n")

    lines.append(f"## 3. מודל נאיבי\n")
    lines.append(f"**הגדרה:** התחזית לכל שורה ב-test היא **קבועה** = ממוצע ה-{TARGET} ב-train.\n")
    lines.append(f"```python")
    lines.append(f"y_pred[i] = mean(y_train)  # כל i")
    lines.append(f"```\n")
    lines.append(f"**הקבוע שנלמד:** {train_mean:.4f}\n")
    lines.append(f"זה הוא ה-floor האבסולוטי. כל מודל שלא מנצח אותו — לא שווה את המאמץ.\n")

    lines.append(f"## 4. תוצאות\n")
    lines.append(f"| מטריקה | ערך |")
    lines.append(f"|---|---|")
    lines.append(f"| MAE  | **{mae:.4f}** |")
    lines.append(f"| RMSE | **{rmse:.4f}** |")
    lines.append(f"| R²   | **{r2:.4f}** |")
    lines.append(f"\n### פירוש המספרים\n")
    lines.append(f"- **MAE = {mae:.3f}** — המודל טועה בממוצע ב-±{mae:.3f} רייטינג. "
                 f"נזכור שטווח הרייטינג בנתונים הוא 0 עד {y_true.max():.2f}.")
    if r2 < 0:
        lines.append(f"- **R² = {r2:.3f} (שלילי!)** — המודל **גרוע מ-baseline פנימי** (ממוצע test). "
                     f"זה אומר שיש שינוי דרמטי בהתפלגות בין train ל-test (drift). "
                     f"כנראה שתקופת test כוללת אירועים יוצאי-דופן שהעלו את הרייטינג.")
    else:
        lines.append(f"- **R² = {r2:.3f}** — המודל מסביר {r2*100:.1f}% מהשונות בtest. "
                     f"R² חיובי מציין שהוא טוב יותר מהבייסליין הפנימי (ממוצע test).")
    lines.append("")

    lines.append(f"## 5. השוואות שפיות (Sanity)\n")
    lines.append(f"| תחזית | MAE |")
    lines.append(f"|---|---|")
    lines.append(f"| **המודל הנאיבי שלנו** (ממוצע train = {train_mean:.3f}) | **{mae:.4f}** |")
    lines.append(f"| חיזוי 0 קבוע | {zero_mae:.4f} |")
    lines.append(f"| Oracle: ממוצע test = {test_mean:.3f} (אסור בפועל!) | {test_mean_mae:.4f} |")
    lines.append("")
    lines.append(f"**הפער בין הנאיבי שלנו ל-oracle** ({mae - test_mean_mae:.4f}) "
                 f"מציין כמה ‘drift’ יש בין train ל-test — אם הפער גדול, "
                 f"זה אומר שההתפלגות השתנתה ולא רק שצריך מודל יותר חכם.\n")

    lines.append(f"## 6. השוואה למודלים מתקדמים\n")
    lines.append(f"| מודל | MAE | יחס לנאיבי |")
    lines.append(f"|---|---|---|")
    lines.append(f"| 🐌 הנאיבי הזה | {mae:.4f} | 1.00× |")
    lines.append(f"| Baseline (ממוצע-רצועה, V1) | 0.305 | {0.305 / mae:.2f}× |")
    lines.append(f"| RandomForest default (V1) | 0.280 | {0.280 / mae:.2f}× |")
    lines.append(f"| 🏆 RandomForest tuned (V2) | 0.270 | {0.270 / mae:.2f}× |")
    lines.append("")
    if mae > 0.30:
        improvement = (mae - 0.270) / mae * 100
        lines.append(f"**מסקנה:** המודל המתקדם משפר את ה-MAE ב-**{improvement:.1f}%** מעל הנאיבי. "
                     f"זה שיפור משמעותי שמצדיק את הסיבוכיות — תחזית מדויקת יותר ב-±{mae - 0.270:.3f} רייטינג בממוצע.\n")

    lines.append(f"## 7. הערות מתודולוגיות\n")
    lines.append(f"- **למה מודל נאיבי בכלל?** הוא ה-‘null hypothesis’ של הפרויקט. "
                 f"כל מודל מתקדם חייב להציע **שיפור משמעותי** מעליו — אחרת, יותר טוב לחזות "
                 f"ממוצע ולחסוך זמן.")
    lines.append(f"- **הקפדה על פיצול כרונולוגי** היא נושא קריטי. random split על time series "
                 f"מנפח את התוצאות ב-30-50% ויוצר תחושה שהמודל טוב בהרבה ממה שהוא באמת.")
    lines.append(f"- **הקבוע שנלמד ({train_mean:.3f}) הוא ממוצע ה-train בלבד** — train mean ≠ test mean. "
                 f"אם יש מגמת זמן (וב-i24 יש — קליטה גדלה), הקבוע יהיה מוטה כלפי מטה ב-test.")
    lines.append(f"- **R² שלילי או גבולי** הוא דגל אדום למשמרת בהתפלגות. במקרה שלנו, אירועי 2026-Q1 "
                 f"(שאגת הארי, מתקפה איראנית) שינו את ההתפלגות לעומת תקופת ה-train (2025).")
    lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nDone. Wrote:")
    print(f"  {OUT_MD}  ({os.path.getsize(OUT_MD):,} bytes)")
    print(f"\n=== Summary ===")
    print(f"  Train mean (the prediction): {train_mean:.4f}")
    print(f"  Test MAE:  {mae:.4f}")
    print(f"  Test RMSE: {rmse:.4f}")
    print(f"  Test R^2:  {r2:.4f}")


if __name__ == "__main__":
    main()
