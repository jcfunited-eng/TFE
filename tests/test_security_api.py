"""Tests for Guala occurrence endpoint authentication and sliding-window rate limiting."""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from dsf_ai_service.lean_actor import LeanOrganismActor
from dsf_ai_service.lean_production_app import (
    OCCURRENCE_ROUTE,
    OccurrenceRateLimiter,
    create_lean_production_app,
)
from guala_caretaker import caretaker


class DummyOrganismActor(LeanOrganismActor):
    """Minimal actor stub sufficient for HTTP lifecycle and occurrence testing."""

    def __init__(self) -> None:
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def close(self) -> None:
        self.closed = True

    def observation(self) -> dict[str, object]:
        return {
            "available": True,
            "durability_blocked": False,
            "checkpoint_error": None,
            "cleanup_error": None,
        }

    def offer(self, physical_occurrence) -> concurrent.futures.Future:
        future = concurrent.futures.Future()
        result = MagicMock()
        result.native_interval_count = 1
        result.pressure = None
        future.set_result(result)
        return future


SAMPLE_UNATTENDED_BODY = {
    "kind": "unattended",
}


@pytest.fixture
def test_app():
    return create_lean_production_app(actor_factory=lambda: DummyOrganismActor())


def test_occurrence_auth_missing_token_returns_401(test_app, monkeypatch):
    monkeypatch.setenv("GUALA_OCCURRENCE_AUTH_TOKEN", "secure-organism-token-xyz")
    with TestClient(test_app) as client:
        response = client.post(OCCURRENCE_ROUTE, json=SAMPLE_UNATTENDED_BODY)
        assert response.status_code == 401
        assert "invalid or missing occurrence authorization token" in response.text


def test_occurrence_auth_invalid_token_returns_401(test_app, monkeypatch):
    monkeypatch.setenv("GUALA_OCCURRENCE_AUTH_TOKEN", "secure-organism-token-xyz")
    with TestClient(test_app) as client:
        # Bad Bearer token
        res_bearer = client.post(
            OCCURRENCE_ROUTE,
            json=SAMPLE_UNATTENDED_BODY,
            headers={"Authorization": "Bearer bad-token-123"},
        )
        assert res_bearer.status_code == 401

        # Bad X-Guala-Token header
        res_header = client.post(
            OCCURRENCE_ROUTE,
            json=SAMPLE_UNATTENDED_BODY,
            headers={"X-Guala-Token": "bad-token-123"},
        )
        assert res_header.status_code == 401


def test_occurrence_auth_valid_bearer_token_returns_200(test_app, monkeypatch):
    monkeypatch.setenv("GUALA_OCCURRENCE_AUTH_TOKEN", "secure-organism-token-xyz")
    with TestClient(test_app) as client:
        response = client.post(
            OCCURRENCE_ROUTE,
            json=SAMPLE_UNATTENDED_BODY,
            headers={"Authorization": "Bearer secure-organism-token-xyz"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["schema"] == "guala.lean_occurrence_result.v1"
        assert data["native_interval_count"] == 1


def test_occurrence_auth_valid_x_guala_token_returns_200(test_app, monkeypatch):
    monkeypatch.setenv("GUALA_OCCURRENCE_AUTH_TOKEN", "secure-organism-token-xyz")
    with TestClient(test_app) as client:
        response = client.post(
            OCCURRENCE_ROUTE,
            json=SAMPLE_UNATTENDED_BODY,
            headers={"X-Guala-Token": "secure-organism-token-xyz"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["schema"] == "guala.lean_occurrence_result.v1"


def test_occurrence_auth_fallback_to_guala_api_token(test_app, monkeypatch):
    monkeypatch.delenv("GUALA_OCCURRENCE_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("GUALA_API_TOKEN", "fallback-guala-key-abc")
    with TestClient(test_app) as client:
        response = client.post(
            OCCURRENCE_ROUTE,
            json=SAMPLE_UNATTENDED_BODY,
            headers={"Authorization": "Bearer fallback-guala-key-abc"},
        )
        assert response.status_code == 200


def test_occurrence_open_when_no_token_configured(test_app, monkeypatch):
    monkeypatch.delenv("GUALA_OCCURRENCE_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("GUALA_API_TOKEN", raising=False)
    with TestClient(test_app) as client:
        response = client.post(OCCURRENCE_ROUTE, json=SAMPLE_UNATTENDED_BODY)
        assert response.status_code == 200


def test_occurrence_rate_limiting_saturation(test_app, monkeypatch):
    monkeypatch.delenv("GUALA_OCCURRENCE_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("GUALA_API_TOKEN", raising=False)
    with TestClient(test_app) as client:
        # Default rate limit is 16 requests per second
        for _ in range(16):
            res = client.post(OCCURRENCE_ROUTE, json=SAMPLE_UNATTENDED_BODY)
            assert res.status_code == 200

        # 17th request in the same window must be rejected with 429
        rejected = client.post(OCCURRENCE_ROUTE, json=SAMPLE_UNATTENDED_BODY)
        assert rejected.status_code == 429
        assert "occurrence rate limit exceeded" in rejected.text


def test_caretaker_occurrence_headers(monkeypatch):
    # With token configured
    monkeypatch.setenv("GUALA_OCCURRENCE_AUTH_TOKEN", "token-alpha")
    headers = caretaker._occurrence_headers()
    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == "Bearer token-alpha"
    assert headers["X-Guala-Token"] == "token-alpha"

    # Without token configured
    monkeypatch.delenv("GUALA_OCCURRENCE_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("GUALA_API_TOKEN", raising=False)
    caretaker.AUTH_TOKEN = None
    headers_clean = caretaker._occurrence_headers()
    assert headers_clean == {"Content-Type": "application/json"}
    assert "Authorization" not in headers_clean

