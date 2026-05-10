# -*- coding: utf-8 -*-
"""Shared visual style for all pages — modern, polished design system.

Call apply_style() at the top of each Streamlit page (after set_page_config).
"""
import streamlit as st


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

/* ----- Typography ----- */
* {
  font-family: 'Heebo', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}

/* ----- RTL ----- */
.main, .block-container, [data-testid="stSidebar"] {
  direction: rtl;
  text-align: right;
}
[data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }

/* ----- Page background ----- */
[data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 50%, #F8FAFC 100%);
}

[data-testid="stHeader"] {
  background: transparent;
}

/* ----- Sidebar ----- */
[data-testid="stSidebar"] {
  background: white !important;
  border-left: 1px solid #E5E7EB;
  box-shadow: -2px 0 8px rgba(0,0,0,0.03);
}

[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
  border-radius: 10px;
  margin: 4px 8px;
  padding: 10px 14px;
  transition: all 0.2s ease;
  font-weight: 500;
}

[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
  background: linear-gradient(90deg, #EFF6FF 0%, #DBEAFE 100%);
  transform: translateX(-3px);
}

[data-testid="stSidebar"] [data-testid="stSidebarNav"] [aria-current="page"] {
  background: linear-gradient(90deg, #2563EB 0%, #1D4ED8 100%);
  color: white !important;
}

/* ----- Headers ----- */
h1 {
  color: #1E3A8A !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em;
  margin-bottom: 0.5rem !important;
}

h2 {
  color: #1F2937 !important;
  font-weight: 700 !important;
  border-bottom: 3px solid;
  border-image: linear-gradient(90deg, #2563EB, #DBEAFE) 1;
  padding-bottom: 10px;
  margin-top: 2rem !important;
  letter-spacing: -0.01em;
}

h3 {
  color: #374151 !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em;
}

h4, h5, h6 {
  color: #4B5563 !important;
  font-weight: 600 !important;
}

/* ----- Metrics ----- */
[data-testid="stMetric"] {
  background: white;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px solid #E5E7EB;
  box-shadow: 0 2px 4px rgba(0,0,0,0.04);
  transition: all 0.2s ease;
}

[data-testid="stMetric"]:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}

[data-testid="stMetricValue"] {
  direction: ltr;
  text-align: right;
  font-size: 2rem !important;
  font-weight: 800 !important;
  color: #1E40AF !important;
  letter-spacing: -0.02em;
}

[data-testid="stMetricLabel"] {
  color: #6B7280 !important;
  font-weight: 500;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

[data-testid="stMetricDelta"] {
  font-size: 0.85rem;
  font-weight: 600;
}

/* ----- Buttons ----- */
.stButton > button {
  direction: rtl;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.95rem;
  padding: 10px 24px;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  border: 1px solid #E5E7EB;
}

.stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.1);
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
  color: white;
  border: none;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
}

.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #1D4ED8 0%, #1E3A8A 100%);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.5);
}

.stDownloadButton > button {
  border-radius: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  color: white !important;
  border: none;
  padding: 10px 20px;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

/* ----- Containers (with border=True) ----- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: white !important;
  border-radius: 16px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
  padding: 8px !important;
  border: 1px solid #E5E7EB !important;
}

/* ----- DataFrames ----- */
[data-testid="stDataFrame"] {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #E5E7EB;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* ----- Expanders ----- */
.streamlit-expanderHeader {
  border-radius: 12px;
  background: white;
  font-weight: 600;
  border: 1px solid #E5E7EB;
}

[data-testid="stExpander"] {
  border: 1px solid #E5E7EB !important;
  border-radius: 12px !important;
  background: white !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ----- Alerts ----- */
.stAlert {
  border-radius: 12px;
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  padding: 14px 18px;
}

[data-testid="stAlert"][data-baseweb="notification"] {
  border-radius: 12px;
}

/* ----- Inputs ----- */
.stTextInput input, .stNumberInput input, .stTimeInput input,
.stSelectbox > div > div, .stDateInput > div > div {
  border-radius: 10px !important;
  border: 1px solid #E5E7EB !important;
  transition: all 0.2s ease !important;
}

.stTextInput input:focus, .stNumberInput input:focus,
.stSelectbox > div > div:focus-within, .stDateInput > div > div:focus-within {
  border-color: #2563EB !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

/* ----- Radio + Checkbox ----- */
.stRadio [role="radiogroup"] {
  gap: 8px;
}

.stRadio [role="radiogroup"] label {
  background: white;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid #E5E7EB;
  transition: all 0.2s ease;
  cursor: pointer;
}

.stRadio [role="radiogroup"] label:hover {
  border-color: #2563EB;
  background: #EFF6FF;
}

/* ----- Captions ----- */
[data-testid="stCaptionContainer"] {
  color: #6B7280 !important;
  font-size: 0.875rem;
}

/* ----- Plotly ----- */
.js-plotly-plot {
  border-radius: 12px;
  overflow: hidden;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  padding: 8px;
}

/* ----- Hero card ----- */
.hero-result {
  background: linear-gradient(135deg, #2563EB 0%, #1E40AF 50%, #1E3A8A 100%);
  border-radius: 20px;
  padding: 36px 32px;
  color: white;
  text-align: center;
  box-shadow: 0 10px 40px rgba(37, 99, 235, 0.3);
  margin: 24px 0;
}

.hero-result .number {
  font-size: 5em;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.04em;
  text-shadow: 0 4px 20px rgba(0,0,0,0.2);
  background: linear-gradient(180deg, #FFFFFF 0%, #DBEAFE 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-result .label {
  font-size: 1.15em;
  opacity: 0.95;
  margin-top: 12px;
  font-weight: 500;
}

.hero-result .meta {
  margin-top: 16px;
  font-size: 0.95em;
  opacity: 0.85;
  font-weight: 400;
}

/* ----- Scenario cards ----- */
.scenario-card {
  padding: 20px;
  border-radius: 16px;
  background: white;
  border: 1px solid #E5E7EB;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: all 0.2s ease;
}

.scenario-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0,0,0,0.08);
}

.scenario-card.selected {
  border: 3px solid #2563EB;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.2);
}

/* ----- Hide Streamlit chrome ----- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.stDeployButton { display: none; }

/* ----- Divider ----- */
hr {
  border: none;
  border-top: 1px solid #E5E7EB;
  margin: 2rem 0;
}

/* ----- Tooltips ----- */
[data-baseweb="tooltip"] {
  border-radius: 8px !important;
  font-size: 0.85rem;
}

/* ----- Bottom padding for the page ----- */
.main .block-container {
  padding-bottom: 4rem;
}
</style>
"""


def apply_style():
    """Apply the unified visual style. Call once per page after set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)
