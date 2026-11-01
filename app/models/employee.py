
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Employee(Base):

    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.department_id"),
        nullable=False
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

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    department: Mapped["Department"] = relationship(
        back_populates="employees"
    )

    managed_requisitions: Mapped[list["Requisition"]] = relationship(
        "Requisition",
        back_populates="hiring_manager",
        foreign_keys="[Requisition.hiring_manager_id]",
    )

    def __repr__(self):
        return f"<Employee(name={self.full_name})>"
