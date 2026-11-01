
from types import SimpleNamespace

from validation.anomaly_detector import detect_experience_anomaly


def test_experience_within_range():
    candidate = SimpleNamespace(experience_years=1.0)
    requisition = SimpleNamespace(
        experience_min=0,
        experience_max=2
    )

    assert detect_experience_anomaly(candidate, requisition) == []


def test_experience_above_range():
    candidate = SimpleNamespace(experience_years=5.0)
    requisition = SimpleNamespace(
        experience_min=0,
        experience_max=2
    )

    anomalies = detect_experience_anomaly(candidate, requisition)

    assert len(anomalies) == 1
    # A02 = experience exceeds maximum allowed range
    assert anomalies[0]["anomaly_code"] == "A02"


def test_experience_below_range():
    candidate = SimpleNamespace(experience_years=0.5)
    requisition = SimpleNamespace(
        experience_min=1,
        experience_max=3
    )

    anomalies = detect_experience_anomaly(candidate, requisition)

    assert len(anomalies) == 1
    assert anomalies[0]["anomaly_code"] == "A01"
