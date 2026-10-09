"""Taste-inspired editorial theme for the existing Streamlit recruitment dashboard."""
import streamlit as st


def apply_taste_theme():
    """Add an editorial sage/cream treatment without changing app logic."""
    st.markdown('''
    <style>
    :root {color-scheme:light}
    .stApp {background:#F6F3E9;color:#243D33}
    [data-testid="stHeader"] {background:#F6F3E9}
    [data-testid="stSidebar"] {background:#EAECE2;border-right:1px solid #D6DCD1}
    .block-container {max-width:1320px;padding:2rem 3.2rem 4rem}
    h1,h2,h3 {color:#263F34;letter-spacing:-.035em}
    h1 {font-family:Georgia,serif;font-weight:500;line-height:1.08}
    h2,h3 {font-family:Georgia,serif;font-weight:500}
    p, label {color:#526759}
    .hero {background:#E9EEE3!important;border:1px solid #D6DCCE!important;border-radius:9px!important;padding:35px 39px!important}
    .hero-title {font-family:Georgia,serif!important;font-weight:500!important;font-size:clamp(2rem,4vw,3.5rem)!important;letter-spacing:-.055em!important}
    .hero-subtitle {max-width:600px!important;font-size:1.05rem!important;line-height:1.7!important}
    .eyebrow,.section-kicker {letter-spacing:.17em!important;font-size:.68rem!important;text-transform:uppercase!important;color:#956D4B!important}
    [data-testid="stMetric"] {background:#FFFCF6!important;border:1px solid #D8DED2!important;border-radius:9px!important;box-shadow:none!important;padding:20px 24px!important}
    [data-testid="stMetricValue"] {font-family:Georgia,serif!important;font-size:2.1rem!important;color:#2E6048!important;font-weight:500!important}
    [data-testid="stTabs"] [data-baseweb="tab-list"] {gap:14px;border-bottom:1px solid #C9D2C6}
    [data-testid="stTabs"] button[role="tab"] {background:transparent!important;border-radius:0!important;color:#718172!important;padding:12px 3px!important}
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color:#2D6048!important;border-bottom:2px solid #2D6048!important;font-weight:700}
    .stButton button[kind="primary"] {background:#2E6048!important;border:1px solid #2E6048!important;color:white!important;border-radius:8px!important}
    .stButton button[kind="primary"]:hover {background:#254B39!important}
    .finding-card {border-radius:8px!important}
    [data-testid="stDataFrame"],[data-testid="stExpander"] {border-radius:8px}
    @media(max-width:900px){.block-container{padding:1.2rem}}
    </style>
    ''', unsafe_allow_html=True)
