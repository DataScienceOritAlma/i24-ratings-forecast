# -*- coding: utf-8 -*-
"""Lightweight password gate for Streamlit.

Reads APP_PASSWORD from .streamlit/secrets.toml (or env var as fallback).
Anyone with the URL must enter the password before seeing the app.
"""
import os
import streamlit as st


def _get_password() -> str:
    try:
        return st.secrets["APP_PASSWORD"]
    except Exception:
        return os.environ.get("APP_PASSWORD", "")


def require_password() -> bool:
    """Returns True if the user has entered the correct password.
    Otherwise renders the password form and stops the script."""
    expected = _get_password()
    if not expected:
        st.warning("⚠️ לא הוגדרה סיסמה. עדכן/י `APP_PASSWORD` ב-secrets.toml")
        return True

    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 🔐 כניסה לחיזויי i24")
    pw = st.text_input("סיסמה", type="password", key="pw_input")
    if st.button("כניסה", type="primary"):
        if pw == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("סיסמה שגויה")
    st.stop()
