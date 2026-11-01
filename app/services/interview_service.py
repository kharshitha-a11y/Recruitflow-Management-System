"""
app/services/interview_service.py
=================================
Service layer for Interview scheduling, interviewer assignments, and lifecycle.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import (
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
    validate_interview_assignment,
    validate_interview_status_transition,
)
from app.models import Application, Employee, Interview, Interviewer


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    application_id: Optional[int] = None,
    status: Optional[str] = None,
    interview_round: Optional[int] = None,
) -> list[Interview]:
    """Return a paginated list of interviews with optional filters."""
    stmt = select(Interview).offset(skip).limit(limit)
    if application_id is not None:
        stmt = stmt.where(Interview.application_id == application_id)
    if status:
        stmt = stmt.where(Interview.status == status)
    if interview_round is not None:
        stmt = stmt.where(Interview.interview_round == interview_round)
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, interview_id: int) -> Optional[Interview]:
    """Return a single interview by primary key, or None."""
    return db.get(Interview, interview_id)


def create(
    db: Session,
    application_id: int,
    interview_round: int,
    interview_type: str,
    scheduled_at: datetime,
) -> Interview:
    """
    Schedule a new interview for an application.
    Enforces that the application exists and no duplicate round exists.
    """
    if not db.get(Application, application_id):
        raise ResourceNotFoundError(f"Application ID {application_id} not found.")

    existing = db.scalar(
        select(Interview).where(
            Interview.application_id == application_id,
            Interview.interview_round == interview_round,
        )
    )
    if existing:
        raise ConflictError(
            f"Interview round {interview_round} already exists for Application {application_id}."
        )

    interview = Interview(
        application_id=application_id,
        interview_round=interview_round,
        interview_type=interview_type.strip(),
        scheduled_at=scheduled_at,
        status="scheduled",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def update_schedule(
    db: Session,
    interview_id: int,
    scheduled_at: datetime,
    interview_type: Optional[str] = None,
) -> Interview:
    """
    Update the date/time and/or type of a scheduled interview.
    """
    interview = db.get(Interview, interview_id)
    if not interview:
        raise ResourceNotFoundError(f"Interview ID {interview_id} not found.")

    if interview.status not in ("scheduled", "rescheduled"):
        raise BusinessRuleError(
            f"Cannot update schedule for interview with status '{interview.status}'."
        )

    interview.scheduled_at = scheduled_at
    if interview_type:
        interview.interview_type = interview_type.strip()

    db.commit()
    db.refresh(interview)
    return interview


def assign_interviewer(
    db: Session,
    interview_id: int,
    employee_id: int,
) -> Interviewer:
    """
    Assign an employee to an interview panel.

    Enforces business rules:
      - Interview must exist (ResourceNotFoundError)
      - Employee must exist (ResourceNotFoundError)
      - Interview must be in 'scheduled' status (BusinessRuleError)
      - Employee cannot be assigned twice to the same interview (ConflictError)
    """
    interview = db.get(Interview, interview_id)
    if not interview:
        raise ResourceNotFoundError(f"Interview ID {interview_id} not found.")

    employee = db.get(Employee, employee_id)
    if not employee:
        raise ResourceNotFoundError(f"Employee ID {employee_id} not found.")

    errors = validate_interview_assignment(interview, employee)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    existing = db.get(
        Interviewer,
        {"interview_id": interview_id, "employee_id": employee_id},
    )
    if existing:
        raise ConflictError(
            f"Employee {employee_id} is already assigned to Interview {interview_id}."
        )

    assignment = Interviewer(
        interview_id=interview_id,
        employee_id=employee_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_interviewers(db: Session, interview_id: int) -> list[Interviewer]:
    """Return all employees assigned to a given interview panel."""
    return list(
        db.scalars(
            select(Interviewer).where(Interviewer.interview_id == interview_id)
        ).all()
    )


def update_status(
    db: Session,
    interview_id: int,
    new_status: str,
    completed_at: Optional[datetime] = None,
) -> Interview:
    """
    Update an interview's status enforcing valid transitions.
    """
    interview = db.get(Interview, interview_id)
    if not interview:
        raise ResourceNotFoundError(f"Interview ID {interview_id} not found.")

    errors = validate_interview_status_transition(interview.status, new_status)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    interview.status = new_status
    if new_status == "completed":
        interview.completed_at = completed_at or datetime.now(timezone.utc)
    elif new_status != "completed":
        interview.completed_at = None

    db.commit()
    db.refresh(interview)
    return interview


def cancel(db: Session, interview_id: int) -> Interview:
    """Cancel an interview."""
    return update_status(db, interview_id, "cancelled")


def reschedule(
    db: Session,
    interview_id: int,
    new_scheduled_at: datetime,
    reason: Optional[str] = None,
) -> Interview:
    """Reschedule an interview."""
    interview = db.get(Interview, interview_id)
    if not interview:
        raise ResourceNotFoundError(f"Interview ID {interview_id} not found.")

    if interview.status in ("completed", "cancelled"):
        raise BusinessRuleError(f"Cannot reschedule an interview in '{interview.status}' status.")

    interview.scheduled_at = new_scheduled_at
    interview.status = "rescheduled"

    db.commit()
    db.refresh(interview)
    return interview


def complete(
    db: Session,
    interview_id: int,
    completed_at: Optional[datetime] = None,
) -> Interview:
    """Record completion of an interview."""
    return update_status(db, interview_id, "completed", completed_at=completed_at)
