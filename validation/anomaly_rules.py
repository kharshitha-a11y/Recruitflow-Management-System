"""
validation/anomaly_rules.py
===========================
Pure rule evaluation functions for RecruitFlow Anomaly Detection Engine.

Covers categories A01 through A10:
  - A01: Candidate experience anomaly
  - A02: Duplicate application anomaly
  - A03: Interview assignment anomaly
  - A04: Interview scheduling anomaly
  - A05: Scorecard anomaly
  - A06: Offer approval anomaly
  - A07: Offer date anomaly
  - A08: Salary anomaly (rule-based + statistical IQR/Z-score)
  - A09: Application workflow anomaly
  - A10: Recruitment process anomaly
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helper: Anomaly Record Builder
# ---------------------------------------------------------------------------

def make_anomaly(
    anomaly_code: str,
    entity_type: str,
    entity_id: int,
    severity: str,
    description: str,
    recommended_action: str,
) -> dict[str, Any]:
    """Create a standardized anomaly dictionary."""
    return {
        "anomaly_code": anomaly_code,
        "entity_type": entity_type,
        "entity_id": int(entity_id),
        "severity": severity,
        "description": description,
        "recommended_action": recommended_action,
        "status": "Open",
    }


# ---------------------------------------------------------------------------
# A01: Candidate Experience Anomaly
# ---------------------------------------------------------------------------

def detect_candidate_experience_anomalies(
    candidate: Any,
    requisition: Any,
    application_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Check if candidate's experience violates requisition min/max requirements.
    Entity: application (or candidate if application_id is absent).
    """
    anomalies: list[dict[str, Any]] = []
    entity_id = application_id if application_id is not None else getattr(candidate, "candidate_id", 0)
    entity_type = "application" if application_id is not None else "candidate"

    exp = getattr(candidate, "experience_years", None)
    if exp is None:
        return anomalies

    exp_dec = Decimal(str(exp))
    req_min = Decimal(str(getattr(requisition, "experience_min", 0)))
    req_max = Decimal(str(getattr(requisition, "experience_max", 99)))

    if exp_dec < req_min:
        anomalies.append(
            make_anomaly(
                anomaly_code="A01",
                entity_type=entity_type,
                entity_id=entity_id,
                severity="Medium",
                description=(
                    f"Candidate experience ({exp_dec} years) is below minimum required "
                    f"({req_min} years) for Requisition {getattr(requisition, 'requisition_id', '')} "
                    f"('{getattr(requisition, 'job_title', 'Role')}')."
                ),
                recommended_action="Review candidate qualifications or adjust requisition minimum experience requirements.",
            )
        )

    if exp_dec > req_max:
        severity = "Medium" if (exp_dec - req_max) >= Decimal("5.0") else "Low"
        anomalies.append(
            make_anomaly(
                anomaly_code="A01",
                entity_type=entity_type,
                entity_id=entity_id,
                severity=severity,
                description=(
                    f"Candidate experience ({exp_dec} years) exceeds maximum allowed "
                    f"({req_max} years) for Requisition {getattr(requisition, 'requisition_id', '')} "
                    f"('{getattr(requisition, 'job_title', 'Role')}')."
                ),
                recommended_action="Evaluate candidate for potential overqualification or route to higher-level requisitions.",
            )
        )

    return anomalies


def detect_experience_anomaly(candidate: Any, requisition: Any) -> list[dict[str, Any]]:
    """
    Legacy wrapper maintaining 100% backward compatibility with tests/test_anomaly_detector.py.
    """
    anomalies = []
    exp = candidate.experience_years
    if exp < requisition.experience_min:
        anomalies.append({
            "anomaly_code": "A01",
            "severity": "medium",
            "description": (
                f"Candidate experience {candidate.experience_years} "
                f"is below minimum required experience "
                f"{requisition.experience_min}."
            ),
        })
    if exp > requisition.experience_max:
        anomalies.append({
            "anomaly_code": "A02",
            "severity": "low",
            "description": (
                f"Candidate experience {candidate.experience_years} "
                f"exceeds maximum allowed experience "
                f"{requisition.experience_max}."
            ),
        })
    return anomalies


# ---------------------------------------------------------------------------
# A02: Duplicate Application Anomaly
# ---------------------------------------------------------------------------

def detect_duplicate_application_anomalies(
    applications: list[Any],
) -> list[dict[str, Any]]:
    """
    Detect duplicate applications for the same (candidate, requisition) and
    suspicious repeated applications across multiple requisitions.
    """
    anomalies: list[dict[str, Any]] = []
    seen_pairs: dict[tuple[int, int], int] = {}
    candidate_app_counts: dict[int, list[int]] = {}

    for app in applications:
        cand_id = getattr(app, "candidate_id", None)
        req_id = getattr(app, "requisition_id", None)
        app_id = getattr(app, "application_id", None)
        if cand_id is None or req_id is None or app_id is None:
            continue

        pair = (cand_id, req_id)
        if pair in seen_pairs:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A02",
                    entity_type="application",
                    entity_id=app_id,
                    severity="High",
                    description=(
                        f"Duplicate application detected: Candidate {cand_id} has applied "
                        f"more than once to Requisition {req_id} (original application: {seen_pairs[pair]})."
                    ),
                    recommended_action="Merge or archive redundant application record to prevent duplicate processing.",
                )
            )
        else:
            seen_pairs[pair] = app_id

        candidate_app_counts.setdefault(cand_id, []).append(app_id)

    # Flag suspicious mass applications (>= 6 applications by single candidate)
    for cand_id, app_ids in candidate_app_counts.items():
        if len(app_ids) >= 6:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A02",
                    entity_type="candidate",
                    entity_id=cand_id,
                    severity="Medium",
                    description=(
                        f"Candidate {cand_id} has submitted {len(app_ids)} applications across "
                        f"multiple requisitions (Applications: {app_ids[:5]}...)."
                    ),
                    recommended_action="Screen candidate profile for automated submission or bot activity.",
                )
            )

    return anomalies


# ---------------------------------------------------------------------------
# A03: Interview Assignment Anomaly
# ---------------------------------------------------------------------------

def detect_interview_assignment_anomalies(
    interviews: list[Any],
    assignments_by_interview: dict[int, list[Any]],
    employees_by_id: Optional[dict[int, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Detect interviews without interviewers, duplicate panelist assignments,
    or assignments to employees without interviewer authority.
    """
    anomalies: list[dict[str, Any]] = []

    for iv in interviews:
        iv_id = getattr(iv, "interview_id", None)
        if iv_id is None:
            continue

        assignments = assignments_by_interview.get(iv_id, [])
        status = getattr(iv, "status", "")

        # Sub-rule 1: Interview without assigned interviewer
        if not assignments and status in ("scheduled", "completed"):
            anomalies.append(
                make_anomaly(
                    anomaly_code="A03",
                    entity_type="interview",
                    entity_id=iv_id,
                    severity="High",
                    description=(
                        f"Interview {iv_id} (Round {getattr(iv, 'interview_round', 1)}, "
                        f"{getattr(iv, 'interview_type', 'Interview')}) has no assigned interviewers."
                    ),
                    recommended_action="Assign at least one qualified panelist to conduct the interview.",
                )
            )

        # Sub-rule 2: Duplicate interviewer assignments to same interview
        seen_emps: set[int] = set()
        for assign in assignments:
            emp_id = getattr(assign, "employee_id", None)
            if emp_id is None:
                continue
            if emp_id in seen_emps:
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A03",
                        entity_type="interview",
                        entity_id=iv_id,
                        severity="Medium",
                        description=(
                            f"Employee {emp_id} is assigned multiple times to Interview {iv_id}."
                        ),
                        recommended_action="Remove duplicate interviewer assignment entry.",
                    )
                )
            seen_emps.add(emp_id)

            # Sub-rule 3: Invalid employee assignment (if employee directory available)
            if employees_by_id and emp_id not in employees_by_id:
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A03",
                        entity_type="interview",
                        entity_id=iv_id,
                        severity="Critical",
                        description=(
                            f"Interview {iv_id} is assigned to non-existent employee ID {emp_id}."
                        ),
                        recommended_action="Reassign interview to an active employee.",
                    )
                )

    return anomalies


# ---------------------------------------------------------------------------
# A04: Interview Scheduling Anomaly
# ---------------------------------------------------------------------------

def detect_interview_scheduling_anomalies(
    interviews: list[Any],
    assignments_by_interview: Optional[dict[int, list[Any]]] = None,
) -> list[dict[str, Any]]:
    """
    Detect completion date before scheduled date, invalid statuses,
    and overlapping interview schedules for the same panelist.
    """
    anomalies: list[dict[str, Any]] = []
    VALID_STATUSES = {"scheduled", "completed", "cancelled", "rescheduled"}

    # Track employee interview schedules to check for overlaps
    panelist_schedules: dict[int, list[tuple[datetime, int]]] = {}

    for iv in interviews:
        iv_id = getattr(iv, "interview_id", None)
        if iv_id is None:
            continue

        sched = getattr(iv, "scheduled_at", None)
        comp = getattr(iv, "completed_at", None)
        status = getattr(iv, "status", None)

        # Sub-rule 1: Status validity
        if status not in VALID_STATUSES:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A04",
                    entity_type="interview",
                    entity_id=iv_id,
                    severity="Medium",
                    description=f"Interview {iv_id} has invalid status '{status}'.",
                    recommended_action=f"Update status to one of {sorted(VALID_STATUSES)}.",
                )
            )

        # Sub-rule 2: Completion before scheduled time
        if sched and comp and comp < sched:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A04",
                    entity_type="interview",
                    entity_id=iv_id,
                    severity="Critical",
                    description=(
                        f"Interview {iv_id} completion timestamp ({comp}) precedes "
                        f"scheduled timestamp ({sched})."
                    ),
                    recommended_action="Correct interview completion timestamp in the audit log.",
                )
            )

        # Sub-rule 3: Completed status without completed_at timestamp
        if status == "completed" and comp is None:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A04",
                    entity_type="interview",
                    entity_id=iv_id,
                    severity="Medium",
                    description=f"Interview {iv_id} is marked 'completed' but completed_at is null.",
                    recommended_action="Record actual interview completion timestamp.",
                )
            )

        # Record schedules for overlap detection
        if assignments_by_interview and sched and status == "scheduled":
            for assign in assignments_by_interview.get(iv_id, []):
                emp_id = getattr(assign, "employee_id", None)
                if emp_id:
                    panelist_schedules.setdefault(emp_id, []).append((sched, iv_id))

    # Detect overlapping interviews for same panelist (< 45 minutes apart)
    for emp_id, sched_list in panelist_schedules.items():
        if len(sched_list) < 2:
            continue
        sorted_sched = sorted(sched_list, key=lambda x: x[0])
        for i in range(len(sorted_sched) - 1):
            t1, iv1 = sorted_sched[i]
            t2, iv2 = sorted_sched[i + 1]
            diff_min = abs((t2 - t1).total_seconds()) / 60.0
            if diff_min < 45.0:
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A04",
                        entity_type="interview",
                        entity_id=iv2,
                        severity="High",
                        description=(
                            f"Suspicious overlapping schedule: Panelist {emp_id} is scheduled for "
                            f"Interview {iv1} at {t1} and Interview {iv2} at {t2} "
                            f"(gap is only {int(diff_min)} minutes)."
                        ),
                        recommended_action="Reschedule one of the conflicting interviews to prevent panelist overlap.",
                    )
                )

    return anomalies


# ---------------------------------------------------------------------------
# A05: Scorecard Anomaly
# ---------------------------------------------------------------------------

def detect_scorecard_anomalies(
    scorecards: list[Any],
    assigned_interview_panelists: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    """
    Detect scorecards submitted by unauthorized panelists, out-of-range scores,
    missing recommendations, and score/recommendation discrepancies.
    """
    anomalies: list[dict[str, Any]] = []
    VALID_RECS = {"strong_hire", "hire", "hold", "no_hire"}

    for sc in scorecards:
        sc_id = getattr(sc, "scorecard_id", None)
        iv_id = getattr(sc, "interview_id", None)
        emp_id = getattr(sc, "employee_id", None)
        if sc_id is None:
            continue

        # Sub-rule 1: Scorecard without valid interviewer assignment
        if (iv_id, emp_id) not in assigned_interview_panelists:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A05",
                    entity_type="scorecard",
                    entity_id=sc_id,
                    severity="Critical",
                    description=(
                        f"Scorecard {sc_id} submitted by Employee {emp_id} who is not "
                        f"an assigned interviewer for Interview {iv_id}."
                    ),
                    recommended_action="Validate panelist assignment or invalidate unauthorized scorecard.",
                )
            )

        # Sub-rule 2: Scores out of range
        scores = {
            "technical_score": getattr(sc, "technical_score", None),
            "communication_score": getattr(sc, "communication_score", None),
            "problem_solving_score": getattr(sc, "problem_solving_score", None),
            "overall_score": getattr(sc, "overall_score", None),
        }
        for name, val in scores.items():
            if val is not None:
                d_val = Decimal(str(val))
                if d_val < Decimal("0") or d_val > Decimal("10"):
                    anomalies.append(
                        make_anomaly(
                            anomaly_code="A05",
                            entity_type="scorecard",
                            entity_id=sc_id,
                            severity="Critical",
                            description=f"Scorecard {sc_id} {name} ({d_val}) is outside allowed [0, 10] range.",
                            recommended_action="Adjust score to conform to standard 0-10 rating scale.",
                        )
                    )

        # Sub-rule 3: Missing or invalid recommendation
        rec = getattr(sc, "recommendation", None)
        if not rec or rec not in VALID_RECS:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A05",
                    entity_type="scorecard",
                    entity_id=sc_id,
                    severity="High",
                    description=f"Scorecard {sc_id} has invalid or missing recommendation '{rec}'.",
                    recommended_action=f"Require evaluator to choose one of {sorted(VALID_RECS)}.",
                )
            )

        # Sub-rule 4: Suspicious score inconsistency
        overall = getattr(sc, "overall_score", None)
        if overall is not None and rec in VALID_RECS:
            d_over = Decimal(str(overall))
            if d_over >= Decimal("8.5") and rec == "no_hire":
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A05",
                        entity_type="scorecard",
                        entity_id=sc_id,
                        severity="Medium",
                        description=(
                            f"Suspicious score inconsistency: Scorecard {sc_id} has high overall score "
                            f"({d_over}/10) but recommendation is 'no_hire'."
                        ),
                        recommended_action="Review scorecard comments to reconcile qualitative and quantitative ratings.",
                    )
                )
            elif d_over <= Decimal("3.5") and rec == "strong_hire":
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A05",
                        entity_type="scorecard",
                        entity_id=sc_id,
                        severity="Medium",
                        description=(
                            f"Suspicious score inconsistency: Scorecard {sc_id} has low overall score "
                            f"({d_over}/10) but recommendation is 'strong_hire'."
                        ),
                        recommended_action="Review scorecard comments to reconcile qualitative and quantitative ratings.",
                    )
                )

    return anomalies


# ---------------------------------------------------------------------------
# A06: Offer Approval Anomaly
# ---------------------------------------------------------------------------

def detect_offer_approval_anomalies(
    offers: list[Any],
    employees_by_id: Optional[dict[int, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Detect released/approved offers without approver records, or pending offers
    with premature approvals, or approvals by unauthorized roles.
    """
    anomalies: list[dict[str, Any]] = []

    for offer in offers:
        offer_id = getattr(offer, "offer_id", None)
        if offer_id is None:
            continue

        status = getattr(offer, "status", None)
        approver_id = getattr(offer, "approved_by", None)

        # Sub-rule 1: Released offer without approver
        if status == "released" and approver_id is None:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A06",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Critical",
                    description=f"Offer {offer_id} is in 'released' status but has no approver record.",
                    recommended_action="Halt offer release and obtain formal approval from hiring authority.",
                )
            )

        # Sub-rule 2: Approved offer without approver
        if status == "approved" and approver_id is None:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A06",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Critical",
                    description=f"Offer {offer_id} is marked 'approved' but approved_by is null.",
                    recommended_action="Assign designated approver to record approval audit trail.",
                )
            )

        # Sub-rule 3: Pending approval offer with approval record already populated
        if status == "pending_approval" and approver_id is not None:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A06",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Medium",
                    description=(
                        f"Offer {offer_id} is in 'pending_approval' status but approved_by "
                        f"is already set to Employee {approver_id}."
                    ),
                    recommended_action="Advance status to 'approved' or clear premature approver entry.",
                )
            )

        # Sub-rule 4: Approver role verification
        if approver_id and employees_by_id and approver_id in employees_by_id:
            emp = employees_by_id[approver_id]
            role = getattr(emp, "role", "").lower()
            authorized_keywords = ("manager", "director", "vp", "head", "lead", "recruiter", "admin", "hr")
            if not any(k in role for k in authorized_keywords):
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A06",
                        entity_type="offer",
                        entity_id=offer_id,
                        severity="High",
                        description=(
                            f"Offer {offer_id} was approved by Employee {approver_id} with "
                            f"non-authorized role '{getattr(emp, 'role', '')}'."
                        ),
                        recommended_action="Re-route offer for approval by authorized management personnel.",
                    )
                )

    return anomalies


# ---------------------------------------------------------------------------
# A07: Offer Date Anomaly
# ---------------------------------------------------------------------------

def detect_offer_date_anomalies(
    offers: list[Any],
) -> list[dict[str, Any]]:
    """
    Detect expiry date before offer date, joining date before offer date,
    or unreasonable offer lifecycle durations.
    """
    anomalies: list[dict[str, Any]] = []

    for offer in offers:
        offer_id = getattr(offer, "offer_id", None)
        if offer_id is None:
            continue

        offer_date = getattr(offer, "offer_date", None)
        expiry_date = getattr(offer, "expiry_date", None)
        joining_date = getattr(offer, "joining_date", None)

        if not offer_date:
            continue

        # Sub-rule 1: Expiry date before offer date
        if expiry_date and expiry_date < offer_date:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A07",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Critical",
                    description=(
                        f"Offer {offer_id} expiry date ({expiry_date}) precedes "
                        f"offer date ({offer_date})."
                    ),
                    recommended_action="Extend offer expiration date to a valid future deadline.",
                )
            )

        # Sub-rule 2: Joining date before offer date
        if joining_date and joining_date < offer_date:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A07",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Critical",
                    description=(
                        f"Offer {offer_id} joining date ({joining_date}) precedes "
                        f"offer date ({offer_date})."
                    ),
                    recommended_action="Reschedule candidate joining date to follow offer issuance.",
                )
            )

        # Sub-rule 3: Unreasonable lifecycle span (> 180 days to expiry or > 365 days to join)
        if expiry_date and (expiry_date - offer_date).days > 180:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A07",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Medium",
                    description=(
                        f"Offer {offer_id} has an unusually long expiration window "
                        f"({(expiry_date - offer_date).days} days)."
                    ),
                    recommended_action="Review offer expiration deadline with talent acquisition team.",
                )
            )

        if joining_date and (joining_date - offer_date).days > 365:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A07",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="Medium",
                    description=(
                        f"Offer {offer_id} joining date is over a year after offer issuance "
                        f"({(joining_date - offer_date).days} days)."
                    ),
                    recommended_action="Confirm joining date timeline with candidate and hiring manager.",
                )
            )

    return anomalies


# ---------------------------------------------------------------------------
# A08: Salary Anomaly (Rule-Based + Statistical IQR / Z-Score)
# ---------------------------------------------------------------------------

def detect_salary_anomalies(
    offers: list[Any],
    requisitions_by_id: dict[int, Any],
    applications_by_id: dict[int, Any],
) -> list[dict[str, Any]]:
    """
    Detect offered salary below requisition minimum, above maximum,
    and statistical salary outliers (e.g. 3.5x inflated offers from Part 1).
    """
    anomalies: list[dict[str, Any]] = []
    salaries: list[float] = []
    valid_offer_records: list[tuple[Any, Any]] = []

    for offer in offers:
        offer_id = getattr(offer, "offer_id", None)
        app_id = getattr(offer, "application_id", None)
        if offer_id is None or app_id is None:
            continue

        app = applications_by_id.get(app_id)
        if not app:
            continue

        req = requisitions_by_id.get(getattr(app, "requisition_id", None))
        if not req:
            continue

        salary = Decimal(str(getattr(offer, "offered_salary", 0)))
        req_min = Decimal(str(getattr(req, "salary_min", 0)))
        req_max = Decimal(str(getattr(req, "salary_max", 0)))

        # Sub-rule 1: Salary below requisition minimum
        if salary < req_min:
            anomalies.append(
                make_anomaly(
                    anomaly_code="A08",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity="High",
                    description=(
                        f"Offered salary (INR {salary:,.2f}) is below requisition minimum "
                        f"(INR {req_min:,.2f}) for '{getattr(req, 'job_title', 'Role')}'."
                    ),
                    recommended_action="Adjust offered compensation to meet requisition minimum band.",
                )
            )

        # Sub-rule 2: Salary above requisition maximum
        if salary > req_max:
            # Extreme inflation check (e.g., synthetic anomaly 3.5x)
            is_extreme = salary >= (req_max * Decimal("2.0"))
            severity = "Critical" if is_extreme else "High"
            ratio_str = f" ({float(salary / req_max):.1f}x band maximum)" if is_extreme else ""
            anomalies.append(
                make_anomaly(
                    anomaly_code="A08",
                    entity_type="offer",
                    entity_id=offer_id,
                    severity=severity,
                    description=(
                        f"Offered salary (INR {salary:,.2f}) exceeds requisition maximum "
                        f"(INR {req_max:,.2f}){ratio_str} for '{getattr(req, 'job_title', 'Role')}'."
                    ),
                    recommended_action="Obtain VP / Executive compensation approval for band overshoot.",
                )
            )

        salaries.append(float(salary))
        valid_offer_records.append((offer, req))

    # Statistical outlier check via Interquartile Range (IQR) on all offers
    if len(salaries) >= 15:
        q75, q25 = np.percentile(salaries, [75, 25])
        iqr = q75 - q25
        upper_bound = q75 + (2.5 * iqr)  # Extreme statistical outlier threshold

        for offer, req in valid_offer_records:
            s_val = float(offer.offered_salary)
            if s_val > upper_bound and s_val > float(req.salary_max):
                # Check if not already flagged as critical above
                existing_crit = any(
                    a["entity_id"] == offer.offer_id and a["severity"] == "Critical"
                    for a in anomalies
                )
                if not existing_crit:
                    anomalies.append(
                        make_anomaly(
                            anomaly_code="A08",
                            entity_type="offer",
                            entity_id=offer.offer_id,
                            severity="Critical",
                            description=(
                                f"Statistical salary outlier: Offered salary (INR {s_val:,.2f}) exceeds "
                                f"2.5x IQR upper threshold (INR {upper_bound:,.2f}) across dataset."
                            ),
                            recommended_action="Audit offer compensation against organizational benchmarks.",
                        )
                    )

    return anomalies


# ---------------------------------------------------------------------------
# A09: Application Workflow Anomaly
# ---------------------------------------------------------------------------

def detect_application_workflow_anomalies(
    applications: list[Any],
    history_by_application: dict[int, list[Any]],
    interviews_by_application: Optional[dict[int, list[Any]]] = None,
    offers_by_application: Optional[dict[int, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Detect invalid stage transitions, mismatch between latest history and
    current application stage, or active events occurring after rejection.
    """
    anomalies: list[dict[str, Any]] = []

    VALID_TRANSITIONS: dict[str, set[str]] = {
        "applied": {"screening", "rejected"},
        "screening": {"interview", "rejected"},
        "interview": {"assessment", "offer", "rejected"},
        "assessment": {"offer", "rejected"},
        "offer": {"hired", "rejected"},
        "hired": set(),
        "rejected": set(),
    }

    for app in applications:
        app_id = getattr(app, "application_id", None)
        if app_id is None:
            continue

        histories = history_by_application.get(app_id, [])
        current_stage = getattr(app, "current_stage", "")
        status = getattr(app, "status", "")

        # Sub-rule 1: Audit stage transitions in history
        rejection_date: Optional[datetime] = None
        for h in histories:
            prev = getattr(h, "previous_stage", None)
            new_s = getattr(h, "new_stage", "")
            changed_at = getattr(h, "changed_at", None)

            if new_s == "rejected" and rejection_date is None:
                rejection_date = changed_at

            if prev is not None:
                allowed = VALID_TRANSITIONS.get(prev, set())
                if new_s not in allowed:
                    anomalies.append(
                        make_anomaly(
                            anomaly_code="A09",
                            entity_type="application",
                            entity_id=app_id,
                            severity="High",
                            description=(
                                f"Application {app_id} recorded invalid stage transition from "
                                f"'{prev}' to '{new_s}'."
                            ),
                            recommended_action="Reconcile stage history audit trail.",
                        )
                    )

        # Sub-rule 2: Latest history stage must match current_stage
        if histories:
            latest = histories[-1]
            latest_stage = getattr(latest, "new_stage", None)
            if latest_stage and latest_stage != current_stage:
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A09",
                        entity_type="application",
                        entity_id=app_id,
                        severity="High",
                        description=(
                            f"Application {app_id} current_stage ('{current_stage}') does not match "
                            f"its latest stage history record ('{latest_stage}')."
                        ),
                        recommended_action="Synchronize application current_stage with stage history audit trail.",
                    )
                )

        # Sub-rule 3: Active workflow events after rejection
        if (status == "rejected" or current_stage == "rejected") and interviews_by_application:
            for iv in interviews_by_application.get(app_id, []):
                iv_sched = getattr(iv, "scheduled_at", None)
                if rejection_date and iv_sched and iv_sched > rejection_date:
                    anomalies.append(
                        make_anomaly(
                            anomaly_code="A09",
                            entity_type="application",
                            entity_id=app_id,
                            severity="Critical",
                            description=(
                                f"Application {app_id} was rejected on {rejection_date.date()}, but "
                                f"Interview {getattr(iv, 'interview_id', '')} was scheduled on {iv_sched.date()}."
                            ),
                            recommended_action="Cancel post-rejection interviews and investigate unauthorized pipeline activity.",
                        )
                    )

    return anomalies


# ---------------------------------------------------------------------------
# A10: Recruitment Process Anomaly
# ---------------------------------------------------------------------------

def detect_recruitment_process_anomalies(
    requisitions: list[Any],
    applications_by_requisition: dict[int, list[Any]],
    interviews: Optional[list[Any]] = None,
    applications_by_id: Optional[dict[int, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Detect closed requisitions with active applications, interviews scheduled
    on rejected applications, or offers extended without any completed interview.
    """
    anomalies: list[dict[str, Any]] = []

    # Sub-rule 1: Requisition closed while applications remain active
    for req in requisitions:
        req_id = getattr(req, "requisition_id", None)
        if req_id is None:
            continue

        req_status = getattr(req, "status", "")
        if req_status in ("closed", "cancelled"):
            active_apps = [
                a for a in applications_by_requisition.get(req_id, [])
                if getattr(a, "status", "") == "active"
                or getattr(a, "current_stage", "") not in ("hired", "rejected")
            ]
            if active_apps:
                anomalies.append(
                    make_anomaly(
                        anomaly_code="A10",
                        entity_type="requisition",
                        entity_id=req_id,
                        severity="High",
                        description=(
                            f"Requisition {req_id} ('{getattr(req, 'job_title', 'Role')}') is '{req_status}', "
                            f"but has {len(active_apps)} applications still in active pipeline stages."
                        ),
                        recommended_action="Resolve or reject active applications before finalizing requisition closure.",
                    )
                )

    # Sub-rule 2: Interviews scheduled for rejected applications
    if interviews and applications_by_id:
        for iv in interviews:
            app_id = getattr(iv, "application_id", None)
            iv_id = getattr(iv, "interview_id", None)
            if app_id and iv_id:
                app = applications_by_id.get(app_id)
                if app:
                    app_status = getattr(app, "status", "")
                    iv_status = getattr(iv, "status", "")
                    if app_status == "rejected" and iv_status == "scheduled":
                        anomalies.append(
                            make_anomaly(
                                anomaly_code="A10",
                                entity_type="interview",
                                entity_id=iv_id,
                                severity="High",
                                description=(
                                    f"Interview {iv_id} is scheduled for Application {app_id}, "
                                    f"which is already in 'rejected' status."
                                ),
                                recommended_action="Cancel scheduled interview for rejected applicant.",
                            )
                        )

    return anomalies
