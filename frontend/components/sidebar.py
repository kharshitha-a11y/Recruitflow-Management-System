"""
frontend/components/sidebar.py
==============================
Enterprise sidebar navigation, branding, and live backend health status.
Constructed with zero leading markdown indentation to guarantee proper HTML rendering.
"""

import streamlit as st
from frontend.api_client import api_client

PAGES = [
    "📊 Main Dashboard",
    "👤 Candidate Management",
    "📋 Requisition Management",
    "📑 Application Management",
    "📅 Interview Management",
    "💼 Offer Management",
    "🔍 Anomaly Monitoring",
]


def render_sidebar() -> str:
    """
    Renders enterprise sidebar branding and returns the selected page name.
    """
    with st.sidebar:
        # Branding Header
        header_html = (
            '<div style="padding: 10px 0 18px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 18px;">'
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<div style="width: 38px; height: 38px; '
            'background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%); '
            'border-radius: 8px; display: flex; align-items: center; justify-content: center; '
            'color: white; font-weight: 800; font-size: 1.25rem; '
            'box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);">'
            'RF</div>'
            '<div>'
            '<div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; line-height: 1.2; letter-spacing: -0.02em;">'
            'RecruitFlow</div>'
            '<div style="font-size: 0.75rem; font-weight: 500; color: #64748B;">'
            'Enterprise Recruitment SaaS</div>'
            '</div></div></div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)

        # Live Backend Connectivity Badge
        health = api_client.check_health()
        if health.success:
            version = health.data.get("version", "1.0.0") if isinstance(health.data, dict) else "1.0.0"
            badge_html = (
                f'<div style="background: #DEF7EC; border: 1px solid #BCF0DA; color: #03543F; '
                f'padding: 7px 12px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; '
                f'display: flex; align-items: center; gap: 8px; margin-bottom: 20px;">'
                f'<span style="color: #10B981; font-size: 0.85rem;">●</span> Backend Connected (v{version})'
                f'</div>'
            )
        else:
            badge_html = (
                '<div style="background: #FDE8E8; border: 1px solid #FBD5D5; color: #9B1C1C; '
                'padding: 7px 12px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; '
                'display: flex; align-items: center; gap: 8px; margin-bottom: 20px;">'
                '<span style="color: #EF4444; font-size: 0.85rem;">●</span> Backend Disconnected'
                '</div>'
            )
        st.markdown(badge_html, unsafe_allow_html=True)

        # Navigation Menu Header
        nav_label = (
            '<div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; '
            'letter-spacing: 0.05em; color: #64748B; margin-bottom: 8px;">Navigation</div>'
        )
        st.markdown(nav_label, unsafe_allow_html=True)

        selected_page = st.radio(
            label="Navigation Menu",
            options=PAGES,
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)

        # System Architecture Footnote
        footer_html = (
            '<div style="font-size: 0.75rem; color: #94A3B8; line-height: 1.5;">'
            '<b>Stack:</b> FastAPI • PostgreSQL • Streamlit<br>'
            '<b>Architecture:</b> 100% REST APIs (Zero Direct DB)'
            '</div>'
        )
        st.markdown(footer_html, unsafe_allow_html=True)

        return selected_page
