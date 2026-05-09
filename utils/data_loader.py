# -*- coding: utf-8 -*-
"""Cached data loaders for the i24 ratings app."""
import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@st.cache_data
def load_processed() -> pd.DataFrame:
    """Load the engineered dataset (10K rows × 34 cols)."""
    path = os.path.join(DATA_DIR, "תוכניות_מעובד.xlsx")
    df = pd.read_excel(path, sheet_name="נתונים מעובדים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    return df


@st.cache_data
def load_predictions() -> pd.DataFrame:
    """Load the all-models predictions on the test set."""
    path = os.path.join(DATA_DIR, "predictions_all.xlsx")
    df = pd.read_excel(path, sheet_name="חיזויים")
    df["תאריך שידור"] = pd.to_datetime(df["תאריך שידור"])
    return df


@st.cache_data
def load_metrics_summary() -> pd.DataFrame:
    """Load the per-model metrics summary."""
    path = os.path.join(DATA_DIR, "predictions_all.xlsx")
    return pd.read_excel(path, sheet_name="סיכום מטריקות", index_col=0)


@st.cache_data
def load_events() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "אירועים_מדויקים.csv")
    return pd.read_csv(path)


def best_model_column() -> str:
    """The model column we'll show by default — the V3 winner."""
    return "חזוי_13_HistGradientBoosting"
