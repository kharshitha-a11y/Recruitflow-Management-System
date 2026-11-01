"""
app/schemas/application.py
==========================
Pydantic schemas for Application and Stage History endpoints.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase

VALID_APPLICATION_STAGES = (
    "applied",
    "screening",
    "interview",
    "assessment",
    "offer",
    "hired",
    "rejected",
)


class ApplicationCreate(BaseModel):
    """Payload to submit a candidate application for a job requisition."""
    candidate_id: int = Field(..., description="Candidate ID", json_schema_extra={"example": 1})
    requisition_id: int = Field(..., description="Job requisition ID", json_schema_extra={"example": 1})
    source: Optional[str] = Field(None, max_length=50, json_schema_extra={"example": "LinkedIn"})


class ApplicationStageAdvance(BaseModel):
    """Payload to advance application to the next recruitment stage."""
    new_stage: str = Field(..., description="Target recruitment stage", json_schema_extra={"example": "screening"})
    changed_by: Optional[int] = Field(None, description="Employee ID performing transition", json_schema_extra={"example": 2})
    remarks: Optional[str] = Field(None, description="Stage change remarks or feedback", json_schema_extra={"example": "Resume shortlisted for technical review."})

    @field_validator("new_stage")
    @classmethod
    def stage_must_be_valid(cls, v: str) -> str:
        if v not in VALID_APPLICATION_STAGES:
            raise ValueError(f"new_stage must be one of {VALID_APPLICATION_STAGES}")
        return v


class ApplicationResponse(OrmBase):
    """Application record representation."""
    application_id: int
    candidate_id: int
    requisition_id: int
    application_date: date
    current_stage: str
    status: str
    source: Optional[str]
    created_at: datetime


class StageHistoryResponse(OrmBase):
    """Application stage audit history entry."""
    history_id: int
    application_id: int
    previous_stage: Optional[str]
    new_stage: str
    changed_by: Optional[int]
    changed_at: datetime
    remarks: Optional[str]

