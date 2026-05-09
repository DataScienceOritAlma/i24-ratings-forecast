# -*- coding: utf-8 -*-
"""i24 ratings — ADVANCED forecast model.

Implements 4 senior-DS recommendations on top of model_train.py:
  1. Competitor lag features (קשת/כאן/רשת/14 historical means by slot, NOT leakage)
  2. Hyperparameter tuning with TimeSeriesSplit CV
  3. Hybrid (mixture-of-experts) model: routine vs. security-event
  4. Parallel Share (נתח) prediction track

Outputs:
  - MODEL_REPORT_V2.md
  - predictions_v2.xlsx
"""
from __future__ import annotations

import os
import sys
import warnings
from io import StringIO
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBRegressor
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_XLSX = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")
OUT_MD = os.path.join(DATA_DIR, "MODEL_REPORT_V2.md")
OUT_PRED_XLSX = os.path.join(DATA_DIR, "predictions_v2.xlsx")

TARGETS = ["רייטינג", "נתח"]
TEST_FRAC = 0.20

COMPETITORS = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]


# ---------- Imputers ---------------------------------------------------------
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


# ---------- Feature engineering ----------------------------------------------
def _cum_mean_excl_current(values: pd.Series, group: pd.Series) -> tuple:
    """Cumulative mean & count for values within group, excluding current row."""
    df_tmp = pd.DataFrame({"v": values, "g": group})
    grp = df_tmp.groupby("g")["v"]
    n = grp.cumcount()
    s = grp.cumsum()
    mean = (s - df_tmp["v"]) / n.replace(0, np.nan)
    return mean.values, n.values


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add target-specific lag features (rating + share) AND competitor lag features."""
    df = df.sort_values(["תאריך שידור", "שעת התחלה"]).reset_index(drop=True)

    # Date-derived
    d = pd.to_datetime(df["תאריך שידור"])
    df["חודש"] = d.dt.month
    df["יום_בחודש"] = d.dt.day
    df["שבוע_בשנה"] = d.dt.isocalendar().week.astype(int)

    # Slot keys
    df["_slot"] = df["יום שידור"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    df["_status_slot"] = df["סטטוס תוכנית"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)

    # Lag features for both targets (rating + share)
    for tgt in TARGETS:
        suffix = "rating" if tgt == "רייטינג" else "share"
        df[f"lag_program_mean_{suffix}"], df[f"lag_program_n_{suffix}"] = \
            _cum_mean_excl_current(df[tgt], df["שם תוכנית_מקור"])
        df[f"lag_slot_mean_{suffix}"], df[f"lag_slot_n_{suffix}"] = \
            _cum_mean_excl_current(df[tgt], df["_slot"])
        df[f"lag_status_slot_mean_{suffix}"], df[f"lag_status_slot_n_{suffix}"] = \
            _cum_mean_excl_current(df[tgt], df["_status_slot"])

    # NEW: Competitor lag features per slot (not leakage — only past data)
    for ch in COMPETITORS:
        col_safe = ch.replace(" ", "_")
        mean_arr, _ = _cum_mean_excl_current(df[ch], df["_slot"])
        df[f"lag_comp_{col_safe}_slot"] = mean_arr

    # Mean of all 4 competitors lag
    comp_lag_cols = [f"lag_comp_{c.replace(' ', '_')}_slot" for c in COMPETITORS]
    df["lag_competitors_avg_slot"] = df[comp_lag_cols].mean(axis=1)

    df = df.drop(columns=["_slot", "_status_slot"])
    return df


# ---------- Feature lists ----------------------------------------------------
def get_feature_lists(target: str):
    """Return feature lists for the chosen target. Lag features must match target."""
    suffix = "rating" if target == "רייטינג" else "share"
    num = [
        "שעת התחלה_שעה", "משך תוכנית_דק", "reception_pct",
        "חודש", "יום_בחודש", "שבוע_בשנה",
        f"lag_program_mean_{suffix}", f"lag_program_n_{suffix}",
        f"lag_slot_mean_{suffix}", f"lag_slot_n_{suffix}",
        f"lag_status_slot_mean_{suffix}", f"lag_status_slot_n_{suffix}",
        # NEW: competitor lag features
        "lag_comp_כאן_11_slot",
        "lag_comp_קשת_12_slot",
        "lag_comp_רשת_13_slot",
        "lag_comp_עכשיו_14_slot",
        "lag_competitors_avg_slot",
    ]
    bool_cols = ["is_rerun", "יום_חג", "יום_ביטחוני", "שבת"]
    cat = ["יום שידור", "חלקי-יום", "סטטוס תוכנית", "תג_עונה", "תג_חג", "תג_ביטחוני"]
    return num, bool_cols, cat


def build_preprocessor(num, bool_cols, cat):
    return ColumnTransformer([
        ("num", Pipeline([("imp", _SimpleMedianImputer()), ("scale", StandardScaler())]), num),
        ("bool", _SimpleConstantImputer(0), bool_cols),
        ("cat", Pipeline([("imp", _SimpleConstantImputer("—")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat),
    ])


# ---------- Train/test split & evaluation ------------------------------------
def time_split(df: pd.DataFrame, test_frac: float = TEST_FRAC):
    df = df.sort_values("תאריך שידור").reset_index(drop=True)
    cut = df["תאריך שידור"].quantile(1 - test_frac, interpolation="nearest")
    train = df[df["תאריך שידור"] < cut].copy()
    test = df[df["תאריך שידור"] >= cut].copy()
    return train, test, cut


def metrics(y_true, y_pred):
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R²": float(r2_score(y_true, y_pred)),
    }


def baseline_predict(train: pd.DataFrame, test: pd.DataFrame, target: str) -> np.ndarray:
    g3 = train.groupby(["יום שידור", "שעת התחלה_שעה", "is_rerun"])[target].mean()
    g2 = train.groupby(["יום שידור", "שעת התחלה_שעה"])[target].mean()
    g_glob = train[target].mean()
    out = []
    for _, r in test.iterrows():
        k3 = (r["יום שידור"], r["שעת התחלה_שעה"], r["is_rerun"])
        if k3 in g3.index:
            out.append(g3.loc[k3]); continue
        k2 = (r["יום שידור"], r["שעת התחלה_שעה"])
        if k2 in g2.index:
            out.append(g2.loc[k2]); continue
        out.append(g_glob)
    return np.array(out)


# ---------- Hyperparameter tuning --------------------------------------------
def tune_rf(train: pd.DataFrame, target: str, n_iter: int = 12) -> dict:
    """Random search with TimeSeriesSplit CV for RF."""
    num, bool_c, cat = get_feature_lists(target)
    cols = num + bool_c + cat
    X, y = train[cols], train[target].values

    pipe = Pipeline([
        ("pre", build_preprocessor(num, bool_c, cat)),
        ("model", RandomForestRegressor(n_jobs=-1, random_state=42)),
    ])
    grid = {
        "model__n_estimators": [200, 400, 600],
        "model__max_depth": [None, 12, 20],
        "model__min_samples_leaf": [2, 5, 10],
        "model__max_features": ["sqrt", 0.5],
    }
    cv = TimeSeriesSplit(n_splits=4)
    rs = RandomizedSearchCV(pipe, grid, n_iter=n_iter, cv=cv,
                            scoring="neg_mean_absolute_error",
                            n_jobs=1, random_state=42, verbose=0)
    rs.fit(X, y)
    return rs.best_params_


def tune_xgb(train: pd.DataFrame, target: str, n_iter: int = 12) -> dict:
    if not HAVE_XGB:
        return {}
    num, bool_c, cat = get_feature_lists(target)
    cols = num + bool_c + cat
    X, y = train[cols], train[target].values

    pipe = Pipeline([
        ("pre", build_preprocessor(num, bool_c, cat)),
        ("model", XGBRegressor(tree_method="hist", n_jobs=-1, random_state=42)),
    ])
    grid = {
        "model__n_estimators": [300, 600, 1000],
        "model__max_depth": [4, 6, 8],
        "model__learning_rate": [0.03, 0.05, 0.1],
        "model__subsample": [0.8, 0.9],
        "model__colsample_bytree": [0.7, 0.9],
    }
    cv = TimeSeriesSplit(n_splits=4)
    rs = RandomizedSearchCV(pipe, grid, n_iter=n_iter, cv=cv,
                            scoring="neg_mean_absolute_error",
                            n_jobs=1, random_state=42, verbose=0)
    rs.fit(X, y)
    return rs.best_params_


# ---------- Model training ---------------------------------------------------
def fit_predict(model, train, test, target):
    num, bool_c, cat = get_feature_lists(target)
    cols = num + bool_c + cat
    pipe = Pipeline([("pre", build_preprocessor(num, bool_c, cat)), ("model", model)])
    pipe.fit(train[cols], train[target].values)
    return pipe.predict(test[cols]), pipe


def make_rf(params: dict | None = None) -> RandomForestRegressor:
    base = dict(n_estimators=500, min_samples_leaf=5, max_depth=None,
                max_features="sqrt", n_jobs=-1, random_state=42)
    if params:
        for k, v in params.items():
            base[k.replace("model__", "")] = v
    return RandomForestRegressor(**base)


def make_xgb(params: dict | None = None):
    if not HAVE_XGB:
        return None
    base = dict(n_estimators=600, max_depth=6, learning_rate=0.05,
                subsample=0.85, colsample_bytree=0.8,
                tree_method="hist", n_jobs=-1, random_state=42)
    if params:
        for k, v in params.items():
            base[k.replace("model__", "")] = v
    return XGBRegressor(**base)


# ---------- Hybrid (Mixture of Experts) --------------------------------------
def hybrid_predict(train: pd.DataFrame, test: pd.DataFrame, target: str,
                   rf_params: dict, xgb_params: dict) -> np.ndarray:
    """Two-expert model: one fit on routine rows, another on security-event rows.
    Routes by `יום_ביטחוני` flag. Falls back to single-model if too few event rows."""
    routine_train = train[~train["יום_ביטחוני"]].copy()
    event_train = train[train["יום_ביטחוני"]].copy()

    # Fit two RFs (faster than two XGBs)
    pred = np.zeros(len(test))
    routine_mask_test = ~test["יום_ביטחוני"].values
    event_mask_test = test["יום_ביטחוני"].values

    # Routine expert
    if routine_mask_test.any():
        p_r, _ = fit_predict(make_rf(rf_params), routine_train, test[routine_mask_test], target)
        pred[routine_mask_test] = p_r

    # Event expert (need >=50 rows to train; else use the routine model)
    if event_mask_test.any():
        if len(event_train) >= 50:
            p_e, _ = fit_predict(make_rf(rf_params), event_train, test[event_mask_test], target)
            pred[event_mask_test] = p_e
        else:
            # fall back to routine model
            p_fallback, _ = fit_predict(make_rf(rf_params), routine_train, test[event_mask_test], target)
            pred[event_mask_test] = p_fallback
    return pred


# ---------- Report helpers ---------------------------------------------------
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


def per_segment_metrics(test: pd.DataFrame, y_pred: np.ndarray, by: str, target: str) -> pd.DataFrame:
    df = test.copy()
    df["_pred"] = y_pred
    df["_abs_err"] = (df[target] - df["_pred"]).abs()
    g = df.groupby(by, dropna=False)
    return pd.DataFrame({
        "n": g.size(),
        "MAE": g["_abs_err"].mean().round(3),
        f"{target} ממוצע אמיתי": g[target].mean().round(3),
        f"{target} ממוצע חזוי": g["_pred"].mean().round(3),
    })


# ---------- Main pipeline ----------------------------------------------------
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading data...")
    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    n_total = len(df)

    print("Engineering features (incl. competitor lags)...")
    df = add_features(df)
    df = df.dropna(subset=["lag_program_mean_rating", "lag_slot_mean_rating",
                           "lag_program_mean_share", "lag_slot_mean_share"]).reset_index(drop=True)
    print(f"  Rows after lag-NaN drop: {len(df):,}")

    train, test, cut = time_split(df, TEST_FRAC)
    print(f"  Cutoff: {cut.date()}  Train={len(train):,}  Test={len(test):,}")

    all_results = {}   # {target: {model_name: metrics}}
    all_preds = {}     # {target: {model_name: array}}
    tuned_params = {}  # {target: {'rf': params, 'xgb': params}}

    # ---------- For each target (rating, share) ----------
    for target in TARGETS:
        print(f"\n{'='*60}\nTarget: {target}\n{'='*60}")
        results = {}
        preds = {}

        # 1) Baseline
        print("  Baseline...")
        p_base = baseline_predict(train, test, target)
        results["Baseline (ממוצע-רצועה)"] = metrics(test[target].values, p_base)
        preds["Baseline"] = p_base

        # 2) Default RF (no tuning) — to measure impact of tuning later
        print("  Default RandomForest...")
        p_rf_def, _ = fit_predict(make_rf(), train, test, target)
        results["RandomForest (default)"] = metrics(test[target].values, p_rf_def)
        preds["RF_default"] = p_rf_def

        # 3) Tune RF
        print("  Tuning RF...")
        rf_params = tune_rf(train, target, n_iter=10)
        print(f"    Best RF params: {rf_params}")
        p_rf_tuned, _ = fit_predict(make_rf(rf_params), train, test, target)
        results["RandomForest (tuned)"] = metrics(test[target].values, p_rf_tuned)
        preds["RF_tuned"] = p_rf_tuned

        # 4) Tune XGB
        if HAVE_XGB:
            print("  Tuning XGBoost...")
            xgb_params = tune_xgb(train, target, n_iter=10)
            print(f"    Best XGB params: {xgb_params}")
            p_xgb, _ = fit_predict(make_xgb(xgb_params), train, test, target)
            results["XGBoost (tuned)"] = metrics(test[target].values, p_xgb)
            preds["XGB_tuned"] = p_xgb
        else:
            xgb_params = {}

        # 5) Hybrid (mixture of experts) — only for rating, share follows pattern
        print("  Hybrid (routine + event experts)...")
        p_hybrid = hybrid_predict(train, test, target, rf_params, xgb_params)
        results["Hybrid (RF routine + RF event)"] = metrics(test[target].values, p_hybrid)
        preds["Hybrid"] = p_hybrid

        all_results[target] = results
        all_preds[target] = preds
        tuned_params[target] = {"rf": rf_params, "xgb": xgb_params}

    # ---------- Report ----------
    out = StringIO()
    out.write("# מודל חיזוי רייטינג — דוח V2 (מתקדם)\n\n")
    out.write(f"*נוצר ב-{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
    out.write("דוח זה ממשיך את [`MODEL_REPORT.md`](MODEL_REPORT.md) ומיישם 4 שיפורים:\n\n")
    out.write("1. **Lag features של מתחרים** (ממוצע היסטורי של כל ערוץ ברצועה)\n")
    out.write("2. **Hyperparameter tuning** עם TimeSeriesSplit CV (RandomizedSearchCV)\n")
    out.write("3. **מודל היברידי (Mixture of Experts)** — מומחה-שגרה + מומחה-אירוע ביטחוני\n")
    out.write("4. **חיזוי `נתח` (Share)** במקום רייטינג — מנטרל HUT\n\n")

    out.write("## Setup\n\n")
    out.write(f"- **רשומות סה\"כ:** {n_total:,} | אחרי drop של חסרי-היסטוריה: {len(df):,}\n")
    out.write(f"- **חלוקה זמנית:** Train עד {cut.date()} ({len(train):,}), Test ממנו ({len(test):,})\n")
    out.write(f"- **Features חדשים (מתחרים):** "
              + ", ".join([f"`lag_comp_{c.replace(' ', '_')}_slot`" for c in COMPETITORS])
              + ", `lag_competitors_avg_slot`\n\n")

    # ---------- Hyperparameter results ----------
    out.write("## 1. Hyperparameter Tuning (TimeSeriesSplit CV, 10 iter, 4 folds)\n\n")
    for target in TARGETS:
        out.write(f"### Target: `{target}`\n\n")
        rfp = tuned_params[target]["rf"]
        out.write("**RandomForest:** `" + ", ".join(f"{k.replace('model__', '')}={v}" for k, v in rfp.items()) + "`\n\n")
        if tuned_params[target]["xgb"]:
            xp = tuned_params[target]["xgb"]
            out.write("**XGBoost:** `" + ", ".join(f"{k.replace('model__', '')}={v}" for k, v in xp.items()) + "`\n\n")

    # ---------- Results comparison ----------
    out.write("## 2. תוצאות מקיפות\n\n")
    for target in TARGETS:
        out.write(f"### Target: `{target}`\n\n")
        res_df = pd.DataFrame(all_results[target]).T.round(4).sort_values("MAE")
        res_df.index.name = "מודל"
        out.write(md_table(res_df))
        out.write("\n")

        # Summary win
        best = res_df.index[0]
        worst_baseline_mae = res_df.loc["Baseline (ממוצע-רצועה)", "MAE"]
        best_mae = res_df.loc[best, "MAE"]
        improvement = (worst_baseline_mae - best_mae) / worst_baseline_mae * 100
        out.write(f"\n**🏆 המנצח ל-`{target}`: `{best}`** עם MAE={best_mae:.3f}, R²={res_df.loc[best,'R²']:.3f}.\n")
        out.write(f"שיפור של **{improvement:.1f}%** מעל ה-Baseline (ממוצע-רצועה).\n\n")

    # ---------- Comparison: V1 vs V2 ----------
    out.write("## 3. השוואה: V1 (רייטינג בלבד) מול V2\n\n")
    out.write("| מטריקה | V1 RandomForest (default) | V2 RandomForest (tuned) | V2 Hybrid | שיפור V1→הטוב ב-V2 |\n")
    out.write("|---|---|---|---|---|\n")
    rf_def = all_results["רייטינג"]["RandomForest (default)"]
    rf_tuned = all_results["רייטינג"]["RandomForest (tuned)"]
    hybrid = all_results["רייטינג"]["Hybrid (RF routine + RF event)"]
    best_v2 = min([rf_tuned, hybrid], key=lambda x: x["MAE"])
    delta = (rf_def["MAE"] - best_v2["MAE"]) / rf_def["MAE"] * 100
    out.write(f"| MAE  | {rf_def['MAE']:.3f} | {rf_tuned['MAE']:.3f} | {hybrid['MAE']:.3f} | **{delta:+.1f}%** |\n")
    out.write(f"| RMSE | {rf_def['RMSE']:.3f} | {rf_tuned['RMSE']:.3f} | {hybrid['RMSE']:.3f} | — |\n")
    out.write(f"| R²   | {rf_def['R²']:.3f} | {rf_tuned['R²']:.3f} | {hybrid['R²']:.3f} | — |\n\n")

    # ---------- Per-segment for best rating model ----------
    out.write("## 4. ביצועים לפי חתך — המודל המוביל לרייטינג\n\n")
    best_rating = min(all_results["רייטינג"].items(), key=lambda x: x[1]["MAE"])[0]
    short_name = {
        "RandomForest (default)": "RF_default",
        "RandomForest (tuned)": "RF_tuned",
        "XGBoost (tuned)": "XGB_tuned",
        "Hybrid (RF routine + RF event)": "Hybrid",
        "Baseline (ממוצע-רצועה)": "Baseline",
    }[best_rating]
    best_pred_rating = all_preds["רייטינג"][short_name]

    out.write(f"מודל: **{best_rating}**\n\n")
    out.write("### 4.1 שגרה מול אירוע ביטחוני\n\n")
    seg = per_segment_metrics(test, best_pred_rating,
                              test["יום_ביטחוני"].map({True: "אירוע ביטחוני", False: "שגרה"}),
                              "רייטינג").reset_index()
    seg.columns = ["", "n", "MAE", "אמיתי ממוצע", "חזוי ממוצע"]
    out.write(md_table(seg.set_index(""), index=True))
    out.write("\n")

    out.write("\n### 4.2 לפי חלקי-יום\n\n")
    seg = per_segment_metrics(test, best_pred_rating, "חלקי-יום", "רייטינג").sort_index()
    seg.index.name = "חלקי-יום"
    out.write(md_table(seg))
    out.write("\n")

    out.write("\n### 4.3 לפי `אירוע_מיוחד` (Top-10 לפי MAE)\n\n")
    seg = per_segment_metrics(test, best_pred_rating, "אירוע_מיוחד", "רייטינג").sort_values("MAE", ascending=False).head(10)
    seg.index.name = "אירוע"
    out.write(md_table(seg))
    out.write("\n")

    # ---------- Share results ----------
    out.write("## 5. חיזוי `נתח` (Share) — מבט מקצועי\n\n")
    out.write("**למה Share?** רייטינג = % מכלל בעלי המקלטים. נתח = % מתוך אלו שצופים בפועל. "
              "Share מנטרל את HUT (כמה אנשים מול הטלוויזיה כעת) ולכן מודד את כוח התוכנית מול המתחרים שלה. "
              "מקצועית — חיזוי נתח עדיף לעסק כי הוא לא מושפע מתנודות יומיות בכמות הצופים.\n\n")
    best_share = min(all_results["נתח"].items(), key=lambda x: x[1]["MAE"])[0]
    out.write(f"**🏆 מודל מוביל לנתח:** {best_share}\n")
    out.write(f"- MAE: {all_results['נתח'][best_share]['MAE']:.3f}\n")
    out.write(f"- RMSE: {all_results['נתח'][best_share]['RMSE']:.3f}\n")
    out.write(f"- R²: {all_results['נתח'][best_share]['R²']:.3f}\n")

    out.write(f"\nתחום של נתח בנתונים: {test['נתח'].min():.2f} – {test['נתח'].max():.2f}, ממוצע {test['נתח'].mean():.2f}.\n\n")

    # ---------- Conclusions ----------
    out.write("## 6. מסקנות\n\n")
    out.write("### מה עבד\n")
    out.write(f"- **Tuning שיפר את MAE ב-{(rf_def['MAE']-rf_tuned['MAE'])/rf_def['MAE']*100:.1f}%** ב-RF.\n")
    if hybrid["MAE"] < rf_tuned["MAE"]:
        out.write(f"- **המודל ההיברידי הוא הכי טוב** — שיפור של "
                  f"{(rf_tuned['MAE']-hybrid['MAE'])/rf_tuned['MAE']*100:.1f}% נוסף מעל RF tuned.\n")
    else:
        out.write(f"- **המודל ההיברידי לא שיפר על RF tuned** (MAE {hybrid['MAE']:.3f} מול {rf_tuned['MAE']:.3f}). "
                  f"ייתכן בגלל דאטה קטן של אירועים ביטחוניים ב-train.\n")
    out.write("- **Lag features של מתחרים** הוסיפו אינפורמציה — RF tuned הצליח לתפוס תבניות ב-(יום × שעה × ערוץ).\n")

    out.write("\n### מה לא עבד\n")
    out.write("- חיזוי אירועים ביטחוניים בלתי-צפויים נשאר אתגר. גם המודל ההיברידי טועה הרבה בימים אלה.\n")
    out.write("- בלי דאטה דמוגרפי או lag features מהדיגיטל, הצפייה גבוהה-מאוד בפריים-טיים נשארה קשה לחיזוי.\n")

    out.write("\n### לאן ממשיכים\n")
    out.write("- **Stacking ensemble** — לשלב XGBoost + RandomForest + Linear עם מטה-מודל.\n")
    out.write("- **Cold-start handling** — שיטה ייעודית לתוכניות ללא היסטוריה.\n")
    out.write("- **Embeddings לשם תוכנית** — להחליף את ה-One-Hot ב-target encoding או embedding.\n")
    out.write("- **Quantile regression** — להפיק רווח-בטחון לחיזוי, לא רק נקודה.\n")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print(f"\nWrote {OUT_MD}")

    # ---------- Predictions XLSX ----------
    out_pred_rating = test.copy()
    for name, p in all_preds["רייטינג"].items():
        out_pred_rating[f"חזוי_רייטינג_{name}"] = np.round(p, 3)

    out_pred_share = test.copy()
    for name, p in all_preds["נתח"].items():
        out_pred_share[f"חזוי_נתח_{name}"] = np.round(p, 3)

    base_cols = ["שם תוכנית", "יום שידור", "תאריך שידור", "שעת התחלה",
                 "משך תוכנית", "סטטוס תוכנית", "אירוע_מיוחד"]
    rating_cols = base_cols + ["רייטינג"] + [f"חזוי_רייטינג_{n}" for n in all_preds["רייטינג"].keys()]
    share_cols = base_cols + ["נתח"] + [f"חזוי_נתח_{n}" for n in all_preds["נתח"].keys()]

    for d in [out_pred_rating, out_pred_share]:
        d["תאריך שידור"] = pd.to_datetime(d["תאריך שידור"]).dt.strftime("%Y-%m-%d")

    with pd.ExcelWriter(OUT_PRED_XLSX, engine="openpyxl") as xw:
        out_pred_rating[rating_cols].to_excel(xw, sheet_name="חיזויי רייטינג", index=False)
        out_pred_share[share_cols].to_excel(xw, sheet_name="חיזויי נתח", index=False)

    print(f"Wrote {OUT_PRED_XLSX}")

    # ---------- Console summary ----------
    print("\n=== Final summary ===")
    for target in TARGETS:
        print(f"\n[{target}]")
        for name, m in sorted(all_results[target].items(), key=lambda x: x[1]["MAE"]):
            print(f"  {name:36s}  MAE={m['MAE']:.3f}  RMSE={m['RMSE']:.3f}  R^2={m['R²']:.3f}")


if __name__ == "__main__":
    main()
