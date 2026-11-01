"""
app/api/routes/employees.py
===========================
REST API endpoints for Employee management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EmployeeCreate, EmployeeResponse
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[EmployeeResponse],
    summary="List employees",
    description="Retrieve a paginated list of employees, optionally filtered by department.",
)
def list_employees(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
):
    return employee_service.get_all(db, skip=skip, limit=limit, department_id=department_id)


@router.post(
    "/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee",
    description="Create an employee profile. Department must exist and email must be unique.",
)
def create_employee(body: EmployeeCreate, db: DBSession):
    return employee_service.create(
        db,
        department_id=body.department_id,
        full_name=body.full_name,
        email=body.email,
        role=body.role,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee by ID",
    description="Fetch full details for an individual employee.",
)
def get_employee(employee_id: int, db: DBSession):
    emp = employee_service.get_by_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found.",
        )
    return emp

