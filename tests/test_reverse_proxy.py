"""
tests/test_reverse_proxy.py
===========================
Automated test suite verifying the RecruitFlow Single-URL Reverse Proxy routing,
path rewriting, header preservation, and upstream forwarding.
"""

import pytest
from unittest.mock import MagicMock, patch

from proxy_server import app, determine_target_url, HOP_BY_HOP, BACKEND_HTTP, FRONTEND_HTTP
from tests.conftest import ASGIClient


def test_routing_rules_fastapi_endpoints():
    """Verify that Swagger, ReDoc, OpenAPI schema, and health endpoints map to backend."""
    assert determine_target_url("/health", "") == f"{BACKEND_HTTP}/health"
    assert determine_target_url("/docs", "") == f"{BACKEND_HTTP}/docs"
    assert determine_target_url("/redoc", "") == f"{BACKEND_HTTP}/redoc"
    assert determine_target_url("/openapi.json", "") == f"{BACKEND_HTTP}/openapi.json"


def test_routing_rules_api_prefix_stripping():
    """Verify that /api/ prefix is stripped and forwarded to backend root."""
    assert determine_target_url("/api/candidates/", "") == f"{BACKEND_HTTP}/candidates/"
    assert determine_target_url("/api/requisitions/", "status=OPEN") == f"{BACKEND_HTTP}/requisitions/?status=OPEN"
    assert determine_target_url("/api", "") == f"{BACKEND_HTTP}/"
    assert determine_target_url("/api/anomalies/detect", "") == f"{BACKEND_HTTP}/anomalies/detect"


def test_routing_rules_frontend_ui():
    """Verify that root, page assets, and frontend routes map to Streamlit."""
    assert determine_target_url("/", "") == f"{FRONTEND_HTTP}/"
    assert determine_target_url("/candidates", "") == f"{FRONTEND_HTTP}/candidates"
    assert determine_target_url("/static/css/main.css", "") == f"{FRONTEND_HTTP}/static/css/main.css"


def test_hop_by_hop_headers_filtered():
    """Verify that connection-specific hop-by-hop headers are excluded from forwarding."""
    for header in ["connection", "keep-alive", "transfer-encoding", "upgrade"]:
        assert header in HOP_BY_HOP


@patch("proxy_server.http_pool.request")
def test_proxy_http_forwarding_health(mock_pool_request):
    """Test HTTP GET /health forwarded through ASGI proxy."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.read.side_effect = [b'{"status": "ok", "project": "RecruitFlow"}', b""]
    mock_pool_request.return_value = mock_response

    client = ASGIClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project"] == "RecruitFlow"

    # Verify target was backend health endpoint
    mock_pool_request.assert_called_once()
    args, kwargs = mock_pool_request.call_args
    assert args[0] == "GET"
    assert args[1] == f"{BACKEND_HTTP}/health"


@patch("proxy_server.http_pool.request")
def test_proxy_http_forwarding_api_endpoint(mock_pool_request):
    """Test HTTP GET /api/candidates/ forwarded with stripped /api prefix."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.read.side_effect = [b'[{"candidate_id": 1, "first_name": "Test"}]', b""]
    mock_pool_request.return_value = mock_response

    client = ASGIClient(app)
    response = client.get("/api/candidates/?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["candidate_id"] == 1

    # Verify target was stripped backend candidates endpoint with query params
    mock_pool_request.assert_called_once()
    args, kwargs = mock_pool_request.call_args
    assert args[0] == "GET"
    assert args[1] == f"{BACKEND_HTTP}/candidates/?limit=5"


@patch("proxy_server.http_pool.request")
def test_proxy_upstream_error_handling(mock_pool_request):
    """Test proxy returns 502 Bad Gateway when upstream service is unreachable."""
    mock_pool_request.side_effect = Exception("Connection refused by upstream")

    client = ASGIClient(app)
    response = client.get("/api/unreachable")

    assert response.status_code == 502
    assert "Bad Gateway" in response.json()["error"]
