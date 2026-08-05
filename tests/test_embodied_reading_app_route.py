"""The embodied-reading lesson app surface is permanently retired.

The legacy Python reading-lesson cognition routes were removed with the
native-organism cutover.  This guard keeps the surface from being
resurrected: the routes must be absent, or must refuse with the permanent
retired-cognition contract, and must never schedule cognition work.
"""

from __future__ import annotations

import dsf_ai_service.app as appmod
from dsf_ai_service.embodied_reading_http_contract import ROUTE_PATH


def test_reading_lesson_routes_are_absent_or_permanently_retired(
    monkeypatch,
) -> None:
    from fastapi.testclient import TestClient

    scheduled = []
    monkeypatch.setattr(
        appmod,
        "_schedule_mutating_background",
        lambda *_args, **_kwargs: scheduled.append(True),
        raising=False,
    )
    monkeypatch.setattr(appmod, "_GUALALOOM_API_KEY", "reading-guard-key")
    client = TestClient(appmod.app)

    start = client.post(
        ROUTE_PATH,
        headers={"X-API-Key": "reading-guard-key"},
        json={},
    )
    poll = client.get(
        ROUTE_PATH + "/" + "0" * 64,
        headers={"X-API-Key": "reading-guard-key"},
    )
    for response in (start, poll):
        assert response.status_code in (404, 410)
        if response.status_code == 410:
            body = response.json()
            assert body["status"] == "unavailable"
            assert body["reason"] == "legacy_python_cognition_retired"
            assert body["schema"] == (
                "guala.retired_cognition.unavailable.v1"
            )
    assert scheduled == []


def test_no_reading_operation_registry_remains_mounted() -> None:
    assert not hasattr(appmod, "_embodied_reading_operations")
