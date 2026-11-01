"""
app/services/application_service.py
==================================
Service layer for Application management and stage transitions.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import (
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
    validate_application,
    validate_application_stage_transition,
)
from app.models import (
    Application,
    ApplicationStageHistory,
    Candidate,
    Employee,
    Requisition,
)


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    candidate_id: Optional[int] = None,
    requisition_id: Optional[int] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
) -> list[Application]:
    """
    Return a paginated list of applications filtered by job, candidate, status, and stage.
    """
    stmt = select(Application).offset(skip).limit(limit)

    if candidate_id is not None:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    if requisition_id is not None:
        stmt = stmt.where(Application.requisition_id == requisition_id)
    if status:
        stmt = stmt.where(Application.status == status)
    if stage:
        stmt = stmt.where(Application.current_stage == stage)

    return list(db.scalars(stmt).all())


def get_by_id(db: Session, application_id: int) -> Optional[Application]:
    """Return a single application by primary key, or None."""
    return db.get(Application, application_id)


def get_stage_history(
    db: Session, application_id: int
) -> list[ApplicationStageHistory]:
    """Return the full stage audit trail for a given application."""
    return list(
        db.scalars(
            select(ApplicationStageHistory)
            .where(ApplicationStageHistory.application_id == application_id)
            .order_by(ApplicationStageHistory.changed_at)
        ).all()
    )


def create(
    db: Session,
    candidate_id: int,
    requisition_id: int,
    source: Optional[str] = None,
    changed_by: Optional[int] = None,
) -> Application:
    """
    Submit a new job application.

    Enforces business rules:
      - Candidate must exist (ResourceNotFoundError)
      - Requisition must exist (ResourceNotFoundError)
      - Requisition must be open (BusinessRuleError)
      - Candidate experience must be within requisition range (BusinessRuleError)
      - Candidate cannot apply to the same requisition twice (ConflictError)
    """
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise ResourceNotFoundError(f"Candidate ID {candidate_id} not found.")

    requisition = db.get(Requisition, requisition_id)
    if not requisition:
        raise ResourceNotFoundError(f"Requisition ID {requisition_id} not found.")

    # Business rule validation: open status + experience range
    errors = validate_application(candidate, requisition)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    # Duplicate check
    existing = db.scalar(
        select(Application).where(
            Application.candidate_id == candidate_id,
            Application.requisition_id == requisition_id,
        )
    )
    if existing:
        raise ConflictError(
            f"Candidate {candidate_id} has already applied to Requisition {requisition_id}."
        )

    application = Application(
        candidate_id=candidate_id,
        requisition_id=requisition_id,
        current_stage="applied",
        status="active",
        source=source,
    )
    db.add(application)
    db.flush()

    # Initial stage history record
    history = ApplicationStageHistory(
        application_id=application.application_id,
        previous_stage=None,
        new_stage="applied",
        changed_by=changed_by,
        remarks="Application received.",
    )
    db.add(history)
    db.commit()
    db.refresh(application)
    return application


def advance_stage(
    db: Session,
    application_id: int,
    new_stage: str,
    changed_by: Optional[int] = None,
    remarks: Optional[str] = None,
) -> Application:
    """
    Advance an application to a new recruitment stage.

    Validates:
      - Application exists (ResourceNotFoundError)
      - Employee changed_by exists if provided (ResourceNotFoundError)
      - Stage transition follows valid pipeline progression (BusinessRuleError)
    """
    application = db.get(Application, application_id)
    if not application:
        raise ResourceNotFoundError(f"Application ID {application_id} not found.")

    if changed_by is not None and not db.get(Employee, changed_by):
        raise ResourceNotFoundError(f"Employee ID {changed_by} not found.")

    previous_stage = application.current_stage

    errors = validate_application_stage_transition(previous_stage, new_stage)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    history = ApplicationStageHistory(
        application_id=application_id,
        previous_stage=previous_stage,
        new_stage=new_stage,
        changed_by=changed_by,
        remarks=remarks,
    )
    db.add(history)

    application.current_stage = new_stage

    # Update top-level status for terminal stages
    if new_stage == "hired":
        application.status = "hired"
    elif new_stage == "rejected":
        application.status = "rejected"

    db.commit()
    db.refresh(application)
    return application
