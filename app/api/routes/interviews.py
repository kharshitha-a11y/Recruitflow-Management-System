"""
app/api/routes/interviews.py
============================
REST API endpoints for Interview scheduling, panels, and status workflows.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    InterviewCompletion,
    InterviewCreate,
    InterviewerAssignCreate,
    InterviewerResponse,
    InterviewReschedule,
    InterviewResponse,
    InterviewScheduleUpdate,
    InterviewStatusUpdate,
)
from app.services import interview_service

router = APIRouter(prefix="/interviews", tags=["Interviews"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[InterviewResponse],
    summary="List interviews",
    description="Retrieve paginated list of interviews, optionally filtered by application, status, or round.",
)
def list_interviews(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    status: Optional[str] = Query(None, description="Filter by status (scheduled, completed, cancelled, rescheduled)"),
    interview_round: Optional[int] = Query(None, description="Filter by round number"),
):
    return interview_service.get_all(
        db,
        skip=skip,
        limit=limit,
        application_id=application_id,
        status=status,
        interview_round=interview_round,
    )


@router.post(
    "/",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule interview",
    description="Schedule a new interview round for an application. Each round number must be unique per application.",
)
def create_interview(body: InterviewCreate, db: DBSession):
    return interview_service.create(
        db,
        application_id=body.application_id,
        interview_round=body.interview_round,
        interview_type=body.interview_type,
        scheduled_at=body.scheduled_at,
    )


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Get interview details",
    description="Fetch single interview record.",
)
def get_interview(interview_id: int, db: DBSession):
    interview = interview_service.get_by_id(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found.",
        )
    return interview


@router.patch(
    "/{interview_id}/schedule",
    response_model=InterviewResponse,
    summary="Update interview schedule",
    description="Update scheduled time or interview type for an upcoming interview.",
)
def update_interview_schedule(
    interview_id: int,
    body: InterviewScheduleUpdate,
    db: DBSession,
):
    return interview_service.update_schedule(
        db,
        interview_id=interview_id,
        scheduled_at=body.scheduled_at,
        interview_type=body.interview_type,
    )


@router.post(
    "/{interview_id}/assign-interviewer",
    response_model=InterviewerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign interviewer",
    description="Assign an employee to the interview panel. Interview must be in 'scheduled' status and employee cannot be assigned twice.",
)
def assign_interviewer(
    interview_id: int,
    body: InterviewerAssignCreate,
    db: DBSession,
):
    return interview_service.assign_interviewer(
        db,
        interview_id=interview_id,
        employee_id=body.employee_id,
    )


@router.get(
    "/{interview_id}/interviewers",
    response_model=list[InterviewerResponse],
    summary="List interviewers",
    description="Return all panel members assigned to an interview.",
)
def list_interviewers(interview_id: int, db: DBSession):
    interview = interview_service.get_by_id(db, interview_id)
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found.",
        )
    return interview_service.get_interviewers(db, interview_id)


@router.patch(
    "/{interview_id}/status",
    response_model=InterviewResponse,
    summary="Update interview status",
    description="Transition interview status (scheduled -> completed / cancelled / rescheduled).",
)
def update_interview_status(
    interview_id: int,
    body: InterviewStatusUpdate,
    db: DBSession,
):
    return interview_service.update_status(
        db,
        interview_id=interview_id,
        new_status=body.status,
        completed_at=body.completed_at,
    )


@router.post(
    "/{interview_id}/cancel",
    response_model=InterviewResponse,
    summary="Cancel interview",
    description="Action endpoint to cancel an interview.",
)
def cancel_interview(interview_id: int, db: DBSession):
    return interview_service.cancel(db, interview_id)


@router.post(
    "/{interview_id}/reschedule",
    response_model=InterviewResponse,
    summary="Reschedule interview",
    description="Action endpoint to reschedule an interview with a new timestamp.",
)
def reschedule_interview(
    interview_id: int,
    body: InterviewReschedule,
    db: DBSession,
):
    return interview_service.reschedule(
        db,
        interview_id=interview_id,
        new_scheduled_at=body.new_scheduled_at,
        reason=body.reason,
    )


@router.post(
    "/{interview_id}/complete",
    response_model=InterviewResponse,
    summary="Record interview completion",
    description="Action endpoint to record interview completion and set completed_at timestamp.",
)
def complete_interview(
    interview_id: int,
    body: Optional[InterviewCompletion] = None,
    db: DBSession = None,
):
    completed_at = body.completed_at if body else None
    return interview_service.complete(db, interview_id, completed_at=completed_at)

