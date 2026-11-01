"""
frontend/api_client.py
======================
Centralized HTTP client for communicating with the RecruitFlow FastAPI backend.
Never accesses PostgreSQL directly; all data flows via REST API endpoints.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional
import requests

logger = logging.getLogger("recruitflow.frontend")

DEFAULT_BACKEND_URL = (
    os.getenv("BACKEND_API_URL")
    or os.getenv("BACKEND_URL")
    or "http://localhost:8000"
).rstrip("/")
DEFAULT_TIMEOUT = int(os.getenv("API_TIMEOUT_SECONDS", "30"))


@dataclass
class APIResponse:
    """Standardized response wrapper for all frontend API calls."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 0


class APIClient:
    """Enterprise REST API client for RecruitFlow."""

    def __init__(self, base_url: str = DEFAULT_BACKEND_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> APIResponse:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        clean_params = None
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}

        try:
            resp = self.session.request(
                method=method,
                url=url,
                params=clean_params,
                json=json,
                timeout=self.timeout,
            )
            status = resp.status_code

            # Parse JSON if available
            try:
                body = resp.json()
            except Exception:
                body = resp.text

            if 200 <= status < 300:
                return APIResponse(success=True, data=body, status_code=status)

            # Extract detail message from FastAPI error envelope
            error_msg = f"HTTP {status}"
            if isinstance(body, dict):
                error_msg = body.get("detail", body.get("message", str(body)))
            elif isinstance(body, str) and body:
                error_msg = body

            return APIResponse(success=False, error=str(error_msg), status_code=status)

        except requests.exceptions.ConnectionError:
            err = (
                f"Cannot connect to RecruitFlow backend at {self.base_url}. "
                "Please verify that the FastAPI server is running."
            )
            logger.error(err)
            return APIResponse(success=False, error=err, status_code=503)
        except requests.exceptions.Timeout:
            err = f"Backend request timed out after {self.timeout}s on {endpoint}."
            logger.error(err)
            return APIResponse(success=False, error=err, status_code=504)
        except Exception as exc:
            err = f"Unexpected client error communicating with backend: {exc}"
            logger.exception(err)
            return APIResponse(success=False, error=err, status_code=500)

    # -----------------------------------------------------------------------
    # System & Analytics
    # -----------------------------------------------------------------------

    def check_health(self) -> APIResponse:
        return self._request("GET", "/health")

    def get_analytics_overview(self) -> APIResponse:
        return self._request("GET", "/analytics/overview")

    # -----------------------------------------------------------------------
    # Departments & Employees
    # -----------------------------------------------------------------------

    def get_departments(self) -> APIResponse:
        return self._request("GET", "/departments/")

    def create_department(self, department_name: str) -> APIResponse:
        return self._request("POST", "/departments/", json={"department_name": department_name})

    def get_employees(
        self,
        department_id: Optional[int] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/employees/",
            params={
                "department_id": department_id,
                "role": role,
                "search": search,
                "skip": skip,
                "limit": limit,
            },
        )

    def create_employee(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/employees/", json=data)

    # -----------------------------------------------------------------------
    # Requisitions
    # -----------------------------------------------------------------------

    def get_requisitions(
        self,
        department_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/requisitions/",
            params={
                "department_id": department_id,
                "status": status,
                "search": search,
                "skip": skip,
                "limit": limit,
            },
        )

    def get_requisition(self, requisition_id: int) -> APIResponse:
        return self._request("GET", f"/requisitions/{requisition_id}")

    def create_requisition(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/requisitions/", json=data)

    def update_requisition(self, requisition_id: int, data: dict[str, Any]) -> APIResponse:
        return self._request("PATCH", f"/requisitions/{requisition_id}", json=data)

    def update_requisition_status(self, requisition_id: int, status: str) -> APIResponse:
        return self._request("PATCH", f"/requisitions/{requisition_id}/status", json={"status": status})

    def close_requisition(self, requisition_id: int) -> APIResponse:
        return self._request("POST", f"/requisitions/{requisition_id}/close")

    # -----------------------------------------------------------------------
    # Candidates
    # -----------------------------------------------------------------------

    def get_candidates(
        self,
        search: Optional[str] = None,
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        qualification: Optional[str] = None,
        location: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/candidates/",
            params={
                "search": search,
                "min_experience": min_experience,
                "max_experience": max_experience,
                "qualification": qualification,
                "location": location,
                "skip": skip,
                "limit": limit,
            },
        )

    def get_candidate(self, candidate_id: int) -> APIResponse:
        return self._request("GET", f"/candidates/{candidate_id}")

    def create_candidate(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/candidates/", json=data)

    def update_candidate(self, candidate_id: int, data: dict[str, Any]) -> APIResponse:
        return self._request("PATCH", f"/candidates/{candidate_id}", json=data)

    # -----------------------------------------------------------------------
    # Applications
    # -----------------------------------------------------------------------

    def get_applications(
        self,
        requisition_id: Optional[int] = None,
        candidate_id: Optional[int] = None,
        current_stage: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/applications/",
            params={
                "requisition_id": requisition_id,
                "candidate_id": candidate_id,
                "current_stage": current_stage,
                "status": status,
                "source": source,
                "skip": skip,
                "limit": limit,
            },
        )

    def get_application(self, application_id: int) -> APIResponse:
        return self._request("GET", f"/applications/{application_id}")

    def create_application(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/applications/", json=data)

    def advance_application_stage(
        self, application_id: int, new_stage: str, notes: Optional[str] = None
    ) -> APIResponse:
        return self._request(
            "PATCH",
            f"/applications/{application_id}/stage",
            json={"new_stage": new_stage, "notes": notes},
        )

    def get_application_history(self, application_id: int) -> APIResponse:
        return self._request("GET", f"/applications/{application_id}/history")

    # -----------------------------------------------------------------------
    # Interviews & Scorecards
    # -----------------------------------------------------------------------

    def get_interviews(
        self,
        application_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/interviews/",
            params={
                "application_id": application_id,
                "status": status,
                "skip": skip,
                "limit": limit,
            },
        )

    def get_interview(self, interview_id: int) -> APIResponse:
        return self._request("GET", f"/interviews/{interview_id}")

    def schedule_interview(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/interviews/", json=data)

    def update_interview_schedule(self, interview_id: int, scheduled_at: str) -> APIResponse:
        return self._request(
            "PATCH",
            f"/interviews/{interview_id}/schedule",
            json={"scheduled_at": scheduled_at},
        )

    def assign_interviewer(self, interview_id: int, employee_id: int) -> APIResponse:
        return self._request(
            "POST",
            f"/interviews/{interview_id}/assign-interviewer",
            json={"employee_id": employee_id},
        )

    def update_interview_status(
        self, interview_id: int, status: str, notes: Optional[str] = None
    ) -> APIResponse:
        return self._request(
            "PATCH",
            f"/interviews/{interview_id}/status",
            json={"status": status, "notes": notes},
        )

    def get_scorecards(
        self,
        interview_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        recommendation: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/scorecards/",
            params={
                "interview_id": interview_id,
                "employee_id": employee_id,
                "recommendation": recommendation,
                "skip": skip,
                "limit": limit,
            },
        )

    def submit_scorecard(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/scorecards/", json=data)

    def get_interview_scorecards(self, interview_id: int) -> APIResponse:
        return self._request("GET", f"/scorecards/interview/{interview_id}")

    def get_interview_scorecard_summary(self, interview_id: int) -> APIResponse:
        return self._request("GET", f"/scorecards/interview/{interview_id}/summary")

    # -----------------------------------------------------------------------
    # Offers
    # -----------------------------------------------------------------------

    def get_offers(
        self,
        application_id: Optional[int] = None,
        status: Optional[str] = None,
        approver_id: Optional[int] = None,
        is_expired: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/offers/",
            params={
                "application_id": application_id,
                "status": status,
                "approver_id": approver_id,
                "is_expired": is_expired,
                "skip": skip,
                "limit": limit,
            },
        )

    def get_offer(self, offer_id: int) -> APIResponse:
        return self._request("GET", f"/offers/{offer_id}")

    def create_offer(self, data: dict[str, Any]) -> APIResponse:
        return self._request("POST", "/offers/", json=data)

    def submit_offer_for_approval(self, offer_id: int) -> APIResponse:
        return self._request("POST", f"/offers/{offer_id}/submit-for-approval")

    def approve_offer(
        self, offer_id: int, approver_id: int, notes: Optional[str] = None
    ) -> APIResponse:
        return self._request(
            "POST",
            f"/offers/{offer_id}/approve",
            json={"approved_by": approver_id, "remarks": notes},
        )

    def reject_offer(
        self, offer_id: int, approver_id: int, reason: Optional[str] = None
    ) -> APIResponse:
        return self._request(
            "POST",
            f"/offers/{offer_id}/reject",
            json={"approved_by": approver_id, "remarks": reason},
        )

    def release_offer(self, offer_id: int) -> APIResponse:
        return self._request("POST", f"/offers/{offer_id}/release")

    def candidate_decision_offer(self, offer_id: int, decision: str, reason: Optional[str] = None) -> APIResponse:
        if decision.lower() in ("accepted", "accept"):
            return self._request("POST", f"/offers/{offer_id}/accept", json={"reason": reason})
        return self._request("POST", f"/offers/{offer_id}/candidate-reject", json={"reason": reason})

    def check_offer_expiry(self) -> APIResponse:
        return self._request("POST", "/offers/check-expiry")

    # -----------------------------------------------------------------------
    # Data Quality & Anomaly Detection
    # -----------------------------------------------------------------------

    def run_anomaly_detection(self) -> APIResponse:
        return self._request("POST", "/anomalies/detect")

    def get_anomaly_summary(self) -> APIResponse:
        return self._request("GET", "/anomalies/summary")

    def get_anomalies(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        entity_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
    ) -> APIResponse:
        return self._request(
            "GET",
            "/anomalies/",
            params={
                "skip": skip,
                "limit": limit,
                "category": category,
                "entity_type": entity_type,
                "severity": severity,
                "status": status,
            },
        )

    def get_anomaly(self, anomaly_id: int) -> APIResponse:
        return self._request("GET", f"/anomalies/{anomaly_id}")

    def update_anomaly_status(
        self,
        anomaly_id: int,
        status: str,
        notes: Optional[str] = None,
        resolved_by: Optional[int] = None,
    ) -> APIResponse:
        return self._request(
            "PATCH",
            f"/anomalies/{anomaly_id}/status",
            json={
                "status": status,
                "notes": notes,
                "resolved_by": resolved_by,
            },
        )


# Global singleton instance for Streamlit session reuse
api_client = APIClient()

