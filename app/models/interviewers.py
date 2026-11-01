
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Interviewer(Base):

    __tablename__ = "interviewers"

    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("interviews.interview_id"),
        primary_key=True
    )

    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id"),
        primary_key=True
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    interview: Mapped["Interview"] = relationship(
        back_populates="interviewer_assignments"
    )

    employee: Mapped["Employee"] = relationship("Employee")

    scorecards: Mapped[list["Scorecard"]] = relationship(
        primaryjoin=(
            "and_("
            "Interviewer.interview_id == Scorecard.interview_id, "
            "Interviewer.employee_id == Scorecard.employee_id"
            ")"
        ),
        foreign_keys="[Scorecard.interview_id, Scorecard.employee_id]",
        viewonly=True,
    )

    def __repr__(self):
        return (
            f"<Interviewer("
            f"interview_id={self.interview_id}, "
            f"employee_id={self.employee_id})>"
        )
