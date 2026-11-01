"""
app/schemas/department.py
=========================
Pydantic schemas for Department endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.common import OrmBase


class DepartmentCreate(BaseModel):
    """Payload to create a new department."""
    department_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique name of the department",
        json_schema_extra={"example": "Engineering"}
    )


class DepartmentResponse(OrmBase):
    """Department record representation."""
    department_id: int
    department_name: str
    created_at: datetime

