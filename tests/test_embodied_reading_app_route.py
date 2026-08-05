from __future__ import annotations

import asyncio
import inspect
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import dsf_ai_service.app as appmod
from dsf_ai_service.embodied_reading_http_contract import (
    RESPONSE_SCHEMA,
    ROUTE_PATH,
)
from dsf_ai_service.embodied_reading_operation import (
    EMBODIED_READING_OPERATION_ACCEPTED_SCHEMA,
    EmbodiedReadingOperationRegistry,
)
from tests.test_embodied_reading_http_contract import WAV, _payload


def _request(payload: dict[str, object]) -> Request:
    body = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
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

    return Request({
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
    }, receive)


def _response_json(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


class _Lifecycle:
    def __init__(self) -> None:
        self.active = 0

    def admit_mutation(self) -> bool:
        self.active += 1
        return True

    def finish_mutation(self) -> None:
        self.active -= 1


def test_routes_are_dedicated_authenticated_and_memory_bounded() -> None:
    start_source = inspect.getsource(appmod.embodied_reading_lesson)
    poll_source = inspect.getsource(appmod.poll_embodied_reading_lesson)
    middleware = inspect.getsource(appmod.bounded_live_sensory_ingress)

    assert "_EMBODIED_READING_ROUTE_PATH" in start_source
    assert "dependencies=[Depends(_api_key_dep)]" in start_source
    assert "_schedule_mutating_background" in start_source
    assert "durably_experience_embodied_reading_http_request" in start_source
    assert "sound_frame" not in start_source
    assert "_run_lifecycle_executor" in start_source
    assert "dependencies=[Depends(_api_key_dep)]" in poll_source
    assert "_embodied_reading_operations.poll" in poll_source
    assert "_EMBODIED_READING_ROUTE_PATH" in middleware
    assert "_EMBODIED_READING_REQUEST_MAX_BYTES" in middleware


def test_start_returns_before_lesson_and_terminal_poll_consumes_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []
    started = asyncio.Event()
    release = asyncio.Event()
    lifecycle = _Lifecycle()
    registry = EmbodiedReadingOperationRegistry(
        token_factory=lambda: "5" * 64,
    )

    class _Guala:
        def durably_experience_embodied_reading_http_request(
            self,
            *,
            request,
            state_dir,
        ):
            calls.append((request, state_dir))
            return {
                "boundary": {
                    "record_count": 1,
                    "retained_pcm_bytes": 0,
                },
                "lesson": {
                    "lesson_count": 1,
                    "retained_pcm_bytes": 0,
                },
            }

    async def _blocked_executor(function, *args):
        started.set()
        await release.wait()
        return function(*args)

    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_guala", _Guala())
    monkeypatch.setattr(
        appmod,
        "_embodied_reading_operations",
        registry,
    )
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_mutating_background_tasks", set())
    monkeypatch.setattr(
        appmod,
        "_run_lifecycle_executor",
        _blocked_executor,
    )

    async def _scenario() -> None:
        accepted_response = await asyncio.wait_for(
            appmod.embodied_reading_lesson(_request(_payload())),
            timeout=0.5,
        )
        accepted = _response_json(accepted_response)
        assert accepted_response.status_code == 202
        assert (
            accepted["schema"]
            == EMBODIED_READING_OPERATION_ACCEPTED_SCHEMA
        )
        assert accepted["state"] == "accepted"
        assert accepted["operation_id"] == "5" * 64
        await asyncio.wait_for(started.wait(), timeout=0.5)
        assert lifecycle.active == 1

        pending_response = await appmod.poll_embodied_reading_lesson(
            accepted["operation_id"]
        )
        assert pending_response.status_code == 202
        assert _response_json(pending_response)["state"] == "running"

        release.set()
        await asyncio.gather(*tuple(appmod._mutating_background_tasks))
        assert lifecycle.active == 0
        assert len(calls) == 1
        assert calls[0][1] == appmod.STATE_DIR
        retained_result = registry._operations[
            accepted["operation_id"]
        ].result_json
        assert retained_result is not None
        assert WAV not in retained_result

        terminal_response = await appmod.poll_embodied_reading_lesson(
            accepted["operation_id"]
        )
        assert terminal_response.status_code == 200
        terminal = _response_json(terminal_response)
        result = terminal["result"]
        assert result["schema"] == RESPONSE_SCHEMA
        assert result["retained_pcm_bytes"] == 0
        assert not any(result["claims"].values())
        assert "pcm_s16le" not in repr(result)
        with pytest.raises(HTTPException) as consumed:
            await appmod.poll_embodied_reading_lesson(
                accepted["operation_id"]
            )
        assert consumed.value.status_code == 410

    asyncio.run(_scenario())


def test_start_rejects_meaning_remote_and_capacity_without_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace())
    supplied = _payload()
    supplied["meaning"] = "letter B"
    with pytest.raises(HTTPException) as invalid:
        asyncio.run(appmod.embodied_reading_lesson(_request(supplied)))
    assert invalid.value.status_code == 400

    full = EmbodiedReadingOperationRegistry(
        max_operations=1,
        token_factory=lambda: "6" * 64,
    )
    full.create("a" * 64)
    monkeypatch.setattr(appmod, "_embodied_reading_operations", full)
    with pytest.raises(HTTPException) as capacity:
        asyncio.run(appmod.embodied_reading_lesson(_request(_payload())))
    assert capacity.value.status_code == 429

    monkeypatch.setattr(appmod, "_is_remote", lambda: True)
    with pytest.raises(HTTPException) as remote_start:
        asyncio.run(appmod.embodied_reading_lesson(_request(_payload())))
    assert remote_start.value.status_code == 501
    with pytest.raises(HTTPException) as remote_poll:
        asyncio.run(appmod.poll_embodied_reading_lesson("7" * 64))
    assert remote_poll.value.status_code == 501
    assert "authenticated physical lesson transport" in (
        remote_start.value.detail
    )


def test_background_rejection_returns_only_bounded_failure_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = EmbodiedReadingOperationRegistry(
        token_factory=lambda: "8" * 64,
    )
    lifecycle = _Lifecycle()

    async def _rejected_executor(_function, *_args):
        raise ValueError("private physical rejection detail")

    monkeypatch.setattr(appmod, "_is_remote", lambda: False)
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace())
    monkeypatch.setattr(
        appmod,
        "_embodied_reading_operations",
        registry,
    )
    monkeypatch.setattr(appmod, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(appmod, "_mutating_background_tasks", set())
    monkeypatch.setattr(
        appmod,
        "_run_lifecycle_executor",
        _rejected_executor,
    )

    async def _scenario() -> None:
        accepted_response = await appmod.embodied_reading_lesson(
            _request(_payload())
        )
        operation_id = _response_json(accepted_response)["operation_id"]
        await asyncio.gather(*tuple(appmod._mutating_background_tasks))
        failure_response = await appmod.poll_embodied_reading_lesson(
            operation_id
        )
        assert failure_response.status_code == 409
        failure = _response_json(failure_response)
        assert failure["failure_code"] == "lesson_rejected"
        assert "private physical rejection detail" not in repr(failure)
        assert WAV not in repr(registry).encode("utf-8")

    asyncio.run(_scenario())
