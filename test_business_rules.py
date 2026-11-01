
from datetime import date
from types import SimpleNamespace

from app.business_rules import (
    validate_application,
    validate_offer,
    validate_interview_assignment,
)


def test_valid_application():
    candidate = SimpleNamespace(experience_years=1.0)
    requisition = SimpleNamespace(
        status="open",
        experience_min=0,
        experience_max=2,
    )

    assert validate_application(candidate, requisition) == []


def test_application_experience_violation():
    candidate = SimpleNamespace(experience_years=4.0)
    requisition = SimpleNamespace(
        status="open",
        experience_min=0,
        experience_max=2,
    )

    errors = validate_application(candidate, requisition)

    assert "Candidate exceeds maximum experience." in errors


def test_offer_without_approver():
    offer = SimpleNamespace(
        status="released",
        approved_by=None,
        offer_date=date(2026, 10, 30),
        expiry_date=date(2026, 11, 9),
        joining_date=date(2026, 12, 14),
    )

    errors = validate_offer(offer)

    assert "Approved or released offer has no approver." in errors



def test_valid_offer():
    offer = SimpleNamespace(
        status="released",
        approved_by=1,
        offer_date=date(2026, 10, 30),
        expiry_date=date(2026, 11, 9),
        joining_date=date(2026, 12, 14),
    )

    assert validate_offer(offer) == []


def test_valid_interview_assignment():
    interview = SimpleNamespace(status="scheduled")
    interviewer = SimpleNamespace(employee_id=3)

    assert validate_interview_assignment(interview, interviewer) == []


def test_interview_assignment_with_missing_interviewer():
    interview = SimpleNamespace(status="scheduled")
    interviewer = None

    errors = validate_interview_assignment(interview, interviewer)

    assert "Interviewer does not exist." in errors


def test_interview_assignment_with_wrong_status():
    interview = SimpleNamespace(status="completed")
    interviewer = SimpleNamespace(employee_id=3)

    errors = validate_interview_assignment(interview, interviewer)

    assert "Interview is not in scheduled status." in errors
