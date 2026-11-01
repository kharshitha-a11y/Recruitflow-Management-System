"""
validation/__init__.py
======================
RecruitFlow Data Quality and Anomaly Detection Engine.
"""

from validation.anomaly_detector import AnomalyDetector, detect_experience_anomaly
from validation.data_quality import (
    CATEGORY_LABELS,
    calculate_data_quality_metrics,
)
from validation.validation_service import (
    get_all_anomalies,
    get_anomaly_by_id,
    get_data_quality_summary,
    run_detection_and_persist,
    update_anomaly_status,
)

__all__ = [
    "AnomalyDetector",
    "detect_experience_anomaly",
    "calculate_data_quality_metrics",
    "CATEGORY_LABELS",
    "run_detection_and_persist",
    "get_all_anomalies",
    "get_anomaly_by_id",
    "update_anomaly_status",
    "get_data_quality_summary",
]

