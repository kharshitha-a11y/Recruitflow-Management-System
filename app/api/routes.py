"""
app/api/routes.py
=================
Backward compatibility proxy redirecting to modular app.api.routes package.
"""

from app.api.routes import (
    ALL_ROUTERS,
    departments_router,
    employees_router,
    candidates_router,
    requisitions_router,
    applications_router,
    interviews_router,
    scorecards_router,
    offers_router,
    anomalies_router,
)

__all__ = [
    "ALL_ROUTERS",
    "departments_router",
    "employees_router",
    "candidates_router",
    "requisitions_router",
    "applications_router",
    "interviews_router",
    "scorecards_router",
    "offers_router",
    "anomalies_router",
]
