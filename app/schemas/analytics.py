"""
app/schemas/analytics.py
========================
Pydantic schemas for analytics and dashboard metrics.
"""

from typing import Any
from pydantic import BaseModel, Field


class DepartmentRequisitions(BaseModel):
    department_name: str
    total_requisitions: int
    open_requisitions: int


class MonthlyTrend(BaseModel):
    month: str
    applications: int
    hires: int


class AnalyticsOverviewResponse(BaseModel):
    total_candidates: int = Field(..., description="Total registered candidates")
    total_requisitions: int = Field(..., description="Total job requisitions")
    open_positions: int = Field(..., description="Requisitions currently open")
    total_applications: int = Field(..., description="Total submitted applications")
    interviews_scheduled: int = Field(..., description="Total scheduled or completed interviews")
    offers_released: int = Field(..., description="Offers released or decisioned")
    hiring_conversion_rate: float = Field(..., description="Percentage of applications resulting in hire")
    avg_time_to_hire_days: float = Field(..., description="Average days from application to hire")
    applications_by_stage: dict[str, int] = Field(..., description="Application counts per stage")
    applications_by_source: dict[str, int] = Field(..., description="Application counts by recruitment channel")
    hiring_trends: list[MonthlyTrend] = Field(..., description="Monthly trend of applications and hires")
    requisitions_by_department: list[DepartmentRequisitions] = Field(..., description="Department requisition breakdown")
    interview_outcomes: dict[str, int] = Field(..., description="Interviewer recommendations breakdown")
    offer_status_breakdown: dict[str, int] = Field(..., description="Offers categorized by lifecycle status")
    offer_acceptance_rate: float = Field(..., description="Offer acceptance rate percentage")

