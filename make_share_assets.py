# -*- coding: utf-8 -*-
"""
make_share_assets.py
--------------------
מייצר את נכסי השיתוף של האתר:
  docs/og-cover.png   — תמונת Open Graph 1200x630 (LinkedIn/WhatsApp/Twitter)
  docs/icon-180.png   — apple-touch-icon
  docs/favicon-32.png — fallback ל-favicon (דפדפנים ישנים)
RTL בעברית מטופל ע"י python-bidi (matplotlib לא מסדר RTL).
"""
import io
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from bidi.algorithm import get_display
    def rtl(s):
        return get_display(str(s))
except ImportError:
    def rtl(s):
        return str(s)

mpl.rcParams['font.family'] = ['Arial', 'DejaVu Sans']
mpl.rcParams['axes.unicode_minus'] = False

DOCS = Path(__file__).parent / "docs"

NAVY = "#0A2540"
BLUE = "#1E5DB8"
ACCENT = "#FF6B35"


def gradient_bg(ax, w, h):
    """רקע גרדיאנט אלכסוני נייבי→כחול + זוהר כתום."""
    cmap = LinearSegmentedColormap.from_list("brand", [NAVY, BLUE])
    yy, xx = np.mgrid[0:h, 0:w]
    grad = (0.65 * xx / w + 0.35 * (1 - yy / h))
    ax.imshow(grad, extent=[0, w, 0, h], origin='upper',
              cmap=cmap, aspect='auto', zorder=0)
    glow = np.exp(-(((xx - w * 0.16) ** 2 + (yy - h * 0.9) ** 2)
                    / (2 * (w * 0.30) ** 2)))
    ax.imshow(glow, extent=[0, w, 0, h], origin='upper',
              cmap=LinearSegmentedColormap.from_list(
                  "glow", [(0, 0, 0, 0), ACCENT]),
              alpha=0.30, aspect='auto', zorder=1)


def chip(ax, x, y, text, fs=20):
    t = ax.text(x, y, text, fontsize=fs, fontweight='bold',
                color='#0A2540', ha='center', va='center', zorder=4,
                bbox=dict(boxstyle='round,pad=0.55', fc='white',
                          ec='none'))
    return t


# ===== OG cover 1200x630 =====
W, H = 1200, 630
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
gradient_bg(ax, W, H)

ax.text(W - 70, H - 70, "i24 NEWS  ·  Data Science Portfolio",
        fontsize=20, color='#9DB8D9', ha='right', va='top',
        fontweight='bold', zorder=4)

ax.text(W - 70, H - 175, rtl("מקסם למדע"), fontsize=86,
        color='white', ha='right', va='top', fontweight='bold', zorder=4)
ax.text(W - 70, H - 285, rtl("חיזוי רייטינג טלוויזיה — מ-EDA למוצר חי באוויר"),
        fontsize=30, color='#CFE0F5', ha='right', va='top', zorder=4)

chip(ax, W - 150, 150, "MAE 0.263")
chip(ax, W - 360, 150, "R² 0.603")
chip(ax, W - 560, 150, rtl("19 מודלים"))

ax.text(70, 55, "datascienceoritalma.github.io/i24-ratings-forecast",
        fontsize=19, color='#9DB8D9', ha='left', va='center', zorder=4)
ax.add_patch(FancyBboxPatch((W - 250, H - 70), 180, 8,
             boxstyle='round,pad=0', fc=ACCENT, ec='none', zorder=4))

fig.savefig(DOCS / "og-cover.png", dpi=100)
plt.close(fig)


# ===== icons (i24 monogram) =====
def make_icon(size, fname):
    fig = plt.figure(figsize=(size / 100, size / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 64); ax.set_ylim(0, 64); ax.axis('off')
    cmap = LinearSegmentedColormap.from_list("brand", [NAVY, BLUE])
    yy, xx = np.mgrid[0:64, 0:64]
    ax.imshow((xx + (63 - yy)) / 126, extent=[0, 64, 0, 64],
              origin='upper', cmap=cmap, aspect='auto')
    ax.add_patch(FancyBboxPatch((2, 2), 60, 60,
                 boxstyle='round,pad=0,rounding_size=14',
                 fc='none', ec='none'))
    ax.add_patch(plt.Circle((49, 49), 6, color=ACCENT, zorder=3))
    ax.text(32, 30, "i24", fontsize=size * 0.30, fontweight='bold',
            color='white', ha='center', va='center', zorder=3)
    fig.savefig(DOCS / fname, dpi=100, transparent=True)
    plt.close(fig)


make_icon(180, "icon-180.png")
make_icon(32, "favicon-32.png")

print("Saved: docs/og-cover.png, docs/icon-180.png, docs/favicon-32.png")
