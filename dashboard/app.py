# ---------------------------------------------------------------------------
# app.py — Streamlit dashboard entry point
# ---------------------------------------------------------------------------
# Run with:  streamlit run dashboard/app.py
# ---------------------------------------------------------------------------

import os
import sys

# MUST be first: ensure project root is on sys.path
# Streamlit uses exec() for pages, so __file__ may not resolve reliably.
# Use os.getcwd() which is the project root when invoked correctly.
_root = os.getcwd()
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from dashboard.styles import inject_css

st.set_page_config(
    page_title="LLM Cost Router",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# -- Sidebar navigation -------------------------------------------------------

st.sidebar.title("LLM Cost Router")
st.sidebar.markdown("---")

PAGES = {
    "Overview": "overview",
    "Live Router": "live_router",
    "Request Explorer": "request_explorer",
    "Model Comparison": "model_comparison",
    "Evaluation Lab": "evaluation_lab",
    "Observability": "observability",
}

selected = st.sidebar.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.caption("Phase 10 — Dashboard")

# -- Page routing --------------------------------------------------------------

page = PAGES[selected]

if page == "overview":
    from dashboard.pages import overview
    overview.render()
elif page == "live_router":
    from dashboard.pages import live_router
    live_router.render()
elif page == "request_explorer":
    from dashboard.pages import request_explorer
    request_explorer.render()
elif page == "model_comparison":
    from dashboard.pages import model_comparison
    model_comparison.render()
elif page == "evaluation_lab":
    from dashboard.pages import evaluation_lab
    evaluation_lab.render()
elif page == "observability":
    from dashboard.pages import observability
    observability.render()
