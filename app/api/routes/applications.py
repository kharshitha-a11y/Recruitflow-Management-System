"""
app/api/routes/applications.py
==============================
REST API endpoints for Applications lifecycle and recruitment stage progression.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStageAdvance,
    StageHistoryResponse,
)
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["Applications"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[ApplicationResponse],
    summary="List and filter applications",
    description="Retrieve applications filtered by requisition (job), candidate, status, or recruitment stage.",
)
def list_applications(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    candidate_id: Optional[int] = Query(None, description="Filter by candidate ID"),
    requisition_id: Optional[int] = Query(None, description="Filter by job requisition ID"),
    job_id: Optional[int] = Query(None, description="Alias for requisition_id"),
    status: Optional[str] = Query(None, description="Filter by status (active, hired, rejected)"),
    stage: Optional[str] = Query(None, description="Filter by stage (applied, screening, interview, assessment, offer, hired, rejected)"),
):
    target_requisition = requisition_id if requisition_id is not None else job_id
    return application_service.get_all(
        db,
        skip=skip,
        limit=limit,
        candidate_id=candidate_id,
        requisition_id=target_requisition,
        status=status,
        stage=stage,
    )


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create application",
    description="Submit an application. Enforces that requisition is open, candidate meets experience criteria, and no duplicate application exists.",
)
def create_application(body: ApplicationCreate, db: DBSession):
    return application_service.create(
        db,
        candidate_id=body.candidate_id,
        requisition_id=body.requisition_id,
        source=body.source,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="View application details",
    description="Fetch single application record.",
)
def get_application(application_id: int, db: DBSession):
    app = application_service.get_by_id(db, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found.",
        )
    return app


@router.post(
    "/{application_id}/advance",
    response_model=ApplicationResponse,
    summary="Change application stage",
    description="Advance application stage along the recruitment pipeline. Audit record is appended to stage history.",
)
def advance_application_stage(
    application_id: int,
    body: ApplicationStageAdvance,
    db: DBSession,
):
    return application_service.advance_stage(
        db,
        application_id=application_id,
        new_stage=body.new_stage,
        changed_by=body.changed_by,
        remarks=body.remarks,
    )


@router.patch(
    "/{application_id}/stage",
    response_model=ApplicationResponse,
    summary="Change application stage (PATCH)",
    description="Alternative PATCH endpoint to update application stage.",
)
def patch_application_stage(
    application_id: int,
    body: ApplicationStageAdvance,
    db: DBSession,
):
    return advance_application_stage(application_id=application_id, body=body, db=db)


@router.get(
    "/{application_id}/history",
    response_model=list[StageHistoryResponse],
    summary="Track application history",
    description="Retrieve complete audit trail of stage transitions for an application in chronological order.",
)
def get_application_history(application_id: int, db: DBSession):
    app = application_service.get_by_id(db, application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {application_id} not found.",
        )
    return application_service.get_stage_history(db, application_id)

