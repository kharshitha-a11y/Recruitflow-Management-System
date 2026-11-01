
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Offer(Base):

    __tablename__ = "offers"

    __table_args__ = (

        UniqueConstraint(
            "application_id",
            name="uq_offer_application"
        ),

        CheckConstraint(
            "offered_salary >= 0",
            name="ck_offer_salary"
        ),

        CheckConstraint(
            "expiry_date >= offer_date",
            name="ck_offer_expiry"
        ),

        CheckConstraint(
            "joining_date >= offer_date",
            name="ck_offer_joining"
        ),

        CheckConstraint(
            "status IN "
            "('draft', 'pending_approval', 'approved', "
            "'released', 'accepted', 'rejected', 'expired')",
            name="ck_offer_status"
        ),
    )

    offer_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("applications.application_id"),
        nullable=False
    )

    offered_salary: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    offer_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    expiry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    joining_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        server_default="draft"
    )

    approved_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    application: Mapped["Application"] = relationship(
        back_populates="offer"
    )

    approver: Mapped["Employee | None"] = relationship(
        "Employee",
        foreign_keys="[Offer.approved_by]",
    )

    def __repr__(self):
        return f"<Offer(id={self.offer_id}, status={self.status})>"
