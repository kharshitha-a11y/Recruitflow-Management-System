
from datetime import datetime

from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Department(Base):

    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    department_name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    employees: Mapped[list["Employee"]] = relationship(
        back_populates="department"
    )

    requisitions: Mapped[list["Requisition"]] = relationship(
        back_populates="department"
    )

    def __repr__(self):
        return f"<Department(name={self.department_name})>"
