"""
app/api/routes/__init__.py
==========================
Modular routes package registry.
"""

from app.api.routes.departments import router as departments_router
from app.api.routes.employees import router as employees_router
from app.api.routes.requisitions import router as requisitions_router
from app.api.routes.candidates import router as candidates_router
from app.api.routes.applications import router as applications_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.scorecards import router as scorecards_router
from app.api.routes.offers import router as offers_router
from app.api.routes.anomalies import router as anomalies_router
from app.api.routes.analytics import router as analytics_router

ALL_ROUTERS = [
    departments_router,
    employees_router,
    candidates_router,
    requisitions_router,
    applications_router,
    interviews_router,
    scorecards_router,
    offers_router,
    anomalies_router,
    analytics_router,
]

__all__ = [
    "departments_router",
    "employees_router",
    "candidates_router",
    "requisitions_router",
    "applications_router",
    "interviews_router",
    "scorecards_router",
    "offers_router",
    "anomalies_router",
    "analytics_router",
    "ALL_ROUTERS",
]
