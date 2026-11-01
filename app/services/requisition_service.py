"""
app/services/requisition_service.py
==================================
Service layer for Job Requisition operations and workflow lifecycle.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import (
    BusinessRuleError,
    ResourceNotFoundError,
    validate_requisition_transition,
)
from app.models import Department, Employee, Requisition


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
) -> list[Requisition]:
    """Return a paginated list of job requisitions with optional filters."""
    stmt = select(Requisition).offset(skip).limit(limit)
    if status:
        stmt = stmt.where(Requisition.status == status)
    if department_id is not None:
        stmt = stmt.where(Requisition.department_id == department_id)
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, requisition_id: int) -> Optional[Requisition]:
    """Return a single requisition by primary key, or None."""
    return db.get(Requisition, requisition_id)


def create(
    db: Session,
    department_id: int,
    hiring_manager_id: int,
    job_title: str,
    employment_type: str,
    location: str,
    openings: int,
    experience_min: int,
    experience_max: int,
    salary_min: Decimal,
    salary_max: Decimal,
    status: str = "draft",
) -> Requisition:
    """
    Create a new job requisition.
    Validates department and hiring manager exist.
    """
    if not db.get(Department, department_id):
        raise ResourceNotFoundError(f"Department ID {department_id} not found.")

    if not db.get(Employee, hiring_manager_id):
        raise ResourceNotFoundError(f"Hiring manager Employee ID {hiring_manager_id} not found.")

    req = Requisition(
        department_id=department_id,
        hiring_manager_id=hiring_manager_id,
        job_title=job_title.strip(),
        employment_type=employment_type.strip(),
        location=location.strip(),
        openings=openings,
        experience_min=experience_min,
        experience_max=experience_max,
        salary_min=salary_min,
        salary_max=salary_max,
        status=status,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def update(
    db: Session,
    requisition_id: int,
    **kwargs: Any,
) -> Requisition:
    """
    Update details of an existing job requisition.
    """
    req = db.get(Requisition, requisition_id)
    if not req:
        raise ResourceNotFoundError(f"Requisition ID {requisition_id} not found.")

    # Validate foreign keys if being updated
    if "department_id" in kwargs and kwargs["department_id"] is not None:
        if not db.get(Department, kwargs["department_id"]):
            raise ResourceNotFoundError(f"Department ID {kwargs['department_id']} not found.")
        req.department_id = kwargs["department_id"]

    if "hiring_manager_id" in kwargs and kwargs["hiring_manager_id"] is not None:
        if not db.get(Employee, kwargs["hiring_manager_id"]):
            raise ResourceNotFoundError(f"Hiring manager Employee ID {kwargs['hiring_manager_id']} not found.")
        req.hiring_manager_id = kwargs["hiring_manager_id"]

    for field in (
        "job_title",
        "employment_type",
        "location",
        "openings",
        "experience_min",
        "experience_max",
        "salary_min",
        "salary_max",
    ):
        if field in kwargs and kwargs[field] is not None:
            setattr(req, field, kwargs[field])

    # Validate ranges
    if req.experience_max < req.experience_min:
        raise BusinessRuleError("experience_max must be >= experience_min.")
    if req.salary_max < req.salary_min:
        raise BusinessRuleError("salary_max must be >= salary_min.")

    db.commit()
    db.refresh(req)
    return req


def update_status(
    db: Session,
    requisition_id: int,
    new_status: str,
) -> Requisition:
    """
    Update requisition status enforcing state transitions.
    Transitions: draft -> open -> on_hold -> closed/cancelled
    """
    req = db.get(Requisition, requisition_id)
    if not req:
        raise ResourceNotFoundError(f"Requisition ID {requisition_id} not found.")

    errors = validate_requisition_transition(req.status, new_status)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    req.status = new_status
    if new_status in ("closed", "cancelled") and req.closed_at is None:
        req.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(req)
    return req


def close(db: Session, requisition_id: int) -> Requisition:
    """Explicit action to close an active requisition."""
    return update_status(db, requisition_id, "closed")
