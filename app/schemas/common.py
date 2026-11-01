"""
app/schemas/common.py
=====================
Shared base models and common response schemas.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    """
    Base class for all ORM-backed response schemas.
    Enables automatic serialization of SQLAlchemy model instances.
    """
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Generic status message response."""
    message: str
    detail: Optional[str] = None

