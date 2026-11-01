
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    String,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Application(Base):

    __tablename__ = "applications"

    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "requisition_id",
            name="uq_candidate_requisition"
        ),
    )

    application_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("candidates.candidate_id"),
        nullable=False
    )

    requisition_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("requisitions.requisition_id"),
        nullable=False
    )

    application_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False
    )

    current_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="applied",
        server_default="applied"
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        server_default="active"
    )

    source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    candidate: Mapped["Candidate"] = relationship(
        back_populates="applications"
    )

    requisition: Mapped["Requisition"] = relationship(
        back_populates="applications"
    )

    stage_history: Mapped[list["ApplicationStageHistory"]] = relationship(
        back_populates="application",
        order_by="ApplicationStageHistory.changed_at",
        cascade="all, delete-orphan",
    )

    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )

    offer: Mapped["Offer | None"] = relationship(
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Application(id={self.application_id})>"
