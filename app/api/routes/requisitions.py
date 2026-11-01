"""
app/api/routes/requisitions.py
==============================
REST API endpoints for Job Requisitions lifecycle.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    RequisitionCreate,
    RequisitionResponse,
    RequisitionStatusUpdate,
    RequisitionUpdate,
)
from app.services import requisition_service

router = APIRouter(prefix="/requisitions", tags=["Requisitions"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[RequisitionResponse],
    summary="List job requisitions",
    description="Retrieve a paginated list of requisitions, with optional filters by status or department.",
)
def list_requisitions(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status (draft, open, on_hold, closed, cancelled)"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
):
    return requisition_service.get_all(
        db, skip=skip, limit=limit, status=status, department_id=department_id
    )


@router.post(
    "/",
    response_model=RequisitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create job requisition",
    description="Open a new hiring requisition. Validates department and hiring manager exist.",
)
def create_requisition(body: RequisitionCreate, db: DBSession):
    return requisition_service.create(
        db,
        department_id=body.department_id,
        hiring_manager_id=body.hiring_manager_id,
        job_title=body.job_title,
        employment_type=body.employment_type,
        location=body.location,
        openings=body.openings,
        experience_min=body.experience_min,
        experience_max=body.experience_max,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        status=body.status,
    )


@router.get(
    "/{requisition_id}",
    response_model=RequisitionResponse,
    summary="View requisition details",
    description="Fetch complete specifications and status of a single job requisition.",
)
def get_requisition(requisition_id: int, db: DBSession):
    req = requisition_service.get_by_id(db, requisition_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requisition {requisition_id} not found.",
        )
    return req


@router.patch(
    "/{requisition_id}",
    response_model=RequisitionResponse,
    summary="Update requisition details",
    description="Update fields of an existing job requisition (e.g. openings, salary range, experience requirements).",
)
def update_requisition(
    requisition_id: int,
    body: RequisitionUpdate,
    db: DBSession,
):
    update_data = body.model_dump(exclude_unset=True)
    return requisition_service.update(db, requisition_id, **update_data)


@router.patch(
    "/{requisition_id}/status",
    response_model=RequisitionResponse,
    summary="Change requisition status",
    description="Transition requisition state (e.g. draft -> open -> on_hold -> closed). Invalid transitions are rejected.",
)
def update_requisition_status(
    requisition_id: int,
    body: RequisitionStatusUpdate,
    db: DBSession,
):
    return requisition_service.update_status(db, requisition_id, body.status)


@router.post(
    "/{requisition_id}/close",
    response_model=RequisitionResponse,
    summary="Close requisition",
    description="Mark an open or on-hold requisition as closed, recording the closed_at timestamp.",
)
def close_requisition(requisition_id: int, db: DBSession):
    return requisition_service.close(db, requisition_id)

