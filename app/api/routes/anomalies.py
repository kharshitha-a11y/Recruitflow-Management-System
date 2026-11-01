"""
app/api/routes/anomalies.py
===========================
REST API endpoints for Anomaly Detection and Data Quality Management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AnomalyDetectionRunResponse,
    AnomalyResponse,
    AnomalyStatusUpdate,
    DataQualityReportResponse,
)
from validation import validation_service

router = APIRouter(prefix="/anomalies", tags=["Data Quality & Anomalies"])
DBSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/detect",
    response_model=AnomalyDetectionRunResponse,
    summary="Run anomaly detection engine",
    description=(
        "Executes full scan of all recruitment records across rules A01 to A10. "
        "Deduplicates and persists discovered anomalies to the database."
    ),
)
def run_anomaly_detection(db: DBSession):
    return validation_service.run_detection_and_persist(db, save_to_db=True)


@router.get(
    "/summary",
    response_model=DataQualityReportResponse,
    summary="Retrieve data quality summary",
    description=(
        "Returns comprehensive data quality metrics: total records inspected, "
        "anomalies found, category breakdown (A01-A10), severity distribution, "
        "and data quality percentage calculated without double-counting."
    ),
)
def get_data_quality_summary(db: DBSession):
    return validation_service.get_data_quality_summary(db)


@router.get(
    "/",
    response_model=list[AnomalyResponse],
    summary="Retrieve all anomalies",
    description="Retrieve paginated list of anomalies with multi-criteria filtering.",
)
def list_anomalies(
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    anomaly_code: Optional[str] = Query(None, description="Filter by anomaly rule code (A01 - A10)"),
    category: Optional[str] = Query(None, description="Alias for anomaly_code"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (candidate, application, interview, scorecard, offer, requisition)"),
    severity: Optional[str] = Query(None, description="Filter by severity (Critical, High, Medium, Low)"),
    status: Optional[str] = Query(None, description="Filter by status (Open, Investigating, Resolved, False Positive)"),
):
    target_code = anomaly_code or category
    return validation_service.get_all_anomalies(
        db,
        skip=skip,
        limit=limit,
        anomaly_code=target_code,
        entity_type=entity_type,
        severity=severity,
        status=status,
    )


@router.get(
    "/category/{category}",
    response_model=list[AnomalyResponse],
    summary="Retrieve anomalies by category",
    description="Fetch anomalies filtered by rule category (e.g. A01, A02, A08).",
)
def get_anomalies_by_category(
    category: str,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return validation_service.get_all_anomalies(
        db,
        skip=skip,
        limit=limit,
        anomaly_code=category,
    )


@router.get(
    "/severity/{severity}",
    response_model=list[AnomalyResponse],
    summary="Retrieve anomalies by severity",
    description="Fetch anomalies filtered by severity level (Critical, High, Medium, Low).",
)
def get_anomalies_by_severity(
    severity: str,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    return validation_service.get_all_anomalies(
        db,
        skip=skip,
        limit=limit,
        severity=severity,
    )


@router.get(
    "/{anomaly_id}",
    response_model=AnomalyResponse,
    summary="View anomaly details",
    description="Fetch complete details, recommended remediation action, and investigation history for a single anomaly.",
)
def get_anomaly_details(anomaly_id: int, db: DBSession):
    anomaly = validation_service.get_anomaly_by_id(db, anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found.",
        )
    return anomaly


@router.patch(
    "/{anomaly_id}/status",
    response_model=AnomalyResponse,
    summary="Update anomaly status",
    description="Transition anomaly lifecycle status (Open -> Investigating -> Resolved / False Positive).",
)
def update_anomaly_status(
    anomaly_id: int,
    body: AnomalyStatusUpdate,
    db: DBSession,
):
    return validation_service.update_anomaly_status(
        db,
        anomaly_id=anomaly_id,
        new_status=body.status,
        resolved_by=body.resolved_by,
        notes=body.notes,
    )

