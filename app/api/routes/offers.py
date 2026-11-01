"""
app/api/routes/offers.py
========================
REST API endpoints for Job Offer lifecycle, approval workflows, and expiry tracking.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    OfferApprovalAction,
    OfferCandidateDecision,
    OfferCreate,
    OfferExpiryCheckResponse,
    OfferResponse,
    OfferStatusUpdate,
    OfferUpdate,
)
from app.services import offer_service

router = APIRouter(prefix="/offers", tags=["Offers"])
DBSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=list[OfferResponse],
    summary="List all offers",
    description="Retrieve a paginated list of job offers with optional filters by application or status.",
)
def list_offers(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    status: Optional[str] = Query(None, description="Filter by offer status"),
):
    return offer_service.get_all(
        db, skip=skip, limit=limit, application_id=application_id, status=status
    )


@router.post(
    "/",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create offer",
    description=(
        "Create a new job offer for an application. Business rules enforced: "
        "one offer per application, dates must be valid (expiry >= offer date, joining >= offer date)."
    ),
)
def create_offer(body: OfferCreate, db: DBSession):
    return offer_service.create(
        db,
        application_id=body.application_id,
        offered_salary=body.offered_salary,
        offer_date=body.offer_date,
        expiry_date=body.expiry_date,
        joining_date=body.joining_date,
        status=body.status,
        approved_by=body.approved_by,
    )


@router.get(
    "/expired",
    response_model=list[OfferResponse],
    summary="Track expired offers",
    description="Retrieve all offers whose expiration deadline has passed and were not accepted.",
)
def get_expired_offers(db: DBSession):
    return offer_service.get_expired_offers(db)


@router.post(
    "/check-expiry",
    response_model=OfferExpiryCheckResponse,
    summary="Scan and mark expired offers",
    description="Batch process that scans all pending/released offers past their expiry date and updates them to 'expired'.",
)
def check_expired_offers(db: DBSession):
    result = offer_service.check_and_mark_expired(db)
    return OfferExpiryCheckResponse(**result)


@router.get(
    "/{offer_id}",
    response_model=OfferResponse,
    summary="Get offer by ID",
    description="Fetch single offer record.",
)
def get_offer(offer_id: int, db: DBSession):
    offer = offer_service.get_by_id(db, offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} not found.",
        )
    return offer


@router.patch(
    "/{offer_id}",
    response_model=OfferResponse,
    summary="Update offer details",
    description="Update salary or dates on a draft/pending offer before approval.",
)
def update_offer(
    offer_id: int,
    body: OfferUpdate,
    db: DBSession,
):
    update_data = body.model_dump(exclude_unset=True)
    return offer_service.update(db, offer_id, **update_data)


@router.patch(
    "/{offer_id}/status",
    response_model=OfferResponse,
    summary="Update offer status",
    description="Update offer workflow status. Validates transition rules and approver constraints.",
)
def update_offer_status(
    offer_id: int,
    body: OfferStatusUpdate,
    db: DBSession,
):
    return offer_service.update_status(
        db,
        offer_id=offer_id,
        new_status=body.status,
        approved_by=body.approved_by,
    )


@router.post(
    "/{offer_id}/submit-for-approval",
    response_model=OfferResponse,
    summary="Submit offer for approval",
    description="Action endpoint to submit a draft offer for management review (draft -> pending_approval).",
)
def submit_for_approval(offer_id: int, db: DBSession):
    return offer_service.submit_for_approval(db, offer_id)


@router.post(
    "/{offer_id}/approve",
    response_model=OfferResponse,
    summary="Approve offer",
    description="Action endpoint to approve an offer. Enforces that only authorized employees (managers/directors/HR) can approve.",
)
def approve_offer(
    offer_id: int,
    body: OfferApprovalAction,
    db: DBSession,
):
    return offer_service.approve(
        db,
        offer_id=offer_id,
        approver_id=body.approved_by,
        remarks=body.remarks,
    )


@router.post(
    "/{offer_id}/reject",
    response_model=OfferResponse,
    summary="Reject offer",
    description="Action endpoint for management review to reject a pending offer.",
)
def reject_offer(
    offer_id: int,
    body: OfferApprovalAction,
    db: DBSession,
):
    return offer_service.reject(
        db,
        offer_id=offer_id,
        approver_id=body.approved_by,
        remarks=body.remarks,
    )


@router.post(
    "/{offer_id}/release",
    response_model=OfferResponse,
    summary="Release offer to candidate",
    description="Action endpoint to release an approved offer to the candidate. Enforces that the offer must be approved and have an approver.",
)
def release_offer(offer_id: int, db: DBSession):
    return offer_service.release(db, offer_id)


@router.post(
    "/{offer_id}/accept",
    response_model=OfferResponse,
    summary="Candidate accepts offer",
    description="Action endpoint for candidate acceptance. Advances the associated application to 'hired' state.",
)
def accept_offer(
    offer_id: int,
    body: Optional[OfferCandidateDecision] = None,
    db: DBSession = None,
):
    return offer_service.accept(db, offer_id)


@router.post(
    "/{offer_id}/candidate-reject",
    response_model=OfferResponse,
    summary="Candidate declines offer",
    description="Action endpoint when a candidate declines a released offer. Advances application to 'rejected'.",
)
def candidate_reject_offer(
    offer_id: int,
    body: Optional[OfferCandidateDecision] = None,
    db: DBSession = None,
):
    reason = body.reason if body else None
    return offer_service.candidate_reject(db, offer_id, reason=reason)

