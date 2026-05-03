"""Unit tests for the Flask app.

Run locally:
    pytest -v

Run from repo root:
    pytest 01-observability/app/ -v
"""
from unittest.mock import patch

import pytest

from app import app


@pytest.fixture
def client():
    """Flask test client — lets us hit endpoints without running a real server."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_returns_200(client):
    """Liveness probe: /health must always be 200 + healthy JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_metrics_returns_prometheus_format(client):
    """Prometheus contract: /metrics must return text/plain with metric data."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    # The body should contain at least one of our defined metrics
    body = response.data.decode()
    assert "app_requests_total" in body or "app_request_duration_seconds" in body


def test_data_returns_success(client):
    """/api/data: happy path — 200 with success JSON shape."""
    response = client.get("/api/data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert "message" in payload["data"]
    assert "timestamp" in payload["data"]


def test_error_returns_500(client):
    """/api/error: deliberately fails — must return 500 with error JSON."""
    response = client.get("/api/error")
    assert response.status_code == 500
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "Simulated failure"


def test_slow_returns_200_eventually(client):
    """/api/slow: skips the 6-second sleep so tests stay fast.

    We mock time.sleep so the test runs in milliseconds. The endpoint should
    still return 200 with success JSON.
    """
    with patch("app.time.sleep") as mock_sleep:
        response = client.get("/api/slow")
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"
    mock_sleep.assert_called_once_with(6)


def test_request_counter_increments(client):
    """After hitting /api/data, the counter must appear in /metrics."""
    client.get("/api/data")
    metrics_response = client.get("/metrics")
    body = metrics_response.data.decode()
    assert 'app_requests_total{endpoint="/api/data",method="GET"}' in body


def test_error_counter_increments(client):
    """After hitting /api/error, the error counter must appear in /metrics."""
    client.get("/api/error")
    metrics_response = client.get("/metrics")
    body = metrics_response.data.decode()
    assert 'app_errors_total{endpoint="/api/error",status_code="500"}' in body
