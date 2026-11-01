"""
app/api/routes/scorecards.py
============================
REST API endpoints for Interview Scorecards and evaluation metrics.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ScorecardCreate,
    ScorecardResponse,
    ScorecardSummaryResponse,
)
from app.services import scorecard_service

router = APIRouter(prefix="/scorecards", tags=["Scorecards"])
DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=ScorecardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit scorecard",
    description=(
        "Submit an interview evaluation scorecard. Enforces that: "
        "1) The employee is an assigned interviewer for this interview. "
        "2) Scores are between 0 and 10. "
        "3) Each interviewer can only submit one scorecard per interview. "
        "If overall_score is omitted, it is automatically computed as the average."
    ),
)
def create_scorecard(body: ScorecardCreate, db: DBSession):
    return scorecard_service.create(
        db,
        interview_id=body.interview_id,
        employee_id=body.employee_id,
        technical_score=body.technical_score,
        communication_score=body.communication_score,
        problem_solving_score=body.problem_solving_score,
        overall_score=body.overall_score,
        recommendation=body.recommendation,
        feedback=body.feedback,
    )


@router.get(
    "/",
    response_model=list[ScorecardResponse],
    summary="List scorecards",
    description="Retrieve scorecards optionally filtered by interview or submitting employee.",
)
def list_scorecards(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    interview_id: Optional[int] = Query(None, description="Filter by interview ID"),
    employee_id: Optional[int] = Query(None, description="Filter by evaluator employee ID"),
):
    return scorecard_service.get_all(
        db, skip=skip, limit=limit, interview_id=interview_id, employee_id=employee_id
    )


@router.get(
    "/interview/{interview_id}",
    response_model=list[ScorecardResponse],
    summary="Get scorecards by interview",
    description="Fetch all submitted scorecards for a specific interview.",
)
def get_interview_scorecards(interview_id: int, db: DBSession):
    return scorecard_service.get_by_interview(db, interview_id)


@router.get(
    "/interview/{interview_id}/summary",
    response_model=ScorecardSummaryResponse,
    summary="Calculate overall score and evaluation summary",
    description="Aggregate scores across all panel interviewers, calculate average ratings, and tally hiring recommendations.",
)
def get_interview_scorecard_summary(interview_id: int, db: DBSession):
    return scorecard_service.get_interview_summary(db, interview_id)


@router.get(
    "/interview/{interview_id}/feedback",
    summary="Retrieve interviewer feedback",
    description="Retrieve qualitative feedback and notes submitted by panel interviewers.",
)
def get_interview_feedback(interview_id: int, db: DBSession):
    scorecards = scorecard_service.get_by_interview(db, interview_id)
    return [
        {
            "scorecard_id": sc.scorecard_id,
            "employee_id": sc.employee_id,
            "recommendation": sc.recommendation,
            "overall_score": float(sc.overall_score),
            "feedback": sc.feedback,
            "submitted_at": sc.submitted_at,
        }
        for sc in scorecards
    ]


@router.get(
    "/{scorecard_id}",
    response_model=ScorecardResponse,
    summary="Get scorecard by ID",
    description="Fetch single scorecard details.",
)
def get_scorecard(scorecard_id: int, db: DBSession):
    sc = scorecard_service.get_by_id(db, scorecard_id)
    if not sc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scorecard {scorecard_id} not found.",
        )
    return sc

