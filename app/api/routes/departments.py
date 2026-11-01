"""
app/api/routes/departments.py
=============================
REST API endpoints for Department management.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DepartmentCreate, DepartmentResponse
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["Departments"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[DepartmentResponse],
    summary="List departments",
    description="Retrieve a paginated list of all departments in the organization.",
)
def list_departments(
    db: DBSession,
    skip: int = Query(0, ge=0, description="Offset records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Page limit"),
):
    return department_service.get_all(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create department",
    description="Register a new organizational department. Department name must be unique.",
)
def create_department(body: DepartmentCreate, db: DBSession):
    return department_service.create(db, department_name=body.department_name)


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Get department by ID",
    description="Fetch full details for a single department.",
)
def get_department(department_id: int, db: DBSession):
    dept = department_service.get_by_id(db, department_id)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {department_id} not found.",
        )
    return dept

