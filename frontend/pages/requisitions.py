"""
frontend/pages/requisitions.py
==============================
Job Requisition management page for creating, listing, inspecting,
and transitioning job postings.
"""

from typing import Any
import pandas as pd
import streamlit as st
from frontend.api_client import api_client
from frontend.components.tables import format_currency, render_empty_state, render_info_card, render_page_header


def render_requisitions_page() -> None:
    """Renders the Requisitions Management view."""
    render_page_header(
        title="Job Requisitions",
        subtitle="Manage recruitment headcount, opening budgets, department allocations, and requisition lifecycles.",
        icon="📋",
    )

    tab_list, tab_create = st.tabs(["📋 Requisitions Directory", "➕ Create Job Requisition"])

    # Load departments for filters and forms
    dept_resp = api_client.get_departments()
    dept_map = {d["department_id"]: d["department_name"] for d in (dept_resp.data or [])} if dept_resp.success else {}

    # -----------------------------------------------------------------------
    # TAB 1: Requisitions Directory
    # -----------------------------------------------------------------------
    with tab_list:
        col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
        with col_f1:
            dept_filter = st.selectbox(
                "Filter by Department",
                options=["All Departments"] + list(dept_map.values()),
                index=0,
            )
        with col_f2:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All Statuses", "open", "closed", "draft", "on_hold", "cancelled"],
                index=0,
            )
        with col_f3:
            search_title = st.text_input("Search Job Title", placeholder="e.g. Software Engineer, Director")

        selected_dept_id = None
        if dept_filter != "All Departments":
            for did, dname in dept_map.items():
                if dname == dept_filter:
                    selected_dept_id = did
                    break

        selected_status = None if status_filter == "All Statuses" else status_filter

        with st.spinner("Loading requisitions from backend API..."):
            resp = api_client.get_requisitions(
                department_id=selected_dept_id,
                status=selected_status,
                search=search_title.strip() if search_title else None,
                limit=100,
            )

        if not resp.success:
            st.error(f"Failed to fetch requisitions: {resp.error}")
            return

        requisitions = resp.data or []
        if not requisitions:
            render_empty_state(
                message="No requisitions found matching current criteria.",
                action_hint="Clear filter selections or create a new job opening.",
            )
            return

        table_rows = []
        for r in requisitions:
            table_rows.append({
                "Req ID": r["requisition_id"],
                "Job Title": r["job_title"],
                "Department": dept_map.get(r.get("department_id"), f"Dept #{r.get('department_id')}"),
                "Status": r["status"].replace("_", " ").title(),
                "Openings": r.get("openings") or r.get("openings_count") or 1,
                "Experience Range": f"{float(r.get('experience_min', 0)):.0f} - {float(r.get('experience_max', 0)):.0f} yrs",
                "Salary Budget": f"{format_currency(r.get('salary_min'))} to {format_currency(r.get('salary_max'))}",
                "Created": str(r.get("created_at", ""))[:10],
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Requisition Lifecycle & Actions Panel
        st.subheader("⚙️ Requisition Lifecycle & Status Management")
        req_options = {
            f"#{r['requisition_id']} – {r['job_title']} [{r['status'].upper()}]": r['requisition_id']
            for r in requisitions
        }
        selected_label = st.selectbox("Select Requisition to Inspect / Update:", list(req_options.keys()))

        if selected_label:
            selected_req_id = req_options[selected_label]
            req_detail_resp = api_client.get_requisition(selected_req_id)
            if req_detail_resp.success:
                req = req_detail_resp.data
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    info_items = [
                        ("Job Title", req["job_title"]),
                        ("Department", dept_map.get(req.get("department_id"), req.get("department_id"))),
                        ("Hiring Manager ID", req.get("hiring_manager_id") or "Unassigned"),
                        ("Current Status", req["status"].upper()),
                        ("Headcount Openings", req.get("openings") or req.get("openings_count") or 1),
                        ("Required Experience", f"{req.get('experience_min')} – {req.get('experience_max')} years"),
                        ("Compensation Range", f"{format_currency(req.get('salary_min'))} – {format_currency(req.get('salary_max'))}"),
                    ]
                    render_info_card(
                        title=f"Requisition #{req['requisition_id']} Details",
                        items=info_items,
                        subtitle="Governed by organizational hiring caps & department budgets",
                        accent_color="#2563EB",
                    )

                with col_d2:
                    st.markdown("<h5 style='color: #0F172A; font-weight: 700;'>Requisition Actions</h5>", unsafe_allow_html=True)
                    current_status = req["status"]

                    new_status = st.selectbox(
                        "Update Lifecycle Status",
                        options=["open", "closed", "draft", "on_hold", "cancelled"],
                        index=["open", "closed", "draft", "on_hold", "cancelled"].index(current_status)
                        if current_status in ["open", "closed", "draft", "on_hold", "cancelled"]
                        else 0,
                    )

                    if st.button("Apply Status Update", type="primary", use_container_width=True):
                        if new_status == current_status:
                            st.info("Requisition is already in this status.")
                        else:
                            up_resp = api_client.update_requisition(selected_req_id, {"status": new_status})
                            if up_resp.success:
                                st.success(f"Requisition status updated to '{new_status}'!")
                                st.rerun()
                            else:
                                st.error(f"Failed to update status: {up_resp.error}")

                    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                    if current_status == "open":
                        if st.button("🔒 Close Requisition", use_container_width=True):
                            close_resp = api_client.close_requisition(selected_req_id)
                            if close_resp.success:
                                st.success(f"Requisition #{selected_req_id} closed successfully!")
                                st.rerun()
                            else:
                                st.error(f"Close failed: {close_resp.error}")

    # -----------------------------------------------------------------------
    # TAB 2: Create Requisition Form
    # -----------------------------------------------------------------------
    with tab_create:
        st.markdown("<h4 style='color: #0F172A; font-weight: 700; margin-bottom: 14px;'>Open New Job Requisition</h4>", unsafe_allow_html=True)
        with st.form("create_requisition_form"):
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                title_in = st.text_input("Job Title *", placeholder="e.g. Senior Backend Engineer")
                dept_names = list(dept_map.values())
                sel_dept_name = st.selectbox("Department *", dept_names if dept_names else ["Default"])
                mgr_id_in = st.number_input("Hiring Manager (Employee ID) *", min_value=1, value=1, step=1)
                openings_in = st.number_input("Approved Headcount Openings *", min_value=1, max_value=100, value=1, step=1)
            with col_cr2:
                exp_min_in = st.number_input("Minimum Experience (Years) *", min_value=0, max_value=30, value=3, step=1)
                exp_max_in = st.number_input("Maximum Experience (Years) *", min_value=0, max_value=40, value=8, step=1)
                sal_min_in = st.number_input("Budget Minimum Salary (INR) *", min_value=100000.0, max_value=100000000.0, value=1200000.0, step=50000.0)
                sal_max_in = st.number_input("Budget Maximum Salary (INR) *", min_value=100000.0, max_value=100000000.0, value=2200000.0, step=50000.0)

            submit_req = st.form_submit_button("Create Requisition", type="primary", use_container_width=True)
            if submit_req:
                if not title_in.strip():
                    st.error("Job Title is required.")
                elif exp_min_in > exp_max_in:
                    st.error("Minimum experience cannot exceed maximum experience.")
                elif sal_min_in > sal_max_in:
                    st.error("Minimum salary budget cannot exceed maximum salary budget.")
                else:
                    found_dept_id = None
                    for did, dname in dept_map.items():
                        if dname == sel_dept_name:
                            found_dept_id = did
                            break

                    payload = {
                        "job_title": title_in.strip(),
                        "department_id": found_dept_id or 1,
                        "hiring_manager_id": int(mgr_id_in),
                        "openings": int(openings_in),
                        "experience_min": int(exp_min_in),
                        "experience_max": int(exp_max_in),
                        "salary_min": float(sal_min_in),
                        "salary_max": float(sal_max_in),
                        "status": "open",
                        "location": "Bengaluru, India",
                        "employment_type": "full_time",
                    }
                    create_r = api_client.create_requisition(payload)
                    if create_r.success:
                        st.success(f"Requisition created successfully! ID #{create_r.data['requisition_id']}")
                        st.rerun()
                    else:
                        st.error(f"Requisition creation failed: {create_r.error}")
