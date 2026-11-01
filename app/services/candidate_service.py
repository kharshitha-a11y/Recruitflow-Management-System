"""
app/services/candidate_service.py
=================================
Service layer for Candidate profile management and multi-criteria search.
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.business_rules import ConflictError, ResourceNotFoundError
from app.models import Candidate


def get_all(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = None,
    email: Optional[str] = None,
    min_experience: Optional[Decimal] = None,
    max_experience: Optional[Decimal] = None,
    location: Optional[str] = None,
    highest_qualification: Optional[str] = None,
) -> list[Candidate]:
    """
    Return candidates matching optional query criteria with pagination.
    Supports full search & filtering by keywords, experience, location, and qualification.
    """
    stmt = select(Candidate).offset(skip).limit(limit)

    if q:
        search_pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Candidate.full_name.ilike(search_pattern),
                Candidate.email.ilike(search_pattern),
                Candidate.current_location.ilike(search_pattern),
            )
        )

    if email:
        stmt = stmt.where(Candidate.email == email.strip().lower())

    if min_experience is not None:
        stmt = stmt.where(Candidate.experience_years >= min_experience)

    if max_experience is not None:
        stmt = stmt.where(Candidate.experience_years <= max_experience)

    if location:
        stmt = stmt.where(Candidate.current_location.ilike(f"%{location.strip()}%"))

    if highest_qualification:
        stmt = stmt.where(
            Candidate.highest_qualification.ilike(f"%{highest_qualification.strip()}%")
        )

    return list(db.scalars(stmt).all())


def get_by_id(db: Session, candidate_id: int) -> Optional[Candidate]:
    """Return a single candidate by primary key, or None."""
    return db.get(Candidate, candidate_id)


def get_by_email(db: Session, email: str) -> Optional[Candidate]:
    """Return a candidate matching the given email, or None."""
    return db.scalar(
        select(Candidate).where(Candidate.email == email.strip().lower())
    )


def create(
    db: Session,
    full_name: str,
    email: str,
    experience_years: Decimal,
    phone: Optional[str] = None,
    highest_qualification: Optional[str] = None,
    current_location: Optional[str] = None,
) -> Candidate:
    """
    Register a new candidate in the system.
    Raises ConflictError (HTTP 409) if the email is already in use.
    """
    clean_email = email.strip().lower()
    if get_by_email(db, clean_email):
        raise ConflictError(f"Candidate with email '{clean_email}' already exists.")

    candidate = Candidate(
        full_name=full_name.strip(),
        email=clean_email,
        phone=phone.strip() if phone else None,
        experience_years=experience_years,
        highest_qualification=highest_qualification.strip() if highest_qualification else None,
        current_location=current_location.strip() if current_location else None,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def update(
    db: Session,
    candidate_id: int,
    **kwargs,
) -> Candidate:
    """
    Update candidate profile details.
    Raises ResourceNotFoundError if candidate is not found.
    """
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise ResourceNotFoundError(f"Candidate ID {candidate_id} not found.")

    for field in (
        "full_name",
        "phone",
        "experience_years",
        "highest_qualification",
        "current_location",
    ):
        if field in kwargs and kwargs[field] is not None:
            setattr(candidate, field, kwargs[field])

    db.commit()
    db.refresh(candidate)
    return candidate
