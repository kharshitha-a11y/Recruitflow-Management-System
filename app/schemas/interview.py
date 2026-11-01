"""
app/schemas/interview.py
========================
Pydantic schemas for Interview and Interviewer Assignment endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase

VALID_INTERVIEW_STATUSES = frozenset(
    {"scheduled", "completed", "cancelled", "rescheduled"}
)


class InterviewCreate(BaseModel):
    """Payload to schedule a new interview."""
    application_id: int = Field(..., description="Target application ID", json_schema_extra={"example": 1})
    interview_round: int = Field(..., gt=0, description="Round number (1, 2, 3...)", json_schema_extra={"example": 1})
    interview_type: str = Field(..., max_length=50, json_schema_extra={"example": "Technical Round 1"})
    scheduled_at: datetime = Field(..., description="Timestamp of the interview", json_schema_extra={"example": "2026-11-05T14:00:00Z"})


class InterviewScheduleUpdate(BaseModel):
    """Payload to update an interview schedule date/time and/or type."""
    scheduled_at: datetime = Field(..., description="New scheduled time", json_schema_extra={"example": "2026-11-06T15:00:00Z"})
    interview_type: Optional[str] = Field(None, max_length=50)


class InterviewStatusUpdate(BaseModel):
    """Payload to update an interview status."""
    status: str = Field(..., description="New interview status", json_schema_extra={"example": "completed"})
    completed_at: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_INTERVIEW_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_INTERVIEW_STATUSES)}")
        return v


class InterviewReschedule(BaseModel):
    """Payload to reschedule an existing interview."""
    new_scheduled_at: datetime = Field(..., description="Rescheduled interview timestamp", json_schema_extra={"example": "2026-11-08T10:00:00Z"})
    reason: Optional[str] = Field(None, description="Reason for rescheduling", json_schema_extra={"example": "Candidate requested reschedule due to conflict."})


class InterviewCompletion(BaseModel):
    """Payload to mark an interview as completed."""
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp (defaults to current time)")


class InterviewerAssignCreate(BaseModel):
    """Payload to assign an employee to the interview panel."""
    employee_id: int = Field(..., description="Employee ID to assign", json_schema_extra={"example": 3})


class InterviewerResponse(OrmBase):
    """Interviewer assignment representation."""
    interview_id: int
    employee_id: int
    assigned_at: datetime


class InterviewResponse(OrmBase):
    """Interview record representation."""
    interview_id: int
    application_id: int
    interview_round: int
    interview_type: str
    scheduled_at: datetime
    completed_at: Optional[datetime]
    status: str

