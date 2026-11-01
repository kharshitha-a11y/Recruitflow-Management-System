"""
frontend/pages/dashboard.py
===========================
Main executive recruitment analytics dashboard with real-time KPI metrics
and interactive Plotly visualizations.
"""

import streamlit as st
from frontend.api_client import api_client
from frontend.components.charts import (
    chart_department_requisitions,
    chart_interview_outcomes,
    chart_monthly_trends,
    chart_offer_status,
    chart_source_distribution,
    chart_stage_funnel,
)
from frontend.components.metrics import render_metric_row
from frontend.components.tables import render_empty_state, render_page_header


def render_dashboard_page() -> None:
    """Renders the executive recruitment analytics dashboard."""
    col_title, col_action = st.columns([4, 1.2])
    with col_title:
        render_page_header(
            title="Recruitment Analytics Dashboard",
            subtitle="Real-time recruitment lifecycle KPIs, velocity benchmarks, and pipeline analytics powered by FastAPI & PostgreSQL.",
            icon="📊",
        )
    with col_action:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Analytics", use_container_width=True, type="secondary"):
            st.rerun()

    # Fetch live aggregations from backend API
    with st.spinner("Loading live recruitment metrics from backend API..."):
        resp = api_client.get_analytics_overview()

    if not resp.success:
        st.error(f"Failed to load dashboard metrics from backend: {resp.error}")
        render_empty_state(
            message="Backend Analytics Service Offline",
            action_hint="Ensure the FastAPI backend is running at http://localhost:8000 and click Refresh.",
        )
        return

    data = resp.data or {}

    # -----------------------------------------------------------------------
    # Section 1: KPI Cards Grid (8 Key Metrics)
    # -----------------------------------------------------------------------
    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # Row 1: Volume Metrics
    row_1 = [
        {
            "title": "Total Candidates",
            "value": f"{data.get('total_candidates', 0):,}",
            "subtitle": "Active talent directory pool",
            "badge": "Talent Pool",
            "badge_type": "info",
            "border_accent": "#2563EB",
            "icon": "👤",
        },
        {
            "title": "Total Requisitions",
            "value": f"{data.get('total_requisitions', 0):,}",
            "subtitle": "All opened headcount demands",
            "badge": "Requisitions",
            "badge_type": "neutral",
            "border_accent": "#64748B",
            "icon": "📋",
        },
        {
            "title": "Open Positions",
            "value": f"{data.get('open_positions', 0):,}",
            "subtitle": "Actively hiring openings",
            "badge": "Active",
            "badge_type": "success",
            "border_accent": "#10B981",
            "icon": "🟢",
        },
        {
            "title": "Total Applications",
            "value": f"{data.get('total_applications', 0):,}",
            "subtitle": "Cumulative candidate submissions",
            "badge": "Pipeline",
            "badge_type": "purple",
            "border_accent": "#8B5CF6",
            "icon": "📑",
        },
    ]
    render_metric_row(row_1)

    # Row 2: Velocity & Outcome Metrics
    conv_rate = float(data.get("hiring_conversion_rate", 0.0))
    time_to_hire = float(data.get("avg_time_to_hire_days", 0.0))

    row_2 = [
        {
            "title": "Interviews Scheduled",
            "value": f"{data.get('interviews_scheduled', 0):,}",
            "subtitle": "Completed & upcoming rounds",
            "badge": "Interviews",
            "badge_type": "info",
            "border_accent": "#06B6D4",
            "icon": "📅",
        },
        {
            "title": "Offers Released",
            "value": f"{data.get('offers_released', 0):,}",
            "subtitle": f"{data.get('offer_acceptance_rate', 0.0):.1f}% candidate acceptance rate",
            "badge": "Offers",
            "badge_type": "warning",
            "border_accent": "#F59E0B",
            "icon": "💼",
        },
        {
            "title": "Hiring Conversion",
            "value": f"{conv_rate:.2f}%",
            "subtitle": "Applicant-to-hire pipeline yield",
            "badge": "Efficiency",
            "badge_type": "success" if conv_rate >= 10 else "neutral",
            "border_accent": "#10B981",
            "icon": "🎯",
        },
        {
            "title": "Avg Time to Hire",
            "value": f"{time_to_hire:.1f} days",
            "subtitle": "Application creation to offer acceptance",
            "badge": "Velocity",
            "badge_type": "neutral",
            "border_accent": "#EC4899",
            "icon": "⏱️",
        },
    ]
    render_metric_row(row_2)

    st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 20px 0;'>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Section 2: Visualizations Grid (Row 1 - Pipeline & Sourcing)
    # -----------------------------------------------------------------------
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.plotly_chart(
            chart_stage_funnel(data.get("applications_by_stage", {})),
            use_container_width=True,
        )
    with col_c2:
        st.plotly_chart(
            chart_source_distribution(data.get("applications_by_source", {})),
            use_container_width=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Section 3: Visualizations Grid (Row 2 - Trends & Departments)
    # -----------------------------------------------------------------------
    col_c3, col_c4 = st.columns(2)
    with col_c3:
        st.plotly_chart(
            chart_monthly_trends(data.get("hiring_trends", [])),
            use_container_width=True,
        )
    with col_c4:
        st.plotly_chart(
            chart_department_requisitions(data.get("requisitions_by_department", [])),
            use_container_width=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Section 4: Visualizations Grid (Row 3 - Evaluations & Offers)
    # -----------------------------------------------------------------------
    col_c5, col_c6 = st.columns(2)
    with col_c5:
        st.plotly_chart(
            chart_interview_outcomes(data.get("interview_outcomes", {})),
            use_container_width=True,
        )
    with col_c6:
        st.plotly_chart(
            chart_offer_status(data.get("offer_status_breakdown", {})),
            use_container_width=True,
        )
