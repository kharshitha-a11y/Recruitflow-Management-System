"""
app/schemas/requisition.py
==========================
Pydantic schemas for Job Requisition endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase

VALID_REQUISITION_STATUSES = frozenset(
    {"draft", "open", "on_hold", "closed", "cancelled"}
)


class RequisitionCreate(BaseModel):
    """Payload to create a new job requisition."""
    department_id: int = Field(..., description="Target department ID", json_schema_extra={"example": 1})
    hiring_manager_id: int = Field(..., description="Assigned hiring manager ID", json_schema_extra={"example": 1})
    job_title: str = Field(..., max_length=150, json_schema_extra={"example": "Senior Python Backend Engineer"})
    employment_type: str = Field(..., max_length=50, json_schema_extra={"example": "Full-time"})
    location: str = Field(..., max_length=100, json_schema_extra={"example": "Hyderabad"})
    openings: int = Field(..., gt=0, json_schema_extra={"example": 3})
    experience_min: int = Field(..., ge=0, json_schema_extra={"example": 2})
    experience_max: int = Field(..., ge=0, json_schema_extra={"example": 6})
    salary_min: Decimal = Field(..., ge=Decimal("0"), json_schema_extra={"example": "800000.00"})
    salary_max: Decimal = Field(..., ge=Decimal("0"), json_schema_extra={"example": "1500000.00"})
    status: str = Field("draft", json_schema_extra={"example": "open"})

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_REQUISITION_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_REQUISITION_STATUSES)}")
        return v

    @field_validator("experience_max")
    @classmethod
    def experience_range_valid(cls, v: int, info) -> int:
        exp_min = info.data.get("experience_min", 0)
        if v < exp_min:
            raise ValueError("experience_max must be >= experience_min")
        return v

    @field_validator("salary_max")
    @classmethod
    def salary_range_valid(cls, v: Decimal, info) -> Decimal:
        sal_min = info.data.get("salary_min", Decimal("0"))
        if v < sal_min:
            raise ValueError("salary_max must be >= salary_min")
        return v


class RequisitionUpdate(BaseModel):
    """Payload for updating requisition details (partial update)."""
    job_title: Optional[str] = Field(None, max_length=150)
    employment_type: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    openings: Optional[int] = Field(None, gt=0)
    experience_min: Optional[int] = Field(None, ge=0)
    experience_max: Optional[int] = Field(None, ge=0)
    salary_min: Optional[Decimal] = Field(None, ge=Decimal("0"))
    salary_max: Optional[Decimal] = Field(None, ge=Decimal("0"))
    hiring_manager_id: Optional[int] = None
    department_id: Optional[int] = None


class RequisitionStatusUpdate(BaseModel):
    """Payload to transition requisition status."""
    status: str = Field(..., description="Target requisition status", json_schema_extra={"example": "open"})

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_REQUISITION_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_REQUISITION_STATUSES)}")
        return v


class RequisitionResponse(OrmBase):
    """Job requisition record representation."""
    requisition_id: int
    department_id: int
    hiring_manager_id: int
    job_title: str
    employment_type: str
    location: str
    openings: int
    experience_min: int
    experience_max: int
    salary_min: Decimal
    salary_max: Decimal
    status: str
    created_at: datetime
    closed_at: Optional[datetime]

