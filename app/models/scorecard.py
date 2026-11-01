
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    Text,
    DateTime,
    ForeignKeyConstraint,
    UniqueConstraint,
    CheckConstraint,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Scorecard(Base):

    __tablename__ = "scorecards"

    __table_args__ = (

        # Only one scorecard per interviewer per interview
        UniqueConstraint(
            "interview_id",
            "employee_id",
            name="uq_interview_employee_scorecard"
        ),

        # Only assigned interviewers can submit scorecards
        ForeignKeyConstraint(
            ["interview_id", "employee_id"],
            [
                "interviewers.interview_id",
                "interviewers.employee_id"
            ],
            name="fk_scorecard_interviewer"
        ),

        CheckConstraint(
            "technical_score BETWEEN 0 AND 10",
            name="ck_technical_score"
        ),

        CheckConstraint(
            "communication_score BETWEEN 0 AND 10",
            name="ck_communication_score"
        ),

        CheckConstraint(
            "problem_solving_score BETWEEN 0 AND 10",
            name="ck_problem_solving_score"
        ),

        CheckConstraint(
            "overall_score BETWEEN 0 AND 10",
            name="ck_overall_score"
        ),

        CheckConstraint(
            "recommendation IN "
            "('strong_hire', 'hire', 'hold', 'no_hire')",
            name="ck_scorecard_recommendation"
        ),
    )

    scorecard_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    interview_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    technical_score: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False
    )

    communication_score: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False
    )

    problem_solving_score: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False
    )

    overall_score: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False
    )

    recommendation: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    interviewer_record: Mapped["Interviewer"] = relationship(
        "Interviewer",
        primaryjoin=(
            "and_("
            "Scorecard.interview_id == Interviewer.interview_id, "
            "Scorecard.employee_id == Interviewer.employee_id"
            ")"
        ),
        foreign_keys="[Scorecard.interview_id, Scorecard.employee_id]",
        viewonly=True,
    )

    def __repr__(self):
        return (
            f"<Scorecard("
            f"interview_id={self.interview_id}, "
            f"employee_id={self.employee_id})>"
        )
