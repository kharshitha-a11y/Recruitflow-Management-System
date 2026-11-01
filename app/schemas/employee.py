"""
app/schemas/employee.py
=======================
Pydantic schemas for Employee endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import OrmBase


class EmployeeCreate(BaseModel):
    """Payload to create a new employee."""
    department_id: int = Field(..., description="ID of the department", json_schema_extra={"example": 1})
    full_name: str = Field(..., min_length=1, max_length=150, json_schema_extra={"example": "Rahul Sharma"})
    email: str = Field(..., max_length=150, json_schema_extra={"example": "rahul.sharma@recruitflow.com"})
    role: str = Field(..., max_length=50, json_schema_extra={"example": "Hiring Manager"})


class EmployeeResponse(OrmBase):
    """Employee record representation."""
    employee_id: int
    department_id: int
    full_name: str
    email: str
    role: str
    created_at: datetime

