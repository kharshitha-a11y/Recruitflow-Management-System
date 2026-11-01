"""
app/services/department_service.py
==================================
Service layer for Department entity operations.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import ConflictError, ResourceNotFoundError
from app.models import Department


def get_all(db: Session, skip: int = 0, limit: int = 100) -> list[Department]:
    """Return a paginated list of all departments."""
    stmt = select(Department).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, department_id: int) -> Optional[Department]:
    """Return a single department by primary key, or None."""
    return db.get(Department, department_id)


def create(db: Session, department_name: str) -> Department:
    """
    Create a new department.
    Raises ConflictError (HTTP 409) if the department name already exists.
    """
    clean_name = department_name.strip()
    existing = db.scalar(
        select(Department).where(Department.department_name == clean_name)
    )
    if existing:
        raise ConflictError(f"Department '{clean_name}' already exists.")

    dept = Department(department_name=clean_name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept
