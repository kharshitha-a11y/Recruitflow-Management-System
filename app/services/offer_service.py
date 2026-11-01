"""
app/services/offer_service.py
=============================
Service layer for Offer management, approval workflows, and expiry tracking.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules import (
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
    validate_offer,
    validate_offer_approval,
    validate_offer_status_transition,
)
from app.models import Application, Employee, Offer


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    application_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[Offer]:
    """Return a paginated list of all job offers with optional filters."""
    stmt = select(Offer).offset(skip).limit(limit)
    if application_id is not None:
        stmt = stmt.where(Offer.application_id == application_id)
    if status:
        stmt = stmt.where(Offer.status == status)
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, offer_id: int) -> Optional[Offer]:
    """Return a single offer by primary key, or None."""
    return db.get(Offer, offer_id)


def create(
    db: Session,
    application_id: int,
    offered_salary: Decimal,
    offer_date: date,
    expiry_date: date,
    joining_date: Optional[date] = None,
    status: str = "draft",
    approved_by: Optional[int] = None,
) -> Offer:
    """
    Create a new job offer for an application.

    Enforces business rules:
      - Application must exist (ResourceNotFoundError)
      - Application can have at most one offer (ConflictError)
      - Approver must exist if provided (ResourceNotFoundError)
      - Date constraints & status rules via validate_offer (BusinessRuleError)
    """
    if not db.get(Application, application_id):
        raise ResourceNotFoundError(f"Application ID {application_id} not found.")

    existing = db.scalar(
        select(Offer).where(Offer.application_id == application_id)
    )
    if existing:
        raise ConflictError(
            f"An offer already exists for Application {application_id}."
        )

    if approved_by is not None:
        approver = db.get(Employee, approved_by)
        if not approver:
            raise ResourceNotFoundError(f"Approver Employee ID {approved_by} not found.")

    temp = SimpleNamespace(
        status=status,
        approved_by=approved_by,
        offer_date=offer_date,
        expiry_date=expiry_date,
        joining_date=joining_date,
    )
    errors = validate_offer(temp)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    offer = Offer(
        application_id=application_id,
        offered_salary=offered_salary,
        offer_date=offer_date,
        expiry_date=expiry_date,
        joining_date=joining_date,
        status=status,
        approved_by=approved_by,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def update(
    db: Session,
    offer_id: int,
    **kwargs,
) -> Offer:
    """Update details of a draft offer."""
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    if offer.status not in ("draft", "pending_approval"):
        raise BusinessRuleError(f"Cannot edit offer details in status '{offer.status}'.")

    for field in ("offered_salary", "expiry_date", "joining_date"):
        if field in kwargs and kwargs[field] is not None:
            setattr(offer, field, kwargs[field])

    # Re-validate
    errors = validate_offer(offer)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    db.commit()
    db.refresh(offer)
    return offer


def update_status(
    db: Session,
    offer_id: int,
    new_status: str,
    approved_by: Optional[int] = None,
) -> Offer:
    """
    Update offer status enforcing state transition rules.
    """
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    errors = validate_offer_status_transition(offer.status, new_status)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    if approved_by is not None:
        approver = db.get(Employee, approved_by)
        if not approver:
            raise ResourceNotFoundError(f"Approver Employee ID {approved_by} not found.")
        offer.approved_by = approved_by

    offer.status = new_status

    temp = SimpleNamespace(
        status=offer.status,
        approved_by=offer.approved_by,
        offer_date=offer.offer_date,
        expiry_date=offer.expiry_date,
        joining_date=offer.joining_date,
    )
    errors = validate_offer(temp)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    db.commit()
    db.refresh(offer)
    return offer


def submit_for_approval(db: Session, offer_id: int) -> Offer:
    """Submit a draft offer for management approval."""
    return update_status(db, offer_id, "pending_approval")


def approve(
    db: Session,
    offer_id: int,
    approver_id: int,
    remarks: Optional[str] = None,
) -> Offer:
    """
    Approve an offer in pending_approval status.
    Enforces business rule: Only authorized employees can approve offers.
    """
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    approver = db.get(Employee, approver_id)
    if not approver:
        raise ResourceNotFoundError(f"Approver Employee ID {approver_id} not found.")

    errors = validate_offer_approval(offer, approver)
    if errors:
        raise BusinessRuleError("; ".join(errors))

    return update_status(db, offer_id, "approved", approved_by=approver_id)


def reject(
    db: Session,
    offer_id: int,
    approver_id: int,
    remarks: Optional[str] = None,
) -> Offer:
    """Reject an offer during review."""
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    approver = db.get(Employee, approver_id)
    if not approver:
        raise ResourceNotFoundError(f"Approver Employee ID {approver_id} not found.")

    return update_status(db, offer_id, "rejected")


def release(db: Session, offer_id: int) -> Offer:
    """
    Release an approved offer to the candidate.
    Enforces rule: Released offers must have an approver.
    """
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    if offer.status != "approved":
        raise BusinessRuleError(
            f"Offer must be in 'approved' status to be released, currently '{offer.status}'."
        )

    if offer.approved_by is None:
        raise BusinessRuleError("Released offer must have an approver.")

    return update_status(db, offer_id, "released")


def accept(db: Session, offer_id: int) -> Offer:
    """
    Candidate accepts the offer.
    Advances the associated application stage to 'hired' and status to 'hired'.
    """
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    if offer.status != "released":
        raise BusinessRuleError(f"Cannot accept offer in '{offer.status}' status. Must be 'released'.")

    updated_offer = update_status(db, offer_id, "accepted")

    # Advance application to hired
    application = db.get(Application, offer.application_id)
    if application:
        application.current_stage = "hired"
        application.status = "hired"
        db.commit()

    return updated_offer


def candidate_reject(db: Session, offer_id: int, reason: Optional[str] = None) -> Offer:
    """Candidate declines the released offer."""
    offer = db.get(Offer, offer_id)
    if not offer:
        raise ResourceNotFoundError(f"Offer ID {offer_id} not found.")

    if offer.status != "released":
        raise BusinessRuleError(f"Cannot decline offer in '{offer.status}' status. Must be 'released'.")

    updated_offer = update_status(db, offer_id, "rejected")

    # Mark application as rejected
    application = db.get(Application, offer.application_id)
    if application:
        application.current_stage = "rejected"
        application.status = "rejected"
        db.commit()

    return updated_offer


def get_expired_offers(db: Session) -> list[Offer]:
    """Retrieve all active offers that have passed their expiration deadline."""
    today = date.today()
    stmt = (
        select(Offer)
        .where(
            Offer.expiry_date < today,
            Offer.status.in_(["draft", "pending_approval", "approved", "released"]),
        )
    )
    return list(db.scalars(stmt).all())


def check_and_mark_expired(db: Session) -> dict:
    """
    Scan database for past-due offers and transition them to 'expired' status.
    Returns audit summary.
    """
    expired_offers = get_expired_offers(db)
    expired_ids: list[int] = []

    for offer in expired_offers:
        offer.status = "expired"
        expired_ids.append(offer.offer_id)

    db.commit()
    return {
        "total_checked": len(expired_offers),
        "expired_count": len(expired_ids),
        "expired_offer_ids": expired_ids,
    }
