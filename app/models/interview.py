
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Interview(Base):

    __tablename__ = "interviews"

    __table_args__ = (
        CheckConstraint(
            "interview_round > 0",
            name="ck_interview_round"
        ),

        CheckConstraint(
            "status IN "
            "('scheduled', 'completed', 'cancelled', 'rescheduled')",
            name="ck_interview_status"
        ),

        UniqueConstraint(
            "application_id",
            "interview_round",
            name="uq_application_interview_round"
        ),
    )

    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.application_id"),
        nullable=False
    )

    interview_round: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    interview_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="scheduled",
        server_default="scheduled"
    )

    application: Mapped["Application"] = relationship(
        back_populates="interviews"
    )

    interviewer_assignments: Mapped[list["Interviewer"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
    )

    scorecards: Mapped[list["Scorecard"]] = relationship(
        primaryjoin=(
            "and_(Interview.interview_id == Scorecard.interview_id)"
        ),
        foreign_keys="[Scorecard.interview_id]",
        viewonly=True,
    )

    def __repr__(self):
        return (
            f"<Interview("
            f"id={self.interview_id}, "
            f"round={self.interview_round})>"
        )
