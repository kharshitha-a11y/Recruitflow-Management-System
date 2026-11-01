"""
validation/data_quality.py
==========================
Data Quality Metrics, Formulas, and Report Generation for RecruitFlow.

Formulas:
---------
1. Entity-Level Data Quality Percentage (No double-counting):
   A single entity (e.g. an Application or Offer) may have multiple anomalies.
   To avoid penalizing the score more than 100% per entity, we compute:

       Unique Anomalous Entities = |{ (entity_type, entity_id) with Active Anomalies }|
       Clean Entities = Total Records Inspected - Unique Anomalous Entities
       Data Quality % = max(0.0, (Clean Entities / Total Records Inspected) * 100)

2. Weighted Data Quality Score:
   Accounts for severity penalty:
       Penalty = sum(weight_i * count_i)
       where Critical=1.0, High=0.5, Medium=0.25, Low=0.1
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence


CATEGORY_LABELS: dict[str, str] = {
    "A01": "Candidate experience anomaly",
    "A02": "Duplicate application anomaly",
    "A03": "Interview assignment anomaly",
    "A04": "Interview scheduling anomaly",
    "A05": "Scorecard anomaly",
    "A06": "Offer approval anomaly",
    "A07": "Offer date anomaly",
    "A08": "Salary anomaly",
    "A09": "Application workflow anomaly",
    "A10": "Recruitment process anomaly",
}

SEVERITY_WEIGHTS: dict[str, float] = {
    "Critical": 1.0,
    "High": 0.5,
    "Medium": 0.25,
    "Low": 0.1,
}


def calculate_data_quality_metrics(
    anomalies: Sequence[Any],
    total_records_inspected: int,
    records_by_entity: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Calculate comprehensive data quality statistics and percentages.
    Supports either dictionary anomaly objects or SQLAlchemy Anomaly model instances.
    """
    total_anomalies = len(anomalies)

    # Initialize aggregations
    anomalies_by_category: dict[str, int] = {code: 0 for code in CATEGORY_LABELS}
    anomalies_by_severity: dict[str, int] = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }
    anomalies_by_status: dict[str, int] = {
        "Open": 0,
        "Investigating": 0,
        "Resolved": 0,
        "False Positive": 0,
    }

    # Set of unique entities with unresolved issues (to prevent double counting)
    unique_active_anomalous_entities: set[tuple[str, int]] = set()

    for item in anomalies:
        code = getattr(item, "anomaly_code", None) or (item.get("anomaly_code") if isinstance(item, dict) else None)
        sev = getattr(item, "severity", None) or (item.get("severity") if isinstance(item, dict) else None)
        status = getattr(item, "status", None) or (item.get("status") if isinstance(item, dict) else "Open")
        e_type = getattr(item, "entity_type", None) or (item.get("entity_type") if isinstance(item, dict) else "")
        e_id = getattr(item, "entity_id", None) or (item.get("entity_id") if isinstance(item, dict) else 0)

        # Category breakdown
        if code in anomalies_by_category:
            anomalies_by_category[code] += 1
        else:
            anomalies_by_category[str(code)] = 1

        # Severity breakdown
        if sev in anomalies_by_severity:
            anomalies_by_severity[sev] += 1
        else:
            anomalies_by_severity[str(sev)] = 1

        # Status breakdown
        if status in anomalies_by_status:
            anomalies_by_status[status] += 1
        else:
            anomalies_by_status[str(status)] = 1

        # Track active anomalous entities
        if status in ("Open", "Investigating"):
            unique_active_anomalous_entities.add((e_type, e_id))

    unique_anomalous_count = len(unique_active_anomalous_entities)

    # Calculate Data Quality Percentage
    if total_records_inspected > 0:
        clean_entities = max(0, total_records_inspected - unique_anomalous_count)
        dq_percentage = round((clean_entities / total_records_inspected) * 100.0, 2)
    else:
        dq_percentage = 100.0

    return {
        "total_records_inspected": total_records_inspected,
        "records_inspected_by_entity": records_by_entity or {},
        "total_anomalies_found": total_anomalies,
        "unique_anomalous_entities": unique_anomalous_count,
        "clean_records_count": max(0, total_records_inspected - unique_anomalous_count),
        "data_quality_percentage": dq_percentage,
        "anomalies_by_category": anomalies_by_category,
        "category_descriptions": CATEGORY_LABELS,
        "anomalies_by_severity": anomalies_by_severity,
        "anomalies_by_status": anomalies_by_status,
        "active_anomalies_count": (
            anomalies_by_status.get("Open", 0) + anomalies_by_status.get("Investigating", 0)
        ),
        "resolved_anomalies_count": (
            anomalies_by_status.get("Resolved", 0) + anomalies_by_status.get("False Positive", 0)
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

