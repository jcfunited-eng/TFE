from __future__ import annotations

import asyncio
import base64
import hashlib
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from dsf_ai_service.learned_body_act_trial import (
    LEARNED_BODY_ACT_TRIAL_REQUEST_SCHEMA,
    LearnedBodyActTrialCapacityError,
    LearnedBodyActTrialRegistry,
    LearnedBodyActTrialUnavailableError,
    LearnedBodyActTrialUnknownError,
    canonical_trial_request_sha256,
)
from dsf_ai_service.substrate.embodiment_world import VOCAL_SAMPLE_RATE_HZ
from dsf_ai_service.substrate.experience_grown_vocal_causal_act import (
    ExperienceGrownVocalCausalActReceipt,
)


API_KEY = "async-learned-body-act-test-key"
PCM_S16LE = b"\x01\x00\xfe\xff\x03\x00\xfc\xff"
PCM_SHA256 = hashlib.sha256(PCM_S16LE).hexdigest()


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _emitted_result() -> dict[str, object]:
    values = {
        name: _sha(name)
        for name in ExperienceGrownVocalCausalActReceipt.__dataclass_fields__
    }
    values["emitted_pressure_sha256"] = PCM_SHA256
    values["learned_pressure_sha256"] = PCM_SHA256
    receipt = ExperienceGrownVocalCausalActReceipt(**values)
    receipt_payload = {
        **receipt.payload(),
        "authority_hmac_sha256": receipt.authority_hmac_sha256,
        "authority_receipt_sha256": receipt.authority_receipt_sha256,
    }
    return {
        "binding_created": False,
        "outcome_settlement_receipt_sha256": _sha("outcome"),
        "world_revision_after": 18,
        "world_revision_before": 17,
        "vocal_causal_act": {
            "act_receipt": receipt_payload,
            "additional_world_mutation": True,
            "pcm_s16le": PCM_S16LE,
            "pcm_sha256": PCM_SHA256,
            "program_custody_receipt_sha256": (
                receipt_payload["program_custody_receipt_sha256"]
            ),
            "reason": "exact_experience_grown_relation",
            "retained_pcm_bytes": 0,
            "sample_count": len(PCM_S16LE) // 2,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": (
                "guala.embodied_action_experience."
                "vocal_causal_act.v1"
            ),
            "selection_authority_hmac_sha256": _sha("selection-hmac"),
            "selection_authority_receipt_sha256": _sha(
                "selection-receipt"
            ),
            "state": "emitted",
        },
    }


def _request() -> dict[str, object]:
    return {
        "duration_microseconds": 100_000,
        "nonce": "async-learned-body-act-0001",
        "operation": "move",
        "port_id": "W1-self-body-port",
        "target_pose": {
            "heading_millidegrees": 0,
            "position": {
                "x_mm": 1_200,
                "y_mm": 1_400,
                "z_mm": 0,
            },
        },
        "tutor_id": "joe",
    }


def _response_json(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


class _Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        return self.value


def test_registry_is_bounded_expires_unstarted_and_fails_closed_on_restart(
) -> None:
    clock = _Clock()
    tokens = iter(("1" * 64, "2" * 64))
    registry = LearnedBodyActTrialRegistry(
        max_operations=1,
        max_tombstones=1,
        ttl_seconds=5,
        monotonic_now=clock,
        token_factory=lambda: next(tokens),
    )
    digest = _sha("request")
    first = registry.create(digest)
    with pytest.raises(LearnedBodyActTrialCapacityError):
        registry.create(digest)

    clock.value = 15.0
    assert registry.mark_running(first) is False
    with pytest.raises(LearnedBodyActTrialUnavailableError):
        registry.poll(first)
    second = registry.create(digest)
    assert second == "2" * 64
    restarted = LearnedBodyActTrialRegistry()
    with pytest.raises(LearnedBodyActTrialUnknownError):
        restarted.poll(second)


def test_running_custody_survives_ttl_until_terminal_pickup() -> None:
    clock = _Clock()
    registry = LearnedBodyActTrialRegistry(
        max_operations=1,
        max_tombstones=1,
        ttl_seconds=5,
        monotonic_now=clock,
        token_factory=lambda: "3" * 64,
    )
    operation_id = registry.create(_sha("slow-request"))
    assert registry.mark_running(operation_id) is True

    clock.value = 100.0
    status_code, running = registry.poll(operation_id)
    assert status_code == 202
    assert running["state"] == "running"
    assert registry.complete(operation_id, {"physical": "terminal"}) is True

    clock.value = 104.0
    status_code, completed = registry.poll(operation_id)
    assert status_code == 200
    assert completed["result"] == {"physical": "terminal"}
    with pytest.raises(LearnedBodyActTrialUnavailableError):
        registry.poll(operation_id)


@pytest.mark.parametrize(
    ("result", "failure_code"),
    (
        ({"unbounded": "payload"}, "response_bound_exceeded"),
        ({"raw": b"\x00\x01"}, "result_not_json"),
    ),
)
def test_registry_fails_closed_on_nontransport_or_oversize_result(
    result: dict[str, object],
    failure_code: str,
) -> None:
    registry = LearnedBodyActTrialRegistry(
        max_result_bytes=2,
        token_factory=lambda: "4" * 64,
    )
    operation_id = registry.create(_sha("bounded-request"))
    registry.mark_running(operation_id)
    registry.complete(operation_id, result)

    status_code, failure = registry.poll(operation_id)
    assert status_code == 409
    assert failure["state"] == "failed"
    assert failure["failure_code"] == failure_code
    with pytest.raises(LearnedBodyActTrialUnavailableError):
        registry.poll(operation_id)


def test_request_digest_is_exact_and_content_neutral() -> None:
    payload = {
        "schema": LEARNED_BODY_ACT_TRIAL_REQUEST_SCHEMA,
        "tutor_id": "joe",
        "nonce": "physical-request",
        "port_id": "W1-self-body-port",
        "command_payload_base64": "AAE=",
    }
    first = canonical_trial_request_sha256(payload)
    second = canonical_trial_request_sha256(dict(reversed(tuple(
        payload.items()
    ))))
    assert first == second
    assert first != canonical_trial_request_sha256({
        **payload,
        "command_payload_base64": "AAI=",
    })
    assert not {
        "word",
        "label",
        "expected_word",
        "imitation",
        "intelligibility",
    }.intersection(payload)


def test_start_returns_before_execution_and_terminal_poll_is_one_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import dsf_ai_service.app as app_module

    class _Lifecycle:
        def __init__(self) -> None:
            self.active = 0

        def admit_mutation(self) -> bool:
            self.active += 1
            return True

        def finish_mutation(self) -> None:
            self.active -= 1

    lifecycle = _Lifecycle()
    registry = LearnedBodyActTrialRegistry(
        token_factory=lambda: "5" * 64,
    )
    started = asyncio.Event()
    release = asyncio.Event()
    transported = app_module._embodied_action_transport(
        _emitted_result()
    )

    async def _blocked_execution(_req, *, command_payload):
        assert isinstance(command_payload, bytes)
        started.set()
        await release.wait()
        return transported

    monkeypatch.setattr(
        app_module,
        "_learned_body_act_trial_operations",
        registry,
    )
    monkeypatch.setattr(app_module, "_deployment_lifecycle", lifecycle)
    monkeypatch.setattr(app_module, "_mutating_background_tasks", set())
    monkeypatch.setattr(
        app_module,
        "_execute_embodied_action_experience",
        _blocked_execution,
    )
    request = app_module.EmbodiedActionExperienceRequest(**_request())

    async def _scenario() -> None:
        accepted_response = await asyncio.wait_for(
            app_module.start_learned_body_act_trial(request),
            timeout=0.5,
        )
        accepted = _response_json(accepted_response)
        assert accepted_response.status_code == 202
        assert accepted["state"] == "accepted"
        assert accepted["operation_id"] == "5" * 64
        assert len(accepted["request_sha256"]) == 64
        await asyncio.wait_for(started.wait(), timeout=0.5)
        assert lifecycle.active == 1

        pending_response = await app_module.poll_learned_body_act_trial(
            accepted["operation_id"]
        )
        assert pending_response.status_code == 202
        assert _response_json(pending_response)["state"] == "running"

        release.set()
        tasks = tuple(app_module._mutating_background_tasks)
        await asyncio.gather(*tasks)
        assert lifecycle.active == 0
        terminal_response = await app_module.poll_learned_body_act_trial(
            accepted["operation_id"]
        )
        assert terminal_response.status_code == 200
        terminal = _response_json(terminal_response)
        assert terminal["result"] == transported
        assert "vocal_causal_act" not in terminal["result"]
        encoded = base64.b64encode(PCM_S16LE).decode("ascii")
        assert json.dumps(terminal, sort_keys=True).count(encoded) == 1
        assert "sight_articulatory_playback" not in json.dumps(terminal)
        with pytest.raises(HTTPException) as captured:
            await app_module.poll_learned_body_act_trial(
                accepted["operation_id"]
            )
        assert captured.value.status_code == 410

    asyncio.run(_scenario())


@pytest.mark.parametrize(
    "forbidden_field",
    (
        "word",
        "label",
        "expected_word",
        "imitation",
        "intelligibility",
        "pcm_s16le_base64",
    ),
)
def test_both_trial_routes_require_api_key_and_start_rejects_semantic_authority(
    monkeypatch: pytest.MonkeyPatch,
    forbidden_field: str,
) -> None:
    import dsf_ai_service.app as app_module

    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", API_KEY)
    client = TestClient(app_module.app)
    unauthenticated_start = client.post(
        "/api/v1/embodiment/learned-body-act-trial",
        json=_request(),
    )
    unauthenticated_poll = client.get(
        "/api/v1/embodiment/learned-body-act-trial/" + ("9" * 64)
    )
    assert unauthenticated_start.status_code == 401
    assert unauthenticated_poll.status_code == 401

    rejected = client.post(
        "/api/v1/embodiment/learned-body-act-trial",
        headers={"X-API-Key": API_KEY},
        json={**_request(), forbidden_field: "forbidden"},
    )
    assert rejected.status_code == 422
