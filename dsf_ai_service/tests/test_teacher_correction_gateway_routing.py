"""Retirement contract for text-addressed teacher correction."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import dsf_ai_service.app as appmod
from dsf_ai_service import substrate_runner


def test_text_teacher_routes_fail_closed_without_engine_access(monkeypatch):
    class _ExplodingEngine:
        def __getattr__(self, name):
            raise AssertionError(
                f"retired teacher route accessed engine attribute {name}"
            )

    monkeypatch.setattr(appmod, "_guala", _ExplodingEngine())
    client = TestClient(appmod.app)

    correction = client.post(
        "/api/v1/teacher/correction",
        json={
            "emission_id": "historical",
            "corrected_text": "scripted expected answer",
            "source": "joe",
        },
    )
    feedback = client.post(
        "/api/v1/teacher/feedback",
        json={"emission_id": "historical", "source": "joe"},
    )

    for response in (correction, feedback):
        assert response.status_code == 410
        body = response.json()
        assert body["state"] == "retired_wrong_architecture"
        assert "causal authority" in body["reason"]


def test_missing_correction_text_cannot_reopen_legacy_validation():
    client = TestClient(appmod.app)

    response = client.post(
        "/api/v1/teacher/correction",
        json={"emission_id": "historical", "source": "joe"},
    )

    assert response.status_code == 410
    assert response.json()["state"] == "retired_wrong_architecture"


def test_remote_teacher_ops_are_bound_to_retirement_handler():
    assert (
        substrate_runner.OP_HANDLERS["teacher_feedback"]
        is substrate_runner.handle_retired_scripted_cognition
    )
    assert (
        substrate_runner.OP_HANDLERS["teacher_correction"]
        is substrate_runner.handle_retired_scripted_cognition
    )


def test_live_ui_has_no_text_correction_affordance():
    ui = (
        Path(appmod.__file__).parent / "static" / "gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "/api/v1/teacher/correction" not in ui
    assert "/api/v1/teacher/feedback" not in ui
    assert "submitCorrection" not in ui
    assert "sendFeedback" not in ui
