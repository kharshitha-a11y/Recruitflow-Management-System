"""
frontend/pages/anomalies.py
===========================
Data Quality and Anomaly Monitoring Hub providing real-time compliance metrics,
A01-A10 breakdown charts, audit logs, and investigation status workflow controls.
"""

from typing import Any
import pandas as pd
import streamlit as st
from frontend.api_client import api_client
from frontend.components.charts import (
    chart_anomalies_by_category,
    chart_anomalies_by_severity,
)
from frontend.components.metrics import render_metric_row
from frontend.components.tables import render_empty_state, render_page_header

SEVERITY_OPTIONS = ["All", "Critical", "High", "Medium", "Low"]
STATUS_OPTIONS = ["All", "Open", "Investigating", "Resolved", "False Positive"]
CATEGORY_OPTIONS = [
    "All", "A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10"
]


def render_anomalies_page() -> None:
    """Renders the Anomaly Monitoring & Data Quality Hub."""
    col_t, col_a = st.columns([3.5, 1.5])
    with col_t:
        render_page_header(
            title="Data Quality & Anomaly Monitoring Hub",
            subtitle="Automated compliance audit engine detecting recruitment discrepancies across rules A01 to A10.",
            icon="🔍",
        )
    with col_a:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Run Anomaly Detection Engine", type="primary", use_container_width=True):
            with st.spinner("Executing full database scan across rules A01 to A10..."):
                run_resp = api_client.run_anomaly_detection()
                if run_resp.success:
                    new_cnt = run_resp.data.get("new_anomalies_detected", 0)
                    prev_cnt = run_resp.data.get("previously_existing_active_anomalies", 0)
                    st.success(f"Audit completed: {new_cnt} new anomalies detected, {prev_cnt:,} active anomalies verified.")
                    st.rerun()
                else:
                    st.error(f"Anomaly detection failed: {run_resp.error}")

    # Fetch live summary metrics
    with st.spinner("Fetching data quality summary from backend API..."):
        summary_resp = api_client.get_anomaly_summary()

    if not summary_resp.success:
        st.error(f"Failed to fetch anomaly summary: {summary_resp.error}")
        return

    summary = summary_resp.data or {}
    severities = summary.get("anomalies_by_severity", {})
    statuses = summary.get("anomalies_by_status", {})
    categories = summary.get("anomalies_by_category", {})
    cat_descs = summary.get("category_descriptions", {})

    # -----------------------------------------------------------------------
    # Section 1: KPI Summary Cards
    # -----------------------------------------------------------------------
    dq_pct = float(summary.get("data_quality_percentage", 100.0))
    badge_dq = "success" if dq_pct >= 85 else ("warning" if dq_pct >= 60 else "danger")

    row_1 = [
        {
            "title": "Data Quality Score",
            "value": f"{dq_pct:.2f}%",
            "subtitle": f"{summary.get('clean_records_count', 0):,} / {summary.get('total_records_inspected', 0):,} clean records",
            "badge": "Entity Yield",
            "badge_type": badge_dq,
            "border_accent": "#10B981" if dq_pct >= 85 else "#F59E0B",
            "icon": "🛡️",
        },
        {
            "title": "Total Anomalies",
            "value": f"{summary.get('total_anomalies_found', 0):,}",
            "subtitle": f"{summary.get('unique_anomalous_entities', 0):,} unique entities flagged",
            "badge": "Discrepancies",
            "badge_type": "danger",
            "border_accent": "#DC2626",
            "icon": "⚠️",
        },
        {
            "title": "Open Issues",
            "value": f"{statuses.get('Open', 0):,}",
            "subtitle": f"Investigating: {statuses.get('Investigating', 0):,}",
            "badge": "Action Required",
            "badge_type": "warning",
            "border_accent": "#EA580C",
            "icon": "⚡",
        },
        {
            "title": "Resolved Issues",
            "value": f"{statuses.get('Resolved', 0) + statuses.get('False Positive', 0):,}",
            "subtitle": "Remediated compliance records",
            "badge": "Audited",
            "badge_type": "success",
            "border_accent": "#059669",
            "icon": "✅",
        },
    ]
    render_metric_row(row_1)

    # Row 2: Severity Distribution
    row_2 = [
        {
            "title": "Critical Severity",
            "value": f"{severities.get('Critical', 0):,}",
            "subtitle": "Immediate intervention required",
            "badge": "Critical",
            "badge_type": "danger",
            "border_accent": "#991B1B",
            "icon": "🔴",
        },
        {
            "title": "High Severity",
            "value": f"{severities.get('High', 0):,}",
            "subtitle": "Workflow & panel inconsistencies",
            "badge": "High",
            "badge_type": "warning",
            "border_accent": "#EA580C",
            "icon": "🟠",
        },
        {
            "title": "Medium Severity",
            "value": f"{severities.get('Medium', 0):,}",
            "subtitle": "Experience & rating deviations",
            "badge": "Medium",
            "badge_type": "warning",
            "border_accent": "#EAB308",
            "icon": "🟡",
        },
        {
            "title": "Low Severity",
            "value": f"{severities.get('Low', 0):,}",
            "subtitle": "Minor overqualification entries",
            "badge": "Low",
            "badge_type": "info",
            "border_accent": "#2563EB",
            "icon": "🔵",
        },
    ]
    render_metric_row(row_2)

    st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 20px 0;'>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Section 2: Visualizations Grid
    # -----------------------------------------------------------------------
    col_c1, col_c2 = st.columns([1.6, 1.0])
    with col_c1:
        st.plotly_chart(
            chart_anomalies_by_category(categories, cat_descs),
            use_container_width=True,
        )
    with col_c2:
        st.plotly_chart(
            chart_anomalies_by_severity(severities),
            use_container_width=True,
        )

    st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 20px 0;'>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Section 3: Interactive Anomaly Explorer & Status Update Workflow
    # -----------------------------------------------------------------------
    st.subheader("📋 Anomaly Investigation & Remediation Table")

    col_flt1, col_flt2, col_flt3, col_flt4 = st.columns(4)
    with col_flt1:
        cat_sel = st.selectbox("Filter Category", CATEGORY_OPTIONS, index=0)
    with col_flt2:
        sev_sel = st.selectbox("Filter Severity", SEVERITY_OPTIONS, index=0)
    with col_flt3:
        st_sel = st.selectbox("Filter Status", STATUS_OPTIONS, index=0)
    with col_flt4:
        limit_sel = st.selectbox("Page Size", [50, 100, 200], index=0)

    category_arg = None if cat_sel == "All" else cat_sel
    severity_arg = None if sev_sel == "All" else sev_sel
    status_arg = None if st_sel == "All" else st_sel

    with st.spinner("Loading anomaly records from backend API..."):
        anom_resp = api_client.get_anomalies(
            category=category_arg,
            severity=severity_arg,
            status=status_arg,
            limit=limit_sel,
        )

    if not anom_resp.success:
        st.error(f"Failed to fetch anomalies: {anom_resp.error}")
        return

    anomalies = anom_resp.data or []
    if not anomalies:
        render_empty_state(
            message="No anomalies match the selected filters.",
            action_hint="Select 'All' to view the full audit history.",
        )
        return

    table_rows = []
    for a in anomalies:
        table_rows.append({
            "Anomaly ID": a["anomaly_id"],
            "Rule": a["anomaly_code"],
            "Entity": f"{a['entity_type'].title()} #{a['entity_id']}",
            "Severity": a["severity"],
            "Status": a["status"],
            "Description": a["description"],
            "Recommended Action": a["recommended_action"],
            "Detected At": str(a.get("detected_at", ""))[:19].replace("T", " "),
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # Status Update Controller
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    with st.expander("🛠️ Update Anomaly Investigation Status", expanded=True):
        anom_choice_map = {
            f"#{a['anomaly_id']} [{a['anomaly_code']} - {a['severity']}] {a['entity_type']} #{a['entity_id']} ({a['status']})": a["anomaly_id"]
            for a in anomalies
        }
        selected_anom_label = st.selectbox("Select Anomaly to Update:", list(anom_choice_map.keys()))

        if selected_anom_label:
            selected_anom_id = anom_choice_map[selected_anom_label]
            col_u1, col_u2 = st.columns([2, 3])
            with col_u1:
                new_anom_status = st.selectbox(
                    "New Status",
                    ["Investigating", "Resolved", "False Positive", "Open"],
                )
            with col_u2:
                status_notes = st.text_input(
                    "Remediation Notes",
                    placeholder="e.g. Verified with hiring manager; duplicate entry flagged for cleanup.",
                )

            if st.button("Apply Status Change", type="primary"):
                up_resp = api_client.update_anomaly_status(selected_anom_id, new_anom_status, status_notes)
                if up_resp.success:
                    st.success(f"Anomaly #{selected_anom_id} status updated to '{new_anom_status}'!")
                    st.rerun()
                else:
                    st.error(f"Status update failed: {up_resp.error}")
