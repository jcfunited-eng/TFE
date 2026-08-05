"""Production boundary for the deleted typed-conversation task adapter."""

from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace

import pytest

import dsf_ai_service.app as appmod


@pytest.mark.parametrize(
    "message_fields",
    [
        {"text": "are you there", "source": "joe"},
        {"text": "hello", "command": "/listen", "source": "wc"},
        {"text": "", "command": "/converse", "source": "joe"},
        {"text": "", "command": "/mail", "source": "joe"},
    ],
)
def test_text_intake_is_retired_without_task_or_engine_mutation(
    monkeypatch,
    message_fields,
):
    """The typed-chat intake stays absent, or refuses without mutation."""
    scheduled = []
    if not hasattr(appmod, "gualaloom_chat"):
        # The legacy typed-chat surface is fully deleted: the route must be
        # absent or refused, and the request must schedule no mutation.
        monkeypatch.setattr(
            appmod,
            "_schedule_mutating_background",
            lambda *_args, **_kwargs: scheduled.append(True),
            raising=False,
        )
        from fastapi.testclient import TestClient

        response = TestClient(appmod.app).post(
            "/api/v1/gualaloom", json=message_fields
        )
        assert response.status_code in (404, 410)
        assert scheduled == []
        return
    monkeypatch.setattr(
        appmod,
        "_schedule_mutating_background",
        lambda *_args, **_kwargs: scheduled.append(True),
    )
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace(tick=7))

    response = asyncio.run(
        appmod.gualaloom_chat(appmod.GLMessage(**message_fields))
    )

    assert response.status_code == 410
    body = json.loads(response.body)
    assert body["state"] == "retired_wrong_architecture"
    assert "exact_full_field_q" in body["replacement"]
    assert scheduled == []


def test_legacy_converse_task_poll_route_is_retired():
    """The converse-task poll surface stays absent, or refuses with 410."""
    if not hasattr(appmod, "get_converse_task"):
        return
    response = asyncio.run(appmod.get_converse_task("historical-task"))

    assert response.status_code == 410
    assert json.loads(response.body) == appmod._RETIRED_SCRIPTED_COGNITION


def test_text_converse_workers_and_priority_gate_are_deleted():
    source = inspect.getsource(appmod)

    for retired_name in (
        "_converse_tasks",
        "def _run_converse(",
        "def _run_glew_converse_turn(",
        "def _converse_turn_begin(",
        "def _converse_turn_end(",
        "def _converse_turn_in_flight(",
        "def _converse_admission_busy(",
        "_GLEW_ENGINE_ENABLED",
    ):
        assert retired_name not in source
