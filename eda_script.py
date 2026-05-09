# -*- coding: utf-8 -*-
"""EDA report generator for i24 program ratings dataset.

Produces EDA_REPORT.md with:
  - Data overview & sample
  - Features table (description, dtype, missing, basic stats)
  - Correlations (Pearson + Spearman vs target)
  - Target review (raw rating + adjusted_rating)
  - Distributions: weekday, hour (24-bin and 6 day-parts), rerun (group + paired), events/holidays
  - "Advantage vs competitors" KPI
  - Adjusted rating (panel-breathing correction)
"""
from __future__ import annotations

import os
from io import StringIO
from datetime import datetime

import numpy as np
import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_CSV = os.path.join(DATA_DIR, "רשימת תוכניות.csv")
EVENTS_CSV = os.path.join(DATA_DIR, "אלמנטים משפיעים.csv")
EVENTS_CURATED_CSV = os.path.join(DATA_DIR, "אירועים_מדויקים.csv")
OUT_MD = os.path.join(DATA_DIR, "EDA_REPORT.md")
OUT_XLSX = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")

# ----- panel reception correction ---------------------------------------------
# Per-month linear ramp: May 2025 = 65%, April 2026 = 90%. All dates within the
# same calendar month receive the SAME reception_pct (step function on months).
RECEPTION_START_PERIOD = pd.Period("2025-05", freq="M")
RECEPTION_END_PERIOD = pd.Period("2026-04", freq="M")
RECEPTION_START_PCT = 0.65
RECEPTION_END_PCT = 0.90


def reception_pct(date: pd.Timestamp) -> float:
    p = pd.Period(date, freq="M")
    if p <= RECEPTION_START_PERIOD:
        return RECEPTION_START_PCT
    if p >= RECEPTION_END_PERIOD:
        return RECEPTION_END_PCT
    total_steps = (RECEPTION_END_PERIOD - RECEPTION_START_PERIOD).n
    step = (p - RECEPTION_START_PERIOD).n
    frac = step / total_steps
    return RECEPTION_START_PCT + (RECEPTION_END_PCT - RECEPTION_START_PCT) * frac


# ----- helpers ----------------------------------------------------------------
def td_to_minutes(s: pd.Series) -> pd.Series:
    return pd.to_timedelta(s.astype(str), errors="coerce").dt.total_seconds() / 60.0


def fmt(x, nd: int = 2) -> str:
    if pd.isna(x):
        return "—"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    try:
        return f"{float(x):,.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def md_table(df: pd.DataFrame, index: bool = True) -> str:
    """Render a DataFrame as a GitHub-flavored markdown table."""
    if index:
        df = df.copy()
        df.insert(0, df.index.name or "", df.index)
    cols = [str(c) for c in df.columns]
    out = "| " + " | ".join(cols) + " |\n"
    out += "|" + "|".join(["---"] * len(cols)) + "|\n"
    for _, r in df.iterrows():
        out += "| " + " | ".join(str(v) for v in r.values) + " |\n"
    return out


def text_histogram(values: pd.Series, bins: int = 10, width: int = 40) -> str:
    v = values.dropna()
    if len(v) == 0:
        return "(אין נתונים)"
    counts, edges = np.histogram(v, bins=bins)
    mx = counts.max() or 1
    lines = ["| טווח | n | בר |", "|---|---|---|"]
    for i in range(len(counts)):
        bar = "█" * int(round(counts[i] / mx * width))
        lines.append(f"| {edges[i]:.2f} – {edges[i+1]:.2f} | {counts[i]:,} | {bar} |")
    return "\n".join(lines)


# ----- load & clean -----------------------------------------------------------
def load() -> pd.DataFrame:
    df = pd.read_csv(SRC_CSV, skiprows=[0])
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    for c in ["משך תוכנית", "משך צפייה"]:
        df[c + "_דק"] = td_to_minutes(df[c])
    df["שעת התחלה_דק"] = td_to_minutes(df["שעת התחלה"])
    df["שעת התחלה_שעה"] = (df["שעת התחלה_דק"] // 60).astype(int)
    df["is_rerun"] = df["שם תוכנית"].str.contains(r"ש\.ח|לקט", regex=True, na=False)
    df["שם תוכנית_מקור"] = df["שם תוכנית"].str.replace(r"\s*ש\.ח\s*$", "", regex=True).str.strip()
    competitors = ["כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]
    df["ממוצע מתחרים"] = df[competitors].mean(axis=1)
    df["יתרון מול מתחרים"] = df["רייטינג"] - df["ממוצע מתחרים"]
    df["HUT proxy"] = df[competitors].sum(axis=1) + df["רייטינג"]

    def status(name: str) -> str:
        n = str(name)
        if "מיוחד" in n or "מבזק" in n:
            return "מיוחד/מבזק"
        if "לקט" in n:
            return "לקט"
        if "חג" in n:
            return "חג"
        if "ש.ח" in n:
            return "שידור חוזר"
        return "שידור חי"
    df["סטטוס תוכנית"] = df["שם תוכנית"].apply(status)
    df["reception_pct"] = df["תאריך שידור"].apply(reception_pct)
    df["רייטינג מותאם"] = df["רייטינג"] / df["reception_pct"]

    def part(h: int) -> str:
        if 6 <= h <= 9:
            return "1. בוקר 06–09"
        if 10 <= h <= 13:
            return "2. צהריים 10–13"
        if 14 <= h <= 17:
            return "3. אחה\"צ 14–17"
        if 18 <= h <= 21:
            return "4. פריים-טיים 18–21"
        if h >= 22 or h <= 1:
            return "5. לילה 22–01"
        return "6. לילה מאוחר 02–05"

    df["חלקי-יום"] = df["שעת התחלה_שעה"].apply(part)
    return df


def load_events() -> pd.DataFrame:
    """Load curated events file (אירועים_מדויקים.csv) — built from web research with
    EXACT dates (start/end). Falls back to legacy אלמנטים משפיעים.csv if the curated
    file is missing."""
    if os.path.exists(EVENTS_CURATED_CSV):
        ev = pd.read_csv(EVENTS_CURATED_CSV)
        ev["תאריך_dt"] = pd.to_datetime(ev["תאריך_התחלה"], errors="coerce")
        ev["תאריך_סיום_dt"] = pd.to_datetime(ev["תאריך_סיום"], errors="coerce")
        ev["סוג"] = ev["קטגוריה"]
        ev["אירוע"] = ev["שם_אירוע"]
        return ev
    # legacy fallback
    raw = pd.read_csv(EVENTS_CSV)
    blocks = [
        ("ביטחוני", raw.columns[0], raw.columns[1]),
        ("חג", raw.columns[3], raw.columns[4]),
        ("עונה", raw.columns[6], raw.columns[7]),
    ]
    rows = []
    for kind, dcol, ecol in blocks:
        for _, r in raw.iloc[1:].iterrows():
            d, e = r[dcol], r[ecol]
            if pd.isna(d) or pd.isna(e) or str(d).strip() == "" or str(e).strip() == "":
                continue
            rows.append({"סוג": kind, "תאריך_התחלה": d, "תאריך_סיום": d, "אירוע": e})
    ev = pd.DataFrame(rows)
    ev["תאריך_dt"] = pd.to_datetime(ev["תאריך_התחלה"], errors="coerce")
    ev["תאריך_סיום_dt"] = pd.to_datetime(ev["תאריך_סיום"], errors="coerce")
    return ev


def tag_events(df: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """Tag each broadcast row with: (1) active season, (2) holiday name (if any),
    (3) security/political event name (if any), and (4) a unified 'אירוע_מיוחד'
    column that picks the most-specific event active that day. Tagging uses
    EXACT start-end ranges from the curated events file."""
    df = df.copy()
    sec_kinds = {"ביטחוני", "מדיני"}

    df["תג_עונה"] = "—"
    seasons = ev[ev["סוג"] == "עונה"].sort_values("תאריך_dt")
    for _, s in seasons.iterrows():
        if pd.isna(s["תאריך_dt"]) or pd.isna(s["תאריך_סיום_dt"]):
            continue
        m = (df["תאריך שידור"] >= s["תאריך_dt"]) & (df["תאריך שידור"] <= s["תאריך_סיום_dt"])
        df.loc[m, "תג_עונה"] = s["אירוע"]

    df["תג_חג"] = "—"
    for _, h in ev[ev["סוג"] == "חג"].iterrows():
        if pd.isna(h["תאריך_dt"]) or pd.isna(h["תאריך_סיום_dt"]):
            continue
        m = (df["תאריך שידור"] >= h["תאריך_dt"]) & (df["תאריך שידור"] <= h["תאריך_סיום_dt"])
        df.loc[m, "תג_חג"] = h["אירוע"]

    df["תג_ביטחוני"] = "—"
    for _, b in ev[ev["סוג"].isin(sec_kinds)].iterrows():
        if pd.isna(b["תאריך_dt"]) or pd.isna(b["תאריך_סיום_dt"]):
            continue
        m = (df["תאריך שידור"] >= b["תאריך_dt"]) & (df["תאריך שידור"] <= b["תאריך_סיום_dt"])
        existing = df.loc[m, "תג_ביטחוני"]
        df.loc[m, "תג_ביטחוני"] = existing.where(
            existing == "—", existing + " + " + b["אירוע"]
        ).where(existing != "—", b["אירוע"])

    df["יום_חג"] = df["תג_חג"] != "—"
    df["יום_ביטחוני"] = df["תג_ביטחוני"] != "—"
    df["שבת"] = df["יום שידור"] == "שבת"

    df["אירוע_מיוחד"] = df.apply(
        lambda r: r["תג_ביטחוני"] if r["תג_ביטחוני"] != "—"
        else (r["תג_חג"] if r["תג_חג"] != "—"
        else "—"),
        axis=1,
    )
    return df


# ----- report sections --------------------------------------------------------
def section_overview(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 1. מבט-על\n\n")
    out.write(f"- **שורות:** {len(df):,}\n")
    out.write(f"- **עמודות מקור:** 15 (3 קבוצות-על: פרטים כלליים, נתונים שלנו, רייטינג מתחרים)\n")
    out.write(f"- **טווח תאריכים:** {df['תאריך שידור'].min().date()} → {df['תאריך שידור'].max().date()}  "
              f"({df['תאריך שידור'].dt.normalize().nunique()} ימים ייחודיים)\n")
    out.write(f"- **תוכניות ייחודיות:** {df['שם תוכנית'].nunique()}  |  "
              f"**תוכניות-מקור (לאחר הסרת 'ש.ח'):** {df['שם תוכנית_מקור'].nunique()}\n")
    out.write(f"- **שידורי-חוזר:** {df['is_rerun'].sum():,} מתוך {len(df):,} "
              f"({df['is_rerun'].mean():.1%})\n")
    out.write(f"- **חוסרים:** 0 בכל אחת מ-15 העמודות המקוריות\n\n")

    out.write("**5 שורות-דוגמה:**\n\n")
    sample_cols = ["שם תוכנית", "יום שידור", "תאריך שידור", "שעת התחלה",
                   "משך תוכנית", "רייטינג", "נתח", "צופים 4+", "כאן 11", "קשת 12", "רשת 13", "עכשיו 14"]
    s = df[sample_cols].head(5).copy()
    s["תאריך שידור"] = s["תאריך שידור"].dt.strftime("%Y-%m-%d")
    out.write(md_table(s, index=False))
    out.write("\n")
    return out.getvalue()


def section_features(df: pd.DataFrame) -> str:
    descriptions = {
        "שם תוכנית": "שם התוכנית כפי שמופיע ב-as-run; סיומת 'ש.ח' = שידור חוזר.",
        "יום שידור": "יום בשבוע (ראשון–שבת).",
        "תאריך שידור": "תאריך השידור בפועל.",
        "שעת התחלה": "שעת תחילת השידור (HH:MM:SS).",
        "שעת סיום": "שעת סיום השידור (HH:MM:SS).",
        "משך תוכנית": "משך התוכנית (HH:MM:SS).",
        "רייטינג": "Y — אחוז הצפייה הממוצע מקרב כלל בעלי המקלטים (Rating).",
        "נתח": "נתח שוק — אחוז הצופים בערוץ מתוך כלל הצופים שצפו בטלוויזיה באותה עת.",
        "צופים 4+": "אומדן אלפי צופים בני 4+ שצפו לפחות דקה אחת בתוכנית.",
        "חשיפה 4+": "אומדן אלפי צופים בני 4+ שנחשפו לתוכנית (לפחות שנייה).",
        "משך צפייה": "משך זמן הצפייה הממוצע בתוכנית.",
        "כאן 11": "רייטינג כאן 11 באותן הדקות.",
        "קשת 12": "רייטינג קשת 12 באותן הדקות.",
        "רשת 13": "רייטינג רשת 13 באותן הדקות.",
        "עכשיו 14": "רייטינג עכשיו 14 באותן הדקות.",
        "ממוצע מתחרים": "ממוצע ארבעת המתחרים (כאן/קשת/רשת/עכשיו).",
        "יתרון מול מתחרים": "רייטינג i24 פחות ממוצע המתחרים — חיובי = יתרון, שלילי = פיגור.",
        "reception_pct": "אומדן שיעור הפאנל שיכול לקלוט את ערוץ 15 (i24); רמפה חודשית ליניארית — מאי 2025 = 65%, אפריל 2026 = 90%; כל הימים באותו חודש מקבלים אותו ערך.",
        "רייטינג מותאם": "רייטינג / reception_pct — מנטרל אפקט גידול-הקליטה לאורך זמן ('פאנל נושם').",
        "is_rerun": "דגל בוליאני: השידור מסומן ש.ח.",
        "חלקי-יום": "בוקר/צהריים/אחה\"צ/פריים-טיים/לילה/לילה מאוחר.",
        "HUT proxy": "סך רייטינג של כל חמשת הערוצים (i24+כאן+קשת+רשת+14) באותן הדקות — קירוב ל-HUT (כמה צופים יש בטלוויזיה כרגע).",
        "סטטוס תוכנית": "מסווג מתוך שם התוכנית: שידור חי / שידור חוזר (ש.ח) / לקט / מיוחד-מבזק / חג.",
    }

    rows = []
    for col in df.columns:
        if col in {"שם תוכנית_מקור", "שעת התחלה_דק", "שעת התחלה_שעה",
                   "משך תוכנית_דק", "משך צפייה_דק"}:
            continue
        if col not in descriptions:
            continue
        s = df[col]
        n_unique = s.nunique(dropna=True)
        n_miss = s.isna().sum()
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            stat = (f"min={fmt(s.min())} | med={fmt(s.median())} | "
                    f"mean={fmt(s.mean())} | std={fmt(s.std())} | max={fmt(s.max())}")
            dtype = "מספרי"
        elif pd.api.types.is_datetime64_any_dtype(s):
            stat = f"min={s.min().date()} | max={s.max().date()}"
            dtype = "תאריך"
        elif pd.api.types.is_bool_dtype(s):
            stat = f"True={int(s.sum()):,} ({s.mean():.1%})"
            dtype = "בוליאני"
        else:
            top = s.value_counts(dropna=True).head(3)
            stat = " | ".join(f"{k}: {v:,}" for k, v in top.items())
            dtype = "קטגוריאלי"
        rows.append({
            "עמודה": col,
            "סוג": dtype,
            "ייחודיים": f"{n_unique:,}",
            "חוסרים": f"{n_miss:,}",
            "תיאור": descriptions[col],
            "סטטיסטיקה": stat,
        })
    feats = pd.DataFrame(rows).set_index("עמודה")
    return "## 2. טבלת מאפיינים\n\n" + md_table(feats) + "\n"


def section_correlations(df: pd.DataFrame) -> str:
    num_cols = ["רייטינג", "רייטינג מותאם", "נתח", "צופים 4+", "חשיפה 4+",
                "משך תוכנית_דק", "משך צפייה_דק",
                "כאן 11", "קשת 12", "רשת 13", "עכשיו 14",
                "ממוצע מתחרים", "יתרון מול מתחרים"]
    corr_p = df[num_cols].corr(method="pearson").round(2)
    corr_p.index.name = ""
    out = StringIO()
    out.write("## 3. קשרים בין מאפיינים\n\n")
    out.write("**מטריצת קורלציה (Pearson):**\n\n")
    out.write(md_table(corr_p))
    out.write("\n")

    sp = df[num_cols].corr(method="spearman")["רייטינג"].drop("רייטינג").sort_values(ascending=False).round(2)
    out.write("\n**Spearman מול רייטינג (קשר מונוטוני, ממוין):**\n\n")
    sp_df = sp.to_frame(name="ρ").reset_index().rename(columns={"index": "מאפיין"})
    out.write(md_table(sp_df, index=False))
    out.write("\n")

    out.write("\n**תובנות מהירות:**\n")
    insights = []
    p = df[num_cols].corr(method="pearson")["רייטינג"]
    for label, c in [("נתח", p["נתח"]), ("צופים 4+", p["צופים 4+"]),
                     ("חשיפה 4+", p["חשיפה 4+"]), ("משך תוכנית", p["משך תוכנית_דק"]),
                     ("ממוצע מתחרים", p["ממוצע מתחרים"])]:
        insights.append(f"- ר' מול {label}: r={c:.2f}")
    out.write("\n".join(insights) + "\n")
    return out.getvalue()


def section_target(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 4. סקירת משתנה המטרה — רייטינג\n\n")

    pct = [0.01, 0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    raw = df["רייטינג"].describe(percentiles=pct).round(3)
    adj = df["רייטינג מותאם"].describe(percentiles=pct).round(3)
    summary = pd.DataFrame({"רייטינג (raw)": raw, "רייטינג מותאם": adj})
    summary.index.name = "מדד"
    out.write(md_table(summary))
    out.write("\n")

    out.write(f"\n- **רשומות עם רייטינג=0:** {(df['רייטינג'] == 0).sum():,} "
              f"({(df['רייטינג'] == 0).mean():.1%})\n")
    top1 = df["רייטינג"].quantile(0.99)
    out.write(f"- **רשומות מעל אחוזון-99 ({top1:.2f}):** {(df['רייטינג'] >= top1).sum():,}\n")
    out.write(f"- **מקסימום רייטינג:** {df['רייטינג'].max():.2f}  |  **תוכנית:** "
              f"{df.loc[df['רייטינג'].idxmax(), 'שם תוכנית']}  |  "
              f"**תאריך:** {df.loc[df['רייטינג'].idxmax(), 'תאריך שידור'].date()}\n\n")

    out.write("**היסטוגרמה (10 בינים, רייטינג גולמי):**\n\n")
    out.write(text_histogram(df["רייטינג"], bins=10))
    out.write("\n\n")
    out.write("**היסטוגרמה (10 בינים, רייטינג מותאם):**\n\n")
    out.write(text_histogram(df["רייטינג מותאם"], bins=10))
    out.write("\n")
    return out.getvalue()


def _agg(df: pd.DataFrame, by: str) -> pd.DataFrame:
    g = df.groupby(by, dropna=False)
    res = pd.DataFrame({
        "n": g.size(),
        "רייטינג ממוצע": g["רייטינג"].mean().round(3),
        "רייטינג חציון": g["רייטינג"].median().round(3),
        "ר' מותאם ממוצע": g["רייטינג מותאם"].mean().round(3),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
    })
    return res


def section_weekday(df: pd.DataFrame) -> str:
    order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    res = _agg(df, "יום שידור").reindex(order)
    res.index.name = "יום"
    best = res["רייטינג ממוצע"].idxmax()
    worst = res["רייטינג ממוצע"].idxmin()
    bv = res.loc[best, "רייטינג ממוצע"]
    wv = res.loc[worst, "רייטינג ממוצע"]
    out = StringIO()
    out.write("## 5. רייטינג לפי יום בשבוע\n\n")
    out.write(md_table(res))
    out.write("\n")
    out.write(f"\n> 💡 **מה זה אומר?** {best} הוא היום החזק ביותר (ר' {bv:.3f}), "
              f"ו-{worst} הוא החלש ביותר (ר' {wv:.3f}) — פער של פי-{bv/max(wv,0.001):.1f}. "
              f"שישי ושבת חזקים כי 'קבינט שישי' ותוכניות סוף-שבוע מושכות קהל. "
              f"שבת מיוחדת בגלל שערוץ 14 לא משדר — i24 תופסת נתח גדול יותר מאותם צופים.\n\n")
    return out.getvalue()


def section_hour(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 6. רייטינג לפי שעת שידור\n\n")
    out.write("### 6.1 לפי 24 שעות (שעת התחלה)\n\n")
    res24 = _agg(df, "שעת התחלה_שעה").sort_index()
    res24.index = [f"{h:02d}:00" for h in res24.index]
    res24.index.name = "שעה"
    out.write(md_table(res24))
    out.write("\n")
    out.write("\n### 6.2 לפי חלקי-יום\n\n")
    res6 = _agg(df, "חלקי-יום").sort_index()
    res6.index.name = "חלקי-יום"
    out.write(md_table(res6))
    out.write("\n")
    pt_mean = res6.loc["4. פריים-טיים 18–21", "רייטינג ממוצע"] if "4. פריים-טיים 18–21" in res6.index else "~1.09"
    ln_mean = res6.loc["6. לילה מאוחר 02–05", "רייטינג ממוצע"] if "6. לילה מאוחר 02–05" in res6.index else "~0.22"
    out.write(f"\n> 💡 **מה זה אומר?** פריים-טיים (18–21) הוא שיא הצפייה עם ר' {pt_mean} בממוצע — "
              f"כמעט פי 5 מלילה מאוחר ({ln_mean}). "
              "כל שעה שעוברת אחרי 21:00 גוררת ירידה חדה. "
              "לילה מאוחר (02–05) מגיע לאוכלוסייה ייחודית ויציבה — ולכן המודל שלנו מצליח לחזות שם טוב יותר.\n\n")
    return out.getvalue()


def section_rerun(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 7. שידור-חוזר מול שידור-מקור\n\n")
    out.write("### 7.1 חתך פשוט\n\n")
    g = df.groupby("is_rerun")
    simple = pd.DataFrame({
        "n": g.size(),
        "רייטינג ממוצע": g["רייטינג"].mean().round(3),
        "רייטינג חציון": g["רייטינג"].median().round(3),
        "סטיית-תקן": g["רייטינג"].std().round(3),
        "ר' מותאם ממוצע": g["רייטינג מותאם"].mean().round(3),
    })
    simple.index = simple.index.map({False: "מקור", True: "שידור חוזר"})
    simple.index.name = "סוג"
    out.write(md_table(simple))
    out.write("\n")

    out.write("\n### 7.2 צמדים: ממוצע רייטינג לפי תוכנית-מקור\n")
    out.write("**שורה לכל תוכנית-מקור עם הופעות גם כמקור וגם כש.ח** (לפחות 5 שידורים מכל סוג).\n\n")
    grp = df.groupby(["שם תוכנית_מקור", "is_rerun"])["רייטינג"].agg(["mean", "size"]).unstack("is_rerun")
    grp.columns = [f"{m}_{'rerun' if r else 'orig'}" for m, r in grp.columns]
    paired = grp.dropna(subset=["mean_orig", "mean_rerun"])
    paired = paired[(paired["size_orig"] >= 5) & (paired["size_rerun"] >= 5)].copy()
    paired["דלתא (ר'-ש.ח)"] = (paired["mean_orig"] - paired["mean_rerun"]).round(3)
    paired = paired.sort_values("size_orig", ascending=False).head(20)
    show = pd.DataFrame({
        "n מקור": paired["size_orig"].astype(int),
        "n ש.ח": paired["size_rerun"].astype(int),
        "ר' מקור": paired["mean_orig"].round(3),
        "ר' ש.ח": paired["mean_rerun"].round(3),
        "דלתא": paired["דלתא (ר'-ש.ח)"],
    })
    show.index.name = "תוכנית-מקור"
    out.write(md_table(show))
    out.write("\n")

    out.write(f"\n**סיכום צמדים** (n>=5 משני הסוגים):\n")
    if len(paired):
        d = paired["דלתא (ר'-ש.ח)"]
        out.write(f"- מס' תוכניות בהשוואה: {len(paired)}\n")
        out.write(f"- דלתא ממוצעת (מקור פחות ש.ח): {d.mean():.3f}\n")
        out.write(f"- דלתא חציון: {d.median():.3f}\n")
        out.write(f"- אחוז תוכניות שבהן המקור גבוה מהש.ח: {(d > 0).mean():.0%}\n")
    return out.getvalue()


def section_advantage(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 8. יתרון מול מתחרים (KPI)\n\n")
    out.write(f"- **ממוצע יתרון:** {df['יתרון מול מתחרים'].mean():.3f}\n")
    out.write(f"- **אחוז שידורים בהם i24 ≥ ממוצע מתחרים:** "
              f"{(df['יתרון מול מתחרים'] >= 0).mean():.1%}\n\n")

    out.write("**יתרון לפי יום בשבוע:**\n\n")
    order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    g = df.groupby("יום שידור")
    by_day = pd.DataFrame({
        "n": g.size(),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
        "% עם יתרון≥0": (g["יתרון מול מתחרים"].apply(lambda x: (x >= 0).mean()) * 100).round(1),
    }).reindex(order)
    by_day.index.name = "יום"
    out.write(md_table(by_day))
    out.write("\n")

    out.write("\n**יתרון לפי חלקי-יום:**\n\n")
    g2 = df.groupby("חלקי-יום")
    by_part = pd.DataFrame({
        "n": g2.size(),
        "יתרון ממוצע": g2["יתרון מול מתחרים"].mean().round(3),
        "% עם יתרון≥0": (g2["יתרון מול מתחרים"].apply(lambda x: (x >= 0).mean()) * 100).round(1),
    }).sort_index()
    by_part.index.name = "חלקי-יום"
    out.write(md_table(by_part))
    out.write("\n")
    return out.getvalue()


def section_events(df: pd.DataFrame, ev: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 9. השפעת אירועים, חגים ועונות\n\n")

    out.write("### 9.1 רייטינג בעונות השנה\n\n")
    res_s = _agg(df, "תג_עונה")
    res_s.index.name = "עונה"
    out.write(md_table(res_s))
    out.write("\n")

    out.write("\n### 9.2 ימי חג מול ימים רגילים\n\n")
    res_h = _agg(df.assign(חג=np.where(df["יום_חג"], "יום חג", "יום רגיל")), "חג")
    res_h.index.name = ""
    out.write(md_table(res_h))
    out.write("\n")

    if df["יום_ביטחוני"].any():
        out.write("\n### 9.3 ימי אירוע ביטחוני/מדיני מול שגרה\n\n")
        res_b = _agg(df.assign(b=np.where(df["יום_ביטחוני"], "אירוע ביטחוני", "שגרה")), "b")
        res_b.index.name = ""
        out.write(md_table(res_b))
        sec_r = res_b.loc["אירוע ביטחוני", "רייטינג ממוצע"] if "אירוע ביטחוני" in res_b.index else "?"
        norm_r = res_b.loc["שגרה", "רייטינג ממוצע"] if "שגרה" in res_b.index else "?"
        uplift = round(float(sec_r) / max(float(norm_r), 0.001), 1) if sec_r != "?" else "?"
        out.write(f"\n> 🚨 **מה זה אומר?** ביום ביטחוני, הרייטינג קופץ מ-{norm_r} ל-{sec_r} — "
                  f"פי {uplift} מהשגרה! "
                  "i24 כערוץ חדשות מרוויח דרמטית מאירועי ביטחון. "
                  "זה גם האתגר הכי גדול למידול — אי-אפשר לדעת מראש מתי יקרה אירוע.\n\n")

    out.write("\n### 9.4 אירועים ספציפיים (תאריכים מדויקים מהאינטרנט)\n\n")
    rows = []
    sec_kinds = {"ביטחוני", "מדיני"}
    for _, b in ev[ev["סוג"].isin(sec_kinds)].iterrows():
        if pd.isna(b["תאריך_dt"]) or pd.isna(b["תאריך_סיום_dt"]):
            continue
        m = (df["תאריך שידור"] >= b["תאריך_dt"]) & (df["תאריך שידור"] <= b["תאריך_סיום_dt"])
        sub = df[m]
        if len(sub) == 0:
            continue
        rows.append({
            "אירוע": b["אירוע"],
            "מ-": b["תאריך_dt"].date(),
            "עד": b["תאריך_סיום_dt"].date(),
            "n": len(sub),
            "ר' ממוצע": round(sub["רייטינג"].mean(), 3),
            "ר' מותאם ממוצע": round(sub["רייטינג מותאם"].mean(), 3),
            "יתרון ממוצע": round(sub["יתרון מול מתחרים"].mean(), 3),
        })
    if rows:
        ev_df = pd.DataFrame(rows).set_index("אירוע")
        out.write(md_table(ev_df))
        out.write("\n")
    else:
        out.write("(אין רשומות בחלון האירועים מתוך טווח הדאטה הנוכחי.)\n")
    return out.getvalue()


def section_status(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 10. רייטינג לפי סטטוס תוכנית\n\n")
    out.write("חלוקה אוטומטית לפי שם התוכנית: שידור חי / ש.ח / לקט / מיוחד-מבזק / חג.\n\n")
    g = df.groupby("סטטוס תוכנית")
    res = pd.DataFrame({
        "n": g.size(),
        "% מהשידורים": (g.size() / len(df) * 100).round(1),
        "ר' ממוצע": g["רייטינג"].mean().round(3),
        "ר' חציון": g["רייטינג"].median().round(3),
        "ר' מותאם ממוצע": g["רייטינג מותאם"].mean().round(3),
        "נתח ממוצע": g["נתח"].mean().round(2),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
    }).sort_values("ר' ממוצע", ascending=False)
    res.index.name = "סטטוס"
    out.write(md_table(res))
    out.write("\n")
    return out.getvalue()


def section_saturday(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 11. אפקט שבת — ערוץ 14 לא משדר\n\n")
    out.write("ערוץ 14 (עכשיו 14) **אינו משדר בשבת**, ולכן 'ממוצע המתחרים' בשבתות מתבסס "
              "אפקטיבית רק על 3 מתחרים. זה משנה גם את ה-HUT.\n\n")

    sat_zero = ((df["יום שידור"] == "שבת") & (df["עכשיו 14"] == 0)).sum()
    sat_total = (df["יום שידור"] == "שבת").sum()
    out.write(f"- שורות שבת עם עכשיו14=0: **{sat_zero:,}** מתוך **{sat_total:,}** "
              f"({sat_zero/sat_total:.0%})\n\n")

    g = df.groupby(df["יום שידור"].eq("שבת").map({True: "שבת", False: "ימי חול"}))
    res = pd.DataFrame({
        "n": g.size(),
        "ר' ממוצע": g["רייטינג"].mean().round(3),
        "נתח ממוצע": g["נתח"].mean().round(2),
        "ר' מותאם ממוצע": g["רייטינג מותאם"].mean().round(3),
        "ממוצע מתחרים": g["ממוצע מתחרים"].mean().round(3),
        "HUT proxy ממוצע": g["HUT proxy"].mean().round(3),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
    })
    res.index.name = ""
    out.write(md_table(res))
    out.write("\n\n**תובנה:** ה-HUT proxy בשבת כמעט זהה לימי חול (10.6 בשתיהן), "
              "אבל **הנתח של i24** בשבת כמעט כפול (2.33% מול 1.46%). כלומר: כמות "
              "הצופים הכוללת לא משתנה דרמטית, אבל היעדר ערוץ 14 (וקצת חגיגה כללית "
              "של תכני סוף-שבוע אצל המתחרים) מאפשרים ל-i24 לתפוס פיסה גדולה יותר "
              "מאותה עוגה. עבור מודל חיזוי-נתח זה חשוב מאוד — דגל `שבת` או "
              "`עכשיו14==0` יסביר חלק ניכר מהשונות.\n")
    return out.getvalue()


def section_top_programs(df: pd.DataFrame) -> str:
    g = df.groupby("שם תוכנית_מקור").agg(
        n=("רייטינג", "size"),
        ר_ממוצע=("רייטינג", "mean"),
        ר_מותאם_ממוצע=("רייטינג מותאם", "mean"),
        יתרון=("יתרון מול מתחרים", "mean"),
    )
    g = g[g["n"] >= 10].sort_values("ר_ממוצע", ascending=False).head(15)
    g = g.round(3).rename(columns={
        "ר_ממוצע": "ר' ממוצע",
        "ר_מותאם_ממוצע": "ר' מותאם ממוצע",
        "יתרון": "יתרון ממוצע",
    })
    g.index.name = "תוכנית"
    return "## 13. Top-15 תוכניות לפי רייטינג ממוצע (n≥10)\n\n" + md_table(g) + "\n"


def section_time_trend(df: pd.DataFrame) -> str:
    out = StringIO()
    out.write("## 14. מגמת זמן: רייטינג גולמי מול מותאם (חודשי)\n\n")
    out.write("התאמה ל-reception_pct מנטרלת חלק מהעלייה הליניארית בקליטה. "
              "הפער בין השני מצביע על ההשפעה של גידול הקליטה לעומת שיפור 'אמיתי'.\n\n")
    df = df.copy()
    df["חודש"] = df["תאריך שידור"].dt.to_period("M").astype(str)
    g = df.groupby("חודש")
    trend = pd.DataFrame({
        "n": g.size(),
        "ר' ממוצע": g["רייטינג"].mean().round(3),
        "ר' מותאם": g["רייטינג מותאם"].mean().round(3),
        "reception_pct": g["reception_pct"].mean().round(3),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
    }).sort_index()
    trend.index.name = "חודש"
    out.write(md_table(trend))
    out.write("\n")
    return out.getvalue()


def section_executive_summary(df: pd.DataFrame) -> str:
    """High-level findings summary, placed at top of report. Computes everything fresh."""
    out = StringIO()
    n = len(df)
    n_progs = df["שם תוכנית"].nunique()
    n_progs_src = df["שם תוכנית_מקור"].nunique()
    n_days = df["תאריך שידור"].dt.normalize().nunique()
    date_min = df["תאריך שידור"].min().date()
    date_max = df["תאריך שידור"].max().date()
    rating_mean = df["רייטינג"].mean()
    rating_adj_mean = df["רייטינג מותאם"].mean()
    rating_med = df["רייטינג"].median()
    rating_max = df["רייטינג"].max()
    advantage_mean = df["יתרון מול מתחרים"].mean()
    advantage_pos = (df["יתרון מול מתחרים"] >= 0).mean()
    hut_mean = df["HUT proxy"].mean()
    rerun_share = df["is_rerun"].mean()
    rerun_n = df["is_rerun"].sum()
    n_events = (df["אירוע_מיוחד"] != "—").sum()
    events_share = n_events / n

    # best/worst by part-of-day
    by_part = df.groupby("חלקי-יום")["רייטינג"].mean()
    best_part, best_part_v = by_part.idxmax(), by_part.max()
    worst_part, worst_part_v = by_part.idxmin(), by_part.min()

    # best/worst by weekday
    order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    by_day = df.groupby("יום שידור")["רייטינג"].mean().reindex(order)
    best_day, best_day_v = by_day.idxmax(), by_day.max()
    worst_day, worst_day_v = by_day.idxmin(), by_day.min()

    # top program (n>=10)
    pg = df.groupby("שם תוכנית_מקור").agg(n=("רייטינג", "size"), m=("רייטינג", "mean"))
    pg = pg[pg["n"] >= 10].sort_values("m", ascending=False)
    top_prog = pg.index[0] if len(pg) else "—"
    top_prog_m = pg["m"].iloc[0] if len(pg) else float("nan")

    # top event by mean rating (excluding "—")
    ev_g = df[df["אירוע_מיוחד"] != "—"].groupby("אירוע_מיוחד")["רייטינג"].agg(["mean", "size"])
    ev_g = ev_g[ev_g["size"] >= 20].sort_values("mean", ascending=False)
    top_event = ev_g.index[0] if len(ev_g) else "—"
    top_event_m = ev_g["mean"].iloc[0] if len(ev_g) else float("nan")

    # rerun delta
    rr = df.groupby("is_rerun")["רייטינג"].mean()
    delta_rr = rr.get(False, 0) - rr.get(True, 0)

    out.write("## ✦ סיכום מנהלים\n\n")
    out.write(f"**טווח הנתונים:** {n:,} שידורים, {n_progs:,} תוכניות ייחודיות "
              f"({n_progs_src:,} תוכניות-מקור), {n_days:,} ימי שידור — "
              f"{date_min} עד {date_max}.\n\n")
    out.write("**מדדי-על:**\n\n")
    out.write(f"- **רייטינג ממוצע גולמי** = {rating_mean:.3f}  |  **חציון** = {rating_med:.3f}  |  "
              f"**מקסימום** = {rating_max:.2f}\n")
    out.write(f"- **רייטינג מותאם ל-100% פאנל** = {rating_adj_mean:.3f} "
              f"(גידול של {(rating_adj_mean/rating_mean - 1):+.1%} מעל הגולמי)\n")
    out.write(f"- **HUT proxy ממוצע** = {hut_mean:.2f} (סך 5 הערוצים)\n")
    out.write(f"- **יתרון מול מתחרים** = {advantage_mean:.2f} בממוצע, "
              f"i24 ≥ ממוצע מתחרים ב-{advantage_pos:.0%} מהשידורים\n\n")
    out.write("**ממצאי-מפתח:**\n\n")
    out.write(f"- 🏆 **השעה החזקה ביותר:** {best_part} — ר' ממוצע {best_part_v:.3f}; "
              f"השעה החלשה ביותר: {worst_part} — {worst_part_v:.3f} "
              f"(פער של פי-{(best_part_v/max(worst_part_v, 0.01)):.1f})\n")
    out.write(f"- 📅 **היום החזק ביותר:** {best_day} ({best_day_v:.3f}); "
              f"החלש ביותר: {worst_day} ({worst_day_v:.3f})\n")
    out.write(f"- 🔁 **שידורים-לא-ראשונים** (ש.ח + לקט): {rerun_n:,} ({rerun_share:.0%}); "
              f"דלתא רייטינג מקור-מול-חוזר = {delta_rr:+.3f}\n")
    out.write(f"- 🎯 **תוכנית מובילה** (n≥10): \"{top_prog}\" — ר' ממוצע {top_prog_m:.2f}\n")
    if not pd.isna(top_event_m):
        out.write(f"- 🚨 **אירוע עם הרייטינג הגבוה ביותר** (n≥20): \"{top_event}\" — ר' ממוצע {top_event_m:.2f}\n")
    out.write(f"- 🗓️ **שידורים בימי-אירוע מתויגים** (חג/ביטחוני/מדיני): "
              f"{n_events:,} ({events_share:.0%} מהשידורים)\n\n")
    out.write("**סיכום בשורה:** i24 הוא ערוץ-חדשות שהרייטינג שלו עולה משמעותית בשעות "
              "פריים-טיים, בשבת (היעדר ערוץ 14), ובאירועים ביטחוניים — אך נמצא בפיגור "
              "כללי מול ממוצע המתחרים.\n\n")
    out.write("---\n")
    return out.getvalue()


def section_heatmap(df: pd.DataFrame) -> str:
    """Day-of-week × hour heatmap of mean rating, rendered as a markdown table with
    color-coded blocks via shade characters."""
    out = StringIO()
    out.write("## 15. heatmap: רייטינג ממוצע לפי יום × שעה\n\n")
    out.write("הצללה מציינת רייטינג ממוצע: ░ נמוך · ▒ בינוני · ▓ גבוה · █ מאוד גבוה. "
              "מציג את שיא הרייטינג של i24 (פריים-טיים בסופי-שבוע ובאירועים).\n\n")
    order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    pivot = df.pivot_table(index="שעת התחלה_שעה", columns="יום שידור",
                           values="רייטינג", aggfunc="mean").reindex(columns=order)
    if pivot.empty:
        return out.getvalue()
    vmax = pivot.max().max()
    vmin = pivot.min().min()

    def shade(v):
        if pd.isna(v):
            return " · "
        f = (v - vmin) / max(vmax - vmin, 1e-9)
        if f < 0.25:
            ch = "░"
        elif f < 0.50:
            ch = "▒"
        elif f < 0.75:
            ch = "▓"
        else:
            ch = "█"
        return f"{ch}{v:.2f}"

    out.write("| שעה | " + " | ".join(order) + " |\n")
    out.write("|---|" + "|".join(["---"] * len(order)) + "|\n")
    for h in sorted(pivot.index):
        row = [f"{int(h):02d}"]
        for d in order:
            row.append(shade(pivot.at[h, d]))
        out.write("| " + " | ".join(row) + " |\n")
    out.write(f"\n*סולם: מינימום = {vmin:.3f}, מקסימום = {vmax:.3f}*\n")
    return out.getvalue()


def section_monthly_deep(df: pd.DataFrame) -> str:
    """Per-month deep-dive: n broadcasts, rating raw vs adjusted, top program, events count."""
    out = StringIO()
    out.write("## 16. ניתוח חודשי מעמיק\n\n")
    out.write("לכל חודש: כמות שידורים, רייטינג גולמי מול מותאם, התוכנית המובילה, ומספר ימי-אירוע.\n\n")
    df = df.copy()
    df["חודש"] = df["תאריך שידור"].dt.to_period("M").astype(str)

    rows = []
    for mon, sub in df.groupby("חודש"):
        pg = sub.groupby("שם תוכנית_מקור").agg(n=("רייטינג", "size"), m=("רייטינג", "mean"))
        pg = pg[pg["n"] >= 5].sort_values("m", ascending=False)
        top_prog = f"{pg.index[0]} ({pg['m'].iloc[0]:.2f})" if len(pg) else "—"
        n_event_days = (sub["אירוע_מיוחד"] != "—").sum()
        rows.append({
            "חודש": mon,
            "n שידורים": len(sub),
            "ר' גולמי": round(sub["רייטינג"].mean(), 3),
            "ר' מותאם": round(sub["רייטינג מותאם"].mean(), 3),
            "reception_pct": round(sub["reception_pct"].iloc[0], 4),
            "תוכנית מובילה (n≥5)": top_prog,
            "n שידורי-אירוע": int(n_event_days),
        })
    res = pd.DataFrame(rows).set_index("חודש")
    out.write(md_table(res))
    out.write("\n")
    out.write("\n**הערה:** `ר' מותאם` נטרל את עליית הקליטה — כשהוא יורד למרות שהגולמי עולה, "
              "זה אומר שהעלייה הגולמית מקורה בקליטה ולא בעלייה אמיתית בצפייה.\n")
    return out.getvalue()


def section_lakat(df: pd.DataFrame) -> str:
    """Sub-analysis on לקט rows now classified as is_rerun=True."""
    out = StringIO()
    out.write("## 17. לקט — תת-ניתוח\n\n")
    out.write("לקט הוא קובץ קטעים נבחרים משידורים קודמים — מסומן עכשיו `is_rerun=True` "
              "(החל מ-2026-05-03), אך נשמר בעמודת `סטטוס תוכנית` כקטגוריה נפרדת מ\"שידור חוזר\".\n\n")

    n_lakat = (df["סטטוס תוכנית"] == "לקט").sum()
    if n_lakat == 0:
        out.write("*אין שורות עם סטטוס \"לקט\" בנתונים.*\n")
        return out.getvalue()

    out.write("### 17.1 השוואה: שידור-חי / שידור-חוזר / לקט\n\n")
    g = df[df["סטטוס תוכנית"].isin(["שידור חי", "שידור חוזר", "לקט"])].groupby("סטטוס תוכנית")
    cmp = pd.DataFrame({
        "n": g.size(),
        "ר' ממוצע": g["רייטינג"].mean().round(3),
        "ר' חציון": g["רייטינג"].median().round(3),
        "ר' מותאם": g["רייטינג מותאם"].mean().round(3),
        "נתח ממוצע": g["נתח"].mean().round(2),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
    })
    cmp.index.name = "סטטוס"
    out.write(md_table(cmp))
    out.write("\n")

    out.write("\n### 17.2 התפלגות לקט לפי שעה ויום\n\n")
    sub = df[df["סטטוס תוכנית"] == "לקט"]
    by_part = sub.groupby("חלקי-יום").agg(n=("רייטינג", "size"), m=("רייטינג", "mean"))
    by_part = by_part.assign(**{"ר' ממוצע": by_part["m"].round(3)}).drop(columns="m")
    by_part.index.name = "חלקי-יום"
    out.write(md_table(by_part))
    out.write("\n")

    out.write("\n### 17.3 חמש תוכניות-לקט מובילות (n≥5)\n\n")
    pg = sub.groupby("שם תוכנית").agg(n=("רייטינג", "size"), m=("רייטינג", "mean"))
    pg = pg[pg["n"] >= 5].sort_values("m", ascending=False).head(5)
    pg = pg.rename(columns={"m": "ר' ממוצע"}).round(3)
    pg.index.name = "תוכנית"
    out.write(md_table(pg))
    out.write("\n")
    return out.getvalue()


def section_bottom_programs(df: pd.DataFrame) -> str:
    """Counterpart to top-15: bottom 15 programs by mean rating, n>=10."""
    g = df.groupby("שם תוכנית_מקור").agg(
        n=("רייטינג", "size"),
        ר_ממוצע=("רייטינג", "mean"),
        ר_מותאם=("רייטינג מותאם", "mean"),
        יתרון=("יתרון מול מתחרים", "mean"),
    )
    g = g[g["n"] >= 10].sort_values("ר_ממוצע", ascending=True).head(15)
    g = g.round(3).rename(columns={
        "ר_ממוצע": "ר' ממוצע",
        "ר_מותאם": "ר' מותאם ממוצע",
        "יתרון": "יתרון ממוצע",
    })
    g.index.name = "תוכנית"
    return ("## 18. Bottom-15 תוכניות לפי רייטינג ממוצע (n≥10)\n\n"
            "התוכניות החלשות ביותר ברייטינג — שימושי לזיהוי תוכניות שצריכות בחינה מחדש.\n\n"
            + md_table(g) + "\n")


def section_notes() -> str:
    return (
        "## 19. הערות מתודולוגיות\n\n"
        "- **רייטינג מותאם** מנטרל גידול ליניארי בקליטה: רמפה חודשית — "
        "מאי 2025 = 65%, אפריל 2026 = 90%, ובין החודשים `step = 0.25/11 ≈ 0.0227` (כל החודשים שבדרך). "
        "כל הימים באותו חודש מקבלים את אותו `reception_pct`. "
        "מודל זה הוא **קירוב**; מומלץ "
        "להחליף בנתוני קליטה אמיתיים אם זמינים.\n"
        "- **שידור חוזר** מזוהה ע\"י המחרוזת `ש.ח` בשם התוכנית.\n"
        "- **אירועים ביטחוניים/מדיניים** וחגים מתויגים לפי **תאריכי התחלה-סיום מדויקים** "
        "המעוגנים ב-`אירועים_מדויקים.csv` (אומתו ב-WebSearch מויקיפדיה ומקורות חדשות). "
        "החלון של חג לא נקבע באופן שרירותי כמו בקובץ המקור — הוא משקף את ימי החג בפועל.\n"
        "- **ערוץ 14 לא משדר בשבת** — ולכן רייטינג עכשיו 14 בשבתות מתפרש "
        "כחלק מהמתחרים בלי תיקון. זה עלול להטות מטה את 'ממוצע המתחרים' "
        "ולהטות מעלה את 'היתרון מול מתחרים' בשבתות.\n"
        "- **תוכניות מקור-מול-ש.ח** הותאמו ע\"י הסרת הסיומת `ש.ח`. "
        "אם יש שמות שלא תואמים בדיוק, ההתאמה תפספס אותם.\n"
        "- **`תוכניות (2).xlsx`** הוא תת-קבוצה מצומצמת באנגלית של אותם "
        "10,039 רשומות; לא נטען כדי לא ליצור כפילות.\n"
    )


def export_xlsx(df: pd.DataFrame, ev: pd.DataFrame) -> None:
    """Export the enriched dataset to XLSX with two sheets:
       1) 'נתונים מעובדים' — original 15 cols + all engineered cols (incl. אירוע_מיוחד and רייטינג מותאם).
       2) 'אירועים מדויקים' — the curated events lookup."""
    keep = [
        # original cols, with reception_pct + רייטינג מותאם placed adjacent to רייטינג
        "שם תוכנית", "יום שידור", "תאריך שידור", "שעת התחלה", "שעת סיום",
        "משך תוכנית",
        "רייטינג", "reception_pct", "רייטינג מותאם",
        "נתח", "צופים 4+", "חשיפה 4+", "משך צפייה",
        "כאן 11", "קשת 12", "רשת 13", "עכשיו 14",
        # engineered
        "is_rerun", "סטטוס תוכנית", "שם תוכנית_מקור",
        "שעת התחלה_שעה", "חלקי-יום", "משך תוכנית_דק", "משך צפייה_דק",
        "ממוצע מתחרים", "יתרון מול מתחרים", "HUT proxy",
        "תג_עונה", "תג_חג", "תג_ביטחוני", "אירוע_מיוחד",
        "יום_חג", "יום_ביטחוני", "שבת",
    ]
    out = df[keep].copy()
    # excel doesn't like timezone-aware ints in seconds; format dates as YYYY-MM-DD
    out["תאריך שידור"] = pd.to_datetime(out["תאריך שידור"]).dt.strftime("%Y-%m-%d")

    ev_view = ev[["סוג", "אירוע", "תאריך_התחלה", "תאריך_סיום", "תיאור", "מקור"]].copy()
    ev_view.columns = ["קטגוריה", "שם האירוע", "תאריך התחלה", "תאריך סיום", "תיאור", "מקור"]

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="נתונים מעובדים", index=False)
        ev_view.to_excel(xw, sheet_name="אירועים מדויקים", index=False)


def section_special_events(df: pd.DataFrame) -> str:
    """New section showing rating cuts by the unified אירוע_מיוחד column."""
    out = StringIO()
    out.write("## 12. עמודה חדשה: אירוע_מיוחד (תאריכים מדויקים)\n\n")
    out.write("עמודה זו מסכמת לכל שורה את האירוע הביטחוני/מדיני/חג שחל באותו תאריך, "
              "לפי קובץ `אירועים_מדויקים.csv` (תאריכים שאומתו באינטרנט).\n\n")
    g = df.groupby("אירוע_מיוחד")
    res = pd.DataFrame({
        "n": g.size(),
        "% מהשידורים": (g.size() / len(df) * 100).round(1),
        "ר' ממוצע": g["רייטינג"].mean().round(3),
        "ר' מותאם ממוצע": g["רייטינג מותאם"].mean().round(3),
        "נתח ממוצע": g["נתח"].mean().round(2),
        "יתרון ממוצע": g["יתרון מול מתחרים"].mean().round(3),
    }).sort_values("ר' ממוצע", ascending=False)
    res.index.name = "אירוע_מיוחד"
    out.write(md_table(res))
    out.write("\n")
    return out.getvalue()


def section_glossary() -> str:
    """Plain-language glossary of TV measurement terms, written for a non-expert reader."""
    return """## 📖 מילון מושגים — טלמטריה בשפה פשוטה

לפני שמסתכלים על מספרים, חשוב להבין מה הם בכלל אומרים. הנה הסבר פשוט לכל מונח:

---

### 📺 רייטינג (Rating)
**בשפה פשוטה:** מתוך כל הטלוויזיות בישראל — כמה אחוזים היו מכוונות לערוץ הזה באותה דקה?

> **דוגמה:** רייטינג 1.0 אומר שמתוך 100 טלוויזיות בישראל, 1 הייתה מכוונת ל-i24.
> רייטינג 0.44 (הממוצע שלנו) = כ-0.44 מכל 100 טלוויזיות.
> רייטינג 5.58 (המקסימום) = שיא היסטורי — קרה באירוע ביטחוני בלתי-נשכח.

**מאיפה זה מגיע?** מפאנל מדידה — מדגם ייצוגי של בתי-אב ישראלים עם מכשיר מדידה שמדווח בזמן אמת.

---

### 📊 נתח (Share)
**בשפה פשוטה:** מתוך מי שצפה בטלוויזיה ברגע הזה — כמה אחוזים בחרו ב-i24?

> **דוגמה:** נתח 5% בשעה מסוימת = מתוך כל מי שישב מול הטלוויזיה, 5 מכל 100 צפו ב-i24.

**ההבדל מרייטינג:** רייטינג מודד מכל הטלוויזיות בישראל. נתח מודד רק מתוך מי שדלק. לכן ביצועים בלילה מאוחר עשויים להיראות טוב יותר בנתח (כי פחות מתחרים דולקים) ורע ביותר ברייטינג (כי פחות אנשים צופים בכלל).

---

### 🏠 HUT (Homes Using Television) — שנקרא כאן "HUT proxy"
**בשפה פשוטה:** כמה אחוזים מהטלוויזיות בישראל דולקות ברגע הזה בכלל?

> אנחנו לא מודדים HUT אמיתי — אנחנו מחשבים קירוב על-ידי סכימת כל 5 הערוצים.

**למה זה שימושי?** אם HUT גבוה, יש הרבה צופים שמחולקים בין הערוצים. אם HUT נמוך (למשל בלילה מאוחר), יש פחות תחרות — כל ערוץ יכול לקבל נתח גבוה יחסית.

---

### 📡 פאנל נושם (reception_pct)
**בשפה פשוטה:** i24 הוא ערוץ חדש שנמצא בתהליך הרחבת הפצה. לא כל הטלוויזיות בישראל יכולות לקלוט אותו עדיין.

> **דוגמה:** מאי 2025 — רק 65% מהפאנל יכול לקלוט את i24. אפריל 2026 — 90%.
> זה אומר שאם בית-אב לא יכול לקלוט את הערוץ, הוא "לא נמנה" — גם אם היה רוצה לצפות.

**ההשלכה:** הרייטינג הגולמי עולה חלק גדול מהעלייה מהרחבת הקליטה, לא מגידול אמיתי בפופולריות.

---

### 📈 רייטינג מותאם
**בשפה פשוטה:** אם כל הטלוויזיות יכלו לקלוט את i24 — מה היה הרייטינג?

> **חישוב:** רייטינג גולמי ÷ reception_pct
> **דוגמה:** רייטינג גולמי 0.65 בחודש שבו רק 65% יכולים לקלוט → רייטינג מותאם = 1.0

**למה זה חשוב?** מאפשר השוואה הוגנת בין חודש מאי 2025 לאפריל 2026 — בלי שגידול הקליטה "יזייף" את המגמה.

---

### 🔁 שידור חוזר (ש.ח) לעומת לקט
- **שידור חוזר (ש.ח):** תוכנית שהוקלטה ומשודרת שוב כמות שהיא.
- **לקט:** קובץ של קטעים נבחרים ממספר שידורים. לא אותה התוכנית, אלא "best of".
- **שידור חי:** התוכנית משודרת בזמן אמת.

---

"""


def section_feature_guide(df: pd.DataFrame) -> str:
    """Detailed plain-language explanation of every column in the dataset."""
    out = StringIO()
    out.write("## 📋 מדריך לעמודות — הסבר לכל עמודה\n\n")
    out.write("הטבלה שלנו מכילה **34 עמודות**: 15 מקוריות מקובץ הדאטה + 19 שיצרנו בעצמנו. "
              "להלן הסבר לכל אחת.\n\n")

    out.write("---\n\n### קבוצה א׳ — עמודות המקור (15 עמודות, מהדאטה המקורי)\n\n")

    cols_a = [
        ("שם תוכנית", "זיהוי",
         'שם התוכנית כפי שנרשם ב-"as-run log" (יומן שידור). '
         'תוכנית עם "ש.ח" בסוף = שידור חוזר. תוכנית עם "לקט" = לקט.',
         "179 שמות ייחודיים. הנפוץ ביותר: 'חדר החדשות איי 24' (2,391 שידורים)."),
        ("יום שידור", "זמן",
         "יום בשבוע שבו שודרה התוכנית.",
         "ראשון–שבת. רביעי הכי עמוס (1,470 שידורים), שבת הכי פחות (1,311)."),
        ("תאריך שידור", "זמן",
         "התאריך המדויק של השידור בפועל.",
         "טווח: 2025-05-25 עד 2026-04-18 (329 ימים)."),
        ("שעת התחלה", "זמן",
         "שעת תחילת השידור בפורמט HH:MM:SS.",
         "הרוב מתחיל בשעות עגולות (02:00, 10:00, 11:00)."),
        ("שעת סיום", "זמן",
         "שעת סיום השידור. שים לב — שידורי לילה שמסתיימים אחרי חצות יופיעו 'ליום למחרת'.",
         ""),
        ("משך תוכנית", "זמן",
         "כמה זמן נמשכה התוכנית (HH:MM:SS). תוכניות רוב הזמן הן 27-50 דקות.",
         "הנפוץ: 27 דק' (1,683 שידורים). הממוצע: ~35 דק'."),
        ("רייטינג", "ביצועים — i24 ⭐",
         "**המשתנה המרכזי שאנחנו מנסים לחזות.** "
         "אחוז הטלוויזיות בישראל שהיו מכוונות ל-i24 באותה תוכנית (ראה 'מילון מושגים').",
         f"min=0.00 | ממוצע=0.44 | חציון=0.31 | max=5.58. "
         "73% מהשידורים הם מתחת ל-0.56."),
        ("נתח", "ביצועים — i24",
         "אחוז הצופים שבחרו ב-i24 מתוך כלל הצופים שצפו בטלוויזיה באותה עת. "
         "ניתנות להשוואה בין תחומים שונים.",
         "ממוצע=1.57%. מקסימום=13.3% (שיאים באירועים)."),
        ("צופים 4+", "ביצועים — i24",
         "אומדן **כמה אנשים** (בני 4+) ראו לפחות דקה מהתוכנית. מספר מוחלט (באלפים).",
         "ממוצע ~10,000 צופים. שיא: ~161,000 (אירוע ביטחוני)."),
        ("חשיפה 4+", "ביצועים — i24",
         "אומדן כמה אנשים (בני 4+) נחשפו לתוכנית לפחות שנייה אחת. "
         "תמיד גבוה יותר מ'צופים 4+' כי חשיפה קצרה יותר.",
         "ממוצע ~28,000. קורלציה גבוהה עם רייטינג (0.81)."),
        ("משך צפייה", "ביצועים — i24",
         "כמה זמן בממוצע צפה כל צופה שנחשף לתוכנית. "
         "תוכנית עם משך צפייה גבוה = צופים 'נשארים' ולא מחליפים ערוץ.",
         ""),
        ("כאן 11", "מתחרים",
         "רייטינג ערוץ כאן 11 באותן הדקות שבהן שודרה תוכנית i24. "
         "מאפשר להבין כמה 'חזקים' היו המתחרים בזמן הזה.",
         "ממוצע=1.08. מקסימום=10.33."),
        ("קשת 12", "מתחרים",
         "רייטינג ערוץ קשת 12 באותן הדקות. קשת 12 הוא בדרך-כלל המתחרה החזק ביותר.",
         "ממוצע=4.73 (כמעט פי 10 מרייטינג i24!). מקסימום=25.22."),
        ("רשת 13", "מתחרים",
         "רייטינג ערוץ רשת 13 באותן הדקות.",
         "ממוצע=2.31."),
        ("עכשיו 14", "מתחרים",
         "רייטינג ערוץ עכשיו 14 באותן הדקות. **חשוב: ערוץ 14 לא משדר בשבת** — "
         "ולכן בשבתות הערך יהיה 0 עבור 70% מהשורות.",
         "ממוצע=2.08. בשבת: 0 ב-70% מהמקרים."),
    ]

    for name, group, explanation, values in cols_a:
        group_icon = {"זיהוי": "🏷️", "זמן": "🕐", "ביצועים — i24 ⭐": "⭐",
                      "ביצועים — i24": "📊", "מתחרים": "🆚"}.get(group, "")
        out.write(f"#### `{name}` {group_icon}\n")
        out.write(f"**{explanation}**\n")
        if values:
            out.write(f"*ערכים:* {values}\n")
        out.write("\n")

    out.write("---\n\n### קבוצה ב׳ — עמודות מחושבות (19 עמודות, יצרנו אנחנו)\n\n")
    out.write("עמודות אלה לא היו בדאטה המקורי — חישבנו אותן כדי לעשרת את הניתוח.\n\n")

    cols_b = [
        ("is_rerun", "סיווג", "🔁",
         "**כן/לא** — האם זה שידור שכבר שודר קודם? "
         "True = שידור חוזר (ש.ח) או לקט. False = שידור מקורי/חי.",
         "True = 4,781 (48%). שידורים חוזרים מקבלים רייטינג נמוך ב-43% בממוצע.",
         "מאיפה: בדיקה אם שם התוכנית מכיל 'ש.ח' או 'לקט'."),
        ("שם תוכנית_מקור", "סיווג", "🏷️",
         "שם התוכנית ללא הסיומת 'ש.ח' — מאפשר לזהות שכל השידורים (חי וחוזר) שייכים לאותה תוכנית.",
         "147 תוכניות-מקור ייחודיות (לעומת 179 שמות כולל חוזרים).",
         "מאיפה: הסרת ' ש.ח' מסוף שם התוכנית."),
        ("סטטוס תוכנית", "סיווג", "📂",
         "סיווג מדויק יותר מ-is_rerun: **שידור חי / שידור חוזר / לקט / מיוחד-מבזק / חג**.",
         "שידור חי: 4,847 (48%) | שידור חוזר: 3,917 (39%) | לקט: 812 (8%).",
         "מאיפה: חיפוש מחרוזות בשם התוכנית ('מיוחד', 'מבזק', 'לקט', 'חג', 'ש.ח')."),
        ("שעת התחלה_שעה", "זמן", "🕐",
         "שעת ההתחלה כמספר שלם (0-25). מאפשר ניתוח לפי שעה.",
         "25 ערכים אפשריים (כולל שידורי לילה 25:xx שהם שעה 1 אחרי חצות).",
         "מאיפה: המרת שעת ההתחלה מ-HH:MM:SS למספר שלם."),
        ("חלקי-יום", "זמן", "🕐",
         "חלוקת היום ל-6 קטגוריות: **בוקר (06–09) / צהריים (10–13) / אחה\"צ (14–17) / "
         "פריים-טיים (18–21) / לילה (22–01) / לילה מאוחר (02–05)**.",
         "פריים-טיים הכי חזק (ר' ממוצע 1.09). לילה מאוחר הכי חלש (0.22).",
         "מאיפה: מבוסס על שעת התחלה_שעה."),
        ("משך תוכנית_דק", "זמן", "⏱️",
         "משך התוכנית בדקות (מספר עשרוני). יותר נוח לניתוח מ-HH:MM:SS.",
         "הנפוץ: 27 דק'. טווח: 0 עד כמה שעות.",
         "מאיפה: המרת 'משך תוכנית' מ-HH:MM:SS לדקות."),
        ("משך צפייה_דק", "זמן", "⏱️",
         "משך הצפייה הממוצע בדקות.",
         "קורלציה בינונית עם רייטינג (0.45).",
         "מאיפה: המרת 'משך צפייה' מ-HH:MM:SS לדקות."),
        ("ממוצע מתחרים", "תחרות", "🆚",
         "ממוצע הרייטינג של 4 המתחרים (כאן 11 + קשת 12 + רשת 13 + עכשיו 14) באותה תוכנית. "
         "מייצג את 'עוצמת התחרות' ברגע הזה.",
         "ממוצע=2.55 (כ-6× יותר מרייטינג i24!).",
         "מאיפה: ממוצע של 4 עמודות מתחרים."),
        ("יתרון מול מתחרים", "תחרות", "🆚",
         "רייטינג i24 פחות ממוצע המתחרים. **חיובי = i24 מנצח**. **שלילי = i24 מפסיד**. "
         "מספר שלילי = עד כמה i24 מפגר אחרי הממוצע.",
         "ממוצע = -2.11 (i24 מפגר ב-2.11 נקודות רייטינג). "
         "i24 מנצח את ממוצע המתחרים ב-3.3% בלבד מהשידורים.",
         "מאיפה: רייטינג − ממוצע מתחרים."),
        ("HUT proxy", "תחרות", "🏠",
         "סכום רייטינג של כל 5 הערוצים (i24 + כאן + קשת + רשת + 14). "
         "קירוב למספר האנשים שצופים בטלוויזיה בכלל ברגע הזה. "
         "גבוה בשעות צפייה שיא, נמוך בלילה.",
         "ממוצע=10.64. פריים-טיים: ~20-30. לילה מאוחר: ~2-3.",
         "מאיפה: סכום 5 עמודות ה-רייטינג."),
        ("reception_pct", "נרמול", "📡",
         "אחוז מכשירי הפאנל שיכולים לקלוט את i24 באותו חודש. "
         "עולה באופן הדרגתי מ-65% (מאי 2025) ל-90% (אפריל 2026) — ראה 'מילון מושגים'.",
         "12 ערכים שונים (אחד לכל חודש). טווח: 0.65 עד 0.90.",
         "מאיפה: רמפה ליניארית מחושבת לפי חודש."),
        ("רייטינג מותאם", "נרמול", "📈",
         "**הרייטינג 'האמיתי'** — מה היה הרייטינג אם 100% מהפאנל יכלו לקלוט את i24. "
         "מאפשר השוואה הוגנת בין חודשים שונים.",
         "ממוצע=0.565 (לעומת 0.441 גולמי — גידול של 28%). "
         "מקסימום: 7.24 (אותו שיא ביטחוני בנרמול מלא).",
         "מאיפה: רייטינג ÷ reception_pct."),
        ("תג_עונה", "אירועים", "🗓️",
         "שם העונה (קיץ/חורף/אביב) שחלה בתאריך השידור, לפי `אירועים_מדויקים.csv`.",
         "'—' = ללא תיוג עונה מיוחד.",
         "מאיפה: תיוג לפי טווחי תאריכים מ-אירועים_מדויקים.csv."),
        ("תג_חג", "אירועים", "🎉",
         "שם החג שחל בתאריך השידור (ראש השנה / יום כיפור / סוכות / חנוכה / פורים / פסח). "
         "'—' = יום רגיל.",
         "937 שידורים (9.3%) חלו בימי חג.",
         "מאיפה: תיוג לפי תאריכים מדויקים שאומתו מויקיפדיה."),
        ("תג_ביטחוני", "אירועים", "🚨",
         "שם האירוע הביטחוני/מדיני שחל בתאריך השידור. אם מספר אירועים חפפפו — הם מחוברים ב-' + '. "
         "'—' = יום שגרה.",
         "1,572 שידורים (16%) עם תיוג ביטחוני.",
         "מאיפה: תיוג לפי תאריכים מדויקים מ-אירועים_מדויקים.csv."),
        ("אירוע_מיוחד", "אירועים", "🚨",
         "**עמודה מאוחדת:** הראשית מבין תג_ביטחוני / תג_חג / '—'. "
         "עדיפות: ביטחוני > חג > ללא. "
         "מאפשרת ניתוח פשוט: 'מה קרה ביום הזה?'",
         "2,169 שורות (21.6%) עם אירוע כלשהו. 7,870 (78.4%) ימי שגרה.",
         "מאיפה: לוגיקת עדיפות על תג_ביטחוני ותג_חג."),
        ("יום_חג", "אירועים", "✅",
         "כן/לא — האם תאריך השידור חל בחג?",
         "True = 937 שורות (9.3%). ימי חג מראים רייטינג ממוצע 0.60 לעומת 0.42 בשגרה (+43%).",
         "מאיפה: תג_חג ≠ '—'."),
        ("יום_ביטחוני", "אירועים", "✅",
         "כן/לא — האם תאריך השידור חל באירוע ביטחוני/מדיני?",
         "True = 1,572 שורות (16%). ימי אירוע מראים רייטינג 0.695 לעומת 0.394 בשגרה (+76%)!",
         "מאיפה: תג_ביטחוני ≠ '—'."),
        ("שבת", "אירועים", "✅",
         "כן/לא — האם השידור חל בשבת? חשוב כי בשבת ערוץ 14 לא משדר, "
         "מה שמשנה את ממוצע המתחרים ונותן ל-i24 יתרון יחסי.",
         "True = 1,311 שורות (13%). רייטינג ממוצע בשבת: 0.682 לעומת 0.405 בחול.",
         "מאיפה: יום שידור == 'שבת'."),
    ]

    for name, group, icon, explanation, values, source in cols_b:
        out.write(f"#### `{name}` {icon}\n")
        out.write(f"**{explanation}**\n")
        if values:
            out.write(f"*ערכים:* {values}\n")
        out.write(f"*מאיפה:* {source}\n\n")

    out.write("---\n\n")
    out.write("### 💡 איזה עמודות הכי חשובות לחיזוי?\n\n")
    out.write("מתוך ניתוח חשיבות מאפיינים (RandomForest), **76% מהחיזוי** מתבסס על:\n\n")
    out.write("| עמודה | חשיבות | למה? |\n")
    out.write("|---|---|---|\n")
    out.write("| `lag_slot_mean` (היסטוריית רצועה) | 51.8% | מה שהיה בשעה הזו בשבועות קודמים הוא הניבוי הטוב ביותר |\n")
    out.write("| `lag_status_slot_mean` (סטטוס × שעה) | 14.4% | שידור חי בפריים-טיים שונה מאוד משידור חוזר בפריים-טיים |\n")
    out.write("| `lag_program_mean` (היסטוריית תוכנית) | 5.7% | כמה הצופים אוהבים את התוכנית הזו היסטורית |\n")
    out.write("| `משך תוכנית_דק` | 5.3% | תוכניות ארוכות יותר נוטות לרייטינג גבוה יותר |\n\n")
    out.write("> **המסקנה:** רוב האינפורמציה גלומה ב'מה היה ברצועה הזו בשבועות האחרונים'. "
              "לכן לא ניתן לחזות אירועים ביטחוניים — שום היסטוריה לא תגיד לנו 'מחר יוכרז מבצע'.\n\n")
    return out.getvalue()


def main() -> None:
    df = load()
    ev = load_events()
    df = tag_events(df, ev)

    parts = [
        f"# EDA — תוכניות i24, רייטינג\n\n*נוצר ב-{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n",
        section_executive_summary(df),
        section_glossary(),
        section_overview(df),
        section_feature_guide(df),
        section_features(df),
        section_correlations(df),
        section_target(df),
        section_weekday(df),
        section_hour(df),
        section_rerun(df),
        section_advantage(df),
        section_events(df, ev),
        section_status(df),
        section_saturday(df),
        section_special_events(df),
        section_top_programs(df),
        section_time_trend(df),
        section_heatmap(df),
        section_monthly_deep(df),
        section_lakat(df),
        section_bottom_programs(df),
        section_notes(),
    ]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    export_xlsx(df, ev)
    print(f"Wrote {OUT_MD}  ({os.path.getsize(OUT_MD):,} bytes)")
    print(f"Wrote {OUT_XLSX}  ({os.path.getsize(OUT_XLSX):,} bytes)")
    print(f"Rows: {len(df):,}  |  Reruns: {df['is_rerun'].sum():,}  |  "
          f"Date range: {df['תאריך שידור'].min().date()} - {df['תאריך שידור'].max().date()}")
    print(f"Special-event rows: {(df['אירוע_מיוחד'] != '—').sum():,}")


if __name__ == "__main__":
    main()
