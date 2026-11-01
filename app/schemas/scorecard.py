"""
app/schemas/scorecard.py
========================
Pydantic schemas for Scorecard endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase

VALID_RECOMMENDATIONS = frozenset(
    {"strong_hire", "hire", "hold", "no_hire"}
)


class ScorecardCreate(BaseModel):
    """Payload to submit an interview evaluation scorecard."""
    interview_id: int = Field(..., description="Interview ID", json_schema_extra={"example": 1})
    employee_id: int = Field(..., description="Evaluating interviewer Employee ID", json_schema_extra={"example": 3})
    technical_score: Decimal = Field(..., description="Score 0.0 - 10.0", json_schema_extra={"example": "8.5"})
    communication_score: Decimal = Field(..., description="Score 0.0 - 10.0", json_schema_extra={"example": "8.0"})
    problem_solving_score: Decimal = Field(..., description="Score 0.0 - 10.0", json_schema_extra={"example": "9.0"})
    overall_score: Optional[Decimal] = Field(
        None,
        description="Optional overall score 0.0 - 10.0. If omitted, calculated automatically as average of scores.",
        json_schema_extra={"example": "8.5"}
    )
    recommendation: str = Field(..., description="Recommendation (strong_hire, hire, hold, no_hire)", json_schema_extra={"example": "hire"})
    feedback: Optional[str] = Field(None, description="Detailed written feedback", json_schema_extra={"example": "Strong grasp of algorithms and system design."})

    @field_validator(
        "technical_score",
        "communication_score",
        "problem_solving_score",
        mode="before",
    )
    @classmethod
    def score_in_range(cls, v) -> Decimal:
        d = Decimal(str(v))
        if not (Decimal("0") <= d <= Decimal("10")):
            raise ValueError("Score must be between 0 and 10")
        return d

    @field_validator("overall_score", mode="before")
    @classmethod
    def overall_score_in_range(cls, v) -> Optional[Decimal]:
        if v is None:
            return None
        d = Decimal(str(v))
        if not (Decimal("0") <= d <= Decimal("10")):
            raise ValueError("overall_score must be between 0 and 10")
        return d

    @field_validator("recommendation")
    @classmethod
    def recommendation_valid(cls, v: str) -> str:
        if v not in VALID_RECOMMENDATIONS:
            raise ValueError(f"recommendation must be one of {sorted(VALID_RECOMMENDATIONS)}")
        return v


class ScorecardResponse(OrmBase):
    """Scorecard evaluation representation."""
    scorecard_id: int
    interview_id: int
    employee_id: int
    technical_score: Decimal
    communication_score: Decimal
    problem_solving_score: Decimal
    overall_score: Decimal
    recommendation: str
    feedback: Optional[str]
    submitted_at: datetime


class ScorecardSummaryResponse(BaseModel):
    """Aggregated scorecard summary for an interview."""
    interview_id: int
    total_scorecards: int
    average_technical_score: Decimal
    average_communication_score: Decimal
    average_problem_solving_score: Decimal
    average_overall_score: Decimal
    recommendations_summary: dict[str, int]

