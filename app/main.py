"""
app/main.py
===========
RecruitFlow – Enterprise Recruitment Management & Analytics System
FastAPI application entry point.

Features:
  - Central FastAPI application with OpenAPI / Swagger documentation at /docs
  - Exception handlers translating domain exceptions to HTTP 400, 404, 409, 500
  - Secure error masking (no database credentials or stack traces leaked)
  - Modular routers for Departments, Employees, Requisitions, Candidates,
    Applications, Interviews, Scorecards, and Offers
  - Liveness and health check endpoints
"""

import logging
import os
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ALL_ROUTERS
from app.business_rules import (
    BusinessRuleError,
    ConflictError,
    ResourceNotFoundError,
)

logger = logging.getLogger("recruitflow")

PROJECT_CONFIG = {
    "project_name": "RecruitFlow",
    "version": "1.0.0",
    "description": "Recruitment Management & Analytics System",
}

# Swagger servers: support direct access and reverse proxy under /api
swagger_servers = [
    {"url": "/", "description": "Direct Backend (Port 8000)"},
    {"url": "/api", "description": "Unified Reverse Proxy (Port 10000)"},
]

app = FastAPI(
    title="RecruitFlow API",
    description=(
        "Enterprise Recruitment Management & Analytics System — "
        "REST API managing the complete recruitment lifecycle: "
        "Departments, Employees, Requisitions, Candidates, "
        "Applications, Interviews, Scorecards, and Offers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=swagger_servers,
)

# ---------------------------------------------------------------------------
# CORS Configuration (Supporting Streamlit frontend and local dev origins)
# ---------------------------------------------------------------------------

cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
else:
    allowed_origins = [
        "http://localhost:10000",
        "http://127.0.0.1:10000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global Exception Handlers (Mapping domain exceptions to proper HTTP codes)
# ---------------------------------------------------------------------------


@app.exception_handler(BusinessRuleError)
async def business_rule_exception_handler(request: Request, exc: BusinessRuleError):
    """Translate business rule violations to HTTP 400 Bad Request."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc), "error_type": "business_rule_violation"},
    )


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
    """Translate missing resources to HTTP 404 Not Found."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc), "error_type": "resource_not_found"},
    )


@app.exception_handler(ConflictError)
async def conflict_exception_handler(request: Request, exc: ConflictError):
    """Translate duplicate/conflicting resources to HTTP 409 Conflict."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc), "error_type": "conflict"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler returning HTTP 500 without leaking
    sensitive configuration, database passwords, or stack traces.
    """
    logger.error("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected server error occurred. Please contact the administrator.",
            "error_type": "internal_server_error",
        },
    )


# ---------------------------------------------------------------------------
# Mount Modular Routers
# ---------------------------------------------------------------------------

for router in ALL_ROUTERS:
    app.include_router(router)


# ---------------------------------------------------------------------------
# Health and Info Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"], summary="API liveness check")
def health_check() -> dict[str, Any]:
    """Verify that the API server is up and responsive."""
    return {
        "status": "ok",
        "project": PROJECT_CONFIG["project_name"],
        "version": PROJECT_CONFIG["version"],
    }


@app.get("/", tags=["Health"], summary="Root endpoint")
def root_info() -> dict[str, Any]:
    """Root metadata and links to documentation."""
    return {
        "message": "Welcome to RecruitFlow API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "version": PROJECT_CONFIG["version"],
    }


# ---------------------------------------------------------------------------
# Dev Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("Starting RecruitFlow API...")
    print("Interactive Swagger UI at http://localhost:8000/docs")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

