
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    DateTime,
    CheckConstraint,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Candidate(Base):

    __tablename__ = "candidates"

    __table_args__ = (
        CheckConstraint(
            "experience_years >= 0",
            name="ck_candidate_experience"
        ),
    )

    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    experience_years: Mapped[float] = mapped_column(
        Numeric(4, 1),
        nullable=False,
        default=0
    )

    highest_qualification: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    current_location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    applications: Mapped[list["Application"]] = relationship(
        back_populates="candidate"
    )

    def __repr__(self):
        return f"<Candidate(name={self.full_name})>"
