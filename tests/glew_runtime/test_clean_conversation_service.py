from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from dsf_ai_service.glew_runtime import conversation as conversation_module
from dsf_ai_service.glew_runtime.conversation import (
    ConversationStatus,
    ConversationTransactionResult,
)
from dsf_ai_service.glew_runtime.conversation_service import (
    STORY_RUNTIME_KEY_HEX_ENV,
    STORY_RUNTIME_KEY_ID_ENV,
    CleanConversationTurn,
    create_clean_conversation_application,
)
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.story_chemistry import (
    PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE,
    StoryChemistryRuntime,
    production_story_chemistry_profile_payload,
)


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ENVIRONMENT = {
    STORY_RUNTIME_KEY_HEX_ENV: "31" * 32,
    STORY_RUNTIME_KEY_ID_ENV: "clean-conversation-service-test-key",
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _result(
    *,
    turn: CleanConversationTurn,
    chemistry: StoryChemistryRuntime,
    visible_text: str,
    status: ConversationStatus = ConversationStatus.EXPRESSION_RELEASED,
) -> ConversationTransactionResult:
    released = status is ConversationStatus.EXPRESSION_RELEASED
    recognition = _digest(f"{turn.task_id}:recognition") if released else None
    commit = _digest(f"{turn.task_id}:commit") if released else None
    initial = _digest(f"{turn.task_id}:initial-event") if released else None
    complete = _digest(f"{turn.task_id}:complete-expression") if released else None
    final = _digest(f"{turn.task_id}:final-settlement") if released else None
    transitions = (
        (_digest(f"{turn.task_id}:transition-1"),)
        if released
        else ()
    )
    reason = (
        "test exact close from injected typed engine"
        if released
        else "test typed no-commit silence"
    )
    payload = conversation_module._conversation_result_payload(
        status=status,
        visible_text=visible_text,
        topology_receipt_sha256=chemistry.manifest.receipt_sha256,
        input_expression_receipt_sha256=turn.receipt_sha256,
        recognition_receipt_sha256=recognition,
        commit_receipt_sha256=commit,
        initial_event_receipt_sha256=initial,
        complete_expression_receipt_sha256=complete,
        final_output_settlement_receipt_sha256=final,
        transition_settlement_receipt_sha256s=transitions,
        reason=reason,
    )
    result = ConversationTransactionResult(
        status=status,
        visible_text=visible_text,
        topology_authority_receipt_sha256=chemistry.manifest.receipt_sha256,
        input_expression_receipt_sha256=turn.receipt_sha256,
        recognition_receipt_sha256=recognition,
        commit_receipt_sha256=commit,
        initial_event_receipt_sha256=initial,
        complete_expression_receipt_sha256=complete,
        final_output_settlement_receipt_sha256=final,
        transition_settlement_receipt_sha256s=transitions,
        reason=reason,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    result.verify()
    return result


class _ExactEngine:
    def __init__(
        self,
        *,
        status: ConversationStatus = ConversationStatus.EXPRESSION_RELEASED,
        delay_seconds: float = 0.0,
    ) -> None:
        self.status = status
        self.delay_seconds = delay_seconds
        self.calls: list[tuple[CleanConversationTurn, StoryChemistryRuntime]] = []
        self._lock = threading.Lock()
        self._active = 0
        self.maximum_active = 0

    def run_clean_conversation(
        self,
        *,
        turn: CleanConversationTurn,
        story_chemistry: StoryChemistryRuntime,
    ) -> ConversationTransactionResult:
        turn.verify()
        assert (
            story_chemistry.manifest.authority_scope
            == PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE
        )
        with self._lock:
            self._active += 1
            self.maximum_active = max(self.maximum_active, self._active)
        try:
            self.calls.append((turn, story_chemistry))
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            visible = (
                f"exact:{turn.text}"
                if self.status is ConversationStatus.EXPRESSION_RELEASED
                else ""
            )
            return _result(
                turn=turn,
                chemistry=story_chemistry,
                visible_text=visible,
                status=self.status,
            )
        finally:
            with self._lock:
                self._active -= 1


class _UntypedEngine:
    def run_clean_conversation(self, *, turn, story_chemistry):
        return {"response": "fabricated fallback is forbidden"}


def _poll_terminal(client: TestClient, poll_url: str) -> dict[str, object]:
    deadline = time.monotonic() + 3.0
    while True:
        response = client.get(poll_url)
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"complete", "error"}:
            return body
        assert time.monotonic() < deadline
        time.sleep(0.005)


def test_module_is_isolated_from_legacy_application_and_exposes_only_contract_routes():
    script = """
import json
import sys
from dsf_ai_service.glew_runtime.conversation_service import app
print(json.dumps({
    "legacy_imported": "dsf_ai_service.app" in sys.modules,
    "paths": sorted(route.path for route in app.routes),
}))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT)

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "legacy_imported": False,
        "paths": [
            "/api/v1/gualaloom",
            "/api/v1/gualaloom/task/{task_id}",
        ],
    }


def test_missing_engine_secret_or_profile_each_returns_explicit_503():
    missing_engine = create_clean_conversation_application(
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
    )
    with TestClient(missing_engine) as client:
        response = client.post(
            "/api/v1/gualaloom",
            json={"text": "hello", "source": "joe"},
        )
        missing_engine_poll = client.get(
            "/api/v1/gualaloom/task/prior-instance-task"
        )
    assert response.status_code == 503
    assert "engine is not injected" in response.json()["error"]["reason"]
    assert response.json()["production_five_sense_chemistry_mounted"] is True
    assert missing_engine_poll.status_code == 503

    missing_secret = create_clean_conversation_application(
        engine=_ExactEngine(),
        environment_provider=lambda: {
            STORY_RUNTIME_KEY_ID_ENV: RUNTIME_ENVIRONMENT[
                STORY_RUNTIME_KEY_ID_ENV
            ]
        },
    )
    with TestClient(missing_secret) as client:
        response = client.post(
            "/api/v1/gualaloom",
            json={"text": "hello", "source": "joe"},
        )
    assert response.status_code == 503
    assert STORY_RUNTIME_KEY_HEX_ENV in response.json()["error"]["reason"]
    assert response.json()["production_five_sense_chemistry_mounted"] is False

    def absent_profile() -> bytes:
        raise FileNotFoundError("production profile resource is absent")

    missing_profile = create_clean_conversation_application(
        engine=_ExactEngine(),
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
        profile_payload_provider=absent_profile,
    )
    with TestClient(missing_profile) as client:
        response = client.post(
            "/api/v1/gualaloom",
            json={"text": "hello", "source": "joe"},
        )
    assert response.status_code == 503
    assert response.json()["error"] == {
        "kind": "FileNotFoundError",
        "reason": "production profile resource is absent",
    }
    assert response.json()["typed_clean_conversation_engine_mounted"] is False


def test_post_202_and_poll_releases_only_the_verified_typed_engine_result():
    engine = _ExactEngine()
    application = create_clean_conversation_application(
        engine=engine,
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
    )

    with TestClient(application) as client:
        accepted = client.post(
            "/api/v1/gualaloom",
            json={"text": "retain the exact experience", "source": "joe"},
        )
        assert accepted.status_code == 202
        admission = accepted.json()
        assert admission["status"] == "accepted"
        assert admission["poll_url"] == (
            f"/api/v1/gualaloom/task/{admission['task_id']}"
        )
        assert admission["retry_after_ms"] == 500
        terminal = _poll_terminal(client, admission["poll_url"])

    assert terminal["status"] == "complete"
    assert terminal["response"] == "exact:retain the exact experience"
    assert terminal["response_source"] == "expression_released"
    assert terminal["motifs"] == 2
    assert terminal["emission_id"] == terminal["conversation_receipt_sha256"]
    assert len(engine.calls) == 1
    turn, chemistry = engine.calls[0]
    assert turn.text == "retain the exact experience"
    assert turn.source == "joe"
    assert turn.receipt_sha256 == admission["turn_receipt_sha256"]
    assert chemistry.manifest.receipt_sha256 == (
        admission["story_chemistry_profile_receipt_sha256"]
    )


def test_typed_silence_remains_empty_and_untyped_engine_output_is_loud_error():
    silent_application = create_clean_conversation_application(
        engine=_ExactEngine(
            status=ConversationStatus.EXPLICIT_NO_COMMIT_SILENCE,
        ),
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
    )
    with TestClient(silent_application) as client:
        accepted = client.post(
            "/api/v1/gualaloom",
            json={"text": "no commit", "source": "joe"},
        )
        silent = _poll_terminal(client, accepted.json()["poll_url"])

    assert silent["status"] == "complete"
    assert silent["response"] == ""
    assert silent["response_source"] == "explicit_no_commit_silence"
    assert silent["emission_id"] is None
    assert "fallback" not in json.dumps(silent).lower()

    untyped_application = create_clean_conversation_application(
        engine=_UntypedEngine(),
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
    )
    with TestClient(untyped_application) as client:
        accepted = client.post(
            "/api/v1/gualaloom",
            json={"text": "reject fabrication", "source": "joe"},
        )
        error = _poll_terminal(client, accepted.json()["poll_url"])

    assert error["status"] == "error"
    assert error["error_kind"] == "ReceiptError"
    assert "untyped result" in error["error"]
    assert "response" not in error


def test_concurrent_admission_has_distinct_tasks_and_atomic_engine_ownership():
    engine = _ExactEngine(delay_seconds=0.025)
    application = create_clean_conversation_application(
        engine=engine,
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
    )

    with TestClient(application) as client:
        admissions = [
            client.post(
                "/api/v1/gualaloom",
                json={"text": f"turn-{index}", "source": "joe"},
            ).json()
            for index in range(6)
        ]
        terminal = [
            _poll_terminal(client, admission["poll_url"])
            for admission in admissions
        ]

    task_ids = [admission["task_id"] for admission in admissions]
    assert len(set(task_ids)) == 6
    assert engine.maximum_active == 1
    assert {value["response"] for value in terminal} == {
        f"exact:turn-{index}" for index in range(6)
    }
    assert len({value["conversation_receipt_sha256"] for value in terminal}) == 6


def test_restart_remounts_identical_profile_and_does_not_claim_old_tasks():
    engine = _ExactEngine()
    profile_reads = {"count": 0}

    def profile_provider() -> bytes:
        profile_reads["count"] += 1
        return production_story_chemistry_profile_payload()

    application = create_clean_conversation_application(
        engine=engine,
        environment_provider=lambda: RUNTIME_ENVIRONMENT,
        profile_payload_provider=profile_provider,
    )

    with TestClient(application) as first_client:
        first = first_client.post(
            "/api/v1/gualaloom",
            json={"text": "before restart", "source": "joe"},
        ).json()
        first_terminal = _poll_terminal(first_client, first["poll_url"])

    with TestClient(application) as restarted_client:
        old_task = restarted_client.get(first["poll_url"])
        second = restarted_client.post(
            "/api/v1/gualaloom",
            json={"text": "after restart", "source": "joe"},
        ).json()
        second_terminal = _poll_terminal(restarted_client, second["poll_url"])

    assert first_terminal["status"] == "complete"
    assert old_task.status_code == 404
    assert old_task.json()["status"] == "not_found"
    assert "prior restarted instance" in old_task.json()["error"]
    assert second_terminal["status"] == "complete"
    assert first["task_id"] != second["task_id"]
    assert profile_reads["count"] == 2
    assert len(engine.calls) == 2
    first_runtime = engine.calls[0][1]
    second_runtime = engine.calls[1][1]
    assert first_runtime.manifest.receipt_sha256 == (
        second_runtime.manifest.receipt_sha256
    )
    assert tuple(state.receipt_sha256 for state in first_runtime.states) == tuple(
        state.receipt_sha256 for state in second_runtime.states
    )
