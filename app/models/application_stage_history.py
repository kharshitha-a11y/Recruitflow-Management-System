
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ApplicationStageHistory(Base):

    __tablename__ = "application_stage_history"

    __table_args__ = (
        CheckConstraint(
            "new_stage IN "
            "('applied', 'screening', 'interview', "
            "'assessment', 'offer', 'hired', 'rejected')",
            name="ck_valid_new_stage"
        ),
    )

    history_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.application_id"),
        nullable=False
    )

    previous_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    new_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    changed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id"),
        nullable=True
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    application: Mapped["Application"] = relationship(
        back_populates="stage_history"
    )

    def __repr__(self):
        return (
            f"<ApplicationStageHistory("
            f"application_id={self.application_id}, "
            f"stage={self.new_stage})>"
        )
