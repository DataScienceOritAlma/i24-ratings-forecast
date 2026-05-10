# -*- coding: utf-8 -*-
"""Data loader — upload-based, session state.

The deployed app does NOT carry data files. Users upload them at runtime
via Streamlit file_uploader. Loaded DataFrames are kept in st.session_state
so they persist across pages within the same browser session.
"""
import pandas as pd
import streamlit as st


SESSION_KEYS = {
    "processed": "df_processed",
    "predictions": "df_predictions",
    "metrics": "df_metrics",
    "events": "df_events",
}


def is_data_loaded() -> bool:
    """True if at minimum the processed + predictions data are loaded."""
    return (SESSION_KEYS["processed"] in st.session_state
            and SESSION_KEYS["predictions"] in st.session_state)


def get_processed() -> pd.DataFrame:
    return st.session_state.get(SESSION_KEYS["processed"])


def get_predictions() -> pd.DataFrame:
    return st.session_state.get(SESSION_KEYS["predictions"])


def get_metrics() -> pd.DataFrame:
    return st.session_state.get(SESSION_KEYS["metrics"])


def get_events() -> pd.DataFrame:
    return st.session_state.get(SESSION_KEYS["events"])


def best_model_column() -> str:
    return "חזוי_13_HistGradientBoosting"


def render_upload_panel() -> None:
    """Render upload widgets. Updates session_state when files are loaded."""
    st.subheader("📤 העלאת קבצי נתונים")
    st.markdown("""
    כדי להפעיל את האפליקציה, יש להעלות את הקבצים הבאים:

    1. **`תוכניות_מעובד.xlsx`** — הדאטה המעובד (חובה)
    2. **`predictions_all.xlsx`** — חיזויי 19 המודלים (חובה)
    3. **`אירועים_מדויקים.csv`** — אירועים מתויגים (אופציונלי)

    > 🔒 **פרטיות:** הקבצים נטענים לזיכרון בלבד למשך הסשן ולא נשמרים בשרת.
    > כשתסגרי את הדפדפן — הנתונים נמחקים.
    """)

    col1, col2 = st.columns(2)

    with col1:
        f_processed = st.file_uploader(
            "תוכניות_מעובד.xlsx",
            type=["xlsx"],
            key="upl_processed",
            help="קובץ הדאטה המעובד (10,039 שורות × 34 עמודות)",
        )

    with col2:
        f_predictions = st.file_uploader(
            "predictions_all.xlsx",
            type=["xlsx"],
            key="upl_predictions",
            help="קובץ חיזויי 19 המודלים על מבחן",
        )

    f_events = st.file_uploader(
        "אירועים_מדויקים.csv (אופציונלי)",
        type=["csv"],
        key="upl_events",
        help="17 אירועים מתויגים — לא חובה",
    )

    if f_processed and f_predictions:
        if st.button("🚀 טעני נתונים", type="primary", use_container_width=True):
            try:
                with st.spinner("טוען נתונים..."):
                    df = pd.read_excel(f_processed, sheet_name="נתונים מעובדים")
                    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
                    st.session_state[SESSION_KEYS["processed"]] = df

                    preds = pd.read_excel(f_predictions, sheet_name="חיזויים")
                    preds["תאריך שידור"] = pd.to_datetime(preds["תאריך שידור"])
                    st.session_state[SESSION_KEYS["predictions"]] = preds

                    try:
                        metrics = pd.read_excel(f_predictions,
                                                sheet_name="סיכום מטריקות",
                                                index_col=0)
                        st.session_state[SESSION_KEYS["metrics"]] = metrics
                    except Exception:
                        st.warning("גליון 'סיכום מטריקות' לא נמצא ב-predictions_all.xlsx — דף 'השוואת מודלים' יעבוד חלקית")

                    if f_events is not None:
                        events = pd.read_csv(f_events)
                        st.session_state[SESSION_KEYS["events"]] = events

                st.success("✅ נתונים נטענו בהצלחה! גללי לתוכן או עברי בין הדפים בתפריט.")
                st.rerun()
            except Exception as e:
                st.error(f"שגיאה בטעינת קבצים: {e}")
                st.exception(e)
    else:
        st.info("👆 העלי את שני הקבצים החובה כדי להפעיל את האפליקציה")


def require_data_or_redirect() -> None:
    """Use this at top of sub-pages: if no data, show a friendly message."""
    if not is_data_loaded():
        st.warning("⚠️ אין נתונים טעונים. חזרי לדף הבית והעלי את הקבצים.")
        st.markdown("[← חזרה לדף הבית](/)")
        st.stop()
