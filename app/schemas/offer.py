"""
app/schemas/offer.py
====================
Pydantic schemas for Job Offer lifecycle endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase

VALID_OFFER_STATUSES = frozenset({
    "draft",
    "pending_approval",
    "approved",
    "released",
    "accepted",
    "rejected",
    "expired",
    "cancelled",
})


class OfferCreate(BaseModel):
    """Payload to create a new job offer."""
    application_id: int = Field(..., description="Target application ID", json_schema_extra={"example": 1})
    offered_salary: Decimal = Field(..., ge=Decimal("0"), json_schema_extra={"example": "1200000.00"})
    offer_date: date = Field(..., description="Date offer is extended", json_schema_extra={"example": "2026-11-01"})
    expiry_date: date = Field(..., description="Offer expiration deadline", json_schema_extra={"example": "2026-11-15"})
    joining_date: Optional[date] = Field(None, description="Proposed start date", json_schema_extra={"example": "2026-12-01"})
    status: str = Field("draft", json_schema_extra={"example": "draft"})
    approved_by: Optional[int] = Field(None, description="Approving manager employee ID", json_schema_extra={"example": None})

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_OFFER_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_OFFER_STATUSES)}")
        return v

    @field_validator("expiry_date")
    @classmethod
    def expiry_after_offer(cls, v: date, info) -> date:
        offer_date = info.data.get("offer_date")
        if offer_date and v < offer_date:
            raise ValueError("expiry_date must be >= offer_date")
        return v

    @field_validator("joining_date")
    @classmethod
    def joining_after_offer(cls, v: Optional[date], info) -> Optional[date]:
        if v is not None:
            offer_date = info.data.get("offer_date")
            if offer_date and v < offer_date:
                raise ValueError("joining_date must be >= offer_date")
        return v


class OfferUpdate(BaseModel):
    """Payload to update an offer in draft status."""
    offered_salary: Optional[Decimal] = Field(None, ge=Decimal("0"))
    expiry_date: Optional[date] = None
    joining_date: Optional[date] = None


class OfferStatusUpdate(BaseModel):
    """Payload to update an offer's workflow status."""
    status: str = Field(..., description="New offer status", json_schema_extra={"example": "pending_approval"})
    approved_by: Optional[int] = Field(None, description="Employee ID performing approval if transitioning to approved", json_schema_extra={"example": 1})

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in VALID_OFFER_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_OFFER_STATUSES)}")
        return v


class OfferApprovalAction(BaseModel):
    """Payload for approving or rejecting an offer."""
    approved_by: int = Field(..., description="Employee ID of the approver", json_schema_extra={"example": 1})
    remarks: Optional[str] = Field(None, description="Decision remarks or notes", json_schema_extra={"example": "Approved as within compensation band."})


class OfferCandidateDecision(BaseModel):
    """Payload when a candidate accepts or declines an offer."""
    reason: Optional[str] = Field(None, description="Optional feedback or notes", json_schema_extra={"example": "Candidate accepted terms."})


class OfferResponse(OrmBase):
    """Job offer record representation."""
    offer_id: int
    application_id: int
    offered_salary: Decimal
    offer_date: date
    expiry_date: date
    joining_date: Optional[date]
    status: str
    approved_by: Optional[int]
    created_at: datetime


class OfferExpiryCheckResponse(BaseModel):
    """Report of expired offers check."""
    total_checked: int
    expired_count: int
    expired_offer_ids: list[int]

