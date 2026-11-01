"""
tests/test_e2e_workflows.py
===========================
Part 5 – Complete End-to-End Recruitment Lifecycle & Workflow Integration Tests.

Validates the 4 complete user journeys required by the enterprise spec:
  1. Workflow 1 – Candidate recruitment (Create candidate -> Create open requisition ->
                  Submit application -> Move through stages -> View history)
  2. Workflow 2 – Interview process (Schedule interview -> Assign interviewers ->
                  Complete interview -> Submit scorecards -> View feedback summary)
  3. Workflow 3 – Offer process (Create offer -> Submit for approval -> Approve ->
                  Release -> Candidate accept/decline)
  4. Workflow 4 – Anomaly detection (Insert anomalous records -> Trigger detection ->
                  Review details -> Update status -> Verify metrics refresh)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest


def unique_email(prefix: str = "e2e") -> str:
    return f"{prefix}.{uuid.uuid4().hex[:8]}@recruitflow.test"


# ---------------------------------------------------------------------------
# Workflow 1 – Candidate Recruitment
# ---------------------------------------------------------------------------

class TestWorkflow1CandidateRecruitment:
    def test_complete_candidate_recruitment_journey(self, client, seed_dept, seed_manager):
        # 1. Create candidate
        cand_email = unique_email("candidate.recruitment")
        cand_resp = client.post("/candidates/", json={
            "full_name": "Eleanor Vance",
            "email": cand_email,
            "phone": "+91 91234 56789",
            "experience_years": 5.5,
            "highest_qualification": "B.Tech / B.E.",
            "current_location": "Bengaluru, India",
        })
        assert cand_resp.status_code == 201
        candidate_id = cand_resp.json()["candidate_id"]

        # 2. Create open requisition
        req_resp = client.post("/requisitions/", json={
            "job_title": "Senior Distributed Systems Engineer",
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "employment_type": "Full-time",
            "location": "Bengaluru",
            "openings": 2,
            "experience_min": 4,
            "experience_max": 8,
            "salary_min": "2000000.00",
            "salary_max": "3500000.00",
            "status": "open",
        })
        assert req_resp.status_code == 201
        requisition_id = req_resp.json()["requisition_id"]

        # 3. Submit application
        app_resp = client.post("/applications/", json={
            "candidate_id": candidate_id,
            "requisition_id": requisition_id,
            "source": "LinkedIn",
            "notes": "Direct applicant via LinkedIn Talent Solutions",
        })
        assert app_resp.status_code == 201
        application_id = app_resp.json()["application_id"]
        assert app_resp.json()["current_stage"] == "applied"
        assert app_resp.json()["status"] == "active"

        # 4. Move application through stages
        # applied -> screening
        s1 = client.patch(f"/applications/{application_id}/stage", json={
            "new_stage": "screening",
            "notes": "Passed initial recruiter screening resume review",
        })
        assert s1.status_code == 200
        assert s1.json()["current_stage"] == "screening"

        # screening -> interview
        s2 = client.patch(f"/applications/{application_id}/stage", json={
            "new_stage": "interview",
            "notes": "Shortlisted for panel interviews",
        })
        assert s2.status_code == 200
        assert s2.json()["current_stage"] == "interview"

        # interview -> assessment
        s3 = client.patch(f"/applications/{application_id}/stage", json={
            "new_stage": "assessment",
            "notes": "Completed take-home systems design project",
        })
        assert s3.status_code == 200
        assert s3.json()["current_stage"] == "assessment"

        # assessment -> offer
        s4 = client.patch(f"/applications/{application_id}/stage", json={
            "new_stage": "offer",
            "notes": "Panel recommended moving to compensation offer",
        })
        assert s4.status_code == 200
        assert s4.json()["current_stage"] == "offer"

        # 5. View application audit history
        hist_resp = client.get(f"/applications/{application_id}/history")
        assert hist_resp.status_code == 200
        history = hist_resp.json()
        assert len(history) >= 4
        stages_recorded = [h["new_stage"] for h in history]
        assert "screening" in stages_recorded
        assert "interview" in stages_recorded
        assert "assessment" in stages_recorded
        assert "offer" in stages_recorded


# ---------------------------------------------------------------------------
# Workflow 2 – Interview Process
# ---------------------------------------------------------------------------

class TestWorkflow2InterviewProcess:
    def test_complete_interview_evaluation_journey(self, client, seed_dept, seed_manager):
        # Setup: Candidate and Application
        cand_resp = client.post("/candidates/", json={
            "full_name": "Marcus Aurelius",
            "email": unique_email("marcus"),
            "experience_years": 6.0,
            "highest_qualification": "M.Tech",
        })
        candidate_id = cand_resp.json()["candidate_id"]

        req_resp = client.post("/requisitions/", json={
            "job_title": "Principal Architect",
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "employment_type": "Full-time",
            "location": "Bengaluru",
            "openings": 1,
            "experience_min": 5,
            "experience_max": 10,
            "salary_min": "3000000.00",
            "salary_max": "5000000.00",
            "status": "open",
        })
        requisition_id = req_resp.json()["requisition_id"]

        app_resp = client.post("/applications/", json={
            "candidate_id": candidate_id,
            "requisition_id": requisition_id,
            "source": "Referral",
        })
        application_id = app_resp.json()["application_id"]

        # Advance to interview stage
        client.patch(f"/applications/{application_id}/stage", json={"new_stage": "screening"})
        client.patch(f"/applications/{application_id}/stage", json={"new_stage": "interview"})

        # 1. Schedule Interview
        sched_time = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        iv_resp = client.post("/interviews/", json={
            "application_id": application_id,
            "interview_round": 1,
            "interview_type": "Technical Round 1",
            "scheduled_at": sched_time,
        })
        assert iv_resp.status_code == 201
        interview_id = iv_resp.json()["interview_id"]
        assert iv_resp.json()["status"] == "scheduled"

        # 2. Assign Interviewer
        assign_resp = client.post(f"/interviews/{interview_id}/assign-interviewer", json={
            "employee_id": seed_manager["employee_id"],
        })
        assert assign_resp.status_code == 201

        # 3. Complete Interview
        comp_time = (datetime.now(timezone.utc) + timedelta(days=3, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        comp_resp = client.patch(f"/interviews/{interview_id}/status", json={
            "status": "completed",
            "notes": "Interview round 1 concluded smoothly",
        })
        assert comp_resp.status_code == 200
        assert comp_resp.json()["status"] == "completed"

        # 4. Submit Scorecard
        sc_resp = client.post("/scorecards/", json={
            "interview_id": interview_id,
            "employee_id": seed_manager["employee_id"],
            "technical_score": 8.5,
            "communication_score": 9.0,
            "problem_solving_score": 8.5,
            "overall_score": 8.67,
            "recommendation": "strong_hire",
            "comments": "Superb systems design skills. Clear communication.",
        })
        assert sc_resp.status_code == 201
        scorecard_id = sc_resp.json()["scorecard_id"]

        # 5. View Interview Feedback & Summary
        sc_list = client.get(f"/scorecards/interview/{interview_id}")
        assert sc_list.status_code == 200
        assert len(sc_list.json()) == 1

        summary_resp = client.get(f"/scorecards/interview/{interview_id}/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert summary["total_scorecards"] == 1
        assert float(summary["average_overall_score"]) == pytest.approx(8.67, rel=0.01)


# ---------------------------------------------------------------------------
# Workflow 3 – Offer Process
# ---------------------------------------------------------------------------

class TestWorkflow3OfferProcess:
    def test_complete_offer_approval_and_acceptance(self, client, seed_dept, seed_manager):
        # Setup authorized approver with role 'HR Manager'
        approver_resp = client.post("/employees/", json={
            "department_id": seed_dept["department_id"],
            "full_name": "Executive Approver",
            "email": unique_email("approver"),
            "role": "HR Manager",
        })
        approver_id = approver_resp.json()["employee_id"]

        # Setup application
        cand_resp = client.post("/candidates/", json={
            "full_name": "David Miller",
            "email": unique_email("david"),
            "experience_years": 4.5,
        })
        candidate_id = cand_resp.json()["candidate_id"]

        req_resp = client.post("/requisitions/", json={
            "job_title": "Data Engineer",
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "employment_type": "Full-time",
            "location": "Bengaluru",
            "openings": 1,
            "experience_min": 3,
            "experience_max": 6,
            "salary_min": "1500000.00",
            "salary_max": "2500000.00",
            "status": "open",
        })
        requisition_id = req_resp.json()["requisition_id"]

        app_resp = client.post("/applications/", json={
            "candidate_id": candidate_id,
            "requisition_id": requisition_id,
            "source": "Company Website",
        })
        application_id = app_resp.json()["application_id"]

        # 1. Create Draft Offer
        off_date = date.today().isoformat()
        join_date = (date.today() + timedelta(days=30)).isoformat()
        exp_date = (date.today() + timedelta(days=14)).isoformat()

        offer_resp = client.post("/offers/", json={
            "application_id": application_id,
            "offered_salary": 2200000.0,
            "offer_date": off_date,
            "joining_date": join_date,
            "expiry_date": exp_date,
        })
        assert offer_resp.status_code == 201
        offer_id = offer_resp.json()["offer_id"]
        assert offer_resp.json()["status"] == "draft"

        # 2. Submit for Approval
        sub_resp = client.post(f"/offers/{offer_id}/submit-for-approval")
        assert sub_resp.status_code == 200
        assert sub_resp.json()["status"] == "pending_approval"

        # 3. Approve Offer
        appr_resp = client.post(f"/offers/{offer_id}/approve", json={
            "approved_by": approver_id,
            "remarks": "Approved within approved compensation band",
        })
        assert appr_resp.status_code == 200
        assert appr_resp.json()["status"] == "approved"
        assert appr_resp.json()["approved_by"] == approver_id

        # 4. Release Approved Offer
        rel_resp = client.post(f"/offers/{offer_id}/release")
        assert rel_resp.status_code == 200
        assert rel_resp.json()["status"] == "released"

        # 5. Record Candidate Acceptance
        accept_resp = client.post(f"/offers/{offer_id}/accept", json={
            "reason": "Accepted all terms",
        })
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "accepted"

        # Verify application automatically transitioned to 'hired'
        app_check = client.get(f"/applications/{application_id}")
        assert app_check.status_code == 200
        assert app_check.json()["current_stage"] == "hired"


# ---------------------------------------------------------------------------
# Workflow 4 – Anomaly Detection & Remediation
# ---------------------------------------------------------------------------

class TestWorkflow4AnomalyDetection:
    def test_complete_anomaly_lifecycle_and_remediation(self, client, seed_dept, seed_manager):
        # 1. Create deliberately anomalous data:
        # Candidate with 1.0 year experience applying to requisition requiring 8.0 - 12.0 years (Rule A01)
        anom_cand = client.post("/candidates/", json={
            "full_name": "Junior Applicant",
            "email": unique_email("junior"),
            "experience_years": 1.0,
        })
        cand_id = anom_cand.json()["candidate_id"]

        anom_req = client.post("/requisitions/", json={
            "job_title": "VP of Architecture",
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "employment_type": "Full-time",
            "location": "Bengaluru",
            "openings": 1,
            "experience_min": 8,
            "experience_max": 12,
            "salary_min": "4000000.00",
            "salary_max": "6000000.00",
            "status": "open",
        })
        req_id = anom_req.json()["requisition_id"]

        # 1. Insert controlled anomalous record directly to database (e.g. bypassing API business rule):
        from app.models import Application
        from tests.conftest import TestSessionLocal
        db = TestSessionLocal()
        try:
            anom_app_record = Application(
                candidate_id=cand_id,
                requisition_id=req_id,
                source="Indeed",
                current_stage="applied",
                status="active",
            )
            db.add(anom_app_record)
            db.commit()
            db.refresh(anom_app_record)
            app_id = anom_app_record.application_id
        finally:
            db.close()

        # 2. Run Anomaly Detection Engine
        detect_resp = client.post("/anomalies/detect")
        assert detect_resp.status_code == 200
        detect_body = detect_resp.json()
        assert "data_quality_percentage" in detect_body
        assert detect_body["total_anomalies_found"] >= 1

        # 3. Retrieve Anomalies filtered by category A01
        list_resp = client.get("/anomalies/category/A01")
        assert list_resp.status_code == 200
        a01_list = list_resp.json()
        assert len(a01_list) >= 1

        # Find the newly created anomaly for this application
        matching_anoms = [a for a in a01_list if a["entity_id"] == app_id]
        assert len(matching_anoms) >= 1
        target_anomaly = matching_anoms[0]
        anomaly_id = target_anomaly["anomaly_id"]

        # 4. Review Anomaly Details
        detail_resp = client.get(f"/anomalies/{anomaly_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["anomaly_code"] == "A01"
        assert detail_resp.json()["severity"] == "Medium"
        assert "below minimum required" in detail_resp.json()["description"]

        # 5. Update Anomaly Status: Open -> Investigating -> Resolved
        upd_inv = client.patch(f"/anomalies/{anomaly_id}/status", json={
            "status": "Investigating",
            "notes": "Talent acquisition reviewing candidate specialized portfolio",
        })
        assert upd_inv.status_code == 200
        assert upd_inv.json()["status"] == "Investigating"

        upd_res = client.patch(f"/anomalies/{anomaly_id}/status", json={
            "status": "Resolved",
            "notes": "Candidate routed to Associate Engineer requisition instead",
            "resolved_by": seed_manager["employee_id"],
        })
        assert upd_res.status_code == 200
        assert upd_res.json()["status"] == "Resolved"
        assert upd_res.json()["resolved_at"] is not None

        # 6. Verify Dashboard Metrics reflect the updated status
        summary_resp = client.get("/anomalies/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert summary["anomalies_by_status"]["Resolved"] >= 1
