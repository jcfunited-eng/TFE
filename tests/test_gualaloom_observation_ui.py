from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_observation_endpoint_exposes_authoritative_embodied_state(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", "observation-route-key")

    import dsf_ai_service.app as app_module
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    organism = Guala()
    previous = app_module._guala
    app_module._guala = organism
    try:
        response = TestClient(app_module.app).get(
            "/api/v1/gualaloom/observation"
        )
        assert response.status_code == 200
        value = response.json()
        assert value["schema"] == "guala.observation_snapshot.v1"
        assert value["embodiment"]["status"] == "observed"
        assert value["embodiment"]["location"] == {
            "room_id": "W1",
            "revision": 0,
        }
        assert value["embodied_action"] == {
            "status": "idle",
            "world_revision": 0,
        }
        assert value["conversation"]["status"] == "unavailable"
        assert len(value["snapshot_receipt_sha256"]) == 64
    finally:
        app_module._guala = previous
        organism.shutdown()


def test_conversation_ui_uses_one_observed_reply_surface() -> None:
    page = Path(
        "dsf_ai_service/static/gualaloom.html"
    ).read_text(encoding="utf-8")

    assert "/api/v1/gualaloom/observation" in page
    assert "function pollObservation()" in page
    assert "addMsg('she is here','system')" not in page
    assert "setTimeout(pollRoom" not in page
    assert "setTimeout(pollLocation" not in page
    assert "addEmissionMsg(resp,d.emission_id||null,text)" in page
    assert "aria-label','confirm this reply'" in page
    assert "aria-label','correct this reply'" in page
    assert "Embodied State" in page
