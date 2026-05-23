# -*- coding: utf-8 -*-
"""i24 ratings — ALL-MODELS comparison + deep error analysis.

This script trains a wide spectrum of regression models on the same
forecast setup (no leakage, time-based split) and produces a
detailed error analysis for each model:
  - Where does each model err? (program, day, hour, event)
  - Top-10 worst predictions per model
  - MAE per segment for each model

Models trained (16):
  Linear family:
    1. Ridge
    2. Lasso
    3. ElasticNet
    4. BayesianRidge
    5. HuberRegressor (robust to outliers)
  Distance / kernel:
    6. KNeighborsRegressor (k=10, distance-weighted)
    7. SVR (RBF kernel)
  Trees (single):
    8. DecisionTreeRegressor (max_depth=10)
  Tree ensembles:
    9. RandomForest (tuned)
    10. ExtraTrees
    11. GradientBoosting (sklearn)
    12. HistGradientBoosting (sklearn fast)
    13. XGBoost (tuned)
    14. LightGBM
    15. CatBoost
  Neural:
    16. MLPRegressor (2 hidden layers)
  Ensembles of ensembles:
    17. Stacking (Ridge meta over RF + XGB + LGB)
  Plus baselines:
    0a. Naive global mean
    0b. Slot mean baseline

Outputs:
  - MODEL_REPORT_ALL.md   — full comparison + per-model error analysis
  - predictions_all.xlsx  — actual + all model predictions side by side
"""
from __future__ import annotations

import os
import sys
import time
import warnings
from io import StringIO
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    RandomForestRegressor, ExtraTreesRegressor,
    GradientBoostingRegressor, HistGradientBoostingRegressor,
    StackingRegressor,
)
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge, HuberRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBRegressor
    HAVE_XGB = True
except ImportError:
    HAVE_XGB = False

try:
    from lightgbm import LGBMRegressor
    HAVE_LGB = True
except ImportError:
    HAVE_LGB = False

try:
    from catboost import CatBoostRegressor
    HAVE_CAT = True
except ImportError:
    HAVE_CAT = False

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_XLSX = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")
OUT_MD = os.path.join(DATA_DIR, "MODEL_REPORT_ALL_v4_adjusted.md")
OUT_PRED_XLSX = os.path.join(DATA_DIR, "predictions_all_v4_adjusted.xlsx")

TARGET = "רייטינג מותאם"
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
def _cum_mean_excl_current(values: pd.Series, group: pd.Series):
    df_tmp = pd.DataFrame({"v": values, "g": group})
    grp = df_tmp.groupby("g")["v"]
    n = grp.cumcount()
    s = grp.cumsum()
    mean = (s - df_tmp["v"]) / n.replace(0, np.nan)
    return mean.values, n.values


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["תאריך שידור", "שעת התחלה"]).reset_index(drop=True)

    d = pd.to_datetime(df["תאריך שידור"])
    df["חודש"] = d.dt.month
    df["יום_בחודש"] = d.dt.day
    df["שבוע_בשנה"] = d.dt.isocalendar().week.astype(int)

    df["_slot"] = df["יום שידור"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)
    df["_status_slot"] = df["סטטוס תוכנית"].astype(str) + "_" + df["שעת התחלה_שעה"].astype(str)

    df["lag_program_mean"], df["lag_program_n"] = \
        _cum_mean_excl_current(df[TARGET], df["שם תוכנית_מקור"])
    df["lag_slot_mean"], df["lag_slot_n"] = \
        _cum_mean_excl_current(df[TARGET], df["_slot"])
    df["lag_status_slot_mean"], df["lag_status_slot_n"] = \
        _cum_mean_excl_current(df[TARGET], df["_status_slot"])

    for ch in COMPETITORS:
        col_safe = ch.replace(" ", "_")
        mean_arr, _ = _cum_mean_excl_current(df[ch], df["_slot"])
        df[f"lag_comp_{col_safe}_slot"] = mean_arr

    comp_lag_cols = [f"lag_comp_{c.replace(' ', '_')}_slot" for c in COMPETITORS]
    df["lag_competitors_avg_slot"] = df[comp_lag_cols].mean(axis=1)

    df = df.drop(columns=["_slot", "_status_slot"])
    return df


PRE_AIRING_FEATURES_NUM = [
    "שעת התחלה_שעה", "משך תוכנית_דק", "reception_pct",
    "חודש", "יום_בחודש", "שבוע_בשנה",
    "lag_program_mean", "lag_program_n",
    "lag_slot_mean", "lag_slot_n",
    "lag_status_slot_mean", "lag_status_slot_n",
    "lag_comp_כאן_11_slot",
    "lag_comp_קשת_12_slot",
    "lag_comp_רשת_13_slot",
    "lag_comp_עכשיו_14_slot",
    "lag_competitors_avg_slot",
]

PRE_AIRING_FEATURES_BOOL = ["is_rerun", "יום_חג", "יום_ביטחוני", "שבת"]

PRE_AIRING_FEATURES_CAT = [
    "יום שידור", "חלקי-יום", "סטטוס תוכנית",
    "תג_עונה", "תג_חג", "תג_ביטחוני",
]

ALL_COLS = PRE_AIRING_FEATURES_NUM + PRE_AIRING_FEATURES_BOOL + PRE_AIRING_FEATURES_CAT


def build_preprocessor():
    return ColumnTransformer([
        ("num", Pipeline([("imp", _SimpleMedianImputer()), ("scale", StandardScaler())]),
         PRE_AIRING_FEATURES_NUM),
        ("bool", _SimpleConstantImputer(0), PRE_AIRING_FEATURES_BOOL),
        ("cat", Pipeline([("imp", _SimpleConstantImputer("—")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
         PRE_AIRING_FEATURES_CAT),
    ])


# ---------- Train / split / metrics ------------------------------------------
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


def naive_global_mean_predict(train, test):
    return np.full(len(test), train[TARGET].mean())


def slot_mean_predict(train, test):
    g3 = train.groupby(["יום שידור", "שעת התחלה_שעה", "is_rerun"])[TARGET].mean()
    g2 = train.groupby(["יום שידור", "שעת התחלה_שעה"])[TARGET].mean()
    g_glob = train[TARGET].mean()
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


def fit_predict(model, train, test):
    pipe = Pipeline([("pre", build_preprocessor()), ("model", model)])
    pipe.fit(train[ALL_COLS], train[TARGET].values)
    return pipe.predict(test[ALL_COLS]), pipe


# ---------- Error-analysis helpers -------------------------------------------
def per_segment_mae(test_df: pd.DataFrame, y_pred: np.ndarray, by, top_n: int = None,
                    sort_by: str = "MAE", ascending: bool = False) -> pd.DataFrame:
    df = test_df.copy()
    df["_pred"] = y_pred
    df["_abs_err"] = (df[TARGET] - df["_pred"]).abs()
    g = df.groupby(by, dropna=False)
    res = pd.DataFrame({
        "n": g.size(),
        "MAE": g["_abs_err"].mean().round(3),
        "ר' אמיתי": g[TARGET].mean().round(3),
        "ר' חזוי": g["_pred"].mean().round(3),
        "הטיה": (g["_pred"].mean() - g[TARGET].mean()).round(3),
    }).sort_values(sort_by, ascending=ascending)
    if top_n:
        res = res.head(top_n)
    return res


def top_errors(test_df: pd.DataFrame, y_pred: np.ndarray, n: int = 10, mode: str = "abs"):
    df = test_df.copy()
    df["pred"] = y_pred
    df["resid"] = df[TARGET] - df["pred"]
    df["abs_err"] = df["resid"].abs()
    if mode == "abs":
        df = df.sort_values("abs_err", ascending=False).head(n)
    elif mode == "under":  # actual >> predicted
        df = df.sort_values("resid", ascending=False).head(n)
    elif mode == "over":  # actual << predicted
        df = df.sort_values("resid").head(n)
    cols = ["שם תוכנית", "יום שידור", "תאריך שידור", "שעת התחלה",
            TARGET, "pred", "resid", "אירוע_מיוחד"]
    out = df[cols].copy()
    out["תאריך שידור"] = pd.to_datetime(out["תאריך שידור"]).dt.strftime("%Y-%m-%d")
    out[[TARGET, "pred", "resid"]] = out[[TARGET, "pred", "resid"]].round(2)
    return out


# ---------- Markdown helpers -------------------------------------------------
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


# ---------- Main -------------------------------------------------------------
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Loading data...")
    df = pd.read_excel(SRC_XLSX, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    n_total = len(df)

    print("Engineering features...")
    df = add_features(df)
    df = df.dropna(subset=["lag_program_mean", "lag_slot_mean"]).reset_index(drop=True)
    print(f"  Rows after lag-NaN drop: {len(df):,}")

    train, test, cut = time_split(df, TEST_FRAC)
    print(f"  Cutoff: {cut.date()}  Train={len(train):,}  Test={len(test):,}")

    # ---------- Model registry ----------
    models = {}

    # Baselines
    models["00_Naive_GlobalMean"]     = ("baseline", naive_global_mean_predict)
    models["01_Slot_Mean"]            = ("baseline", slot_mean_predict)

    # Linear family
    models["02_Ridge"]                = ("sk", Ridge(alpha=1.0, random_state=42))
    models["03_Lasso"]                = ("sk", Lasso(alpha=0.01, random_state=42, max_iter=5000))
    models["04_ElasticNet"]           = ("sk", ElasticNet(alpha=0.01, l1_ratio=0.5,
                                                          random_state=42, max_iter=5000))
    models["05_BayesianRidge"]        = ("sk", BayesianRidge())
    models["06_HuberRegressor"]       = ("sk", HuberRegressor(max_iter=300))

    # Distance / kernel
    models["07_KNN_k10"]              = ("sk", KNeighborsRegressor(n_neighbors=10, weights="distance"))
    models["08_SVR_RBF"]              = ("sk", SVR(kernel="rbf", C=1.0, gamma="scale"))

    # Single tree
    models["09_DecisionTree_d10"]     = ("sk", DecisionTreeRegressor(max_depth=10,
                                                                    min_samples_leaf=10,
                                                                    random_state=42))
    # Tree ensembles
    models["10_RandomForest_tuned"]   = ("sk", RandomForestRegressor(
        n_estimators=400, max_depth=None, min_samples_leaf=5,
        max_features="sqrt", n_jobs=-1, random_state=42))
    models["11_ExtraTrees"]           = ("sk", ExtraTreesRegressor(
        n_estimators=400, min_samples_leaf=5, n_jobs=-1, random_state=42))
    models["12_GradientBoosting"]     = ("sk", GradientBoostingRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05, random_state=42))
    models["13_HistGradientBoosting"] = ("sk", HistGradientBoostingRegressor(
        max_iter=400, max_depth=6, learning_rate=0.05, random_state=42))

    if HAVE_XGB:
        models["14_XGBoost"]          = ("sk", XGBRegressor(
            n_estimators=600, max_depth=6, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.8, random_state=42,
            tree_method="hist", n_jobs=-1, verbosity=0))

    if HAVE_LGB:
        models["15_LightGBM"]         = ("sk", LGBMRegressor(
            n_estimators=600, max_depth=-1, num_leaves=63,
            learning_rate=0.05, subsample=0.85, colsample_bytree=0.8,
            random_state=42, n_jobs=-1, verbosity=-1))

    if HAVE_CAT:
        models["16_CatBoost"]         = ("sk", CatBoostRegressor(
            iterations=600, depth=6, learning_rate=0.05,
            random_state=42, verbose=False))

    # Neural network
    models["17_MLP_64_32"]            = ("sk", MLPRegressor(
        hidden_layer_sizes=(64, 32), max_iter=300, random_state=42,
        early_stopping=True))

    # Stacking (after training base models, we'll add it)

    # ---------- Train each model ----------
    results = {}
    preds = {}
    fit_times = {}

    for name, (kind, est) in models.items():
        print(f"\n{name}...")
        t0 = time.time()
        try:
            if kind == "baseline":
                p = est(train, test)
            else:
                p, _ = fit_predict(est, train, test)
            dt = time.time() - t0
            results[name] = metrics(test[TARGET].values, p)
            preds[name] = p
            fit_times[name] = dt
            print(f"  MAE={results[name]['MAE']:.3f}  R²={results[name]['R²']:.3f}  ({dt:.1f}s)")
        except Exception as e:
            print(f"  FAILED: {e}")

    # ---------- Stacking ensemble (Ridge meta over RF + XGB + LGB) ------------
    print("\n18_Stacking_Ridge_meta ...")
    t0 = time.time()
    estimators = []
    estimators.append(("rf", RandomForestRegressor(
        n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=42)))
    if HAVE_XGB:
        estimators.append(("xgb", XGBRegressor(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            random_state=42, tree_method="hist", n_jobs=-1, verbosity=0)))
    if HAVE_LGB:
        estimators.append(("lgb", LGBMRegressor(
            n_estimators=400, num_leaves=63, learning_rate=0.05,
            random_state=42, n_jobs=-1, verbosity=-1)))
    stack = StackingRegressor(estimators=estimators, final_estimator=Ridge(alpha=1.0),
                              n_jobs=1, passthrough=False)
    try:
        p_st, _ = fit_predict(stack, train, test)
        dt = time.time() - t0
        results["18_Stacking_Ridge_meta"] = metrics(test[TARGET].values, p_st)
        preds["18_Stacking_Ridge_meta"] = p_st
        fit_times["18_Stacking_Ridge_meta"] = dt
        print(f"  MAE={results['18_Stacking_Ridge_meta']['MAE']:.3f}  "
              f"R²={results['18_Stacking_Ridge_meta']['R²']:.3f}  ({dt:.1f}s)")
    except Exception as e:
        print(f"  FAILED: {e}")

    # ============================================================
    # Build report
    # ============================================================
    out = StringIO()
    out.write("# 🎯 השוואת כל המודלים — דוח מקיף\n\n")
    out.write(f"*נוצר ב-{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
    out.write("דוח זה מאמן ומשווה **17+ מודלים** על אותה הגדרת בעיה (forecast ללא leakage, "
              "פיצול כרונולוגי 80/20). לכל מודל ניתוח שגיאות מעמיק.\n\n")

    # ---------- Setup ----------
    out.write("## Setup\n\n")
    out.write(f"- **רשומות סה\"כ:** {n_total:,} | אחרי drop של חסרי-היסטוריה: {len(df):,}\n")
    out.write(f"- **חלוקה זמנית:** Train עד {cut.date()} ({len(train):,}) | "
              f"Test ({len(test):,})\n")
    out.write(f"- **Target:** `{TARGET}` (panel-adjusted: רייטינג / reception_pct)\n")
    out.write(f"- **Features:** {len(PRE_AIRING_FEATURES_NUM)} מספריים, "
              f"{len(PRE_AIRING_FEATURES_BOOL)} בוליאניים, "
              f"{len(PRE_AIRING_FEATURES_CAT)} קטגוריאליים\n\n")

    # ---------- Master comparison ----------
    out.write("## 1. טבלת השוואה כללית — כל המודלים\n\n")
    res_df = pd.DataFrame(results).T.round(4)
    res_df["זמן (שנ')"] = pd.Series(fit_times).round(1)
    res_df = res_df.sort_values("MAE")
    res_df.index.name = "מודל"
    out.write(md_table(res_df))
    out.write("\n")

    best_name = res_df.index[0]
    worst_baseline_mae = res_df.loc["00_Naive_GlobalMean", "MAE"]
    best_mae = res_df.loc[best_name, "MAE"]
    pct = (worst_baseline_mae - best_mae) / worst_baseline_mae * 100
    out.write(f"\n**🏆 המנצח: `{best_name}`** עם MAE={best_mae:.3f} "
              f"(שיפור של {pct:.1f}% מעל הנאיבי הגלובלי).\n\n")

    # ---------- Group view: family analysis ----------
    out.write("## 2. ניתוח לפי משפחת מודלים\n\n")
    families = {
        "Baseline / נאיבי": ["00_Naive_GlobalMean", "01_Slot_Mean"],
        "ליניאריים": ["02_Ridge", "03_Lasso", "04_ElasticNet",
                      "05_BayesianRidge", "06_HuberRegressor"],
        "מרחק / קרנל": ["07_KNN_k10", "08_SVR_RBF"],
        "עץ בודד": ["09_DecisionTree_d10"],
        "Tree ensembles": ["10_RandomForest_tuned", "11_ExtraTrees",
                           "12_GradientBoosting", "13_HistGradientBoosting",
                           "14_XGBoost", "15_LightGBM", "16_CatBoost"],
        "רשת נוירונים": ["17_MLP_64_32"],
        "Stacking": ["18_Stacking_Ridge_meta"],
    }
    fam_rows = []
    for fam, names in families.items():
        names = [n for n in names if n in results]
        if not names:
            continue
        maes = [results[n]["MAE"] for n in names]
        r2s  = [results[n]["R²"]  for n in names]
        best = min(names, key=lambda n: results[n]["MAE"])
        fam_rows.append({
            "משפחה": fam,
            "כמות מודלים": len(names),
            "MAE הטוב": min(maes),
            "MAE הגרוע": max(maes),
            "R² הטוב": max(r2s),
            "המוביל במשפחה": best,
        })
    fam_df = pd.DataFrame(fam_rows).set_index("משפחה")
    out.write(md_table(fam_df))
    out.write("\n")

    # ---------- Per-segment baseline data for cross-model comparison ----------
    test_with_period = test.copy()
    test_with_period["שבוע"] = pd.to_datetime(test_with_period["תאריך שידור"]).dt.to_period("W").astype(str)

    # ---------- Cross-model: MAE per day-of-week ----------
    out.write("## 3. שגיאה לפי יום שבוע — כל המודלים\n\n")
    out.write("השוואת MAE של כל מודל בכל יום שבוע. מודל טוב = MAE נמוך אחיד.\n\n")
    days_order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    dow_table = pd.DataFrame(index=days_order)
    for name in res_df.index:
        if name not in preds: continue
        seg = per_segment_mae(test, preds[name], "יום שידור")
        dow_table[name] = seg.reindex(days_order)["MAE"]
    out.write(md_table(dow_table.round(3)))
    out.write("\n\n")

    # ---------- Cross-model: MAE per day-part ----------
    out.write("## 4. שגיאה לפי חלקי-יום — כל המודלים\n\n")
    parts_order = sorted(test["חלקי-יום"].dropna().unique())
    dp_table = pd.DataFrame(index=parts_order)
    for name in res_df.index:
        if name not in preds: continue
        seg = per_segment_mae(test, preds[name], "חלקי-יום")
        dp_table[name] = seg.reindex(parts_order)["MAE"]
    out.write(md_table(dp_table.round(3)))
    out.write("\n\n")

    # ---------- Cross-model: MAE per event ----------
    out.write("## 5. שגיאה לפי אירוע מיוחד — כל המודלים\n\n")
    events = test["אירוע_מיוחד"].dropna().unique().tolist()
    if events:
        ev_table = pd.DataFrame(index=events)
        for name in res_df.index:
            if name not in preds: continue
            seg = per_segment_mae(test, preds[name], "אירוע_מיוחד")
            ev_table[name] = seg.reindex(events)["MAE"]
        ev_table = ev_table.sort_values(best_name, ascending=False)
        out.write(md_table(ev_table.round(3)))
        out.write("\n\n")

    # ---------- Per-model deep dive ----------
    out.write("## 6. ניתוח מעמיק לכל מודל\n\n")
    out.write("לכל מודל: MAE, איפה הוא טועה הכי הרבה (יום, חלק-יום, אירוע, תוכנית), ועשרת השגיאות הגדולות.\n\n")

    for name in res_df.index:
        if name not in preds:
            continue
        m = results[name]
        p = preds[name]
        out.write(f"### {name}\n\n")
        out.write(f"**ביצועים כלליים:** MAE={m['MAE']:.3f} | RMSE={m['RMSE']:.3f} | R²={m['R²']:.3f}\n\n")

        col_real = "ר' אמיתי"
        col_pred_mean = "ר' חזוי"

        # Worst day
        seg_d = per_segment_mae(test, p, "יום שידור").sort_values("MAE", ascending=False)
        out.write("**3 הימים הכי בעייתיים:**\n")
        for d, row in seg_d.head(3).iterrows():
            mae_v, n_v = row["MAE"], int(row["n"])
            real_v, pred_v = row[col_real], row[col_pred_mean]
            out.write(f"- {d}: MAE={mae_v:.3f} (n={n_v}, אמיתי={real_v:.2f}, חזוי={pred_v:.2f})\n")

        # Worst day-part
        seg_p = per_segment_mae(test, p, "חלקי-יום").sort_values("MAE", ascending=False)
        out.write("\n**3 חלקי-היום הכי בעייתיים:**\n")
        for dp, row in seg_p.head(3).iterrows():
            mae_v, n_v, bias_v = row["MAE"], int(row["n"]), row["הטיה"]
            out.write(f"- {dp}: MAE={mae_v:.3f} (n={n_v}, הטיה={bias_v:+.2f})\n")

        # Worst events
        if events:
            seg_e = per_segment_mae(test, p, "אירוע_מיוחד").sort_values("MAE", ascending=False)
            seg_e = seg_e[seg_e.index != "—"].head(3)
            if len(seg_e):
                out.write("\n**3 האירועים הכי בעייתיים:**\n")
                for ev, row in seg_e.iterrows():
                    mae_v, n_v = row["MAE"], int(row["n"])
                    real_v, pred_v = row[col_real], row[col_pred_mean]
                    out.write(f"- {ev}: MAE={mae_v:.3f} (n={n_v}, אמיתי={real_v:.2f}, חזוי={pred_v:.2f})\n")

        # Worst programs (only those with n >= 5 in test)
        seg_pr = per_segment_mae(test, p, "שם תוכנית_מקור")
        seg_pr = seg_pr[seg_pr["n"] >= 5].sort_values("MAE", ascending=False).head(5)
        if len(seg_pr):
            out.write("\n**5 התוכניות הכי בעייתיות (n≥5 ב-test):**\n")
            for prog, row in seg_pr.iterrows():
                mae_v, n_v, bias_v = row["MAE"], int(row["n"]), row["הטיה"]
                out.write(f"- {prog}: MAE={mae_v:.3f} (n={n_v}, הטיה={bias_v:+.2f})\n")

        # Top errors
        out.write("\n**5 השגיאות הגדולות ביותר (under-prediction — צפינו נמוך, היה גבוה):**\n\n")
        te = top_errors(test, p, n=5, mode="under")
        out.write(md_table(te, index=False))
        out.write("\n")
        out.write("\n**5 ה-over-prediction (צפינו גבוה, היה נמוך):**\n\n")
        te2 = top_errors(test, p, n=5, mode="over")
        out.write(md_table(te2, index=False))
        out.write("\n\n---\n\n")

    # ---------- Where do the BEST and WORST agree? ----------
    out.write("## 7. תוכניות-קושי משותף\n\n")
    out.write("האם יש תוכניות שכל המודלים מתקשים בהן (קושי אמיתי בדאטה)?\n")
    out.write("ואיזה תוכניות רק חלק מהמודלים מצליחים (= בחירת מודל משנה)?\n\n")

    # For each program (n>=5), compute mean MAE across all models
    prog_mae = {}
    for name in res_df.index:
        if name not in preds: continue
        seg = per_segment_mae(test, preds[name], "שם תוכנית_מקור")
        seg = seg[seg["n"] >= 5]
        for prog, row in seg.iterrows():
            prog_mae.setdefault(prog, []).append(row["MAE"])
    prog_summary = pd.DataFrame({
        "MAE ממוצע (כל המודלים)": {p: np.mean(v) for p, v in prog_mae.items()},
        "MAE טוב ביותר": {p: np.min(v) for p, v in prog_mae.items()},
        "MAE גרוע ביותר": {p: np.max(v) for p, v in prog_mae.items()},
        "פיזור (std)": {p: np.std(v) for p, v in prog_mae.items()},
        "n מודלים": {p: len(v) for p, v in prog_mae.items()},
    }).round(3)

    # Hard programs everyone fails on
    hardest = prog_summary.sort_values("MAE טוב ביותר", ascending=False).head(10)
    out.write("### 7.1 תוכניות שכולם נכשלים בהן (ה-MAE הטוב גבוה)\n\n")
    out.write("אלו תוכניות שאף מודל לא מצליח לחזות. כנראה רעש אמיתי בדאטה / drift.\n\n")
    out.write(md_table(hardest))
    out.write("\n")

    # Programs where model choice matters
    out.write("\n### 7.2 תוכניות שבחירת מודל משנה דרמטית (פיזור גבוה)\n\n")
    out.write("אלו תוכניות שמודל אחד מצליח בהן ואחר נכשל. הזדמנות ל-stacking או mixture.\n\n")
    spread = prog_summary.sort_values("פיזור (std)", ascending=False).head(10)
    out.write(md_table(spread))
    out.write("\n")

    # ---------- Methodological notes ----------
    out.write("\n## 8. הערות מתודולוגיות\n\n")
    out.write("- **כל המודלים אומנו על בדיוק אותו preprocessing pipeline** "
              "(StandardScaler לכמותיים, OneHot לקטגוריאליים) → השוואה הוגנת.\n")
    out.write("- **פיצול כרונולוגי**: train עד 2026-02 → test פברואר–אפריל 2026. "
              "כולל את אירועי שאגת הארי (פברואר–מרץ) והמתקפה האיראנית (מרץ).\n")
    out.write("- **Lag features ללא leakage**: כל ערך מחושב רק מהיסטוריה שקדמה לכל שורה.\n")
    out.write("- **תקרת ביצועים מוכרת**: אירועים בלתי-צפויים. לכן השונות ב-MAE בין המודלים "
              "באירועים גדולה הרבה יותר מאשר בשגרה.\n")
    out.write("- **למה MLP לא מנצח?** דאטה קטן (~10K) → רשתות נוירונים מועדות ל-overfit. "
              "Tree ensembles יציבים יותר על דאטה טבלאי קטן.\n")
    out.write("- **למה KNN חלש?** מרחק על one-hot של קטגוריות לא משמעותי "
              "(שבת ו-ראשון נמצאים באותה מרחק יחידתי). KNN זוהר על דאטה רציף.\n")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print(f"\n✓ Wrote {OUT_MD}")

    # ---------- Predictions XLSX ----------
    out_pred = test.copy()
    for name in res_df.index:
        if name in preds:
            out_pred[f"חזוי_{name}"] = np.round(preds[name], 3)
    keep_cols = ["שם תוכנית", "שם תוכנית_מקור", "יום שידור", "תאריך שידור",
                 "שעת התחלה", "חלקי-יום", "סטטוס תוכנית", "אירוע_מיוחד", TARGET] + \
                [f"חזוי_{n}" for n in res_df.index if n in preds]
    out_pred["תאריך שידור"] = pd.to_datetime(out_pred["תאריך שידור"]).dt.strftime("%Y-%m-%d")

    # Also write per-row MAE-rank: which model was best for each test row
    err_cols = []
    for name in preds:
        out_pred[f"_err_{name}"] = (out_pred[TARGET] - preds[name]).abs()
        err_cols.append(f"_err_{name}")
    out_pred["best_model_for_row"] = out_pred[err_cols].idxmin(axis=1).str.replace("_err_", "", regex=False)
    out_pred = out_pred.drop(columns=err_cols)
    keep_cols.append("best_model_for_row")

    # Write summary sheet too
    summary = pd.DataFrame(results).T.round(4)
    summary["זמן (שנ')"] = pd.Series(fit_times).round(1)
    summary = summary.sort_values("MAE")
    summary.index.name = "מודל"

    with pd.ExcelWriter(OUT_PRED_XLSX, engine="openpyxl") as xw:
        out_pred[keep_cols].to_excel(xw, sheet_name="חיזויים", index=False)
        summary.to_excel(xw, sheet_name="סיכום מטריקות")
        # Per-day, per-part MAE tables
        dow_table.round(3).to_excel(xw, sheet_name="MAE לפי יום")
        dp_table.round(3).to_excel(xw, sheet_name="MAE לפי חלק יום")
        if events:
            ev_table.round(3).to_excel(xw, sheet_name="MAE לפי אירוע")
        prog_summary.round(3).to_excel(xw, sheet_name="MAE לפי תוכנית")

    print(f"✓ Wrote {OUT_PRED_XLSX}")

    # ---------- Console summary ----------
    print("\n" + "=" * 70)
    print("Final ranking (sorted by MAE):")
    print("=" * 70)
    for name, row in res_df.iterrows():
        print(f"  {name:32s}  MAE={row['MAE']:.3f}  "
              f"RMSE={row['RMSE']:.3f}  R²={row['R²']:.3f}")


if __name__ == "__main__":
    main()
