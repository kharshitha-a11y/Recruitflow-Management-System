"""
frontend/pages/interviews.py
============================
Interview & Scorecard Management page for scheduling rounds, assigning panelists,
submitting evaluations, and viewing interviewer feedback summaries.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import pandas as pd
import streamlit as st
from frontend.api_client import api_client
from frontend.components.tables import render_empty_state, render_info_card, render_page_header

RECOMMENDATIONS = ["strong_hire", "hire", "hold", "no_hire"]
INTERVIEW_STATUSES = ["scheduled", "completed", "cancelled", "rescheduled"]


def render_interviews_page() -> None:
    """Renders the Interview & Evaluation Management view."""
    render_page_header(
        title="Interview & Scorecard Management",
        subtitle="Schedule interview rounds, assign evaluation panelists, submit scorecard feedback, and track round completion.",
        icon="📅",
    )

    tab_list, tab_schedule, tab_scorecard = st.tabs([
        "📋 Interview Schedule",
        "➕ Schedule Interview & Assign Panel",
        "📝 Submit Scorecard",
    ])

    # -----------------------------------------------------------------------
    # TAB 1: Interview Schedule Directory
    # -----------------------------------------------------------------------
    with tab_list:
        col_f1, col_f2 = st.columns([3, 1.2])
        with col_f1:
            status_filter = st.selectbox(
                "Filter by Interview Status",
                options=["All Statuses"] + INTERVIEW_STATUSES,
                index=0,
            )
        with col_f2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Refresh Schedule", use_container_width=True, type="secondary"):
                st.rerun()

        selected_status = None if status_filter == "All Statuses" else status_filter

        with st.spinner("Loading interviews from backend API..."):
            resp = api_client.get_interviews(status=selected_status, limit=100)

        if not resp.success:
            st.error(f"Failed to fetch interviews: {resp.error}")
            return

        interviews = resp.data or []
        if not interviews:
            render_empty_state(
                message="No interviews found for the selected status.",
                action_hint="Schedule a new interview round.",
            )
            return

        table_rows = []
        for iv in interviews:
            table_rows.append({
                "Interview ID": iv["interview_id"],
                "App ID": iv["application_id"],
                "Round #": iv.get("round_number") or iv.get("interview_round") or 1,
                "Status": iv["status"].title(),
                "Scheduled At": str(iv.get("scheduled_at", ""))[:19].replace("T", " "),
                "Completed At": str(iv.get("completed_at", ""))[:19].replace("T", " ") if iv.get("completed_at") else "Pending",
                "Created": str(iv.get("created_at", ""))[:10],
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Inspection and Feedback Details
        st.subheader("🔍 Interview Details & Panelist Scorecards")
        iv_options = {
            f"Interview #{iv['interview_id']} (App #{iv['application_id']} - Round {iv.get('round_number', 1)} [{iv['status'].upper()}])": iv['interview_id']
            for iv in interviews
        }
        selected_iv_label = st.selectbox("Select Interview to Review:", list(iv_options.keys()))

        if selected_iv_label:
            selected_iv_id = iv_options[selected_iv_label]
            col_iv1, col_iv2 = st.columns(2)

            with col_iv1:
                st.markdown("<h5 style='color: #0F172A; font-weight: 700;'>Status Management</h5>", unsafe_allow_html=True)
                with st.form(f"status_form_{selected_iv_id}"):
                    new_st = st.selectbox("Update Status", INTERVIEW_STATUSES)
                    st_notes = st.text_input("Notes", placeholder="e.g. Candidate completed technical coding assessment.")
                    submit_st = st.form_submit_button("Update Status", type="primary")
                    if submit_st:
                        upd_resp = api_client.update_interview_status(selected_iv_id, new_st, st_notes)
                        if upd_resp.success:
                            st.success(f"Interview #{selected_iv_id} status updated to '{new_st}'!")
                            st.rerun()
                        else:
                            st.error(f"Status update failed: {upd_resp.error}")

                # Panelist Assign Action
                st.markdown("<h5 style='color: #0F172A; font-weight: 700; margin-top: 16px;'>Assign Additional Interviewer</h5>", unsafe_allow_html=True)
                with st.form(f"assign_form_{selected_iv_id}"):
                    emp_id_in = st.number_input("Interviewer (Employee ID) *", min_value=1, step=1)
                    assign_btn = st.form_submit_button("Assign Interviewer", type="primary")
                    if assign_btn:
                        assign_resp = api_client.assign_interviewer(selected_iv_id, int(emp_id_in))
                        if assign_resp.success:
                            st.success(f"Employee #{emp_id_in} assigned to interview #{selected_iv_id}!")
                            st.rerun()
                        else:
                            st.error(f"Failed to assign interviewer: {assign_resp.error}")

            with col_iv2:
                st.markdown("<h5 style='color: #0F172A; font-weight: 700;'>Submitted Scorecards & Ratings</h5>", unsafe_allow_html=True)
                sc_summary_resp = api_client.get_interview_scorecard_summary(selected_iv_id)
                if sc_summary_resp.success and sc_summary_resp.data:
                    summary = sc_summary_resp.data
                    tot_sc = summary.get("total_scorecards", summary.get("scorecard_count", 0))
                    avg_sc = float(summary.get("average_overall_score") or 0)
                    summary_banner = (
                        f'<div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; '
                        f'padding: 14px 18px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">'
                        f'<span style="color: #334155; font-weight: 600;">Total Evaluations: <b>{tot_sc}</b></span>'
                        f'<span style="color: #334155; font-weight: 600;">Avg Overall Score: '
                        f'<span style="font-weight: 800; color: #2563EB; font-size: 1.05rem;">{avg_sc:.2f} / 10.0</span></span>'
                        f'</div>'
                    )
                    st.markdown(summary_banner, unsafe_allow_html=True)

                sc_resp = api_client.get_interview_scorecards(selected_iv_id)
                if sc_resp.success and sc_resp.data:
                    sc_rows = []
                    for sc in sc_resp.data:
                        sc_rows.append({
                            "Scorecard ID": sc["scorecard_id"],
                            "Interviewer ID": sc["employee_id"],
                            "Technical": f"{float(sc.get('technical_score') or 0):.1f}",
                            "Communication": f"{float(sc.get('communication_score') or 0):.1f}",
                            "Problem Solving": f"{float(sc.get('problem_solving_score') or 0):.1f}",
                            "Overall Score": f"{float(sc.get('overall_score') or 0):.1f}",
                            "Recommendation": sc["recommendation"].replace("_", " ").title(),
                            "Feedback": sc.get("feedback") or sc.get("comments") or "",
                        })
                    st.dataframe(pd.DataFrame(sc_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No scorecards submitted yet for this interview round.")

    # -----------------------------------------------------------------------
    # TAB 2: Schedule Interview & Assign Panel
    # -----------------------------------------------------------------------
    with tab_schedule:
        st.markdown("<h4 style='color: #0F172A; font-weight: 700; margin-bottom: 14px;'>Schedule New Interview Round</h4>", unsafe_allow_html=True)
        with st.form("schedule_interview_form"):
            col_sc1, col_sc2 = st.columns(2)
            with col_sc1:
                app_id_in = st.number_input("Application ID *", min_value=1, step=1, help="ID of candidate application")
                round_num_in = st.number_input("Round Number *", min_value=1, max_value=10, value=1, step=1)
            with col_sc2:
                sched_date = st.date_input("Scheduled Date *", value=datetime.now().date() + timedelta(days=2))
                sched_time = st.time_input("Scheduled Time *", value=datetime.strptime("10:00", "%H:%M").time())
                panelist_id_in = st.number_input("Initial Panelist (Employee ID) *", min_value=1, value=1, step=1)

            submit_sched = st.form_submit_button("Schedule Interview & Assign Panel", type="primary", use_container_width=True)
            if submit_sched:
                sched_dt = datetime.combine(sched_date, sched_time).replace(tzinfo=timezone.utc)
                payload = {
                    "application_id": int(app_id_in),
                    "interview_round": int(round_num_in),
                    "interview_type": f"Round {int(round_num_in)} Evaluation",
                    "scheduled_at": sched_dt.isoformat(),
                }
                sch_resp = api_client.schedule_interview(payload)
                if sch_resp.success:
                    new_iv_id = sch_resp.data["interview_id"]
                    api_client.assign_interviewer(new_iv_id, int(panelist_id_in))
                    st.success(f"Interview #{new_iv_id} (Round {round_num_in}) scheduled successfully with Panelist #{panelist_id_in}!")
                    st.rerun()
                else:
                    st.error(f"Failed to schedule interview: {sch_resp.error}")

    # -----------------------------------------------------------------------
    # TAB 3: Submit Scorecard
    # -----------------------------------------------------------------------
    with tab_scorecard:
        st.markdown("<h4 style='color: #0F172A; font-weight: 700; margin-bottom: 14px;'>Submit Panelist Evaluation Scorecard</h4>", unsafe_allow_html=True)
        with st.form("submit_scorecard_form"):
            col_sc_a, col_sc_b = st.columns(2)
            with col_sc_a:
                sc_iv_id = st.number_input("Interview ID *", min_value=1, step=1)
                sc_emp_id = st.number_input("Interviewer Employee ID *", min_value=1, step=1)
                sc_rec = st.selectbox("Hiring Recommendation *", RECOMMENDATIONS)

            with col_sc_b:
                tech_score = st.slider("Technical Competency Score (0 – 10) *", 0.0, 10.0, 7.5, 0.5)
                comm_score = st.slider("Communication & Cultural Fit (0 – 10) *", 0.0, 10.0, 8.0, 0.5)
                prob_score = st.slider("Problem Solving & Architecture (0 – 10) *", 0.0, 10.0, 7.0, 0.5)

            sc_comments = st.text_area("Detailed Interview Feedback & Justification *", placeholder="Strong algorithms foundation. Demonstrated good systems design thinking.")
            auto_overall = round((tech_score + comm_score + prob_score) / 3.0, 2)
            st.info(f"Computed Overall Score: **{auto_overall} / 10.0**")

            submit_sc_btn = st.form_submit_button("Submit Scorecard Evaluation", type="primary", use_container_width=True)
            if submit_sc_btn:
                payload = {
                    "interview_id": int(sc_iv_id),
                    "employee_id": int(sc_emp_id),
                    "technical_score": float(tech_score),
                    "communication_score": float(comm_score),
                    "problem_solving_score": float(prob_score),
                    "overall_score": float(auto_overall),
                    "recommendation": sc_rec,
                    "feedback": sc_comments.strip() if sc_comments else None,
                }
                sc_sub_resp = api_client.submit_scorecard(payload)
                if sc_sub_resp.success:
                    st.success(f"Scorecard submitted successfully! ID #{sc_sub_resp.data['scorecard_id']}")
                    st.rerun()
                else:
                    st.error(f"Scorecard submission failed: {sc_sub_resp.error}")
