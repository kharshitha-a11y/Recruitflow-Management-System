"""
tests/test_api.py
=================
Part 2 – RecruitFlow FastAPI Backend Test Suite

Covers every major API module required by the spec:
  - Health / root endpoints
  - Departments  (CRUD)
  - Employees    (CRUD, filters, duplicate email)
  - Requisitions (CRUD, status transitions, close action)
  - Candidates   (CRUD, search/filter, update, duplicate email)
  - Applications (create, filters, stage advance, history,
                  business-rule violations, duplicate prevention)
  - Interviews   (schedule, assign interviewer, reschedule, cancel, complete,
                  duplicate round, missing resource)
  - Scorecards   (submit, view, auto-computed overall, summary, feedback,
                  business rules: non-assigned reviewer, duplicate scorecard,
                  score out of range)
  - Offers       (create, approval workflow: submit->approve->release->accept,
                  candidate decline, expiry scan, date rules, missing resource)

Uses:
  - In-memory SQLite (isolated, never touches PostgreSQL)
  - ASGIClient from conftest.py  (no httpx dependency)
  - Session-scoped seed fixtures from conftest.py

Run:
    .venv\\Scripts\\python.exe -m pytest tests/test_api.py -v
"""

from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def uniq_email(prefix: str = "user") -> str:
    """Generate a unique email address for each test."""
    return f"{prefix}.{uuid.uuid4().hex[:8]}@test.example"


def future_dt(days: int = 10) -> str:
    """ISO-8601 UTC timestamp N days from now."""
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def future_date(days: int = 10) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_root_ok(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "docs" in r.json()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Departments
# ─────────────────────────────────────────────────────────────────────────────

class TestDepartments:
    def test_create_department(self, client):
        r = client.post("/departments/", json={"department_name": f"Dept-{uuid.uuid4().hex[:6]}"})
        assert r.status_code == 201
        body = r.json()
        assert "department_id" in body
        assert "created_at" in body

    def test_list_departments(self, client, seed_dept):
        r = client.get("/departments/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_get_department_by_id(self, client, seed_dept):
        r = client.get(f"/departments/{seed_dept['department_id']}")
        assert r.status_code == 200
        assert r.json()["department_name"] == seed_dept["department_name"]

    def test_get_department_not_found(self, client):
        r = client.get("/departments/999999")
        assert r.status_code == 404

    def test_duplicate_department_name(self, client, seed_dept):
        r = client.post("/departments/", json={"department_name": seed_dept["department_name"]})
        assert r.status_code == 409

    def test_create_department_missing_name(self, client):
        r = client.post("/departments/", json={})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 3. Employees
# ─────────────────────────────────────────────────────────────────────────────

class TestEmployees:
    def test_create_employee(self, client, seed_dept):
        r = client.post("/employees/", json={
            "department_id": seed_dept["department_id"],
            "full_name": "New Employee",
            "email": uniq_email("emp"),
            "role": "Recruiter",
        })
        assert r.status_code == 201
        assert r.json()["role"] == "Recruiter"

    def test_list_employees(self, client, seed_manager):
        r = client.get("/employees/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_filter_employees_by_department(self, client, seed_dept, seed_manager):
        r = client.get("/employees/", params={"department_id": seed_dept["department_id"]})
        assert r.status_code == 200
        for emp in r.json():
            assert emp["department_id"] == seed_dept["department_id"]

    def test_get_employee_by_id(self, client, seed_manager):
        r = client.get(f"/employees/{seed_manager['employee_id']}")
        assert r.status_code == 200
        assert r.json()["full_name"] == "Test Manager"

    def test_get_employee_not_found(self, client):
        r = client.get("/employees/999999")
        assert r.status_code == 404

    def test_duplicate_employee_email(self, client, seed_manager, seed_dept):
        r = client.post("/employees/", json={
            "department_id": seed_dept["department_id"],
            "full_name": "Dup Email",
            "email": "test.manager@recruitflow.test",
            "role": "HR",
        })
        assert r.status_code == 409

    def test_create_employee_bad_dept(self, client):
        r = client.post("/employees/", json={
            "department_id": 999999,
            "full_name": "Ghost",
            "email": uniq_email("ghost"),
            "role": "Ghost",
        })
        assert r.status_code == 404

    def test_create_employee_missing_fields(self, client):
        r = client.post("/employees/", json={"full_name": "No Email"})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 4. Requisitions
# ─────────────────────────────────────────────────────────────────────────────

class TestRequisitions:
    def _base_payload(self, dept_id, mgr_id) -> dict:
        return {
            "department_id": dept_id,
            "hiring_manager_id": mgr_id,
            "job_title": f"Engineer-{uuid.uuid4().hex[:4]}",
            "employment_type": "Full-time",
            "location": "Remote",
            "openings": 2,
            "experience_min": 1,
            "experience_max": 5,
            "salary_min": "600000.00",
            "salary_max": "1200000.00",
            "status": "draft",
        }

    def test_create_requisition(self, client, seed_dept, seed_manager):
        r = client.post("/requisitions/", json=self._base_payload(
            seed_dept["department_id"], seed_manager["employee_id"]
        ))
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

    def test_list_requisitions(self, client, seed_requisition):
        r = client.get("/requisitions/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_filter_by_status(self, client, seed_requisition):
        r = client.get("/requisitions/", params={"status": "open"})
        assert r.status_code == 200
        for req in r.json():
            assert req["status"] == "open"

    def test_get_requisition_by_id(self, client, seed_requisition):
        r = client.get(f"/requisitions/{seed_requisition['requisition_id']}")
        assert r.status_code == 200
        assert r.json()["requisition_id"] == seed_requisition["requisition_id"]

    def test_get_requisition_not_found(self, client):
        r = client.get("/requisitions/999999")
        assert r.status_code == 404

    def test_update_requisition_status_valid_transition(self, client, seed_dept, seed_manager):
        # Create a fresh draft
        create = client.post("/requisitions/", json=self._base_payload(
            seed_dept["department_id"], seed_manager["employee_id"]
        ))
        req_id = create.json()["requisition_id"]
        r = client.patch(f"/requisitions/{req_id}/status", json={"status": "open"})
        assert r.status_code == 200
        assert r.json()["status"] == "open"

    def test_update_requisition_status_invalid_transition(self, client, seed_dept, seed_manager):
        create = client.post("/requisitions/", json=self._base_payload(
            seed_dept["department_id"], seed_manager["employee_id"]
        ))
        req_id = create.json()["requisition_id"]
        # draft -> closed is not a valid direct transition
        r = client.patch(f"/requisitions/{req_id}/status", json={"status": "closed"})
        assert r.status_code == 400

    def test_close_requisition(self, client, seed_dept, seed_manager):
        create = client.post("/requisitions/", json={**self._base_payload(
            seed_dept["department_id"], seed_manager["employee_id"]
        ), "status": "open"})
        req_id = create.json()["requisition_id"]
        r = client.post(f"/requisitions/{req_id}/close")
        assert r.status_code == 200
        assert r.json()["status"] == "closed"

    def test_bad_experience_range(self, client, seed_dept, seed_manager):
        payload = self._base_payload(seed_dept["department_id"], seed_manager["employee_id"])
        payload["experience_min"] = 10
        payload["experience_max"] = 2
        r = client.post("/requisitions/", json=payload)
        assert r.status_code == 422

    def test_bad_salary_range(self, client, seed_dept, seed_manager):
        payload = self._base_payload(seed_dept["department_id"], seed_manager["employee_id"])
        payload["salary_min"] = "900000"
        payload["salary_max"] = "500000"
        r = client.post("/requisitions/", json=payload)
        assert r.status_code == 422

    def test_requisition_bad_dept(self, client, seed_manager):
        payload = self._base_payload(999999, seed_manager["employee_id"])
        r = client.post("/requisitions/", json=payload)
        assert r.status_code == 404

    def test_requisition_bad_manager(self, client, seed_dept):
        payload = self._base_payload(seed_dept["department_id"], 999999)
        r = client.post("/requisitions/", json=payload)
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 5. Candidates
# ─────────────────────────────────────────────────────────────────────────────

class TestCandidates:
    def test_register_candidate(self, client):
        r = client.post("/candidates/", json={
            "full_name": "Jane Doe",
            "email": uniq_email("jane"),
            "experience_years": "2.5",
            "phone": "+91-9000000002",
            "highest_qualification": "M.Tech",
            "current_location": "Bangalore",
        })
        assert r.status_code == 201
        assert r.json()["experience_years"] == "2.5"

    def test_list_candidates(self, client, seed_candidate):
        r = client.get("/candidates/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_candidate_profile(self, client, seed_candidate):
        r = client.get(f"/candidates/{seed_candidate['candidate_id']}")
        assert r.status_code == 200
        assert r.json()["candidate_id"] == seed_candidate["candidate_id"]

    def test_get_candidate_not_found(self, client):
        r = client.get("/candidates/999999")
        assert r.status_code == 404

    def test_duplicate_candidate_email(self, client, seed_candidate):
        r = client.post("/candidates/", json={
            "full_name": "Dup",
            "email": "test.candidate@example.test",
            "experience_years": "1.0",
        })
        assert r.status_code == 409

    def test_negative_experience(self, client):
        r = client.post("/candidates/", json={
            "full_name": "Neg Exp",
            "email": uniq_email("neg"),
            "experience_years": "-1.0",
        })
        assert r.status_code == 422

    def test_search_candidates_by_name(self, client, seed_candidate):
        r = client.get("/candidates/", params={"q": "Test Candidate"})
        assert r.status_code == 200
        names = [c["full_name"] for c in r.json()]
        assert any("Test Candidate" in n for n in names)

    def test_filter_by_experience(self, client, seed_candidate):
        r = client.get("/candidates/", params={"min_experience": "2.0", "max_experience": "4.0"})
        assert r.status_code == 200
        for c in r.json():
            assert Decimal(str(c["experience_years"])) >= Decimal("2.0")

    def test_filter_by_location(self, client, seed_candidate):
        r = client.get("/candidates/", params={"location": "Test City"})
        assert r.status_code == 200

    def test_update_candidate(self, client, seed_candidate):
        r = client.patch(f"/candidates/{seed_candidate['candidate_id']}", json={
            "current_location": "Mumbai"
        })
        assert r.status_code == 200
        assert r.json()["current_location"] == "Mumbai"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Applications
# ─────────────────────────────────────────────────────────────────────────────

class TestApplications:
    def test_create_application(self, client, seed_application):
        r = client.get(f"/applications/{seed_application['application_id']}")
        assert r.status_code == 200
        assert r.json()["current_stage"] == "applied"

    def test_list_applications(self, client, seed_application):
        r = client.get("/applications/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_filter_by_candidate(self, client, seed_candidate, seed_application):
        r = client.get("/applications/", params={"candidate_id": seed_candidate["candidate_id"]})
        assert r.status_code == 200
        for a in r.json():
            assert a["candidate_id"] == seed_candidate["candidate_id"]

    def test_filter_by_requisition(self, client, seed_requisition, seed_application):
        r = client.get("/applications/", params={"requisition_id": seed_requisition["requisition_id"]})
        assert r.status_code == 200
        for a in r.json():
            assert a["requisition_id"] == seed_requisition["requisition_id"]

    def test_filter_by_stage(self, client, seed_application):
        r = client.get("/applications/", params={"stage": "applied"})
        assert r.status_code == 200
        for a in r.json():
            assert a["current_stage"] == "applied"

    def test_get_application_details(self, client, seed_application):
        r = client.get(f"/applications/{seed_application['application_id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_get_application_not_found(self, client):
        r = client.get("/applications/999999")
        assert r.status_code == 404

    def test_advance_application_stage_valid(self, client, seed_application, seed_manager):
        r = client.post(f"/applications/{seed_application['application_id']}/advance", json={
            "new_stage": "screening",
            "changed_by": seed_manager["employee_id"],
            "remarks": "Shortlisted",
        })
        assert r.status_code == 200
        assert r.json()["current_stage"] == "screening"

    def test_advance_stage_invalid_transition(self, client, seed_application):
        # Try to jump from current stage directly to hired (skipping steps)
        r = client.post(f"/applications/{seed_application['application_id']}/advance", json={
            "new_stage": "hired",
        })
        assert r.status_code == 400

    def test_advance_stage_invalid_name(self, client, seed_application):
        r = client.post(f"/applications/{seed_application['application_id']}/advance", json={
            "new_stage": "nonexistent_stage",
        })
        assert r.status_code == 422

    def test_application_stage_history(self, client, seed_application):
        r = client.get(f"/applications/{seed_application['application_id']}/history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1  # at least the initial "applied" record

    def test_duplicate_application(self, client, seed_candidate, seed_requisition):
        # seed_application already used this pair — second attempt must conflict
        r = client.post("/applications/", json={
            "candidate_id": seed_candidate["candidate_id"],
            "requisition_id": seed_requisition["requisition_id"],
        })
        assert r.status_code == 409

    def test_apply_for_closed_requisition(self, client, seed_dept, seed_manager):
        # Create a fresh candidate
        email = uniq_email("closed")
        cand_r = client.post("/candidates/", json={
            "full_name": "Closed Cand",
            "email": email,
            "experience_years": "3.0",
        })
        cand_id = cand_r.json()["candidate_id"]

        # Create and immediately close a requisition
        req_r = client.post("/requisitions/", json={
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "job_title": f"Closed-{uuid.uuid4().hex[:4]}",
            "employment_type": "Contract",
            "location": "Remote",
            "openings": 1,
            "experience_min": 0,
            "experience_max": 10,
            "salary_min": "100000",
            "salary_max": "200000",
            "status": "open",
        })
        req_id = req_r.json()["requisition_id"]
        client.post(f"/requisitions/{req_id}/close")

        r = client.post("/applications/", json={
            "candidate_id": cand_id,
            "requisition_id": req_id,
        })
        assert r.status_code == 400

    def test_apply_with_too_much_experience(self, client, seed_dept, seed_manager):
        """Candidate with 20 years trying to apply for a 0-2 year role."""
        email = uniq_email("overexp")
        cand_r = client.post("/candidates/", json={
            "full_name": "Over Experienced",
            "email": email,
            "experience_years": "20.0",
        })
        cand_id = cand_r.json()["candidate_id"]

        req_r = client.post("/requisitions/", json={
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "job_title": f"Junior-{uuid.uuid4().hex[:4]}",
            "employment_type": "Full-time",
            "location": "Remote",
            "openings": 1,
            "experience_min": 0,
            "experience_max": 2,
            "salary_min": "300000",
            "salary_max": "600000",
            "status": "open",
        })
        req_id = req_r.json()["requisition_id"]

        r = client.post("/applications/", json={"candidate_id": cand_id, "requisition_id": req_id})
        assert r.status_code == 400

    def test_apply_missing_candidate(self, client, seed_requisition):
        r = client.post("/applications/", json={
            "candidate_id": 999999,
            "requisition_id": seed_requisition["requisition_id"],
        })
        assert r.status_code == 404

    def test_apply_missing_requisition(self, client, seed_candidate):
        r = client.post("/applications/", json={
            "candidate_id": seed_candidate["candidate_id"],
            "requisition_id": 999999,
        })
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 7. Interviews
# ─────────────────────────────────────────────────────────────────────────────

class TestInterviews:
    def test_list_interviews(self, client, seed_interview):
        r = client.get("/interviews/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_interview_by_id(self, client, seed_interview):
        r = client.get(f"/interviews/{seed_interview['interview_id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "scheduled"

    def test_get_interview_not_found(self, client):
        r = client.get("/interviews/999999")
        assert r.status_code == 404

    def test_list_interviewers(self, client, seed_interview):
        r = client.get(f"/interviews/{seed_interview['interview_id']}/interviewers")
        assert r.status_code == 200
        panel = r.json()
        assert len(panel) >= 1
        emp_ids = [p["employee_id"] for p in panel]
        assert seed_interview["interviewer_employee_id"] in emp_ids

    def test_assign_duplicate_interviewer(self, client, seed_interview):
        r = client.post(
            f"/interviews/{seed_interview['interview_id']}/assign-interviewer",
            json={"employee_id": seed_interview["interviewer_employee_id"]},
        )
        assert r.status_code == 409

    def test_assign_nonexistent_employee(self, client, seed_interview):
        r = client.post(
            f"/interviews/{seed_interview['interview_id']}/assign-interviewer",
            json={"employee_id": 999999},
        )
        assert r.status_code == 404

    def test_schedule_new_interview(self, client, seed_application):
        r = client.post("/interviews/", json={
            "application_id": seed_application["application_id"],
            "interview_round": 99,
            "interview_type": "HR Round",
            "scheduled_at": future_dt(5),
        })
        assert r.status_code == 201
        assert r.json()["status"] == "scheduled"

    def test_duplicate_round(self, client, seed_application):
        # Round 1 already exists via seed_interview
        r = client.post("/interviews/", json={
            "application_id": seed_application["application_id"],
            "interview_round": 1,
            "interview_type": "Duplicate",
            "scheduled_at": future_dt(6),
        })
        assert r.status_code == 409

    def test_update_interview_schedule(self, client, seed_interview):
        r = client.patch(f"/interviews/{seed_interview['interview_id']}/schedule", json={
            "scheduled_at": future_dt(15),
        })
        assert r.status_code == 200

    def test_complete_interview(self, client, seed_interview):
        r = client.post(f"/interviews/{seed_interview['interview_id']}/complete")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

    def test_cancel_completed_interview_rejected(self, client, seed_interview):
        # Already completed above – cannot cancel
        r = client.post(f"/interviews/{seed_interview['interview_id']}/cancel")
        assert r.status_code == 400

    def test_interview_invalid_round(self, client, seed_application):
        r = client.post("/interviews/", json={
            "application_id": seed_application["application_id"],
            "interview_round": 0,  # must be > 0
            "interview_type": "Bad Round",
            "scheduled_at": future_dt(3),
        })
        assert r.status_code == 422

    def test_assign_interviewer_to_completed_interview(self, client, seed_interview, seed_manager):
        """Once completed, assigning an interviewer must be rejected."""
        r = client.post(
            f"/interviews/{seed_interview['interview_id']}/assign-interviewer",
            json={"employee_id": seed_manager["employee_id"]},
        )
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# 8. Scorecards
# ─────────────────────────────────────────────────────────────────────────────

class TestScorecards:
    def _scorecard_payload(self, interview_id: int, employee_id: int) -> dict:
        return {
            "interview_id": interview_id,
            "employee_id": employee_id,
            "technical_score": "8.0",
            "communication_score": "7.5",
            "problem_solving_score": "8.5",
            "recommendation": "hire",
            "feedback": "Solid candidate with good fundamentals.",
        }

    def test_submit_scorecard_auto_overall(self, client, seed_interview):
        payload = self._scorecard_payload(
            seed_interview["interview_id"],
            seed_interview["interviewer_employee_id"],
        )
        r = client.post("/scorecards/", json=payload)
        assert r.status_code == 201
        body = r.json()
        # overall_score should be computed as avg(8.0, 7.5, 8.5) = 8.00
        assert float(body["overall_score"]) == pytest.approx(8.0, abs=0.05)

    def test_get_scorecard_by_id(self, client, seed_interview):
        # fetch existing
        r = client.get(f"/scorecards/interview/{seed_interview['interview_id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        sc_id = r.json()[0]["scorecard_id"]

        r2 = client.get(f"/scorecards/{sc_id}")
        assert r2.status_code == 200
        assert r2.json()["scorecard_id"] == sc_id

    def test_get_scorecard_not_found(self, client):
        r = client.get("/scorecards/999999")
        assert r.status_code == 404

    def test_duplicate_scorecard_rejected(self, client, seed_interview):
        payload = self._scorecard_payload(
            seed_interview["interview_id"],
            seed_interview["interviewer_employee_id"],
        )
        r = client.post("/scorecards/", json=payload)
        assert r.status_code == 409

    def test_non_assigned_interviewer_rejected(self, client, seed_interview, seed_manager):
        """Manager (not in interviewer panel) cannot submit a scorecard."""
        payload = self._scorecard_payload(
            seed_interview["interview_id"],
            seed_manager["employee_id"],
        )
        r = client.post("/scorecards/", json=payload)
        assert r.status_code == 400

    def test_score_out_of_range(self, client, seed_interview, seed_interviewer):
        # Use a different interviewer who isn't assigned yet – or just validate at schema
        r = client.post("/scorecards/", json={
            "interview_id": seed_interview["interview_id"],
            "employee_id": seed_interview["interviewer_employee_id"],
            "technical_score": "11.0",  # out of range
            "communication_score": "7.0",
            "problem_solving_score": "8.0",
            "recommendation": "hire",
        })
        assert r.status_code == 422

    def test_invalid_recommendation(self, client, seed_interview):
        r = client.post("/scorecards/", json={
            "interview_id": seed_interview["interview_id"],
            "employee_id": seed_interview["interviewer_employee_id"],
            "technical_score": "7.0",
            "communication_score": "7.0",
            "problem_solving_score": "7.0",
            "recommendation": "maybe",  # not a valid enum
        })
        assert r.status_code == 422

    def test_scorecard_summary(self, client, seed_interview):
        r = client.get(f"/scorecards/interview/{seed_interview['interview_id']}/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["total_scorecards"] >= 1
        assert "average_overall_score" in body
        assert "recommendations_summary" in body

    def test_interviewer_feedback(self, client, seed_interview):
        r = client.get(f"/scorecards/interview/{seed_interview['interview_id']}/feedback")
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        assert "feedback" in items[0]
        assert "recommendation" in items[0]

    def test_list_scorecards_by_interview(self, client, seed_interview):
        r = client.get("/scorecards/", params={"interview_id": seed_interview["interview_id"]})
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. Offers
# ─────────────────────────────────────────────────────────────────────────────

class TestOffers:
    def test_create_offer(self, client, seed_offer):
        r = client.get(f"/offers/{seed_offer['offer_id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_list_offers(self, client, seed_offer):
        r = client.get("/offers/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_offer_not_found(self, client):
        r = client.get("/offers/999999")
        assert r.status_code == 404

    def test_submit_for_approval(self, client, seed_offer):
        r = client.post(f"/offers/{seed_offer['offer_id']}/submit-for-approval")
        assert r.status_code == 200
        assert r.json()["status"] == "pending_approval"

    def test_approve_offer_authorized(self, client, seed_offer):
        r = client.post(f"/offers/{seed_offer['offer_id']}/approve", json={
            "approved_by": seed_offer["manager_employee_id"],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
        assert r.json()["approved_by"] == seed_offer["manager_employee_id"]

    def test_release_offer(self, client, seed_offer):
        r = client.post(f"/offers/{seed_offer['offer_id']}/release")
        assert r.status_code == 200
        assert r.json()["status"] == "released"

    def test_candidate_accepts_offer(self, client, seed_offer):
        r = client.post(f"/offers/{seed_offer['offer_id']}/accept")
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    def test_duplicate_offer_rejected(self, client, seed_application):
        """A second offer for the same application must fail."""
        r = client.post("/offers/", json={
            "application_id": seed_application["application_id"],
            "offered_salary": "900000.00",
            "offer_date": date.today().isoformat(),
            "expiry_date": future_date(10),
        })
        assert r.status_code == 409

    def test_offer_expiry_before_offer_date(self, client, seed_application):
        """expiry_date < offer_date must be rejected at schema validation."""
        today = date.today()
        r = client.post("/offers/", json={
            "application_id": seed_application["application_id"],
            "offered_salary": "700000",
            "offer_date": today.isoformat(),
            "expiry_date": (today - timedelta(days=1)).isoformat(),
        })
        assert r.status_code == 422

    def test_offer_joining_before_offer_date(self, client, seed_application):
        today = date.today()
        r = client.post("/offers/", json={
            "application_id": seed_application["application_id"],
            "offered_salary": "700000",
            "offer_date": today.isoformat(),
            "expiry_date": future_date(10),
            "joining_date": (today - timedelta(days=5)).isoformat(),
        })
        assert r.status_code == 422

    def test_approve_without_approver_rejected(self, client, seed_dept, seed_manager):
        """Cannot transition to 'approved' via status update without approved_by."""
        # Create a fresh offer on a fresh application
        email = uniq_email("noapprover")
        cand_r = client.post("/candidates/", json={
            "full_name": "No Approver Cand",
            "email": email,
            "experience_years": "2.0",
        })
        cand_id = cand_r.json()["candidate_id"]

        req_r = client.post("/requisitions/", json={
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "job_title": f"Temp-{uuid.uuid4().hex[:4]}",
            "employment_type": "Full-time",
            "location": "Remote",
            "openings": 1,
            "experience_min": 0,
            "experience_max": 10,
            "salary_min": "100000",
            "salary_max": "200000",
            "status": "open",
        })
        req_id = req_r.json()["requisition_id"]

        app_r = client.post("/applications/", json={
            "candidate_id": cand_id,
            "requisition_id": req_id,
        })
        app_id = app_r.json()["application_id"]

        offer_r = client.post("/offers/", json={
            "application_id": app_id,
            "offered_salary": "500000",
            "offer_date": date.today().isoformat(),
            "expiry_date": future_date(14),
        })
        offer_id = offer_r.json()["offer_id"]
        client.post(f"/offers/{offer_id}/submit-for-approval")

        # Try to approve without providing approved_by
        r = client.patch(f"/offers/{offer_id}/status", json={"status": "approved"})
        assert r.status_code == 400

    def test_offer_expiry_check_endpoint(self, client):
        r = client.post("/offers/check-expiry")
        assert r.status_code == 200
        body = r.json()
        assert "total_checked" in body
        assert "expired_count" in body
        assert "expired_offer_ids" in body

    def test_list_expired_offers(self, client):
        r = client.get("/offers/expired")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_candidate_declines_released_offer(self, client, seed_dept, seed_manager):
        """Full workflow: create -> approve -> release -> candidate declines."""
        email = uniq_email("decline")
        cand_r = client.post("/candidates/", json={
            "full_name": "Decline Cand",
            "email": email,
            "experience_years": "2.0",
        })
        cand_id = cand_r.json()["candidate_id"]

        req_r = client.post("/requisitions/", json={
            "department_id": seed_dept["department_id"],
            "hiring_manager_id": seed_manager["employee_id"],
            "job_title": f"Decline-Role-{uuid.uuid4().hex[:4]}",
            "employment_type": "Full-time",
            "location": "Remote",
            "openings": 1,
            "experience_min": 0,
            "experience_max": 10,
            "salary_min": "100000",
            "salary_max": "200000",
            "status": "open",
        })
        req_id = req_r.json()["requisition_id"]

        app_r = client.post("/applications/", json={
            "candidate_id": cand_id,
            "requisition_id": req_id,
        })
        app_id = app_r.json()["application_id"]

        offer_r = client.post("/offers/", json={
            "application_id": app_id,
            "offered_salary": "600000",
            "offer_date": date.today().isoformat(),
            "expiry_date": future_date(14),
        })
        assert offer_r.status_code == 201
        offer_id = offer_r.json()["offer_id"]

        client.post(f"/offers/{offer_id}/submit-for-approval")
        client.post(f"/offers/{offer_id}/approve", json={"approved_by": seed_manager["employee_id"]})
        client.post(f"/offers/{offer_id}/release")

        r = client.post(f"/offers/{offer_id}/candidate-reject")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

