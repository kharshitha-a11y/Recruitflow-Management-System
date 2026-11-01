"""
validation/validation_service.py
================================
Service layer orchestrating anomaly detection, deduplicated persistence,
investigation workflows, and reporting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.business_rules import BusinessRuleError, ResourceNotFoundError
from app.models.anomaly import Anomaly
from validation.anomaly_detector import AnomalyDetector
from validation.data_quality import calculate_data_quality_metrics


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


def run_detection_and_persist(
    db: Session,
    save_to_db: bool = True,
) -> dict[str, Any]:
    """
    Run the anomaly detection engine across all database tables,
    persist new anomalies with deduplication, and return summary metrics.

    Deduplication Strategy:
    -----------------------
    Matches existing unresolved anomalies by (anomaly_code, entity_type, entity_id).
    If an unresolved anomaly already exists, it is NOT re-inserted, guaranteeing
    idempotent detection runs.
    """
    detector = AnomalyDetector(db)
    detection_results = detector.run_detection()

    detected_raw = detection_results["anomalies"]
    total_inspected = detection_results["total_records_inspected"]
    inspected_by_entity = detection_results["records_inspected"]

    new_anomalies_count = 0
    existing_unresolved_count = 0

    if save_to_db:
        # Load existing open/investigating anomalies to prevent duplicates
        stmt = select(Anomaly.anomaly_code, Anomaly.entity_type, Anomaly.entity_id).where(
            Anomaly.status.in_(["Open", "Investigating"])
        )
        existing_keys = set(db.execute(stmt).all())

        new_records: list[Anomaly] = []
        for raw in detected_raw:
            key = (raw["anomaly_code"], raw["entity_type"], raw["entity_id"])
            if key in existing_keys:
                existing_unresolved_count += 1
                continue

            anomaly_obj = Anomaly(
                anomaly_code=raw["anomaly_code"],
                entity_type=raw["entity_type"],
                entity_id=raw["entity_id"],
                severity=raw["severity"],
                description=raw["description"],
                recommended_action=raw["recommended_action"],
                status="Open",
            )
            new_records.append(anomaly_obj)
            existing_keys.add(key)  # Prevent internal duplicate in the same batch

        if new_records:
            db.add_all(new_records)
            db.commit()
            new_anomalies_count = len(new_records)

    # Compute current metrics
    all_stored_anomalies = list(db.scalars(select(Anomaly)).all())
    metrics = calculate_data_quality_metrics(
        anomalies=all_stored_anomalies,
        total_records_inspected=total_inspected,
        records_by_entity=inspected_by_entity,
    )

    metrics["new_anomalies_detected"] = new_anomalies_count
    metrics["previously_existing_active_anomalies"] = existing_unresolved_count
    return metrics


def get_all_anomalies(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    anomaly_code: Optional[str] = None,
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> list[Anomaly]:
    """Retrieve paginated and filtered list of anomalies."""
    stmt = select(Anomaly).order_by(Anomaly.detected_at.desc()).offset(skip).limit(limit)

    target_code = anomaly_code or category
    if target_code:
        stmt = stmt.where(Anomaly.anomaly_code == target_code.strip().upper())
    if entity_type:
        stmt = stmt.where(Anomaly.entity_type == entity_type.strip().lower())
    if severity:
        stmt = stmt.where(Anomaly.severity == severity.strip().capitalize())
    if status:
        stmt = stmt.where(Anomaly.status == status.strip())

    return list(db.scalars(stmt).all())


def get_anomaly_by_id(db: Session, anomaly_id: int) -> Optional[Anomaly]:
    """Retrieve a single anomaly by ID."""
    return db.get(Anomaly, anomaly_id)


def update_anomaly_status(
    db: Session,
    anomaly_id: int,
    new_status: str,
    resolved_by: Optional[int] = None,
    notes: Optional[str] = None,
) -> Anomaly:
    """
    Update investigation status of an anomaly.
    Valid statuses: Open, Investigating, Resolved, False Positive.
    Sets resolved_at when marked Resolved or False Positive.
    """
    anomaly = db.get(Anomaly, anomaly_id)
    if not anomaly:
        raise ResourceNotFoundError(f"Anomaly ID {anomaly_id} not found.")

    if new_status not in VALID_ANOMALY_STATUSES:
        raise BusinessRuleError(
            f"Invalid status '{new_status}'. Allowed: {sorted(VALID_ANOMALY_STATUSES)}"
        )

    anomaly.status = new_status
    if notes:
        anomaly.notes = notes.strip()

    if new_status in ("Resolved", "False Positive"):
        anomaly.resolved_at = datetime.now(timezone.utc)
        if resolved_by is not None:
            anomaly.resolved_by = resolved_by
    else:
        anomaly.resolved_at = None

    db.commit()
    db.refresh(anomaly)
    return anomaly


def get_data_quality_summary(db: Session) -> dict[str, Any]:
    """
    Compute live data quality report by inspecting database counts
    and currently stored anomalies.
    """
    from app.models import (
        Application,
        Candidate,
        Interview,
        Offer,
        Requisition,
        Scorecard,
    )

    counts = {
        "candidates": db.scalar(select(func.count(Candidate.candidate_id))) or 0,
        "requisitions": db.scalar(select(func.count(Requisition.requisition_id))) or 0,
        "applications": db.scalar(select(func.count(Application.application_id))) or 0,
        "interviews": db.scalar(select(func.count(Interview.interview_id))) or 0,
        "scorecards": db.scalar(select(func.count(Scorecard.scorecard_id))) or 0,
        "offers": db.scalar(select(func.count(Offer.offer_id))) or 0,
    }
    total_inspected = sum(counts.values())

    all_anomalies = list(db.scalars(select(Anomaly)).all())
    return calculate_data_quality_metrics(
        anomalies=all_anomalies,
        total_records_inspected=total_inspected,
        records_by_entity=counts,
    )

