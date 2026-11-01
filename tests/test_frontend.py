"""
tests/test_frontend.py
======================
Unit and integration tests for RecruitFlow Streamlit frontend,
Plotly chart builders, table formatters, and the REST APIClient.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest
import plotly.graph_objects as go
import requests

from frontend.api_client import APIClient, APIResponse
from frontend.components.charts import (
    chart_anomalies_by_category,
    chart_anomalies_by_severity,
    chart_department_requisitions,
    chart_interview_outcomes,
    chart_monthly_trends,
    chart_offer_status,
    chart_source_distribution,
    chart_stage_funnel,
)
from frontend.components.tables import format_currency, render_status_badge


# ---------------------------------------------------------------------------
# 1. Table & Formatting Helper Tests
# ---------------------------------------------------------------------------

class TestTableFormatters:
    def test_format_currency_valid(self):
        assert format_currency(1500000) == "INR 1,500,000.00"
        assert format_currency(2500000.5) == "INR 2,500,000.50"
        assert format_currency(Decimal("5000000")) == "INR 5,000,000.00"

    def test_format_currency_none_and_invalid(self):
        assert format_currency(None) == "N/A"
        assert format_currency("InvalidString") == "InvalidString"

    def test_render_status_badge(self):
        badge_hired = render_status_badge("hired")
        assert "Hired" in badge_hired
        assert "#DEF7EC" in badge_hired

        badge_critical = render_status_badge("critical")
        assert "Critical" in badge_critical
        assert "#FDE8E8" in badge_critical

        badge_pending = render_status_badge("pending_approval")
        assert "Pending Approval" in badge_pending


# ---------------------------------------------------------------------------
# 2. Plotly Interactive Chart Tests
# ---------------------------------------------------------------------------

class TestPlotlyCharts:
    def test_chart_stage_funnel(self):
        stage_counts = {
            "applied": 1500,
            "screening": 1200,
            "interview": 800,
            "offer": 300,
            "hired": 200,
        }
        fig = chart_stage_funnel(stage_counts)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == "funnel"

    def test_chart_source_distribution(self):
        sources = {"LinkedIn": 500, "Indeed": 400, "Referral": 300}
        fig = chart_source_distribution(sources)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "pie"

    def test_chart_monthly_trends(self):
        trends = [
            {"month": "2026-08", "applications": 100, "hires": 10},
            {"month": "2026-09", "applications": 150, "hires": 15},
        ]
        fig = chart_monthly_trends(trends)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Bar + Scatter

    def test_chart_monthly_trends_empty(self):
        fig = chart_monthly_trends([])
        assert isinstance(fig, go.Figure)

    def test_chart_department_requisitions(self):
        dept_data = [
            {"department_name": "Engineering", "total_requisitions": 20, "open_requisitions": 10},
            {"department_name": "Product", "total_requisitions": 15, "open_requisitions": 5},
        ]
        fig = chart_department_requisitions(dept_data)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Stacked open + filled

    def test_chart_interview_outcomes(self):
        outcomes = {"strong_hire": 50, "hire": 100, "hold": 30, "no_hire": 20}
        fig = chart_interview_outcomes(outcomes)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "pie"

    def test_chart_offer_status(self):
        statuses = {"draft": 10, "pending_approval": 20, "approved": 30, "released": 40, "accepted": 50}
        fig = chart_offer_status(statuses)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"

    def test_chart_anomalies_by_category(self):
        cats = {"A01": 500, "A02": 20, "A08": 5}
        descs = {"A01": "Experience Anomaly", "A02": "Duplicate", "A08": "Salary"}
        fig = chart_anomalies_by_category(cats, descs)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"

    def test_chart_anomalies_by_severity(self):
        sevs = {"Critical": 1, "High": 200, "Medium": 500, "Low": 300}
        fig = chart_anomalies_by_severity(sevs)
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "pie"


# ---------------------------------------------------------------------------
# 3. APIClient Tests
# ---------------------------------------------------------------------------

class TestAPIClient:
    def test_connection_error_handling(self):
        client = APIClient(base_url="http://invalid-nonexistent-domain-12345.local")
        resp = client.check_health()
        assert resp.success is False
        assert "Cannot connect to RecruitFlow backend" in resp.error
        assert resp.status_code == 503

    @patch("requests.Session.request")
    def test_successful_request_parsing(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "version": "1.0.0"}
        mock_request.return_value = mock_resp

        client = APIClient()
        res = client.check_health()
        assert res.success is True
        assert res.data["status"] == "ok"
        assert res.status_code == 200

    @patch("requests.Session.request")
    def test_backend_400_business_rule_error_handling(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"detail": "Candidate experience does not satisfy job requirements."}
        mock_request.return_value = mock_resp

        client = APIClient()
        res = client.create_application({"candidate_id": 1, "requisition_id": 2})
        assert res.success is False
        assert res.status_code == 400
        assert "Candidate experience does not satisfy" in res.error

    @patch("requests.Session.request")
    def test_backend_404_not_found(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "Candidate ID 999999 not found."}
        mock_request.return_value = mock_resp

        client = APIClient()
        res = client.get_candidate(999999)
        assert res.success is False
        assert res.status_code == 404
        assert "not found" in res.error

    @patch("requests.Session.request")
    def test_analytics_overview_call(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "total_candidates": 5000,
            "total_requisitions": 200,
            "open_positions": 100,
            "total_applications": 8000,
            "interviews_scheduled": 2000,
            "offers_released": 500,
            "hiring_conversion_rate": 10.0,
            "avg_time_to_hire_days": 25.0,
            "applications_by_stage": {"applied": 1000},
            "applications_by_source": {"LinkedIn": 1000},
            "hiring_trends": [],
            "requisitions_by_department": [],
            "interview_outcomes": {},
            "offer_status_breakdown": {},
            "offer_acceptance_rate": 50.0,
        }
        mock_request.return_value = mock_resp

        client = APIClient()
        res = client.get_analytics_overview()
        assert res.success is True
        assert res.data["total_candidates"] == 5000


# ---------------------------------------------------------------------------
# 4. Analytics Backend Endpoint Integration
# ---------------------------------------------------------------------------

class TestAnalyticsBackendEndpoint:
    def test_analytics_overview_integration(self, client):
        r = client.get("/analytics/overview")
        assert r.status_code == 200
        body = r.json()
        expected_keys = [
            "total_candidates",
            "total_requisitions",
            "open_positions",
            "total_applications",
            "interviews_scheduled",
            "offers_released",
            "hiring_conversion_rate",
            "avg_time_to_hire_days",
            "applications_by_stage",
            "applications_by_source",
            "hiring_trends",
            "requisitions_by_department",
            "interview_outcomes",
            "offer_status_breakdown",
            "offer_acceptance_rate",
        ]
        for k in expected_keys:
            assert k in body, f"Key {k} missing from /analytics/overview response"

