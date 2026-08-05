"""Proof that the isolated, unowned V7 session surface cannot grow state."""

import asyncio
import json
from pathlib import Path

import dsf_ai_service.app as appmod
import dsf_ai_service.substrate_runner as runner


def _decode_response(response):
    return json.loads(response.body.decode("utf-8"))


def test_every_app_v7_route_returns_the_same_explicit_retirement():
    """Every V7 session surface stays absent, or refuses with 410."""
    from fastapi.testclient import TestClient

    handler_names = (
        "v7_converse",
        "v7_feedback",
        "v7_state",
        "v7_quiet",
        "v7_save",
        "v7_persistence",
    )
    present = [name for name in handler_names if hasattr(appmod, name)]
    if not present:
        # Fully deleted: the HTTP routes must be absent or refused.
        client = TestClient(appmod.app)
        for path in (
            "/api/v1/v7/state/session",
            "/api/v1/v7/save/session",
            "/api/v1/v7/persistence/session",
        ):
            assert client.get(path).status_code in (404, 410)
        for path in ("/api/v1/v7/converse", "/api/v1/v7/feedback"):
            assert client.post(path, json={}).status_code in (404, 410)
        return
    assert present == list(handler_names)
    calls = (
        appmod.v7_converse(
            appmod.V7ConverseRequest(text="text", session_id="session")),
        appmod.v7_feedback(
            appmod.V7FeedbackRequest(session_id="session", correct=True)),
        appmod.v7_state("session"),
        appmod.v7_quiet("session", 10),
        appmod.v7_save("session"),
        appmod.v7_persistence("session"),
    )
    for call in calls:
        response = asyncio.run(call)
        assert response.status_code == 410
        assert _decode_response(response) == appmod._V7_RETIREMENT_STATUS


def test_every_substrate_v7_operation_refuses_without_session_growth():
    for operation in (
        "v7_converse",
        "v7_feedback",
        "v7_state",
        "v7_quiet",
        "v7_save",
    ):
        assert operation not in runner.OP_HANDLERS
        assert not hasattr(runner, f"handle_{operation}")


def test_isolated_v7_engine_implementation_is_deleted():
    assert not (
        Path(__file__).resolve().parents[1]
        / "dsf_ai_service"
        / "substrate"
        / "v7_engine.py"
    ).exists()


def test_browser_has_no_v7_state_poll_or_legacy_status_surface():
    source = (
        Path(__file__).resolve().parents[1]
        / "dsf_ai_service"
        / "static"
        / "gualaloom.html"
    ).read_text(encoding="utf-8")
    assert "/v7/state" not in source
    assert "pollV7State" not in source
    assert "sp-pools" not in source
    assert "sp-nmda" not in source
