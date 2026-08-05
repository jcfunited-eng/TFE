"""Character transport cannot enter Guala as a sensory experience."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import dsf_ai_service.app as app_module
import dsf_ai_service.substrate_runner as substrate_runner
from dsf_ai_service.substrate.ring_buffer import InputRing


def test_input_ring_has_no_text_event_kind_or_partial_mutation() -> None:
    ring = InputRing(size=4)

    assert "text_input" not in ring.KINDS
    with pytest.raises(
        ValueError,
        match="unsupported input event kind",
    ):
        ring.publish("text_input", "bridge", text="not physical sound")
    assert ring.pending == 0
    assert ring.pending_transport_bytes == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "kind": "text_input",
            "source": "bridge",
            "data": {"text": "not physical sound"},
        },
    ],
)
def test_runner_refuses_missing_or_text_kind_before_ring_mutation(
    payload,
) -> None:
    previous = substrate_runner._input_ring
    ring = InputRing(size=4)
    substrate_runner._input_ring = ring
    try:
        result = substrate_runner.handle_ring_write(payload)
    finally:
        substrate_runner._input_ring = previous

    assert result == {
        "ok": False,
        "error": "unsupported physical input event",
        "status_code": 422,
    }
    assert ring.pending == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "kind": "text_input",
            "source": "bridge",
            "data": {"text": "not physical sound"},
        },
    ],
)
def test_http_route_refuses_text_before_local_or_remote_transport(
    monkeypatch,
    payload,
) -> None:
    class _ForbiddenRemote:
        async def call(self, *_args, **_kwargs):
            raise AssertionError("retired text reached remote transport")

    monkeypatch.setattr(app_module, "_is_remote", lambda: True)
    monkeypatch.setattr(
        app_module,
        "_get_substrate_client",
        lambda: _ForbiddenRemote(),
    )

    response = TestClient(app_module.app).post(
        "/api/v1/gualaloom/ring/write",
        json=payload,
    )

    assert response.status_code == 410
    assert response.json() == app_module._RETIRED_SCRIPTED_COGNITION


def test_http_route_preserves_explicit_physical_transport(monkeypatch) -> None:
    calls = []

    class _Remote:
        async def call(self, operation, **payload):
            calls.append((operation, payload))
            return {"ok": True, "seq": 9}

    monkeypatch.setattr(app_module, "_is_remote", lambda: True)
    monkeypatch.setattr(app_module, "_get_substrate_client", lambda: _Remote())
    payload = {
        "kind": "sound_window",
        "source": "microphone",
        "data": {"audio_b64": "AA=="},
    }

    response = TestClient(app_module.app).post(
        "/api/v1/gualaloom/ring/write",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "seq": 9}
    assert calls == [("ring_write", payload)]
