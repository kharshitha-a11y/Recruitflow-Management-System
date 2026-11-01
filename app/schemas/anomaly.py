"""
app/schemas/anomaly.py
======================
Pydantic schemas for Anomaly Detection and Data Quality reporting endpoints.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import OrmBase


VALID_ANOMALY_STATUSES = frozenset({
    "Open",
    "Investigating",
    "Resolved",
    "False Positive",
})

VALID_SEVERITIES = frozenset({
    "Critical",
    "High",
    "Medium",
    "Low",
})


class AnomalyResponse(OrmBase):
    """Full anomaly record representation."""
    anomaly_id: int
    anomaly_code: str
    entity_type: str
    entity_id: int
    severity: str
    description: str
    detected_at: datetime
    status: str
    recommended_action: str
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    notes: Optional[str] = None


class AnomalyStatusUpdate(BaseModel):
    """Payload to update an anomaly's investigation lifecycle status."""
    status: str = Field(..., description="Target status: Open, Investigating, Resolved, False Positive", json_schema_extra={"example": "Investigating"})
    resolved_by: Optional[int] = Field(None, description="Employee ID resolving the issue", json_schema_extra={"example": 1})
    notes: Optional[str] = Field(None, description="Investigation notes or resolution details", json_schema_extra={"example": "Verified qualification exception approved by VP."})

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_ANOMALY_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_ANOMALY_STATUSES)}")
        return v


class DataQualityReportResponse(BaseModel):
    """Comprehensive Data Quality audit report."""
    total_records_inspected: int
    records_inspected_by_entity: dict[str, int]
    total_anomalies_found: int
    unique_anomalous_entities: int
    clean_records_count: int
    data_quality_percentage: float
    anomalies_by_category: dict[str, int]
    category_descriptions: dict[str, str]
    anomalies_by_severity: dict[str, int]
    anomalies_by_status: dict[str, int]
    active_anomalies_count: int
    resolved_anomalies_count: int
    generated_at: str


class AnomalyDetectionRunResponse(DataQualityReportResponse):
    """Result of triggering a full anomaly detection scan."""
    new_anomalies_detected: int
    previously_existing_active_anomalies: int

