"""
app/models/anomaly.py
=====================
SQLAlchemy 2.x database model for detected data quality anomalies.

Stores anomalies identified across recruitment entities (Candidates, Requisitions,
Applications, Interviews, Scorecards, and Offers) with severity classifications,
recommended remediations, and investigation lifecycle statuses.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    __table_args__ = (
        CheckConstraint(
            "severity IN ('Critical', 'High', 'Medium', 'Low')",
            name="ck_anomaly_severity",
        ),
        CheckConstraint(
            "status IN ('Open', 'Investigating', 'Resolved', 'False Positive')",
            name="ck_anomaly_status",
        ),
        Index("ix_anomalies_lookup", "anomaly_code", "entity_type", "entity_id"),
        Index("ix_anomalies_status_severity", "status", "severity"),
    )

    anomaly_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    anomaly_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    entity_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Open",
        server_default="Open",
        index=True,
    )

    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id"),
        nullable=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Optional relationship to resolver employee
    resolver: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        foreign_keys=[resolved_by],
    )

    def __repr__(self) -> str:
        return (
            f"<Anomaly(id={self.anomaly_id}, code={self.anomaly_code}, "
            f"entity={self.entity_type}#{self.entity_id}, severity={self.severity}, "
            f"status={self.status})>"
        )

