"""
tests/test_anomaly_engine.py
============================
Part 3 – RecruitFlow Anomaly Detection & Data Quality Engine Test Suite

Tests:
  - Detection rules A01 to A10
  - Clean records (pass without anomalies)
  - Deliberately anomalous records (trigger expected code and severity)
  - Boundary conditions
  - Duplicate detection (A02)
  - Severity classification
  - Deduplicated persistence on repeated runs (idempotency)
  - Anomaly status transitions (Open -> Investigating -> Resolved -> False Positive)
  - Data quality percentage formula & no double-counting verification
  - FastAPI endpoints for /anomalies
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from validation.anomaly_rules import (
    detect_candidate_experience_anomalies,
    detect_duplicate_application_anomalies,
    detect_interview_assignment_anomalies,
    detect_interview_scheduling_anomalies,
    detect_offer_approval_anomalies,
    detect_offer_date_anomalies,
    detect_recruitment_process_anomalies,
    detect_salary_anomalies,
    detect_scorecard_anomalies,
    detect_application_workflow_anomalies,
)
from validation.data_quality import calculate_data_quality_metrics
from validation.validation_service import (
    get_all_anomalies,
    get_anomaly_by_id,
    get_data_quality_summary,
    run_detection_and_persist,
    update_anomaly_status,
)


# ---------------------------------------------------------------------------
# 1. A01 – Candidate Experience Anomaly Tests
# ---------------------------------------------------------------------------

class TestA01CandidateExperience:
    def test_clean_experience(self):
        cand = SimpleNamespace(candidate_id=1, experience_years=Decimal("3.0"))
        req = SimpleNamespace(requisition_id=10, experience_min=2, experience_max=5, job_title="Engineer")
        anomalies = detect_candidate_experience_anomalies(cand, req, application_id=101)
        assert anomalies == []

    def test_experience_boundary_conditions(self):
        # Exactly equal to min
        cand_min = SimpleNamespace(candidate_id=1, experience_years=Decimal("2.0"))
        req = SimpleNamespace(requisition_id=10, experience_min=2, experience_max=5, job_title="Engineer")
        assert detect_candidate_experience_anomalies(cand_min, req, application_id=101) == []

        # Exactly equal to max
        cand_max = SimpleNamespace(candidate_id=2, experience_years=Decimal("5.0"))
        assert detect_candidate_experience_anomalies(cand_max, req, application_id=102) == []

    def test_experience_below_minimum(self):
        cand = SimpleNamespace(candidate_id=1, experience_years=Decimal("0.5"))
        req = SimpleNamespace(requisition_id=10, experience_min=2, experience_max=5, job_title="Engineer")
        anomalies = detect_candidate_experience_anomalies(cand, req, application_id=101)
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A01"
        assert anomalies[0]["severity"] == "Medium"
        assert "below minimum required" in anomalies[0]["description"]

    def test_experience_above_maximum_moderate(self):
        cand = SimpleNamespace(candidate_id=1, experience_years=Decimal("6.0"))
        req = SimpleNamespace(requisition_id=10, experience_min=2, experience_max=5, job_title="Engineer")
        anomalies = detect_candidate_experience_anomalies(cand, req, application_id=101)
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A01"
        assert anomalies[0]["severity"] == "Low"

    def test_experience_above_maximum_severe(self):
        # 18 years for 2-5 year job (like synthetic anomaly)
        cand = SimpleNamespace(candidate_id=1, experience_years=Decimal("18.0"))
        req = SimpleNamespace(requisition_id=10, experience_min=2, experience_max=5, job_title="Engineer")
        anomalies = detect_candidate_experience_anomalies(cand, req, application_id=101)
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "Medium"


# ---------------------------------------------------------------------------
# 2. A02 – Duplicate Application Anomaly Tests
# ---------------------------------------------------------------------------

class TestA02DuplicateApplications:
    def test_clean_applications(self):
        apps = [
            SimpleNamespace(application_id=1, candidate_id=10, requisition_id=100),
            SimpleNamespace(application_id=2, candidate_id=11, requisition_id=100),
            SimpleNamespace(application_id=3, candidate_id=10, requisition_id=101),
        ]
        assert detect_duplicate_application_anomalies(apps) == []

    def test_duplicate_candidate_job_application(self):
        apps = [
            SimpleNamespace(application_id=1, candidate_id=10, requisition_id=100),
            SimpleNamespace(application_id=2, candidate_id=10, requisition_id=100),
        ]
        anomalies = detect_duplicate_application_anomalies(apps)
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A02"
        assert anomalies[0]["severity"] == "High"
        assert anomalies[0]["entity_id"] == 2

    def test_repeated_mass_applications(self):
        apps = [
            SimpleNamespace(application_id=i, candidate_id=99, requisition_id=100 + i)
            for i in range(7)
        ]
        anomalies = detect_duplicate_application_anomalies(apps)
        mass_anom = [a for a in anomalies if a["entity_type"] == "candidate"]
        assert len(mass_anom) == 1
        assert mass_anom[0]["severity"] == "Medium"
        assert mass_anom[0]["entity_id"] == 99


# ---------------------------------------------------------------------------
# 3. A03 – Interview Assignment Anomaly Tests
# ---------------------------------------------------------------------------

class TestA03InterviewAssignments:
    def test_clean_interview_assignment(self):
        iv = SimpleNamespace(interview_id=1, status="scheduled", interview_round=1, interview_type="Technical")
        assign = [SimpleNamespace(interview_id=1, employee_id=5)]
        anomalies = detect_interview_assignment_anomalies([iv], {1: assign})
        assert anomalies == []

    def test_interview_without_assigned_interviewer(self):
        iv = SimpleNamespace(interview_id=1, status="scheduled", interview_round=1, interview_type="Technical")
        anomalies = detect_interview_assignment_anomalies([iv], {1: []})
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A03"
        assert anomalies[0]["severity"] == "High"
        assert "no assigned interviewers" in anomalies[0]["description"]

    def test_duplicate_interviewer_assignment(self):
        iv = SimpleNamespace(interview_id=1, status="scheduled", interview_round=1, interview_type="Technical")
        assign = [
            SimpleNamespace(interview_id=1, employee_id=5),
            SimpleNamespace(interview_id=1, employee_id=5),
        ]
        anomalies = detect_interview_assignment_anomalies([iv], {1: assign})
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "Medium"
        assert "assigned multiple times" in anomalies[0]["description"]


# ---------------------------------------------------------------------------
# 4. A04 – Interview Scheduling Anomaly Tests
# ---------------------------------------------------------------------------

class TestA04InterviewScheduling:
    def test_clean_scheduling(self):
        t1 = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 10, 11, 0, tzinfo=timezone.utc)
        iv = SimpleNamespace(interview_id=1, scheduled_at=t1, completed_at=t2, status="completed")
        assert detect_interview_scheduling_anomalies([iv]) == []

    def test_completion_before_scheduled_date(self):
        t1 = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
        t_early = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
        iv = SimpleNamespace(interview_id=1, scheduled_at=t1, completed_at=t_early, status="completed")
        anomalies = detect_interview_scheduling_anomalies([iv])
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A04"
        assert anomalies[0]["severity"] == "Critical"

    def test_completed_status_without_timestamp(self):
        t1 = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
        iv = SimpleNamespace(interview_id=1, scheduled_at=t1, completed_at=None, status="completed")
        anomalies = detect_interview_scheduling_anomalies([iv])
        assert any("completed_at is null" in a["description"] for a in anomalies)

    def test_overlapping_panelist_schedules(self):
        t1 = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 11, 10, 10, 15, tzinfo=timezone.utc)  # 15 minutes apart
        iv1 = SimpleNamespace(interview_id=1, scheduled_at=t1, completed_at=None, status="scheduled")
        iv2 = SimpleNamespace(interview_id=2, scheduled_at=t2, completed_at=None, status="scheduled")
        assignments = {
            1: [SimpleNamespace(employee_id=7)],
            2: [SimpleNamespace(employee_id=7)],
        }
        anomalies = detect_interview_scheduling_anomalies([iv1, iv2], assignments)
        overlap = [a for a in anomalies if "overlapping schedule" in a["description"]]
        assert len(overlap) == 1
        assert overlap[0]["severity"] == "High"


# ---------------------------------------------------------------------------
# 5. A05 – Scorecard Anomaly Tests
# ---------------------------------------------------------------------------

class TestA05Scorecards:
    def test_clean_scorecard(self):
        sc = SimpleNamespace(
            scorecard_id=1,
            interview_id=10,
            employee_id=5,
            technical_score=Decimal("8.0"),
            communication_score=Decimal("8.0"),
            problem_solving_score=Decimal("8.0"),
            overall_score=Decimal("8.0"),
            recommendation="hire",
        )
        anomalies = detect_scorecard_anomalies([sc], assigned_interview_panelists={(10, 5)})
        assert anomalies == []

    def test_scorecard_without_valid_assignment(self):
        sc = SimpleNamespace(
            scorecard_id=1,
            interview_id=10,
            employee_id=99,
            technical_score=Decimal("8.0"),
            communication_score=Decimal("8.0"),
            problem_solving_score=Decimal("8.0"),
            overall_score=Decimal("8.0"),
            recommendation="hire",
        )
        anomalies = detect_scorecard_anomalies([sc], assigned_interview_panelists={(10, 5)})
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A05"
        assert anomalies[0]["severity"] == "Critical"
        assert "not an assigned interviewer" in anomalies[0]["description"]

    def test_score_outside_range(self):
        sc = SimpleNamespace(
            scorecard_id=1,
            interview_id=10,
            employee_id=5,
            technical_score=Decimal("12.5"),
            communication_score=Decimal("8.0"),
            problem_solving_score=Decimal("8.0"),
            overall_score=Decimal("9.0"),
            recommendation="hire",
        )
        anomalies = detect_scorecard_anomalies([sc], assigned_interview_panelists={(10, 5)})
        assert any(a["severity"] == "Critical" and "outside allowed" in a["description"] for a in anomalies)

    def test_score_recommendation_discrepancy(self):
        # High score but no_hire
        sc = SimpleNamespace(
            scorecard_id=1,
            interview_id=10,
            employee_id=5,
            technical_score=Decimal("9.0"),
            communication_score=Decimal("9.0"),
            problem_solving_score=Decimal("9.0"),
            overall_score=Decimal("9.0"),
            recommendation="no_hire",
        )
        anomalies = detect_scorecard_anomalies([sc], assigned_interview_panelists={(10, 5)})
        assert any("score inconsistency" in a["description"] for a in anomalies)


# ---------------------------------------------------------------------------
# 6. A06 – Offer Approval Anomaly Tests
# ---------------------------------------------------------------------------

class TestA06OfferApprovals:
    def test_clean_approved_offer(self):
        offer = SimpleNamespace(offer_id=1, status="approved", approved_by=10)
        assert detect_offer_approval_anomalies([offer]) == []

    def test_released_offer_without_approver(self):
        offer = SimpleNamespace(offer_id=1, status="released", approved_by=None)
        anomalies = detect_offer_approval_anomalies([offer])
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A06"
        assert anomalies[0]["severity"] == "Critical"
        assert "no approver record" in anomalies[0]["description"]

    def test_approved_offer_without_approver(self):
        offer = SimpleNamespace(offer_id=1, status="approved", approved_by=None)
        anomalies = detect_offer_approval_anomalies([offer])
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "Critical"

    def test_pending_approval_with_approver_set(self):
        offer = SimpleNamespace(offer_id=1, status="pending_approval", approved_by=5)
        anomalies = detect_offer_approval_anomalies([offer])
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "Medium"


# ---------------------------------------------------------------------------
# 7. A07 – Offer Date Anomaly Tests
# ---------------------------------------------------------------------------

class TestA07OfferDates:
    def test_clean_offer_dates(self):
        t0 = date(2026, 11, 1)
        t_exp = date(2026, 11, 15)
        t_join = date(2026, 12, 1)
        offer = SimpleNamespace(offer_id=1, offer_date=t0, expiry_date=t_exp, joining_date=t_join)
        assert detect_offer_date_anomalies([offer]) == []

    def test_expiry_before_offer_date(self):
        t0 = date(2026, 11, 10)
        t_exp = date(2026, 11, 5)
        offer = SimpleNamespace(offer_id=1, offer_date=t0, expiry_date=t_exp, joining_date=None)
        anomalies = detect_offer_date_anomalies([offer])
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A07"
        assert anomalies[0]["severity"] == "Critical"
        assert "expiry date" in anomalies[0]["description"]

    def test_joining_before_offer_date(self):
        t0 = date(2026, 11, 10)
        t_exp = date(2026, 11, 20)
        t_join = date(2026, 11, 1)
        offer = SimpleNamespace(offer_id=1, offer_date=t0, expiry_date=t_exp, joining_date=t_join)
        anomalies = detect_offer_date_anomalies([offer])
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "Critical"
        assert "joining date" in anomalies[0]["description"]


# ---------------------------------------------------------------------------
# 8. A08 – Salary Anomaly Tests
# ---------------------------------------------------------------------------

class TestA08SalaryAnomalies:
    def test_clean_salary(self):
        offer = SimpleNamespace(offer_id=1, application_id=10, offered_salary=Decimal("600000"))
        req = SimpleNamespace(requisition_id=100, salary_min=Decimal("500000"), salary_max=Decimal("800000"), job_title="Dev")
        app = SimpleNamespace(application_id=10, requisition_id=100)
        anomalies = detect_salary_anomalies([offer], {100: req}, {10: app})
        assert anomalies == []

    def test_salary_below_minimum(self):
        offer = SimpleNamespace(offer_id=1, application_id=10, offered_salary=Decimal("400000"))
        req = SimpleNamespace(requisition_id=100, salary_min=Decimal("500000"), salary_max=Decimal("800000"), job_title="Dev")
        app = SimpleNamespace(application_id=10, requisition_id=100)
        anomalies = detect_salary_anomalies([offer], {100: req}, {10: app})
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A08"
        assert anomalies[0]["severity"] == "High"
        assert "below requisition minimum" in anomalies[0]["description"]

    def test_salary_above_maximum_moderate(self):
        offer = SimpleNamespace(offer_id=1, application_id=10, offered_salary=Decimal("900000"))
        req = SimpleNamespace(requisition_id=100, salary_min=Decimal("500000"), salary_max=Decimal("800000"), job_title="Dev")
        app = SimpleNamespace(application_id=10, requisition_id=100)
        anomalies = detect_salary_anomalies([offer], {100: req}, {10: app})
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A08"
        assert anomalies[0]["severity"] == "High"

    def test_salary_extreme_inflation(self):
        # 3.5x maximum inflation (like synthetic anomaly)
        offer = SimpleNamespace(offer_id=1, application_id=10, offered_salary=Decimal("2800000"))
        req = SimpleNamespace(requisition_id=100, salary_min=Decimal("500000"), salary_max=Decimal("800000"), job_title="Dev")
        app = SimpleNamespace(application_id=10, requisition_id=100)
        anomalies = detect_salary_anomalies([offer], {100: req}, {10: app})
        assert len(anomalies) == 1
        assert anomalies[0]["severity"] == "Critical"
        assert "3.5x band maximum" in anomalies[0]["description"]


# ---------------------------------------------------------------------------
# 9. A09 – Application Workflow Anomaly Tests
# ---------------------------------------------------------------------------

class TestA09ApplicationWorkflow:
    def test_clean_history(self):
        app = SimpleNamespace(application_id=1, current_stage="interview", status="active")
        hist = [
            SimpleNamespace(previous_stage=None, new_stage="applied", changed_at=datetime.now(timezone.utc)),
            SimpleNamespace(previous_stage="applied", new_stage="screening", changed_at=datetime.now(timezone.utc)),
            SimpleNamespace(previous_stage="screening", new_stage="interview", changed_at=datetime.now(timezone.utc)),
        ]
        assert detect_application_workflow_anomalies([app], {1: hist}) == []

    def test_invalid_stage_transition_jump(self):
        app = SimpleNamespace(application_id=1, current_stage="hired", status="hired")
        hist = [
            SimpleNamespace(previous_stage="applied", new_stage="hired", changed_at=datetime.now(timezone.utc)),
        ]
        anomalies = detect_application_workflow_anomalies([app], {1: hist})
        assert any(a["anomaly_code"] == "A09" and "invalid stage transition" in a["description"] for a in anomalies)

    def test_current_stage_inconsistent_with_history(self):
        app = SimpleNamespace(application_id=1, current_stage="offer", status="active")
        hist = [
            SimpleNamespace(previous_stage="applied", new_stage="screening", changed_at=datetime.now(timezone.utc)),
        ]
        anomalies = detect_application_workflow_anomalies([app], {1: hist})
        assert any("does not match its latest stage history" in a["description"] for a in anomalies)

    def test_rejected_application_with_later_interview(self):
        t_rej = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
        t_iv = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
        app = SimpleNamespace(application_id=1, current_stage="rejected", status="rejected")
        hist = [
            SimpleNamespace(previous_stage="applied", new_stage="rejected", changed_at=t_rej),
        ]
        ivs = [SimpleNamespace(interview_id=10, scheduled_at=t_iv)]
        anomalies = detect_application_workflow_anomalies([app], {1: hist}, interviews_by_application={1: ivs})
        assert any(a["severity"] == "Critical" and "was rejected on" in a["description"] for a in anomalies)


# ---------------------------------------------------------------------------
# 10. A10 – Recruitment Process Anomaly Tests
# ---------------------------------------------------------------------------

class TestA10RecruitmentProcess:
    def test_clean_closed_requisition(self):
        req = SimpleNamespace(requisition_id=1, status="closed", job_title="Engineer")
        apps = [
            SimpleNamespace(application_id=1, status="hired", current_stage="hired"),
            SimpleNamespace(application_id=2, status="rejected", current_stage="rejected"),
        ]
        assert detect_recruitment_process_anomalies([req], {1: apps}) == []

    def test_closed_requisition_with_active_applications(self):
        req = SimpleNamespace(requisition_id=1, status="closed", job_title="Engineer")
        apps = [
            SimpleNamespace(application_id=1, status="active", current_stage="interview"),
        ]
        anomalies = detect_recruitment_process_anomalies([req], {1: apps})
        assert len(anomalies) == 1
        assert anomalies[0]["anomaly_code"] == "A10"
        assert anomalies[0]["severity"] == "High"
        assert "applications still in active" in anomalies[0]["description"]

    def test_interview_scheduled_for_rejected_application(self):
        req = SimpleNamespace(requisition_id=1, status="open", job_title="Engineer")
        iv = SimpleNamespace(interview_id=5, application_id=10, status="scheduled")
        app = SimpleNamespace(application_id=10, status="rejected", current_stage="rejected")
        anomalies = detect_recruitment_process_anomalies(
            [req],
            {1: []},
            interviews=[iv],
            applications_by_id={10: app},
        )
        assert any(a["anomaly_code"] == "A10" and "already in 'rejected' status" in a["description"] for a in anomalies)


# ---------------------------------------------------------------------------
# 11. Data Quality Formula & No Double Counting
# ---------------------------------------------------------------------------

class TestDataQualityCalculation:
    def test_dq_formula_without_double_counting(self):
        # 3 anomalies on the SAME entity (Application 10)
        anomalies = [
            {"anomaly_code": "A01", "entity_type": "application", "entity_id": 10, "severity": "Medium", "status": "Open"},
            {"anomaly_code": "A02", "entity_type": "application", "entity_id": 10, "severity": "High", "status": "Open"},
            {"anomaly_code": "A09", "entity_type": "application", "entity_id": 10, "severity": "High", "status": "Open"},
            # 1 anomaly on Candidate 5
            {"anomaly_code": "A02", "entity_type": "candidate", "entity_id": 5, "severity": "Low", "status": "Open"},
        ]
        total_records = 100
        report = calculate_data_quality_metrics(anomalies, total_records)

        assert report["total_anomalies_found"] == 4
        # Unique anomalous entities must be 2, NOT 4!
        assert report["unique_anomalous_entities"] == 2
        # Clean entities = 100 - 2 = 98
        assert report["clean_records_count"] == 98
        # DQ % = 98.0%
        assert report["data_quality_percentage"] == 98.0

    def test_resolved_anomalies_restores_clean_count(self):
        anomalies = [
            {"anomaly_code": "A01", "entity_type": "application", "entity_id": 10, "severity": "Medium", "status": "Resolved"},
            {"anomaly_code": "A02", "entity_type": "candidate", "entity_id": 5, "severity": "Low", "status": "Open"},
        ]
        total_records = 100
        report = calculate_data_quality_metrics(anomalies, total_records)
        # Resolved is not active, only Candidate 5 is active
        assert report["unique_anomalous_entities"] == 1
        assert report["data_quality_percentage"] == 99.0


# ---------------------------------------------------------------------------
# 12. Persistence, Idempotency & Status Updates
# ---------------------------------------------------------------------------

class TestAnomalyServicePersistence:
    def test_run_detection_and_deduplication(self, setup_test_database):
        from tests.conftest import TestSessionLocal
        db = TestSessionLocal()
        try:
            # First run: detects and stores anomalies
            run1 = run_detection_and_persist(db, save_to_db=True)
            initial_count = run1["total_anomalies_found"]

            # Second run: must NOT duplicate records (idempotent)
            run2 = run_detection_and_persist(db, save_to_db=True)
            assert run2["new_anomalies_detected"] == 0
            assert run2["previously_existing_active_anomalies"] >= 0

            # Total rows in DB should match run1
            total_db = len(db.scalars(select(Anomaly)).all())
            assert total_db == initial_count
        finally:
            db.close()

    def test_status_update_workflow(self, setup_test_database):
        from tests.conftest import TestSessionLocal
        db = TestSessionLocal()
        try:
            anom = Anomaly(
                anomaly_code="A01",
                entity_type="candidate",
                entity_id=999,
                severity="Medium",
                description="Test Anomaly",
                recommended_action="Remediate",
                status="Open",
            )
            db.add(anom)
            db.commit()
            db.refresh(anom)

            # Move to Investigating
            updated = update_anomaly_status(db, anom.anomaly_id, "Investigating", notes="Assigned to lead")
            assert updated.status == "Investigating"
            assert updated.notes == "Assigned to lead"
            assert updated.resolved_at is None

            # Move to Resolved
            resolved = update_anomaly_status(db, anom.anomaly_id, "Resolved", notes="Fixed")
            assert resolved.status == "Resolved"
            assert resolved.resolved_at is not None
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 13. API Endpoints Tests
# ---------------------------------------------------------------------------

class TestAnomalyAPIEndpoints:
    def test_detect_endpoint(self, client):
        r = client.post("/anomalies/detect")
        assert r.status_code == 200
        body = r.json()
        assert "data_quality_percentage" in body
        assert "total_records_inspected" in body
        assert "anomalies_by_category" in body

    def test_summary_endpoint(self, client):
        r = client.get("/anomalies/summary")
        assert r.status_code == 200
        body = r.json()
        assert "clean_records_count" in body
        assert "anomalies_by_severity" in body

    def test_list_anomalies_endpoint(self, client):
        r = client.get("/anomalies/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_category_endpoint(self, client):
        r = client.get("/anomalies/category/A01")
        assert r.status_code == 200
        for item in r.json():
            assert item["anomaly_code"] == "A01"

    def test_filter_by_severity_endpoint(self, client):
        r = client.get("/anomalies/severity/Critical")
        assert r.status_code == 200
        for item in r.json():
            assert item["severity"] == "Critical"

    def test_get_anomaly_details_endpoint(self, client):
        list_r = client.get("/anomalies/", params={"limit": 1})
        if list_r.json():
            anom_id = list_r.json()[0]["anomaly_id"]
            r = client.get(f"/anomalies/{anom_id}")
            assert r.status_code == 200
            assert r.json()["anomaly_id"] == anom_id

    def test_get_anomaly_not_found(self, client):
        r = client.get("/anomalies/99999999")
        assert r.status_code == 404

    def test_update_anomaly_status_endpoint(self, client):
        list_r = client.get("/anomalies/", params={"limit": 1})
        if list_r.json():
            anom_id = list_r.json()[0]["anomaly_id"]
            r = client.patch(f"/anomalies/{anom_id}/status", json={
                "status": "Investigating",
                "notes": "Testing status update endpoint",
            })
            assert r.status_code == 200
            assert r.json()["status"] == "Investigating"

