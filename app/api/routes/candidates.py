"""
app/api/routes/candidates.py
============================
REST API endpoints for Candidate registration, search, and profiles.
"""

from decimal import Decimal
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CandidateCreate, CandidateResponse, CandidateUpdate
from app.services import candidate_service

router = APIRouter(prefix="/candidates", tags=["Candidates"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[CandidateResponse],
    summary="List, search, and filter candidates",
    description="Retrieve candidates matching criteria: search keyword (name/email/location), min/max experience, qualification.",
)
def list_candidates(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    q: Optional[str] = Query(None, description="Free text search on full name, email, or location"),
    email: Optional[str] = Query(None, description="Exact match on candidate email"),
    min_experience: Optional[Decimal] = Query(None, ge=0, description="Minimum years of experience"),
    max_experience: Optional[Decimal] = Query(None, ge=0, description="Maximum years of experience"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    highest_qualification: Optional[str] = Query(None, description="Filter by qualification (partial match)"),
):
    return candidate_service.get_all(
        db,
        skip=skip,
        limit=limit,
        q=q,
        email=email,
        min_experience=min_experience,
        max_experience=max_experience,
        location=location,
        highest_qualification=highest_qualification,
    )


@router.post(
    "/",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register candidate",
    description="Register a new job candidate profile. Email address must be unique.",
)
def create_candidate(body: CandidateCreate, db: DBSession):
    return candidate_service.create(
        db,
        full_name=body.full_name,
        email=body.email,
        experience_years=body.experience_years,
        phone=body.phone,
        highest_qualification=body.highest_qualification,
        current_location=body.current_location,
    )


@router.get(
    "/search",
    response_model=list[CandidateResponse],
    summary="Search candidates",
    description="Dedicated search endpoint to filter candidates by keywords and qualifications.",
)
def search_candidates(
    db: DBSession,
    q: Optional[str] = Query(None, description="Keywords to match across name, email, and location"),
    min_experience: Optional[Decimal] = Query(None, ge=0),
    max_experience: Optional[Decimal] = Query(None, ge=0),
    location: Optional[str] = None,
    qualification: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    return candidate_service.get_all(
        db,
        skip=skip,
        limit=limit,
        q=q,
        min_experience=min_experience,
        max_experience=max_experience,
        location=location,
        highest_qualification=qualification,
    )


@router.get(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="View candidate profile",
    description="Fetch full details for an individual candidate.",
)
def get_candidate(candidate_id: int, db: DBSession):
    candidate = candidate_service.get_by_id(db, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found.",
        )
    return candidate


@router.patch(
    "/{candidate_id}",
    response_model=CandidateResponse,
    summary="Update candidate details",
    description="Partially update candidate contact info, experience, or qualifications.",
)
def update_candidate(
    candidate_id: int,
    body: CandidateUpdate,
    db: DBSession,
):
    update_data = body.model_dump(exclude_unset=True)
    return candidate_service.update(db, candidate_id, **update_data)

