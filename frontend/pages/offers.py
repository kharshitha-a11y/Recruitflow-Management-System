"""
frontend/pages/offers.py
========================
Offer Management page managing compensation letters, multi-stage approval workflows,
release to candidates, and acceptance/expiry tracking.
"""

from datetime import date, timedelta
from typing import Any
import pandas as pd
import streamlit as st
from frontend.api_client import api_client
from frontend.components.tables import format_currency, render_empty_state, render_info_card, render_page_header

OFFER_STATUSES = [
    "draft",
    "pending_approval",
    "approved",
    "rejected",
    "released",
    "accepted",
    "declined",
    "expired",
]


def render_offers_page() -> None:
    """Renders the Offer Management view."""
    render_page_header(
        title="Offer Management & Approvals",
        subtitle="Generate candidate compensation packages, route through executive approvals, and manage offer lifecycles.",
        icon="💼",
    )

    tab_list, tab_create = st.tabs(["📋 Offers Directory & Workflow", "➕ Generate New Offer"])

    # -----------------------------------------------------------------------
    # TAB 1: Offers Directory & Approval Actions
    # -----------------------------------------------------------------------
    with tab_list:
        col_f1, col_f2, col_f3 = st.columns([3, 2, 2])
        with col_f1:
            status_filter = st.selectbox(
                "Filter by Offer Status",
                options=["All Statuses"] + OFFER_STATUSES,
                index=0,
            )
        with col_f2:
            expired_filter = st.selectbox("Expiry Filter", ["All", "Active Only", "Expired Only"], index=0)
        with col_f3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Check Expired Offers", use_container_width=True, type="secondary"):
                exp_resp = api_client.check_offer_expiry()
                if exp_resp.success:
                    cnt = exp_resp.data.get("expired_count", 0)
                    st.info(f"Scan complete. {cnt} offers transitioned to expired.")
                    st.rerun()

        selected_status = None if status_filter == "All Statuses" else status_filter
        is_exp = True if expired_filter == "Expired Only" else (False if expired_filter == "Active Only" else None)

        with st.spinner("Loading offers from backend API..."):
            resp = api_client.get_offers(status=selected_status, is_expired=is_exp, limit=100)

        if not resp.success:
            st.error(f"Failed to fetch offers: {resp.error}")
            return

        offers = resp.data or []
        if not offers:
            render_empty_state(
                message="No offers found matching current filters.",
                action_hint="Generate a new candidate offer.",
            )
            return

        table_rows = []
        for off in offers:
            table_rows.append({
                "Offer ID": off["offer_id"],
                "App ID": off["application_id"],
                "Offered Salary": format_currency(off.get("offered_salary")),
                "Status": off["status"].replace("_", " ").title(),
                "Approver ID": off.get("approver_id") or "Unassigned",
                "Offer Date": str(off.get("offer_date", ""))[:10],
                "Joining Date": str(off.get("joining_date", ""))[:10],
                "Expiry Date": str(off.get("expiry_date", ""))[:10],
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)

        # Offer Action & Approval Workflow Hub
        st.subheader("⚙️ Offer Lifecycle & Approval Actions")
        off_options = {
            f"Offer #{o['offer_id']} (App #{o['application_id']} – {format_currency(o.get('offered_salary'))} [{o['status'].upper()}])": o['offer_id']
            for o in offers
        }
        selected_off_label = st.selectbox("Select Offer to Process:", list(off_options.keys()))

        if selected_off_label:
            selected_off_id = off_options[selected_off_label]
            off_detail_resp = api_client.get_offer(selected_off_id)
            if off_detail_resp.success:
                off_data = off_detail_resp.data
                curr_st = off_data["status"]

                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    info_items = [
                        ("Offer ID", f"#{off_data['offer_id']}"),
                        ("Application ID", f"#{off_data['application_id']}"),
                        ("Offered Annual Salary", format_currency(off_data.get("offered_salary"))),
                        ("Lifecycle Status", curr_st.upper()),
                        ("Authorized Approver ID", str(off_data.get("approver_id") or "Not yet assigned")),
                        ("Offer Issue Date", str(off_data.get("offer_date"))),
                        ("Proposed Joining Date", str(off_data.get("joining_date"))),
                        ("Formal Expiry Date", str(off_data.get("expiry_date"))),
                    ]
                    render_info_card(
                        title=f"Offer #{off_data['offer_id']} Specifications",
                        items=info_items,
                        subtitle="Subject to candidate formal acceptance and background audit",
                        accent_color="#F59E0B",
                    )

                with col_o2:
                    st.markdown("<h5 style='color: #0F172A; font-weight: 700;'>Workflow Actions</h5>", unsafe_allow_html=True)

                    # Action 1: Submit for approval
                    if curr_st == "draft":
                        st.info("Offer is in DRAFT. Submit to hiring authorities for budget approval.")
                        if st.button("📤 Submit for Approval", type="primary", use_container_width=True):
                            sub_resp = api_client.submit_offer_for_approval(selected_off_id)
                            if sub_resp.success:
                                st.success("Offer submitted for approval!")
                                st.rerun()
                            else:
                                st.error(f"Action failed: {sub_resp.error}")

                    # Action 2: Approve or Reject
                    elif curr_st == "pending_approval":
                        st.info("Offer is PENDING APPROVAL. Provide authorized approver credentials.")
                        with st.form(f"approval_form_{selected_off_id}"):
                            approver_in = st.number_input("Authorized Approver (Employee ID) *", min_value=1, value=1, step=1)
                            appr_notes = st.text_input("Approval / Rejection Notes", placeholder="Approved within department budget")
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                approve_btn = st.form_submit_button("✅ Approve Offer", type="primary", use_container_width=True)
                            with col_b2:
                                reject_btn = st.form_submit_button("❌ Reject Offer", use_container_width=True)

                            if approve_btn:
                                a_resp = api_client.approve_offer(selected_off_id, int(approver_in), appr_notes)
                                if a_resp.success:
                                    st.success(f"Offer #{selected_off_id} approved!")
                                    st.rerun()
                                else:
                                    st.error(f"Approval failed: {a_resp.error}")

                            if reject_btn:
                                r_resp = api_client.reject_offer(selected_off_id, int(approver_in), appr_notes)
                                if r_resp.success:
                                    st.warning(f"Offer #{selected_off_id} rejected.")
                                    st.rerun()
                                else:
                                    st.error(f"Rejection failed: {r_resp.error}")

                    # Action 3: Release Offer to Candidate
                    elif curr_st == "approved":
                        st.info("Offer is APPROVED and ready to be formally released to the candidate.")
                        if st.button("🚀 Release Offer to Candidate", type="primary", use_container_width=True):
                            rel_resp = api_client.release_offer(selected_off_id)
                            if rel_resp.success:
                                st.success(f"Offer #{selected_off_id} released successfully!")
                                st.rerun()
                            else:
                                st.error(f"Release failed: {rel_resp.error}")

                    # Action 4: Record Candidate Decision
                    elif curr_st == "released":
                        st.info("Offer has been RELEASED to candidate. Awaiting formal decision.")
                        col_dec1, col_dec2 = st.columns(2)
                        with col_dec1:
                            if st.button("🎉 Candidate Accepts", type="primary", use_container_width=True):
                                dec_resp = api_client.candidate_decision_offer(selected_off_id, "accepted")
                                if dec_resp.success:
                                    st.success(f"Offer #{selected_off_id} accepted! Candidate transitioned to hired.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to record acceptance: {dec_resp.error}")
                        with col_dec2:
                            if st.button("🚫 Candidate Declines", use_container_width=True):
                                dec_resp = api_client.candidate_decision_offer(selected_off_id, "declined")
                                if dec_resp.success:
                                    st.warning(f"Offer #{selected_off_id} declined.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to record decline: {dec_resp.error}")

                    else:
                        st.write(f"Offer is in terminal state: **{curr_st.upper()}**")

    # -----------------------------------------------------------------------
    # TAB 2: Generate New Offer Form
    # -----------------------------------------------------------------------
    with tab_create:
        st.markdown("<h4 style='color: #0F172A; font-weight: 700; margin-bottom: 14px;'>Generate Compensation Offer</h4>", unsafe_allow_html=True)
        with st.form("create_offer_form"):
            col_cr1, col_cr2 = st.columns(2)
            with col_cr1:
                new_app_id = st.number_input("Application ID *", min_value=1, step=1)
                new_salary = st.number_input(
                    "Annual Offered Salary (INR) *",
                    min_value=100000.0,
                    max_value=500000000.0,
                    value=1500000.0,
                    step=50000.0,
                )
            with col_cr2:
                off_dt = st.date_input("Offer Date *", value=date.today())
                join_dt = st.date_input("Proposed Joining Date *", value=date.today() + timedelta(days=30))
                exp_dt = st.date_input("Offer Expiry Date *", value=date.today() + timedelta(days=14))

            submit_new_off = st.form_submit_button("Generate Draft Offer", type="primary", use_container_width=True)
            if submit_new_off:
                if join_dt < off_dt:
                    st.error("Proposed joining date cannot precede offer date.")
                elif exp_dt < off_dt:
                    st.error("Offer expiry date cannot precede offer date.")
                else:
                    payload = {
                        "application_id": int(new_app_id),
                        "offered_salary": float(new_salary),
                        "offer_date": off_dt.isoformat(),
                        "joining_date": join_dt.isoformat(),
                        "expiry_date": exp_dt.isoformat(),
                    }
                    gen_resp = api_client.create_offer(payload)
                    if gen_resp.success:
                        st.success(f"Offer generated successfully! ID #{gen_resp.data['offer_id']}")
                        st.rerun()
                    else:
                        st.error(f"Offer generation failed: {gen_resp.error}")
