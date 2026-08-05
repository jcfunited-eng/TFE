from __future__ import annotations

import asyncio
import inspect
import json

import pytest
from starlette.requests import Request

import dsf_ai_service.app as appmod
from dsf_ai_service.embodied_reading_operation import (
    EMBODIED_READING_OPERATION_ACCEPTED_SCHEMA,
    EmbodiedReadingOperationRegistry,
)
from dsf_ai_service.physical_surface_lesson_http_contract import (
    PLAN_RESPONSE_SCHEMA,
    ROUTE_PATH,
    STEP_RESPONSE_SCHEMA,
)
from tests.test_physical_surface_lesson_http_contract import (
    _plan_payload,
    _step_payload,
)


def _request(payload: dict[str, object]) -> Request:
    body = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": ROUTE_PATH,
            "headers": [
                (b"content-length", str(len(body)).encode("ascii")),
            ],
            "client": ("127.0.0.1", 1),
            "server": ("test", 80),
            "scheme": "http",
            "query_string": b"",
        },
        receive,
    )


def _json(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


def test_route_is_authenticated_bounded_and_has_no_raw_lesson_bypass() -> None:
    start = inspect.getsource(appmod.physical_surface_lesson)
    poll = inspect.getsource(appmod.poll_physical_surface_lesson)
    middleware = inspect.getsource(appmod.bounded_live_sensory_ingress)

    assert "dependencies=[Depends(_api_key_dep)]" in start
    assert "issue_physical_surface_tutoring_plan" in start
    assert "durably_experience_physical_surface_tutoring_step" in start
    assert "durably_experience_physical_surface_lesson(" not in start
    assert "_schedule_mutating_background" in start
    assert "dependencies=[Depends(_api_key_dep)]" in poll
    assert "_physical_surface_lesson_operations.poll" in poll
    assert "_PHYSICAL_SURFACE_LESSON_REQUEST_MAX_BYTES" in middleware


def test_start_poll_and_consume_plan_then_step_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    tokens = iter(("8" * 64, "9" * 64))
    registry = EmbodiedReadingOperationRegistry(
        token_factory=lambda: next(tokens),
    )

    class _Guala:
        def issue_physical_surface_tutoring_plan(self, **arguments):
            calls.append(("plan", arguments))
            return {"authority_receipt_sha256": "a" * 64}

        def durably_experience_physical_surface_tutoring_step(
            self,
            **arguments,
        ):
            calls.append(("step", arguments))
            return {
                "retained_pcm_bytes": 0,
                "schema": "guala.physical_surface_tutoring.step_result.v1",
            }

    async def _executor(function, *arguments):
        return function(*arguments)

    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_guala", _Guala())
    monkeypatch.setattr(
        appmod,
        "_physical_surface_lesson_operations",
        registry,
    )
    monkeypatch.setattr(appmod, "_mutating_background_tasks", set())
    monkeypatch.setattr(appmod, "_run_lifecycle_executor", _executor)

    async def _complete(payload):
        accepted_response = await appmod.physical_surface_lesson(
            _request(payload)
        )
        accepted = _json(accepted_response)
        assert accepted_response.status_code == 202
        assert accepted["schema"] == (
            EMBODIED_READING_OPERATION_ACCEPTED_SCHEMA
        )
        await asyncio.gather(*tuple(appmod._mutating_background_tasks))
        terminal_response = await appmod.poll_physical_surface_lesson(
            accepted["operation_id"]
        )
        return _json(terminal_response)["result"]

    async def _scenario() -> None:
        plan = await _complete(_plan_payload())
        assert plan["schema"] == PLAN_RESPONSE_SCHEMA
        assert plan["operation"] == "plan"
        step = await _complete(_step_payload())
        assert step["schema"] == STEP_RESPONSE_SCHEMA
        assert step["operation"] == "step"
        assert step["retained_pcm_bytes"] == 0
        assert not any(step["claims"].values())
        assert calls[0][0] == "plan"
        assert calls[0][1]["state_dir"] == appmod.STATE_DIR
        assert calls[1][0] == "step"
        assert calls[1][1]["step_index"] == 0
        assert "target_object_id" not in calls[1][1]
        assert "source_time_start_ns" not in calls[1][1]

    asyncio.run(_scenario())
