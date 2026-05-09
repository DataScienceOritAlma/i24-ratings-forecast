# -*- coding: utf-8 -*-
"""i24 ratings — forecast model trainer.

Setting: predict `רייטינג` BEFORE the show airs.
- No post-airing features (no נתח / צופים / competitor ratings in those minutes).
- Time-based train/test split (last ~20% of dates as test).
- Compares 4 models: Baseline (slot-mean), Linear, RandomForest, XGBoost.
- Engineers lag features without leakage (cumulative-history at row time).

Outputs:
  - MODEL_REPORT.md     — full markdown report
  - predictions.xlsx    — actual vs predicted on the test set
"""
from __future__ import annotations

import os
from io import StringIO
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBRegressor
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_XLSX = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")
OUT_MD = os.path.join(DATA_DIR, "MODEL_REPORT.md")
OUT_PRED_XLSX = os.path.join(DATA_DIR, "predictions.xlsx")

TARGET = "רייטינג"
TEST_FRAC = 0.20  # last 20% of dates


# ---------- Feature engineering -----------------------------------------------
def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute leakage-free lag features:
    - lag_program_mean: cumulative historical mean rating of this program (excluding the current row)
    - lag_program_n: how many prior airings of this program exist
    - lag_slot_mean: cumulative mean rating in this (weekday × hour) slot
    - lag_slot_n: how many prior airings in this slot
    All "history" is strictly past the current row's airtime."""
    df = df.sort_values(["תאריך שידור", "שעת התחלה"]).reset_index(drop=True)

    # row-level airtime stamp for ordering
    start_h = pd.to_timedelta(df["שעת התחלה"].astype(str), errors="coerce")
    df["_ts"] = pd.to_datetime(df["תאריך שידור"]) + start_h

    # Cumulative mean & count by program (excluding current row).
    g_prog = df.groupby("שם תוכנית_מקור")[TARGET]
    df["lag_program_n"] = g_prog.cumcount()  # n prior airings before this row
    df["lag_program_mean"] = (
        g_prog.cumsum() - df[TARGET]
    ) / df["lag_program_n"].replace(0, np.nan)

    # By (weekday × hour) slot
    df["_slot"] = df["יום שידור"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    g_slot = df.groupby("_slot")[TARGET]
    df["lag_slot_n"] = g_slot.cumcount()
    df["lag_slot_mean"] = (
        g_slot.cumsum() - df[TARGET]
    ) / df["lag_slot_n"].replace(0, np.nan)

    # Same for status (live / rerun / etc.)
    df["_status_slot"] = df["סטטוס תוכנית"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    g_st = df.groupby("_status_slot")[TARGET]
    df["lag_status_slot_n"] = g_st.cumcount()
    df["lag_status_slot_mean"] = (
        g_st.cumsum() - df[TARGET]
    ) / df["lag_status_slot_n"].replace(0, np.nan)

    # Date-derived features
    d = pd.to_datetime(df["תאריך שידור"])
    df["חודש"] = d.dt.month
    df["יום_בחודש"] = d.dt.day
    df["שבוע_בשנה"] = d.dt.isocalendar().week.astype(int)

    df = df.drop(columns=["_slot", "_status_slot", "_ts"])
    return df


# ---------- Modeling ----------------------------------------------------------
PRE_AIRING_FEATURES_NUM = [
    "שעת התחלה_שעה",
    "משך תוכנית_דק",
    "reception_pct",
    "חודש",
    "יום_בחודש",
    "שבוע_בשנה",
    "lag_program_mean",
    "lag_program_n",
    "lag_slot_mean",
    "lag_slot_n",
    "lag_status_slot_mean",
    "lag_status_slot_n",
]

PRE_AIRING_FEATURES_BOOL = [
    "is_rerun",
    "יום_חג",
    "יום_ביטחוני",
    "שבת",
]

PRE_AIRING_FEATURES_CAT = [
    "יום שידור",
    "חלקי-יום",
    "סטטוס תוכנית",
    "תג_עונה",
    "תג_חג",
    "תג_ביטחוני",
]

LEAKAGE_FEATURES = [
    "נתח", "צופים 4+", "חשיפה 4+", "משך צפייה",
    "כאן 11", "קשת 12", "רשת 13", "עכשיו 14",
    "ממוצע מתחרים", "יתרון מול מתחרים", "HUT proxy",
    "רייטינג מותאם",  # derived from target
]


def time_split(df: pd.DataFrame, test_frac: float = TEST_FRAC):
    df = df.sort_values("תאריך שידור").reset_index(drop=True)
    cut = df["תאריך שידור"].quantile(1 - test_frac, interpolation="nearest")
    train = df[df["תאריך שידור"] < cut].copy()
    test = df[df["תאריך שידור"] >= cut].copy()
    return train, test, cut


def build_preprocessor():
    num_pipe = Pipeline([("imp", _SimpleMedianImputer()), ("scale", StandardScaler())])
    bool_pipe = Pipeline([("imp", _SimpleConstantImputer(0))])
    cat_pipe = Pipeline([
        ("imp", _SimpleConstantImputer("—")),
        ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", num_pipe, PRE_AIRING_FEATURES_NUM),
        ("bool", bool_pipe, PRE_AIRING_FEATURES_BOOL),
        ("cat", cat_pipe, PRE_AIRING_FEATURES_CAT),
    ])


# minimal imputers to avoid sklearn version issues
from sklearn.base import BaseEstimator, TransformerMixin


class _SimpleMedianImputer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        X = pd.DataFrame(X).apply(pd.to_numeric, errors="coerce")
        self.medians_ = X.median()
        return self

    def transform(self, X):
        X = pd.DataFrame(X).apply(pd.to_numeric, errors="coerce")
        return X.fillna(self.medians_).values


class _SimpleConstantImputer(BaseEstimator, TransformerMixin):
    def __init__(self, fill):
        self.fill = fill

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = pd.DataFrame(X)
        return X.fillna(self.fill).values


# ---------- Models ------------------------------------------------------------
def baseline_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Predict the mean rating in the (weekday × hour × is_rerun) cell, falling
    back to weekday × hour, then global mean."""
    g3 = train.groupby(["יום שידור", "שעת התחלה_שעה", "is_rerun"])[TARGET].mean()
    g2 = train.groupby(["יום שידור", "שעת התחלה_שעה"])[TARGET].mean()
    g_global = train[TARGET].mean()

    out = []
    for _, r in test.iterrows():
        k3 = (r["יום שידור"], r["שעת התחלה_שעה"], r["is_rerun"])
        if k3 in g3.index:
            out.append(g3.loc[k3]); continue
        k2 = (r["יום שידור"], r["שעת התחלה_שעה"])
        if k2 in g2.index:
            out.append(g2.loc[k2]); continue
        out.append(g_global)
    return np.array(out)


def fit_and_predict(model, train, test):
    pre = build_preprocessor()
    pipe = Pipeline([("pre", pre), ("model", model)])
    cols = PRE_AIRING_FEATURES_NUM + PRE_AIRING_FEATURES_BOOL + PRE_AIRING_FEATURES_CAT
    Xtr, ytr = train[cols], train[TARGET].values
    Xte = test[cols]
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    return pred, pipe


def metrics(y_true, y_pred):
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R²": float(r2_score(y_true, y_pred)),
    }


def feature_importance_from_pipe(pipe, top_n: int = 15):
    """Extract feature importance for tree models, or |coef| for linear."""
    pre = pipe.named_steps["pre"]
    model = pipe.named_steps["model"]
    feat_names = []
    for name, trans, cols in pre.transformers_:
        if name == "cat":
            oh = trans.named_steps["oh"]
            feat_names.extend(oh.get_feature_names_out(cols))
        else:
            feat_names.extend(cols)
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    elif hasattr(model, "coef_"):
        imp = np.abs(model.coef_)
    else:
        return None
    s = pd.Series(imp, index=feat_names).sort_values(ascending=False).head(top_n)
    return s


# ---------- Reporting ---------------------------------------------------------
def md_table(df: pd.DataFrame, index: bool = True) -> str:
    if index:
        df = df.copy()
        df.insert(0, df.index.name or "", df.index)
    cols = [str(c) for c in df.columns]
    out = "| " + " | ".join(cols) + " |\n"
    out += "|" + "|".join(["---"] * len(cols)) + "|\n"
    for _, r in df.iterrows():
        out += "| " + " | ".join(str(v) for v in r.values) + " |\n"
    return out


def per_segment_metrics(test: pd.DataFrame, y_pred: np.ndarray, by: str) -> pd.DataFrame:
    df = test.copy()
    df["_pred"] = y_pred
    df["_abs_err"] = (df[TARGET] - df["_pred"]).abs()
    g = df.groupby(by, dropna=False)
    res = pd.DataFrame({
        "n": g.size(),
        "MAE": g["_abs_err"].mean().round(3),
        "ר' ממוצע אמיתי": g[TARGET].mean().round(3),
        "ר' ממוצע חזוי": g["_pred"].mean().round(3),
    })
    return res


def main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("Loading data...")
    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    n_total = len(df)

    print("Engineering lag features...")
    df = add_lag_features(df)

    # Drop the very early rows where lag features are all NaN
    n_pre = len(df)
    df = df.dropna(subset=["lag_program_mean", "lag_slot_mean"]).reset_index(drop=True)
    print(f"  Dropped {n_pre - len(df)} early rows lacking lag history")

    print("Time-based split...")
    train, test, cut = time_split(df, TEST_FRAC)
    print(f"  Cutoff date: {cut.date()}")
    print(f"  Train: {len(train):,} rows ({train['תאריך שידור'].min().date()} ->{train['תאריך שידור'].max().date()})")
    print(f"  Test:  {len(test):,} rows ({test['תאריך שידור'].min().date()} ->{test['תאריך שידור'].max().date()})")

    results = {}
    pipes = {}
    preds = {}

    # 1) Baseline
    print("\nBaseline (slot mean)...")
    p_base = baseline_predict(train, test)
    results["Baseline (ממוצע-רצועה)"] = metrics(test[TARGET].values, p_base)
    preds["Baseline"] = p_base

    # 2) Ridge linear
    print("Ridge regression...")
    p_lr, pipe_lr = fit_and_predict(Ridge(alpha=1.0, random_state=42), train, test)
    results["Ridge"] = metrics(test[TARGET].values, p_lr)
    pipes["Ridge"] = pipe_lr; preds["Ridge"] = p_lr

    # 3) Random Forest
    print("RandomForest...")
    p_rf, pipe_rf = fit_and_predict(
        RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                              n_jobs=-1, random_state=42),
        train, test
    )
    results["RandomForest"] = metrics(test[TARGET].values, p_rf)
    pipes["RandomForest"] = pipe_rf; preds["RandomForest"] = p_rf

    # 4) XGBoost
    if HAVE_XGB:
        print("XGBoost...")
        p_xgb, pipe_xgb = fit_and_predict(
            XGBRegressor(n_estimators=600, max_depth=6, learning_rate=0.05,
                         subsample=0.85, colsample_bytree=0.8, random_state=42,
                         tree_method="hist", n_jobs=-1),
            train, test
        )
        results["XGBoost"] = metrics(test[TARGET].values, p_xgb)
        pipes["XGBoost"] = pipe_xgb; preds["XGBoost"] = p_xgb

    # ---------- Build report ----------
    out = StringIO()
    out.write(f"# מודל חיזוי רייטינג — דוח\n\n")
    out.write(f"*נוצר ב-{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")

    out.write("## 1. הגדרת הבעיה\n\n")
    out.write(f"- **משתנה מטרה (Y):** `{TARGET}` (גולמי — אחוז צפייה מכלל בעלי המקלטים)\n")
    out.write("- **Setting:** Forecast — תחזית לפני שידור. **לא** משתמשים בעמודות שנמדדות אחרי השידור.\n")
    out.write(f"- **רשומות סה\"כ:** {n_total:,}\n")
    out.write(f"- **לאחר סינון שורות-מוקדמות (חסרי היסטוריה):** {len(df):,}\n")
    out.write(f"- **חלוקה זמנית:** Train עד {cut.date()} → Test ממנו ועד 2026-04-18\n")
    out.write(f"  - Train: {len(train):,}  |  Test: {len(test):,}\n\n")

    out.write("### Features שהוזנו למודל\n\n")
    out.write("**מספריים (12):** " + ", ".join(f"`{c}`" for c in PRE_AIRING_FEATURES_NUM) + "\n\n")
    out.write("**בוליאניים (4):** " + ", ".join(f"`{c}`" for c in PRE_AIRING_FEATURES_BOOL) + "\n\n")
    out.write("**קטגוריאליים (6, One-Hot):** " + ", ".join(f"`{c}`" for c in PRE_AIRING_FEATURES_CAT) + "\n\n")
    out.write("**שהוצאו מסיבת leakage (לא בשימוש):** " + ", ".join(f"`{c}`" for c in LEAKAGE_FEATURES) + "\n\n")

    out.write("### Lag features (הונדסו ללא leakage)\n\n")
    out.write("- `lag_program_mean` — ממוצע רייטינג של אותה תוכנית-מקור בכל השידורים שלה **לפני** השורה הנוכחית.\n")
    out.write("- `lag_program_n` — מספר שידורים קודמים של אותה תוכנית.\n")
    out.write("- `lag_slot_mean` — ממוצע רייטינג ברצועה (יום × שעה) **לפני** השורה.\n")
    out.write("- `lag_slot_n` — מספר שידורים קודמים ברצועה.\n")
    out.write("- `lag_status_slot_mean`, `lag_status_slot_n` — אותו דבר ברמת (סטטוס × שעה).\n\n")

    # Results
    out.write("## 2. תוצאות\n\n")
    res_df = pd.DataFrame(results).T.round(4)
    res_df.index.name = "מודל"
    res_df = res_df.sort_values("MAE")
    out.write(md_table(res_df))
    out.write("\n")
    best = res_df.index[0]
    out.write(f"\n**🏆 המודל המוביל: `{best}`** עם MAE = {res_df.loc[best,'MAE']:.3f}, "
              f"RMSE = {res_df.loc[best,'RMSE']:.3f}, R² = {res_df.loc[best,'R²']:.3f}.\n\n")

    # Naive sanity checks
    naive_mean = float(np.mean(np.abs(test[TARGET].values - train[TARGET].mean())))
    naive_zero = float(np.mean(np.abs(test[TARGET].values)))
    out.write(f"\n**שורות בקרה (sanity):**\n")
    out.write(f"- חיזוי קבוע ב-`mean(train)` ({train[TARGET].mean():.3f}): MAE = {naive_mean:.3f}\n")
    out.write(f"- חיזוי 0: MAE = {naive_zero:.3f}\n\n")

    # Per-segment for the best model
    best_pred = preds.get(best.split(" ")[0], preds.get(best, p_base))
    out.write("## 3. ביצועים לפי חתך\n\n")

    out.write("### 3.1 לפי יום שבוע\n\n")
    seg = per_segment_metrics(test, best_pred, "יום שידור")
    order = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"]
    seg = seg.reindex([d for d in order if d in seg.index])
    seg.index.name = "יום"
    out.write(md_table(seg))
    out.write("\n")

    out.write("\n### 3.2 לפי חלקי-יום\n\n")
    seg = per_segment_metrics(test, best_pred, "חלקי-יום").sort_index()
    seg.index.name = "חלקי-יום"
    out.write(md_table(seg))
    out.write("\n")

    out.write("\n### 3.3 לפי סטטוס תוכנית\n\n")
    seg = per_segment_metrics(test, best_pred, "סטטוס תוכנית").sort_values("MAE")
    seg.index.name = "סטטוס"
    out.write(md_table(seg))
    out.write("\n")

    out.write("\n### 3.4 לפי `אירוע_מיוחד`\n\n")
    seg = per_segment_metrics(test, best_pred, "אירוע_מיוחד").sort_values("MAE", ascending=False)
    seg.index.name = "אירוע"
    out.write(md_table(seg.head(10)))
    out.write("\n")

    # Feature importance — for the best model
    out.write("\n## 4. חשיבות מאפיינים (Top-15)\n\n")
    best_name_for_imp = best if best in pipes else (
        next((n for n in ["RandomForest", "XGBoost", "Ridge"] if n in pipes), None)
    )
    if best_name_for_imp:
        imp = feature_importance_from_pipe(pipes[best_name_for_imp], 15)
        if imp is not None:
            out.write(f"\n### {best_name_for_imp} (המודל המוביל)\n\n")
            imp_df = imp.to_frame(name="חשיבות")
            imp_df["חשיבות"] = imp_df["חשיבות"].apply(lambda x: f"{x:.4f}")
            imp_df.index.name = "Feature"
            out.write(md_table(imp_df))
            out.write("\n")

    # Residual analysis
    out.write("\n## 5. ניתוח שגיאות (Residual Analysis)\n\n")
    test_resid = test.copy()
    test_resid["pred"] = best_pred
    test_resid["resid"] = test_resid[TARGET] - test_resid["pred"]

    out.write("**עשר השגיאות הגדולות (under-prediction — המודל החזיק נמוך והרייטינג היה גבוה):**\n\n")
    big_under = test_resid.sort_values("resid", ascending=False).head(10)
    show = big_under[["שם תוכנית","יום שידור","תאריך שידור","שעת התחלה",
                      TARGET,"pred","resid","אירוע_מיוחד"]].copy()
    show["תאריך שידור"] = pd.to_datetime(show["תאריך שידור"]).dt.strftime("%Y-%m-%d")
    show[[TARGET,"pred","resid"]] = show[[TARGET,"pred","resid"]].round(2)
    out.write(md_table(show, index=False))
    out.write("\n")

    out.write("\n**עשר ה-over-prediction (המודל ציפה גבוה, היה נמוך):**\n\n")
    big_over = test_resid.sort_values("resid").head(10)
    show2 = big_over[["שם תוכנית","יום שידור","תאריך שידור","שעת התחלה",
                      TARGET,"pred","resid","אירוע_מיוחד"]].copy()
    show2["תאריך שידור"] = pd.to_datetime(show2["תאריך שידור"]).dt.strftime("%Y-%m-%d")
    show2[[TARGET,"pred","resid"]] = show2[[TARGET,"pred","resid"]].round(2)
    out.write(md_table(show2, index=False))
    out.write("\n")

    # Notes
    out.write("\n## 6. הערות מתודולוגיות\n\n")
    out.write("- **בלי leakage:** העמודות שנמדדות אחרי השידור (נתח, צופים, חשיפה, רייטינגי המתחרים בזמן אמת) לא הוזנו למודל. ה-lag features מחושבים מראייה כרונולוגית קפדנית — רק מההיסטוריה שקדמה לכל שורה.\n")
    out.write("- **חלוקה זמנית** (לא random) — חיוני לסדרות זמן. random היה יוצר אופטימיזם שווא.\n")
    out.write("- **מגבלות התחזית:** המודל לא יודע לחזות אירועי-ברייקינג בלתי-צפויים (כמו פתיחת מבצע צבאי). יום שידור ביום אירוע ביטחוני יחזה לפי ההיסטוריה הרגילה ויפספס. ראה ניתוח השגיאות.\n")
    out.write("- **`אירוע_מיוחד` כ-feature** — בעייתי בפרודקשן: ידוע מראש לחגים, לא ידוע מראש לברייקינג. במציאות יש להוציא את הברייקינג ולהשאיר רק חגים.\n")
    out.write("- **קולד-סטארט:** תוכניות חדשות בלי היסטוריה מקבלות `lag_program_mean=NaN` שמולא במדיאן ה-train. עבורן הדיוק יורד.\n")
    out.write("- **שיפורים אפשריים:** (א) feature engineering נוסף — מילות מפתח בשם התוכנית (חדשות / כלכלה / ספורט), (ב) lag features של מתחרים (ממוצע ערוץ X באותה רצועה — זה לא leakage), (ג) target אלטרנטיבי `נתח` (נתח-צפייה — מנטרל HUT), (ד) דמוגרפיה לכל קהל יעד.\n")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print(f"\nWrote {OUT_MD}")

    # Predictions XLSX
    out_pred = test.copy()
    for name, p in preds.items():
        out_pred[f"חזוי_{name}"] = np.round(p, 3)
    keep_cols = ["שם תוכנית","יום שידור","תאריך שידור","שעת התחלה",
                 "משך תוכנית","סטטוס תוכנית","אירוע_מיוחד",TARGET] + [
                 f"חזוי_{n}" for n in preds.keys()]
    out_pred["תאריך שידור"] = pd.to_datetime(out_pred["תאריך שידור"]).dt.strftime("%Y-%m-%d")
    out_pred[keep_cols].to_excel(OUT_PRED_XLSX, index=False, sheet_name="חיזויים")
    print(f"Wrote {OUT_PRED_XLSX}")

    print("\nFinal summary:")
    for name, m in sorted(results.items(), key=lambda x: x[1]['MAE']):
        print(f"  {name:30s}  MAE={m['MAE']:.3f}  RMSE={m['RMSE']:.3f}  R^2={m['R²']:.3f}")


if __name__ == "__main__":
    main()
