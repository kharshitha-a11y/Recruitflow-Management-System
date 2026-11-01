"""
frontend/pages/candidates.py
============================
Candidate Management page providing search, filtering, profile views,
registration, editing, and application history.
"""

from typing import Any
import pandas as pd
import streamlit as st
from frontend.api_client import api_client
from frontend.components.tables import render_empty_state, render_info_card, render_page_header


def render_candidates_page() -> None:
    """Renders the Candidate Management view."""
    render_page_header(
        title="Candidate Management",
        subtitle="Search talent profiles, inspect candidate application histories, and register new applicants.",
        icon="👤",
    )

    tab_list, tab_create = st.tabs(["📋 Candidate Directory", "➕ Register New Candidate"])

    # -----------------------------------------------------------------------
    # TAB 1: Candidate Directory & Profiles
    # -----------------------------------------------------------------------
    with tab_list:
        # Search & Filter Controls
        col_s, col_exp1, col_exp2, col_loc = st.columns([3, 1.5, 1.5, 2])
        with col_s:
            search_query = st.text_input("🔍 Search Name, Email, or Phone", placeholder="e.g. John Doe, @example.com")
        with col_exp1:
            min_exp = st.number_input("Min Experience (Yrs)", min_value=0.0, max_value=40.0, value=0.0, step=0.5)
        with col_exp2:
            max_exp = st.number_input("Max Experience (Yrs)", min_value=0.0, max_value=40.0, value=40.0, step=0.5)
        with col_loc:
            location_filter = st.text_input("Location Filter", placeholder="e.g. Bengaluru, Remote")

        col_page, col_refresh = st.columns([4, 1.2])
        with col_page:
            limit = st.selectbox("Records per page", [25, 50, 100], index=0)
        with col_refresh:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Apply Filters", use_container_width=True, type="secondary"):
                st.rerun()

        # Fetch Candidates from API
        with st.spinner("Loading candidate profiles from backend API..."):
            resp = api_client.get_candidates(
                search=search_query.strip() if search_query else None,
                min_experience=float(min_exp) if min_exp > 0 else None,
                max_experience=float(max_exp) if max_exp < 40 else None,
                location=location_filter.strip() if location_filter else None,
                limit=limit,
            )

        if not resp.success:
            st.error(f"Failed to fetch candidates: {resp.error}")
            return

        candidates = resp.data or []
        if not candidates:
            render_empty_state(
                message="No candidates match the selected filters.",
                action_hint="Try broadening your search keywords or resetting experience filters.",
            )
            return

        # Build Interactive Table
        table_data = []
        for c in candidates:
            table_data.append({
                "Candidate ID": c["candidate_id"],
                "Full Name": c["full_name"],
                "Email": c["email"],
                "Phone": c.get("phone") or "N/A",
                "Experience (Yrs)": f"{float(c.get('experience_years', 0)):.1f}",
                "Qualification": c.get("highest_qualification") or "N/A",
                "Location": c.get("current_location") or "N/A",
                "Registered": str(c.get("created_at", ""))[:10],
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Candidate Detail & Profile Inspector
        st.subheader("🔍 Candidate Profile & Application History")
        cand_options = {
            f"#{c['candidate_id']} – {c['full_name']} ({c['email']})": c['candidate_id']
            for c in candidates
        }
        selected_label = st.selectbox("Select Candidate to Inspect:", list(cand_options.keys()))

        if selected_label:
            selected_cand_id = cand_options[selected_label]
            cand_resp = api_client.get_candidate(selected_cand_id)

            if cand_resp.success:
                cand = cand_resp.data
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    info_items = [
                        ("Full Name", cand["full_name"]),
                        ("Email Address", cand["email"]),
                        ("Phone Number", cand.get("phone") or "N/A"),
                        ("Experience", f"{float(cand.get('experience_years', 0)):.1f} years"),
                        ("Highest Degree", cand.get("highest_qualification") or "N/A"),
                        ("Current Location", cand.get("current_location") or "N/A"),
                    ]
                    render_info_card(
                        title=f"Profile #{cand['candidate_id']} – {cand['full_name']}",
                        items=info_items,
                        subtitle=f"Registered in talent database on {str(cand.get('created_at', ''))[:10]}",
                        accent_color="#2563EB",
                    )

                with col_p2:
                    with st.expander("✏️ Edit Candidate Information", expanded=False):
                        with st.form(f"edit_cand_{selected_cand_id}"):
                            edit_phone = st.text_input("Phone", value=cand.get("phone") or "")
                            edit_exp = st.number_input(
                                "Experience (Years)",
                                value=float(cand.get("experience_years") or 0.0),
                                step=0.5,
                            )
                            edit_qual = st.text_input("Highest Qualification", value=cand.get("highest_qualification") or "")
                            edit_loc = st.text_input("Location", value=cand.get("current_location") or "")

                            if st.form_submit_button("Save Profile Changes", type="primary"):
                                update_resp = api_client.update_candidate(
                                    selected_cand_id,
                                    {
                                        "phone": edit_phone.strip() if edit_phone else None,
                                        "experience_years": float(edit_exp),
                                        "highest_qualification": edit_qual.strip() if edit_qual else None,
                                        "current_location": edit_loc.strip() if edit_loc else None,
                                    },
                                )
                                if update_resp.success:
                                    st.success("Candidate profile updated successfully!")
                                    st.rerun()
                                else:
                                    st.error(f"Update failed: {update_resp.error}")

                # Applications submitted by candidate
                st.markdown("<h5 style='margin-top: 15px; color: #0F172A; font-weight: 700;'>Application History</h5>", unsafe_allow_html=True)
                apps_resp = api_client.get_applications(candidate_id=selected_cand_id)
                if apps_resp.success and apps_resp.data:
                    c_apps = apps_resp.data
                    app_rows = []
                    for a in c_apps:
                        stage_label = a["current_stage"].replace("_", " ").title()
                        status_label = a["status"].title()
                        app_rows.append({
                            "App ID": a["application_id"],
                            "Requisition ID": a["requisition_id"],
                            "Stage": stage_label,
                            "Status": status_label,
                            "Source": a.get("source") or "Direct",
                            "Applied Date": str(a.get("created_at", ""))[:10],
                        })
                    st.dataframe(pd.DataFrame(app_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No applications submitted yet by this candidate.")

    # -----------------------------------------------------------------------
    # TAB 2: Register New Candidate Form
    # -----------------------------------------------------------------------
    with tab_create:
        st.markdown("<h4 style='color: #0F172A; font-weight: 700; margin-bottom: 14px;'>Register Candidate Profile</h4>", unsafe_allow_html=True)
        with st.form("new_candidate_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                new_name = st.text_input("Full Name *", placeholder="Jane Doe")
                new_email = st.text_input("Email Address *", placeholder="jane.doe@example.com")
                new_phone = st.text_input("Phone Number", placeholder="+91 98765 43210")
            with col_f2:
                new_exp = st.number_input("Years of Experience *", min_value=0.0, max_value=50.0, value=3.0, step=0.5)
                new_qual = st.selectbox(
                    "Highest Qualification",
                    ["B.Tech / B.E.", "M.Tech / M.E.", "B.Sc", "M.Sc", "BCA", "MCA", "MBA", "Ph.D.", "Other"],
                )
                new_loc = st.text_input("Current Location", placeholder="e.g. Bengaluru, India")

            submitted = st.form_submit_button("Register Candidate Profile", type="primary", use_container_width=True)
            if submitted:
                if not new_name.strip() or not new_email.strip():
                    st.error("Full Name and Email Address are required fields.")
                else:
                    payload = {
                        "full_name": new_name.strip(),
                        "email": new_email.strip(),
                        "phone": new_phone.strip() if new_phone else None,
                        "experience_years": float(new_exp),
                        "highest_qualification": new_qual,
                        "current_location": new_loc.strip() if new_loc else None,
                    }
                    create_resp = api_client.create_candidate(payload)
                    if create_resp.success:
                        st.success(f"Candidate '{new_name}' registered successfully with ID #{create_resp.data['candidate_id']}!")
                        st.rerun()
                    else:
                        st.error(f"Registration failed: {create_resp.error}")
