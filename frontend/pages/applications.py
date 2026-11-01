"""
frontend/pages/applications.py
==============================
Application Management page tracking candidate pipeline flow,
stage progression, audit history, and application submissions.
"""

from typing import Any
import pandas as pd
import streamlit as st
from frontend.api_client import api_client
from frontend.components.tables import render_empty_state, render_page_header

APPLICATION_STAGES = [
    "applied",
    "screening",
    "interview",
    "assessment",
    "offer",
    "hired",
    "rejected",
]


def render_applications_page() -> None:
    """Renders the Application Pipeline & Progression view."""
    render_page_header(
        title="Application Pipeline & Tracking",
        subtitle="Monitor candidate progression through recruitment stages, track audit history, and advance applicant workflows.",
        icon="📑",
    )

    tab_list, tab_create = st.tabs(["📋 Applications Pipeline", "➕ Submit New Application"])

    # -----------------------------------------------------------------------
    # TAB 1: Applications Pipeline Directory
    # -----------------------------------------------------------------------
    with tab_list:
        col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
        with col_f1:
            stage_filter = st.selectbox(
                "Filter by Stage",
                options=["All Stages"] + APPLICATION_STAGES,
                index=0,
            )
        with col_f2:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All Statuses", "active", "rejected", "hired", "withdrawn"],
                index=0,
            )
        with col_f3:
            req_id_filter = st.number_input("Filter by Requisition ID", min_value=0, value=0, step=1)
        with col_f4:
            source_filter = st.selectbox(
                "Filter by Source",
                options=[
                    "All Sources", "LinkedIn", "Indeed", "Naukri", "Referral",
                    "Company Website", "Internshala", "HeadHunter", "Campus Placement"
                ],
                index=0,
            )

        selected_stage = None if stage_filter == "All Stages" else stage_filter
        selected_status = None if status_filter == "All Statuses" else status_filter
        selected_req = int(req_id_filter) if req_id_filter > 0 else None
        selected_source = None if source_filter == "All Sources" else source_filter

        with st.spinner("Loading applications from backend API..."):
            resp = api_client.get_applications(
                requisition_id=selected_req,
                current_stage=selected_stage,
                status=selected_status,
                source=selected_source,
                limit=100,
            )

        if not resp.success:
            st.error(f"Failed to fetch applications: {resp.error}")
            return

        applications = resp.data or []
        if not applications:
            render_empty_state(
                message="No applications found matching the selected filters.",
                action_hint="Adjust filter options or submit a new candidate application.",
            )
            return

        # Build Interactive Table
        table_rows = []
        for app in applications:
            table_rows.append({
                "App ID": app["application_id"],
                "Candidate ID": app["candidate_id"],
                "Requisition ID": app["requisition_id"],
                "Current Stage": app["current_stage"].replace("_", " ").title(),
                "Status": app["status"].title(),
                "Source": app.get("source") or "Direct",
                "Applied Date": str(app.get("created_at", ""))[:10],
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Stage Progression & History Inspector
        st.subheader("🔄 Application Details & Stage Progression")
        app_options = {
            f"App #{a['application_id']} (Candidate #{a['candidate_id']} -> Req #{a['requisition_id']} [{a['current_stage'].upper()}])": a['application_id']
            for a in applications
        }
        selected_label = st.selectbox("Select Application to Advance or Inspect:", list(app_options.keys()))

        if selected_label:
            selected_app_id = app_options[selected_label]
            col_a1, col_a2 = st.columns(2)

            with col_a1:
                st.markdown("<h5 style='color: #0F172A; font-weight: 700;'>Advance Application Stage</h5>", unsafe_allow_html=True)
                with st.form(f"advance_form_{selected_app_id}"):
                    target_stage = st.selectbox("Target Next Stage", APPLICATION_STAGES)
                    advance_notes = st.text_area(
                        "Transition Audit Notes",
                        placeholder="e.g. Candidate successfully cleared technical assessment and culture round.",
                    )
                    advance_btn = st.form_submit_button("Advance Stage", type="primary", use_container_width=True)
                    if advance_btn:
                        adv_resp = api_client.advance_application_stage(selected_app_id, target_stage, advance_notes)
                        if adv_resp.success:
                            st.success(f"Application #{selected_app_id} advanced to '{target_stage}'!")
                            st.rerun()
                        else:
                            st.error(f"Failed to advance stage: {adv_resp.error}")

            with col_a2:
                st.markdown("<h5 style='color: #0F172A; font-weight: 700;'>Stage Transition Audit Log</h5>", unsafe_allow_html=True)
                hist_resp = api_client.get_application_history(selected_app_id)
                if hist_resp.success and hist_resp.data:
                    hist_rows = []
                    for h in hist_resp.data:
                        hist_rows.append({
                            "From Stage": (h.get("previous_stage") or "Initial").replace("_", " ").title(),
                            "To Stage": h["new_stage"].replace("_", " ").title(),
                            "Changed At": str(h.get("changed_at", ""))[:19].replace("T", " "),
                            "Notes": h.get("notes") or "",
                        })
                    st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No stage history logged yet for this application.")

    # -----------------------------------------------------------------------
    # TAB 2: Submit New Application
    # -----------------------------------------------------------------------
    with tab_create:
        st.markdown("<h4 style='color: #0F172A; font-weight: 700; margin-bottom: 14px;'>Submit Candidate Application</h4>", unsafe_allow_html=True)
        with st.form("create_application_form"):
            col_ap1, col_ap2 = st.columns(2)
            with col_ap1:
                cand_id_in = st.number_input("Candidate ID *", min_value=1, step=1, help="ID of registered candidate")
                req_id_in = st.number_input("Job Requisition ID *", min_value=1, step=1, help="ID of open job requisition")
            with col_ap2:
                source_in = st.selectbox(
                    "Recruitment Source",
                    ["LinkedIn", "Indeed", "Naukri", "Referral", "Company Website", "Internshala", "HeadHunter", "Campus Placement"],
                )
                notes_in = st.text_input("Application Cover Notes", placeholder="Candidate profile attached")

            submit_app = st.form_submit_button("Submit Application", type="primary", use_container_width=True)
            if submit_app:
                payload = {
                    "candidate_id": int(cand_id_in),
                    "requisition_id": int(req_id_in),
                    "source": source_in,
                    "notes": notes_in.strip() if notes_in else None,
                }
                c_resp = api_client.create_application(payload)
                if c_resp.success:
                    st.success(f"Application submitted successfully with ID #{c_resp.data['application_id']}!")
                    st.rerun()
                else:
                    st.error(f"Application submission failed: {c_resp.error}")
