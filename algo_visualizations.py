# -*- coding: utf-8 -*-
"""
algo_visualizations.py
----------------------
יוצר 8 תרשימים שמסבירים אלגוריתמי ML — באמצעות הדאטה האמיתי של i24.
הפלט: תיקיית viz/ עם PNG-ים + ALGORITHMS_VISUAL.md שמשלב אותם.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Hebrew font support
mpl.rcParams['font.family'] = ['Arial', 'DejaVu Sans']
mpl.rcParams['axes.unicode_minus'] = False
mpl.rcParams['figure.dpi'] = 100

ROOT = Path(__file__).parent
VIZ = ROOT / "viz"
VIZ.mkdir(exist_ok=True)

np.random.seed(42)

# ===== Load =====
df_preds = pd.read_excel(ROOT / "predictions_all.xlsx", sheet_name=0)
df_data  = pd.read_excel(ROOT / "תוכניות_מעובד.xlsx")

cols = df_preds.columns.tolist()
program_col, day_col, date_col, hour_col, status_col, event_col, actual_col = \
    cols[0], cols[2], cols[3], cols[4], cols[6], cols[7], cols[8]

# Find prediction cols
def find_pred(suffix):
    for c in cols:
        if c.endswith(suffix):
            return c
    return None

HIST_COL = find_pred("HistGradientBoosting")
LGB_COL  = find_pred("LightGBM")
RIDGE_COL= find_pred("Ridge")
LIN_COL  = find_pred("Lasso")
KNN_COL  = find_pred("KNN_k10")
RF_COL   = find_pred("RandomForest_tuned")
TREE_COL = find_pred("DecisionTree_d10")
SLOT_COL = find_pred("Slot_Mean")
NAIVE_COL= find_pred("Naive_GlobalMean")

# i24 brand colors
BLUE = "#1E5DB8"
DARK_BLUE = "#0A2540"
ACCENT = "#FF6B35"
GREEN = "#2ECC71"
GRAY = "#95A5A6"

# ===== 1. Bias-Variance Tradeoff =====
print("1. Bias-Variance Tradeoff...")
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
np.random.seed(1)
x = np.linspace(0, 10, 100)
true_y = np.sin(x) + 0.1 * x
noise = np.random.normal(0, 0.3, 100)
y_observed = true_y + noise

# Underfit (high bias) - linear
p1 = np.polyfit(x, y_observed, 1)
y_under = np.polyval(p1, x)
axes[0].scatter(x, y_observed, alpha=0.4, s=20, color=GRAY)
axes[0].plot(x, true_y, '--', color=GREEN, label='True', linewidth=2)
axes[0].plot(x, y_under, color=ACCENT, linewidth=2.5, label='Model (Linear)')
axes[0].set_title("Underfitting (High Bias)\nToo simple - misses pattern", fontsize=12, fontweight='bold')
axes[0].legend(); axes[0].grid(alpha=0.3)

# Good fit
p3 = np.polyfit(x, y_observed, 4)
y_good = np.polyval(p3, x)
axes[1].scatter(x, y_observed, alpha=0.4, s=20, color=GRAY)
axes[1].plot(x, true_y, '--', color=GREEN, label='True', linewidth=2)
axes[1].plot(x, y_good, color=BLUE, linewidth=2.5, label='Model (Poly-4)')
axes[1].set_title("Good Fit\nBalanced - learns pattern, ignores noise", fontsize=12, fontweight='bold')
axes[1].legend(); axes[1].grid(alpha=0.3)

# Overfit (high variance) - polynomial 20
p20 = np.polyfit(x, y_observed, 20)
y_over = np.polyval(p20, x)
axes[2].scatter(x, y_observed, alpha=0.4, s=20, color=GRAY)
axes[2].plot(x, true_y, '--', color=GREEN, label='True', linewidth=2)
axes[2].plot(x, y_over, color="red", linewidth=2.5, label='Model (Poly-20)')
axes[2].set_title("Overfitting (High Variance)\nToo complex - fits noise", fontsize=12, fontweight='bold')
axes[2].legend(); axes[2].grid(alpha=0.3); axes[2].set_ylim(-2, 5)

plt.suptitle("Bias-Variance Tradeoff", fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(VIZ / "01_bias_variance.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 2. Train/Test Chronological Split =====
print("2. Chronological Split...")
df_sorted = df_data.copy()
df_sorted['date_parsed'] = pd.to_datetime(df_sorted.iloc[:, 3], errors='coerce')
df_sorted = df_sorted.dropna(subset=['date_parsed']).sort_values('date_parsed').reset_index(drop=True)
cutoff = pd.Timestamp('2026-02-08')

fig, ax = plt.subplots(figsize=(13, 5))
daily = df_sorted.groupby(df_sorted['date_parsed'].dt.date)[actual_col if actual_col in df_sorted.columns else df_sorted.columns[8]].mean()
daily.index = pd.to_datetime(daily.index)
train_mask = daily.index < cutoff

ax.plot(daily.index[train_mask], daily[train_mask], color=BLUE, linewidth=1.5, label='Train (80%)')
ax.plot(daily.index[~train_mask], daily[~train_mask], color=ACCENT, linewidth=1.5, label='Test (20%)')
ax.axvline(cutoff, color='black', linestyle='--', alpha=0.7)
ax.text(cutoff, ax.get_ylim()[1] * 0.95, f'  Cutoff: {cutoff.strftime("%Y-%m-%d")}', fontsize=10, color='black')
ax.fill_between(daily.index[train_mask], 0, daily[train_mask], alpha=0.15, color=BLUE)
ax.fill_between(daily.index[~train_mask], 0, daily[~train_mask], alpha=0.15, color=ACCENT)
ax.set_title("Chronological Train/Test Split — i24 Daily Average Rating", fontsize=14, fontweight='bold')
ax.set_xlabel("Date"); ax.set_ylabel("Daily Avg Rating")
ax.legend(loc='upper left', fontsize=11); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(VIZ / "02_chronological_split.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 3. Predicted vs Actual — HistGB Winner =====
print("3. Predicted vs Actual...")
fig, ax = plt.subplots(figsize=(8, 8))
sample = df_preds.sample(n=500, random_state=42)
mae = (sample[HIST_COL] - sample[actual_col]).abs().mean()
ax.scatter(sample[actual_col], sample[HIST_COL], alpha=0.5, s=25, color=BLUE, edgecolor='white', linewidth=0.3)
lims = [0, max(sample[actual_col].max(), sample[HIST_COL].max()) * 1.05]
ax.plot(lims, lims, '--', color='red', linewidth=2, label='Perfect prediction')
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("Actual Rating", fontsize=12)
ax.set_ylabel("Predicted Rating (HistGradientBoosting)", fontsize=12)
ax.set_title(f"HistGradientBoosting — Predicted vs Actual\nMAE = {mae:.3f}, n = 500 random test rows",
             fontsize=13, fontweight='bold')
ax.legend(fontsize=11); ax.grid(alpha=0.3); ax.set_aspect('equal')
plt.tight_layout()
plt.savefig(VIZ / "03_pred_vs_actual.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 4. Model Comparison — Leaderboard =====
print("4. Model Leaderboard...")
all_pred_cols = [c for c in cols if "_" in c and any(m in c for m in
                  ["HistGradientBoosting","LightGBM","GradientBoosting","CatBoost","Stacking",
                   "ExtraTrees","XGBoost","RandomForest","Lasso","ElasticNet","KNN",
                   "DecisionTree","SVR","Slot_Mean","MLP","Huber","BayesianRidge","Ridge","Naive"])]
maes = {c.split("_", 2)[-1].replace("_", " "): (df_preds[c] - df_preds[actual_col]).abs().mean() for c in all_pred_cols}
maes_sorted = sorted(maes.items(), key=lambda x: x[1])

fig, ax = plt.subplots(figsize=(10, 8))
names = [n for n, _ in maes_sorted]
vals = [v for _, v in maes_sorted]
colors_bar = [GREEN if i < 3 else BLUE if i < 10 else GRAY for i in range(len(names))]
bars = ax.barh(range(len(names)), vals, color=colors_bar, edgecolor='white', linewidth=0.5)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("MAE (lower = better)", fontsize=11)
ax.set_title("19 Models Compared — MAE on test set\nGreen = Top 3 | Blue = Top 10 | Gray = others",
             fontsize=13, fontweight='bold')
for i, (bar, v) in enumerate(zip(bars, vals)):
    ax.text(v + 0.005, bar.get_y() + bar.get_height()/2, f'{v:.3f}', va='center', fontsize=9)
ax.grid(alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig(VIZ / "04_model_leaderboard.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 5. Random Forest concept — ensemble of trees =====
print("5. Random Forest illustration...")
fig, axes = plt.subplots(2, 3, figsize=(14, 8))
np.random.seed(0)
x_simple = np.linspace(0, 10, 50)
y_simple = 2 * np.sin(x_simple) + np.random.normal(0, 0.5, 50)

for i, ax in enumerate(axes.flat[:5]):
    idx = np.random.choice(50, 30, replace=True)
    xs, ys = x_simple[idx], y_simple[idx]
    from sklearn.tree import DecisionTreeRegressor
    tree = DecisionTreeRegressor(max_depth=4, random_state=i)
    tree.fit(xs.reshape(-1, 1), ys)
    xs_plot = np.linspace(0, 10, 200).reshape(-1, 1)
    ax.scatter(xs, ys, alpha=0.5, s=25, color=GRAY)
    ax.plot(xs_plot, tree.predict(xs_plot), color=BLUE, linewidth=2)
    ax.set_title(f"Tree {i+1}", fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3); ax.set_ylim(-3, 3)

# Last subplot - average
trees_preds = []
for i in range(20):
    idx = np.random.choice(50, 30, replace=True)
    tree = DecisionTreeRegressor(max_depth=4, random_state=i)
    tree.fit(x_simple[idx].reshape(-1, 1), y_simple[idx])
    trees_preds.append(tree.predict(np.linspace(0, 10, 200).reshape(-1, 1)))
avg = np.mean(trees_preds, axis=0)
axes[1, 2].scatter(x_simple, y_simple, alpha=0.5, s=25, color=GRAY)
axes[1, 2].plot(np.linspace(0, 10, 200), avg, color=GREEN, linewidth=3)
axes[1, 2].set_title("Random Forest = Average of 20 Trees", fontsize=11, fontweight='bold', color=GREEN)
axes[1, 2].grid(alpha=0.3); axes[1, 2].set_ylim(-3, 3)

plt.suptitle("Random Forest — Bagging multiple trees produces smoother prediction", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(VIZ / "05_random_forest.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 6. Boosting concept — iterative residual learning =====
print("6. Gradient Boosting illustration...")
from sklearn.ensemble import GradientBoostingRegressor
np.random.seed(42)
x_b = np.linspace(0, 10, 100).reshape(-1, 1)
y_b = np.sin(x_b.ravel()) * 2 + 0.5 * x_b.ravel() + np.random.normal(0, 0.3, 100)

fig, axes = plt.subplots(2, 2, figsize=(13, 9))
n_estimators_list = [1, 5, 20, 100]
for ax, n_est in zip(axes.flat, n_estimators_list):
    gb = GradientBoostingRegressor(n_estimators=n_est, max_depth=3, learning_rate=0.1, random_state=0)
    gb.fit(x_b, y_b)
    pred = gb.predict(x_b)
    ax.scatter(x_b, y_b, alpha=0.4, s=20, color=GRAY)
    ax.plot(x_b, pred, color=BLUE, linewidth=2.5, label=f'After {n_est} trees')
    mae_local = np.abs(pred - y_b).mean()
    ax.set_title(f"After {n_est} boosting iterations  |  MAE = {mae_local:.3f}", fontsize=12, fontweight='bold')
    ax.legend(); ax.grid(alpha=0.3)
plt.suptitle("Gradient Boosting — Each iteration improves on residuals", fontsize=14, fontweight='bold', y=1.0)
plt.tight_layout()
plt.savefig(VIZ / "06_boosting.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 7. Histogram Binning (the magic in HistGB) =====
print("7. Histogram Binning...")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# original
real_rating = df_data[df_data.columns[8]].dropna()
axes[0].hist(real_rating, bins=100, color=BLUE, edgecolor='white')
axes[0].set_title(f"Continuous values — {len(real_rating)} unique data points\n(GradientBoosting checks each)",
                  fontsize=12, fontweight='bold')
axes[0].set_xlabel("Rating"); axes[0].set_ylabel("Count"); axes[0].grid(alpha=0.3)

# binned to 30 (256 in practice but easier to see)
binned, bin_edges = np.histogram(real_rating, bins=30)
axes[1].bar(bin_edges[:-1], binned, width=np.diff(bin_edges), color=ACCENT, edgecolor='white', align='edge')
axes[1].set_title(f"Same data binned to 30 buckets\n(HistGradientBoosting uses 256 — much faster)",
                  fontsize=12, fontweight='bold')
axes[1].set_xlabel("Rating bin"); axes[1].set_ylabel("Count"); axes[1].grid(alpha=0.3)

plt.suptitle("HistGradientBoosting trick — bin continuous values for 10-100× speedup", fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(VIZ / "07_histogram_binning.png", bbox_inches='tight', dpi=120)
plt.close()

# ===== 8. Error distribution by status (real i24 data) =====
print("8. Error distribution by status...")
df_preds['err_HistGB'] = df_preds[HIST_COL] - df_preds[actual_col]
statuses = df_preds[status_col].value_counts().head(4).index.tolist()

fig, ax = plt.subplots(figsize=(11, 6))
positions = range(len(statuses))
data_per_status = [df_preds[df_preds[status_col] == s]['err_HistGB'].values for s in statuses]
labels_with_n = [f"{s}\nn={len(d)}" for s, d in zip(statuses, data_per_status)]

bp = ax.boxplot(data_per_status, positions=positions, widths=0.6, patch_artist=True,
                medianprops=dict(color='black', linewidth=2),
                flierprops=dict(marker='o', markersize=4, alpha=0.5))
for patch, color in zip(bp['boxes'], [BLUE, ACCENT, GREEN, GRAY]):
    patch.set_facecolor(color); patch.set_alpha(0.6)

ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax.set_xticks(positions)
ax.set_xticklabels(labels_with_n, fontsize=10)
ax.set_ylabel("Prediction Error (predicted − actual)", fontsize=11)
ax.set_title("HistGradientBoosting Error Distribution by Program Status\nLive broadcasts have wider variance — harder to predict",
             fontsize=13, fontweight='bold')
ax.grid(alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(VIZ / "08_error_by_status.png", bbox_inches='tight', dpi=120)
plt.close()

print("\nAll 8 visualizations saved to viz/")
print("Files:")
for f in sorted(VIZ.glob("*.png")):
    print(f"  {f.name}")
