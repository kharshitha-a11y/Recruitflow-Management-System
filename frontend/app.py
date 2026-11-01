"""
frontend/app.py
===============
RecruitFlow – Enterprise Recruitment Management & Analytics Frontend.
Built with Streamlit, Plotly, and REST integration with the FastAPI backend.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from frontend.components.sidebar import render_sidebar
from frontend.pages.dashboard import render_dashboard_page
from frontend.pages.candidates import render_candidates_page
from frontend.pages.requisitions import render_requisitions_page
from frontend.pages.applications import render_applications_page
from frontend.pages.interviews import render_interviews_page
from frontend.pages.offers import render_offers_page
from frontend.pages.anomalies import render_anomalies_page

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RecruitFlow Enterprise",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Enterprise SaaS Custom Styling
# ---------------------------------------------------------------------------
CUSTOM_CSS = """<style>
    /* Global Typography & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    }
    
    .stApp {
        background-color: #F8FAFC !important;
    }

    /* Content Area Max Width & Clean Padding */
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 1400px !important;
    }

    /* Clean Card Containers */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        border-radius: 10px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    /* Streamlit Metric Overrides */
    div[data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        color: #0F172A !important;
        letter-spacing: -0.02em !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: all 0.15s ease-in-out !important;
        padding: 0.45rem 1rem !important;
    }

    /* Primary Button */
    .stButton > button[kind="primary"] {
        background: #2563EB !important;
        border-color: #2563EB !important;
        color: #FFFFFF !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1D4ED8 !important;
        border-color: #1D4ED8 !important;
    }

    /* Secondary Button */
    .stButton > button[kind="secondary"] {
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #F1F5F9 !important;
        border-color: #94A3B8 !important;
    }

    /* Form Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 6px !important;
        border-color: #CBD5E1 !important;
        font-size: 0.9rem !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 18px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        font-weight: 600;
        font-size: 0.92rem;
        color: #64748B;
        border-radius: 6px 6px 0 0;
        background-color: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #2563EB !important;
        border-bottom: 2px solid #2563EB !important;
    }

    /* Table & Dataframe Borders */
    div[data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        background: #FFFFFF !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        color: #1E293B !important;
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    /* Plotly Chart Card Styling */
    .js-plotly-plot {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        padding: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }

    /* Hide Streamlit Default Hamburger & Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main():
    """Application router dispatching to selected page module."""
    selected_page = render_sidebar()

    if selected_page == "📊 Main Dashboard":
        render_dashboard_page()
    elif selected_page == "👤 Candidate Management":
        render_candidates_page()
    elif selected_page == "📋 Requisition Management":
        render_requisitions_page()
    elif selected_page == "📑 Application Management":
        render_applications_page()
    elif selected_page == "📅 Interview Management":
        render_interviews_page()
    elif selected_page == "💼 Offer Management":
        render_offers_page()
    elif selected_page == "🔍 Anomaly Monitoring":
        render_anomalies_page()
    else:
        render_dashboard_page()


if __name__ == "__main__":
    main()
