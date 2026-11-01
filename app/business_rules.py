"""
app/business_rules.py
=====================
Reusable business rules engine for RecruitFlow recruitment workflow.

Enforces business rules such as:
  - Applications can only be submitted for open requisitions.
  - Candidate experience must satisfy job requirements.
  - Duplicate applications must be prevented.
  - Interviewers must be assigned before submitting scorecards.
  - Scorecard values must be between 0 and 10.
  - Only authorized employees can approve offers.
  - Released offers must have an approver.
  - Offer expiry date must not precede offer date.
  - Joining date must be valid (must not precede offer date).
  - Invalid workflow transitions must be rejected.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Custom Exceptions (Mapped to standard HTTP status codes in app/main.py)
# ---------------------------------------------------------------------------


class BusinessRuleError(ValueError):
    """Raised when an operation violates a recruitment business rule (HTTP 400)."""
    pass


class ResourceNotFoundError(KeyError):
    """Raised when a requested entity does not exist in the database (HTTP 404)."""
    pass


class ConflictError(ValueError):
    """Raised when an action would produce a duplicate or conflicting entity (HTTP 409)."""
    pass


# ---------------------------------------------------------------------------
# 1. Application Validation (Preserves Part 1 signature & tests)
# ---------------------------------------------------------------------------


def validate_application(candidate: Any, requisition: Any) -> list[str]:
    """
    Validate whether a candidate can apply for a requisition.
    Returns a list of validation error strings (empty if valid).
    """
    errors: list[str] = []

    # Rule 1: Requisition must be open
    if requisition.status != "open":
        errors.append("Requisition is not open.")

    # Rule 2: Candidate must meet minimum experience
    if candidate.experience_years < requisition.experience_min:
        errors.append("Candidate does not meet minimum experience.")

    # Rule 3: Candidate must not exceed maximum experience
    if candidate.experience_years > requisition.experience_max:
        errors.append("Candidate exceeds maximum experience.")

    return errors


# ---------------------------------------------------------------------------
# 2. Interview Assignment Validation (Preserves Part 1 signature & tests)
# ---------------------------------------------------------------------------


def validate_interview_assignment(interview: Any, interviewer: Any) -> list[str]:
    """
    Validate interviewer assignment to an interview.
    Returns a list of validation error strings (empty if valid).
    """
    errors: list[str] = []

    # Rule 4: Interview must be scheduled
    if interview is None or getattr(interview, "status", None) != "scheduled":
        errors.append("Interview is not in scheduled status.")

    # Rule 5: Interviewer must exist
    if interviewer is None:
        errors.append("Interviewer does not exist.")

    return errors


# ---------------------------------------------------------------------------
# 3. Offer Validation (Preserves Part 1 signature & tests)
# ---------------------------------------------------------------------------


def validate_offer(offer: Any) -> list[str]:
    """
    Validate offer dates and basic approval requirements.
    Returns a list of validation error strings (empty if valid).
    """
    errors: list[str] = []

    # Rule 6: Approved and released offers need an approver
    if offer.status in ("approved", "released"):
        if getattr(offer, "approved_by", None) is None:
            errors.append("Approved or released offer has no approver.")

    # Rule 7: Pending approval should not already have an approver
    if offer.status == "pending_approval":
        if getattr(offer, "approved_by", None) is not None:
            errors.append("Pending approval offer already has an approver.")

    # Rule 8: Offer expiry date must not precede offer date
    if hasattr(offer, "expiry_date") and hasattr(offer, "offer_date"):
        if offer.expiry_date and offer.offer_date and offer.expiry_date < offer.offer_date:
            errors.append("Offer expiry date is before offer date.")

    # Rule 9: Joining date must not precede offer date
    if hasattr(offer, "joining_date") and hasattr(offer, "offer_date"):
        if offer.joining_date is not None and offer.offer_date is not None:
            if offer.joining_date < offer.offer_date:
                errors.append("Joining date is before offer date.")

    return errors


# ---------------------------------------------------------------------------
# 4. Approver Authorization Rules
# ---------------------------------------------------------------------------

AUTHORIZED_APPROVER_ROLES = frozenset({
    "hiring manager",
    "recruiter",
    "hr manager",
    "head of hr",
    "director",
    "director of engineering",
    "vp",
    "vp of engineering",
    "admin",
    "general manager",
    "talent acquisition lead",
})


def is_authorized_approver(role: Optional[str]) -> bool:
    """
    Returns True if the given employee role has authority to approve job offers.
    """
    if not role:
        return False
    norm = role.strip().lower()
    if norm in AUTHORIZED_APPROVER_ROLES:
        return True
    keywords = ("manager", "director", "vp", "head", "lead", "recruiter", "admin", "hr")
    return any(k in norm for k in keywords)


def validate_offer_approval(offer: Any, approver: Any) -> list[str]:
    """
    Validate that an employee is authorized to approve the given offer.
    """
    errors: list[str] = []
    if approver is None:
        errors.append("Approver employee does not exist.")
        return errors

    role = getattr(approver, "role", "")
    if not is_authorized_approver(role):
        errors.append(
            f"Employee '{approver.full_name}' with role '{role}' is not authorized to approve offers."
        )

    if offer.status != "pending_approval":
        errors.append(
            f"Offer must be in 'pending_approval' status to be approved, but is currently '{offer.status}'."
        )

    return errors


# ---------------------------------------------------------------------------
# 5. Scorecard Rules
# ---------------------------------------------------------------------------


def calculate_overall_score(
    technical_score: Decimal,
    communication_score: Decimal,
    problem_solving_score: Decimal,
) -> Decimal:
    """
    Calculate arithmetic mean of technical, communication, and problem-solving scores.
    Rounded to 2 decimal places.
    """
    avg = (Decimal(str(technical_score)) + Decimal(str(communication_score)) + Decimal(str(problem_solving_score))) / Decimal("3")
    return round(avg, 2)


def validate_scorecard_scores(
    technical: Decimal,
    communication: Decimal,
    problem_solving: Decimal,
    overall: Optional[Decimal] = None,
) -> list[str]:
    """
    Validate all scorecard score dimensions are strictly between 0 and 10.
    """
    errors: list[str] = []
    scores = {
        "technical_score": technical,
        "communication_score": communication,
        "problem_solving_score": problem_solving,
    }
    if overall is not None:
        scores["overall_score"] = overall

    for name, val in scores.items():
        try:
            d_val = Decimal(str(val))
            if not (Decimal("0") <= d_val <= Decimal("10")):
                errors.append(f"{name} must be between 0 and 10.")
        except Exception:
            errors.append(f"{name} must be a valid numeric value.")

    return errors


# ---------------------------------------------------------------------------
# 6. Workflow Transition State Machines
# ---------------------------------------------------------------------------

REQUISITION_TRANSITIONS = {
    "draft": {"open", "cancelled"},
    "open": {"on_hold", "closed", "cancelled"},
    "on_hold": {"open", "closed", "cancelled"},
    "closed": set(),      # Terminal
    "cancelled": set(),   # Terminal
}


def validate_requisition_transition(current_status: str, new_status: str) -> list[str]:
    """Validate requisition status transitions."""
    if current_status == new_status:
        return []
    allowed = REQUISITION_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        return [
            f"Invalid requisition status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {sorted(allowed) if allowed else 'None (terminal state)'}."
        ]
    return []


APPLICATION_STAGE_TRANSITIONS = {
    "applied": {"screening", "rejected"},
    "screening": {"interview", "rejected"},
    "interview": {"assessment", "offer", "rejected"},
    "assessment": {"offer", "rejected"},
    "offer": {"hired", "rejected"},
    "hired": set(),       # Terminal
    "rejected": set(),    # Terminal
}


def validate_application_stage_transition(current_stage: str, new_stage: str) -> list[str]:
    """Validate application stage progression."""
    if current_stage == new_stage:
        return []
    allowed = APPLICATION_STAGE_TRANSITIONS.get(current_stage, set())
    if new_stage not in allowed:
        return [
            f"Invalid application stage transition from '{current_stage}' to '{new_stage}'. "
            f"Allowed next stages: {sorted(allowed) if allowed else 'None (terminal state)'}."
        ]
    return []


INTERVIEW_STATUS_TRANSITIONS = {
    "scheduled": {"completed", "cancelled", "rescheduled"},
    "rescheduled": {"scheduled", "completed", "cancelled"},
    "completed": set(),   # Terminal
    "cancelled": set(),   # Terminal
}


def validate_interview_status_transition(current_status: str, new_status: str) -> list[str]:
    """Validate interview status transitions."""
    if current_status == new_status:
        return []
    allowed = INTERVIEW_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        return [
            f"Invalid interview status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {sorted(allowed) if allowed else 'None (terminal state)'}."
        ]
    return []


OFFER_STATUS_TRANSITIONS = {
    "draft": {"pending_approval", "cancelled"},
    "pending_approval": {"approved", "rejected", "cancelled"},
    "approved": {"released", "cancelled"},
    "released": {"accepted", "rejected", "expired"},
    "accepted": set(),    # Terminal
    "rejected": set(),    # Terminal
    "expired": set(),     # Terminal
    "cancelled": set(),   # Terminal
}


def validate_offer_status_transition(current_status: str, new_status: str) -> list[str]:
    """Validate offer status transitions."""
    if current_status == new_status:
        return []
    allowed = OFFER_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        return [
            f"Invalid offer status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {sorted(allowed) if allowed else 'None (terminal state)'}."
        ]
    return []
