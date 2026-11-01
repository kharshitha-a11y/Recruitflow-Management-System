"""
app/schemas/candidate.py
========================
Pydantic schemas for Candidate endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase


class CandidateCreate(BaseModel):
    """Payload to register a new candidate."""
    full_name: str = Field(..., max_length=150, json_schema_extra={"example": "Ananya Reddy"})
    email: str = Field(..., max_length=150, json_schema_extra={"example": "ananya.reddy@example.com"})
    phone: Optional[str] = Field(None, max_length=20, json_schema_extra={"example": "+91-9876543210"})
    experience_years: Decimal = Field(..., ge=Decimal("0"), json_schema_extra={"example": "3.5"})
    highest_qualification: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "B.Tech in Computer Science"})
    current_location: Optional[str] = Field(None, max_length=100, json_schema_extra={"example": "Bangalore"})

    @field_validator("experience_years")
    @classmethod
    def experience_must_be_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("experience_years must be >= 0")
        return v


class CandidateUpdate(BaseModel):
    """Payload to update existing candidate profile details."""
    full_name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    experience_years: Optional[Decimal] = Field(None, ge=Decimal("0"))
    highest_qualification: Optional[str] = Field(None, max_length=100)
    current_location: Optional[str] = Field(None, max_length=100)


class CandidateResponse(OrmBase):
    """Candidate profile representation."""
    candidate_id: int
    full_name: str
    email: str
    phone: Optional[str]
    experience_years: Decimal
    highest_qualification: Optional[str]
    current_location: Optional[str]
    created_at: datetime

