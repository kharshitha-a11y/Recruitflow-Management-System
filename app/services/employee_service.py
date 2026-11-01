"""
app/services/employee_service.py
================================
Service layer for Employee entity operations.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import ConflictError, ResourceNotFoundError
from app.models import Department, Employee


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[int] = None,
) -> list[Employee]:
    """Return a paginated list of employees, optionally filtered by department."""
    stmt = select(Employee).offset(skip).limit(limit)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, employee_id: int) -> Optional[Employee]:
    """Return a single employee by primary key, or None."""
    return db.get(Employee, employee_id)


def get_by_email(db: Session, email: str) -> Optional[Employee]:
    """Return an employee by email, or None."""
    return db.scalar(select(Employee).where(Employee.email == email))


def create(
    db: Session,
    department_id: int,
    full_name: str,
    email: str,
    role: str,
) -> Employee:
    """
    Register a new employee.
    Validates:
      - Department exists (ResourceNotFoundError)
      - Email is unique (ConflictError)
    """
    if not db.get(Department, department_id):
        raise ResourceNotFoundError(f"Department ID {department_id} not found.")

    if get_by_email(db, email):
        raise ConflictError(f"Employee with email '{email}' already exists.")

    employee = Employee(
        department_id=department_id,
        full_name=full_name.strip(),
        email=email.strip().lower(),
        role=role.strip(),
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
