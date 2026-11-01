"""
validation/anomaly_detector.py
==============================
Anomaly Detection Engine for RecruitFlow.

Orchestrates data retrieval, rule evaluation (A01 - A10), severity assignment,
and structured anomaly synthesis.
"""

from __future__ import annotations

from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStageHistory,
    Candidate,
    Department,
    Employee,
    Interview,
    Interviewer,
    Offer,
    Requisition,
    Scorecard,
)
from validation.anomaly_rules import (
    detect_candidate_experience_anomalies,
    detect_duplicate_application_anomalies,
    detect_experience_anomaly,  # Backward compatibility
    detect_interview_assignment_anomalies,
    detect_interview_scheduling_anomalies,
    detect_offer_approval_anomalies,
    detect_offer_date_anomalies,
    detect_recruitment_process_anomalies,
    detect_salary_anomalies,
    detect_scorecard_anomalies,
    detect_application_workflow_anomalies,
)

# Re-export for existing Part 1 tests
__all__ = ["AnomalyDetector", "detect_experience_anomaly"]


class AnomalyDetector:
    """
    Main detection engine that inspects database entities and executes
    rules A01 through A10.
    """

    def __init__(self, db: Session):
        self.db = db

    def run_detection(self) -> dict[str, Any]:
        """
        Execute full scan across all database records and return detected anomalies
        along with inspection statistics.
        """
        # 1. Load entities
        candidates = list(self.db.scalars(select(Candidate)).all())
        requisitions = list(self.db.scalars(select(Requisition)).all())
        applications = list(self.db.scalars(select(Application)).all())
        interviews = list(self.db.scalars(select(Interview)).all())
        interviewers = list(self.db.scalars(select(Interviewer)).all())
        scorecards = list(self.db.scalars(select(Scorecard)).all())
        offers = list(self.db.scalars(select(Offer)).all())
        employees = list(self.db.scalars(select(Employee)).all())
        stage_histories = list(
            self.db.scalars(
                select(ApplicationStageHistory).order_by(ApplicationStageHistory.changed_at)
            ).all()
        )

        # 2. Build fast lookup indices
        candidates_by_id = {c.candidate_id: c for c in candidates}
        requisitions_by_id = {r.requisition_id: r for r in requisitions}
        applications_by_id = {a.application_id: a for a in applications}
        employees_by_id = {e.employee_id: e for e in employees}

        assignments_by_interview: dict[int, list[Interviewer]] = {}
        assigned_panelists: set[tuple[int, int]] = set()
        for assign in interviewers:
            assignments_by_interview.setdefault(assign.interview_id, []).append(assign)
            assigned_panelists.add((assign.interview_id, assign.employee_id))

        history_by_app: dict[int, list[ApplicationStageHistory]] = {}
        for h in stage_histories:
            history_by_app.setdefault(h.application_id, []).append(h)

        apps_by_requisition: dict[int, list[Application]] = {}
        for app in applications:
            apps_by_requisition.setdefault(app.requisition_id, []).append(app)

        interviews_by_app: dict[int, list[Interview]] = {}
        for iv in interviews:
            interviews_by_app.setdefault(iv.application_id, []).append(iv)

        detected_anomalies: list[dict[str, Any]] = []

        # -------------------------------------------------------------------
        # Rule Evaluation
        # -------------------------------------------------------------------

        # A01: Candidate Experience Anomalies (evaluated across applications)
        for app in applications:
            cand = candidates_by_id.get(app.candidate_id)
            req = requisitions_by_id.get(app.requisition_id)
            if cand and req:
                detected_anomalies.extend(
                    detect_candidate_experience_anomalies(
                        candidate=cand,
                        requisition=req,
                        application_id=app.application_id,
                    )
                )

        # A02: Duplicate Applications
        detected_anomalies.extend(
            detect_duplicate_application_anomalies(applications=applications)
        )

        # A03: Interview Assignments
        detected_anomalies.extend(
            detect_interview_assignment_anomalies(
                interviews=interviews,
                assignments_by_interview=assignments_by_interview,
                employees_by_id=employees_by_id,
            )
        )

        # A04: Interview Scheduling
        detected_anomalies.extend(
            detect_interview_scheduling_anomalies(
                interviews=interviews,
                assignments_by_interview=assignments_by_interview,
            )
        )

        # A05: Scorecards
        detected_anomalies.extend(
            detect_scorecard_anomalies(
                scorecards=scorecards,
                assigned_interview_panelists=assigned_panelists,
            )
        )

        # A06: Offer Approvals
        detected_anomalies.extend(
            detect_offer_approval_anomalies(
                offers=offers,
                employees_by_id=employees_by_id,
            )
        )

        # A07: Offer Dates
        detected_anomalies.extend(
            detect_offer_date_anomalies(offers=offers)
        )

        # A08: Salaries
        detected_anomalies.extend(
            detect_salary_anomalies(
                offers=offers,
                requisitions_by_id=requisitions_by_id,
                applications_by_id=applications_by_id,
            )
        )

        # A09: Application Workflow
        detected_anomalies.extend(
            detect_application_workflow_anomalies(
                applications=applications,
                history_by_application=history_by_app,
                interviews_by_application=interviews_by_app,
            )
        )

        # A10: Recruitment Process
        detected_anomalies.extend(
            detect_recruitment_process_anomalies(
                requisitions=requisitions,
                applications_by_requisition=apps_by_requisition,
                interviews=interviews,
                applications_by_id=applications_by_id,
            )
        )

        # Total unique records inspected
        records_inspected = {
            "candidates": len(candidates),
            "requisitions": len(requisitions),
            "applications": len(applications),
            "interviews": len(interviews),
            "scorecards": len(scorecards),
            "offers": len(offers),
        }

        return {
            "anomalies": detected_anomalies,
            "records_inspected": records_inspected,
            "total_records_inspected": sum(records_inspected.values()),
        }
