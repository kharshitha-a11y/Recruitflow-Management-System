
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Integer,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Requisition(Base):

    __tablename__ = "requisitions"

    __table_args__ = (
        CheckConstraint(
            "openings > 0",
            name="ck_requisition_openings"
        ),
        CheckConstraint(
            "experience_min >= 0",
            name="ck_requisition_experience_min"
        ),
        CheckConstraint(
            "experience_max >= experience_min",
            name="ck_requisition_experience_range"
        ),
        CheckConstraint(
            "salary_min >= 0 AND salary_max >= 0",
            name="ck_requisition_salary_nonnegative"
        ),
        CheckConstraint(
            "salary_max >= salary_min",
            name="ck_requisition_salary_range"
        ),
    )

    requisition_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.department_id"),
        nullable=False
    )

    hiring_manager_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.employee_id"),
        nullable=False
    )

    job_title: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    employment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    location: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    openings: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    experience_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    experience_max: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    salary_min: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    salary_max: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        server_default="draft"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    department: Mapped["Department"] = relationship(
        back_populates="requisitions"
    )

    hiring_manager: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="managed_requisitions",
        foreign_keys="[Requisition.hiring_manager_id]",
    )

    applications: Mapped[list["Application"]] = relationship(
        back_populates="requisition"
    )

    def __repr__(self):
        return f"<Requisition(title={self.job_title})>"
