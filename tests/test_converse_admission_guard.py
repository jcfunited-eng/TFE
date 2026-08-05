"""Production boundary for the deleted typed-conversation task adapter."""

from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace

import pytest

import dsf_ai_service.app as appmod


@pytest.mark.parametrize(
    "message",
    [
        appmod.GLMessage(text="are you there", source="joe"),
        appmod.GLMessage(
            text="hello", command="/listen", source="wc"
        ),
        appmod.GLMessage(
            text="", command="/converse", source="joe"
        ),
        appmod.GLMessage(
            text="", command="/mail", source="joe"
        ),
    ],
)
def test_text_intake_is_retired_without_task_or_engine_mutation(
    monkeypatch,
    message,
):
    scheduled = []
    monkeypatch.setattr(
        appmod,
        "_schedule_mutating_background",
        lambda *_args, **_kwargs: scheduled.append(True),
    )
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace(tick=7))

    response = asyncio.run(appmod.gualaloom_chat(message))

    assert response.status_code == 410
    body = json.loads(response.body)
    assert body["state"] == "retired_wrong_architecture"
    assert "exact_full_field_q" in body["replacement"]
    assert scheduled == []


def test_legacy_converse_task_poll_route_is_retired():
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
