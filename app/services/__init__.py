# app/services/__init__.py
# Re-exports all service modules so routes.py can do:
#   from app.services import candidate_service, offer_service, ...

from app.services import (
    department_service,
    employee_service,
    candidate_service,
    requisition_service,
    application_service,
    interview_service,
    scorecard_service,
    offer_service,
)

__all__ = [
    "department_service",
    "employee_service",
    "candidate_service",
    "requisition_service",
    "application_service",
    "interview_service",
    "scorecard_service",
    "offer_service",
]
