from __future__ import annotations

import base64
import copy
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.experience_grown_vocal_causal_act import (
    ExperienceGrownVocalCausalActReceipt,
)


API_KEY = "learned-body-act-transport-test-key"
PCM_S16LE = b"\x01\x00\xfe\xff\x03\x00\xfc\xff"
PCM_SHA256 = hashlib.sha256(PCM_S16LE).hexdigest()


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _receipt() -> dict[str, object]:
    values = {
        name: _sha(name)
        for name in (
            ExperienceGrownVocalCausalActReceipt.__dataclass_fields__
        )
    }
    values["emitted_pressure_sha256"] = PCM_SHA256
    values["learned_pressure_sha256"] = PCM_SHA256
    receipt = ExperienceGrownVocalCausalActReceipt(**values)
    return {
        **receipt.payload(),
        "authority_hmac_sha256": receipt.authority_hmac_sha256,
        "authority_receipt_sha256": receipt.authority_receipt_sha256,
    }


def _emitted_result(
    pcm_s16le: bytes = PCM_S16LE,
) -> dict[str, object]:
    receipt = _receipt()
    return {
        "binding_created": False,
        "outcome_settlement_receipt_sha256": _sha("outcome"),
        "world_revision_after": 18,
        "world_revision_before": 17,
        "vocal_causal_act": {
            "act_receipt": receipt,
            "additional_world_mutation": True,
            "pcm_s16le": pcm_s16le,
            "pcm_sha256": PCM_SHA256,
            "program_custody_receipt_sha256": (
                receipt["program_custody_receipt_sha256"]
            ),
            "reason": "exact_experience_grown_relation",
            "retained_pcm_bytes": 0,
            "sample_count": len(pcm_s16le) // 2,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": (
                "guala.embodied_action_experience."
                "vocal_causal_act.v1"
            ),
            "selection_authority_hmac_sha256": _sha(
                "selection-hmac"
            ),
            "selection_authority_receipt_sha256": _sha(
                "selection-receipt"
            ),
            "state": "emitted",
        },
    }


def _silent_result() -> dict[str, object]:
    return {
        "binding_created": False,
        "outcome_settlement_receipt_sha256": _sha("silent-outcome"),
        "world_revision_after": 22,
        "world_revision_before": 21,
        "vocal_causal_act": {
            "act_receipt": None,
            "additional_world_mutation": False,
            "pcm_s16le": None,
            "pcm_sha256": None,
            "program_custody_receipt_sha256": None,
            "reason": "no_current_experience_grown_relation",
            "retained_pcm_bytes": 0,
            "sample_count": 0,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": (
                "guala.embodied_action_experience."
                "vocal_causal_act.v1"
            ),
            "selection_authority_hmac_sha256": _sha(
                "silent-selection-hmac"
            ),
            "selection_authority_receipt_sha256": _sha(
                "silent-selection-receipt"
            ),
            "state": "silent",
        },
    }


def _contains_bytes(value: object) -> bool:
    if isinstance(value, bytes):
        return True
    if isinstance(value, dict):
        return any(
            _contains_bytes(key) or _contains_bytes(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_bytes(item) for item in value)
    return False


def _converters():
    import dsf_ai_service.app as app_module
    import dsf_ai_service.substrate_runner as runner

    return (
        app_module._embodied_action_transport,
        runner._embodied_action_transport,
    )


def test_emitted_pcm_is_exposed_once_and_local_runner_are_byte_equivalent(
) -> None:
    original = _emitted_result()
    retained_input = copy.deepcopy(original)
    app_convert, runner_convert = _converters()

    local = app_convert(original)
    remote = runner_convert(original)

    assert original == retained_input
    assert local == remote
    assert "vocal_causal_act" not in local
    assert _contains_bytes(local) is False
    learned = local["learned_body_act"]
    assert learned["schema"] == (
        "guala.embodied_action_experience."
        "learned_body_act_transport.v1"
    )
    assert "consequence_evoked" not in learned["schema"]
    assert learned["state"] == "emitted"
    assert learned["sample_rate_hz"] == 16_000
    assert learned["sample_count"] == len(PCM_S16LE) // 2
    assert learned["pcm_sha256"] == PCM_SHA256
    encoded = base64.b64encode(PCM_S16LE).decode("ascii")
    assert learned["pcm_s16le_base64"] == encoded
    assert json.dumps(local, sort_keys=True).count(encoded) == 1
    assert base64.b64decode(
        learned["pcm_s16le_base64"],
        validate=True,
    ) == PCM_S16LE
    assert app_convert(remote) == remote
    assert runner_convert(local) == local


def test_signed_silent_has_no_pcm_surface_and_no_additional_mutation(
) -> None:
    original = _silent_result()
    retained_input = copy.deepcopy(original)
    app_convert, runner_convert = _converters()

    local = app_convert(original)
    remote = runner_convert(original)

    assert original == retained_input
    assert local == remote
    assert "vocal_causal_act" not in local
    learned = local["learned_body_act"]
    assert learned["state"] == "signed_silent"
    assert learned["additional_world_mutation"] is False
    assert not any("pcm" in name for name in learned)
    assert "act_receipt" not in learned
    assert "program_custody_receipt_sha256" not in learned
    assert _contains_bytes(local) is False


@pytest.mark.parametrize(
    "mutation",
    (
        "sample_rate",
        "sample_count",
        "pcm_sha",
        "receipt_missing",
        "receipt_pressure",
        "world_receipt",
        "additional_mutation",
        "retained_pcm",
    ),
)
def test_emitted_tamper_fails_closed_identically(
    mutation: str,
) -> None:
    result = _emitted_result()
    vocal = result["vocal_causal_act"]
    receipt = vocal["act_receipt"]
    if mutation == "sample_rate":
        vocal["sample_rate_hz"] = 8_000
    elif mutation == "sample_count":
        vocal["sample_count"] += 1
    elif mutation == "pcm_sha":
        vocal["pcm_sha256"] = _sha("changed-pcm")
    elif mutation == "receipt_missing":
        del receipt["emission_receipt_sha256"]
    elif mutation == "receipt_pressure":
        receipt["emitted_pressure_sha256"] = _sha("changed-pressure")
    elif mutation == "world_receipt":
        receipt["world_after_receipt_sha256"] = (
            receipt["world_before_receipt_sha256"]
        )
    elif mutation == "additional_mutation":
        vocal["additional_world_mutation"] = False
    else:
        vocal["retained_pcm_bytes"] = 1

    for convert in _converters():
        with pytest.raises(ValueError):
            convert(copy.deepcopy(result))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("pcm_s16le", b"\x00\x00"),
        ("pcm_sha256", _sha("silent-pcm")),
        ("program_custody_receipt_sha256", _sha("silent-program")),
        ("act_receipt", {}),
        ("sample_count", 1),
        ("sample_rate_hz", 8_000),
        ("retained_pcm_bytes", 1),
        ("additional_world_mutation", True),
    ),
)
def test_signed_silent_tamper_fails_closed_identically(
    field: str,
    value: object,
) -> None:
    result = _silent_result()
    result["vocal_causal_act"][field] = value

    for convert in _converters():
        with pytest.raises(ValueError):
            convert(copy.deepcopy(result))


def test_oversize_pcm_fails_before_base64_transport() -> None:
    pcm = b"\x00\x00" * (MAX_VOCAL_SAMPLE_COUNT + 1)
    result = _emitted_result(pcm)

    for convert in _converters():
        with pytest.raises(ValueError, match="transport changed"):
            convert(copy.deepcopy(result))


def _action_request() -> dict[str, object]:
    return {
        "duration_microseconds": 100_000,
        "nonce": "learned-body-act-http-0001",
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


@pytest.mark.parametrize(
    "forbidden_field",
    (
        "cue",
        "pcm_s16le_base64",
        "program_custody",
        "program_id",
        "vocal_coordinates",
    ),
)
def test_action_request_accepts_no_vocal_program_or_media_authority(
    monkeypatch: pytest.MonkeyPatch,
    forbidden_field: str,
) -> None:
    import dsf_ai_service.app as app_module

    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", API_KEY)
    request = {
        **_action_request(),
        forbidden_field: "forbidden",
    }
    response = TestClient(app_module.app).post(
        "/api/v1/embodiment/action-experience",
        headers={"X-API-Key": API_KEY},
        json=request,
    )
    assert response.status_code == 422


def test_local_remote_and_runner_action_responses_are_exactly_equivalent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import dsf_ai_service.app as app_module
    import dsf_ai_service.substrate_runner as runner

    class _Owner:
        def durably_experience_embodied_action(self, **_values):
            return copy.deepcopy(_emitted_result())

    owner = _Owner()
    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", API_KEY)
    monkeypatch.setattr(app_module, "_guala", owner)
    monkeypatch.setattr(app_module, "STATE_DIR", "/exact-state")
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    client = TestClient(app_module.app)
    unauthenticated = client.post(
        "/api/v1/embodiment/action-experience",
        json=_action_request(),
    )
    assert unauthenticated.status_code == 401
    local = client.post(
        "/api/v1/embodiment/action-experience",
        headers={"X-API-Key": API_KEY},
        json=_action_request(),
    )
    assert local.status_code == 200

    monkeypatch.setattr(runner, "_guala", owner)
    monkeypatch.setattr(runner, "STATE_DIR", "/exact-state")
    from dsf_ai_service.substrate.embodiment_world import (
        MoveCommand,
        PoseMM,
        PositionMM,
        encode_command,
    )

    encoded_command = base64.b64encode(encode_command(MoveCommand(
        target_pose=PoseMM(PositionMM(1_200, 1_400, 0), 0),
        duration_microseconds=100_000,
    ))).decode("ascii")
    runner_result = runner.handle_embodied_action_experience({
        "command_payload_base64": encoded_command,
        "nonce": "learned-body-act-http-0001",
        "port_id": "W1-self-body-port",
        "tutor_id": "joe",
    })
    assert runner_result == local.json()

    class _Remote:
        async def call(self, operation, **_values):
            assert operation == "embodied_action_experience"
            return copy.deepcopy(runner_result)

    monkeypatch.setattr(app_module, "_is_remote", lambda: True)
    monkeypatch.setattr(app_module, "_get_substrate_client", _Remote)
    remote = client.post(
        "/api/v1/embodiment/action-experience",
        headers={"X-API-Key": API_KEY},
        json=_action_request(),
    )
    assert remote.status_code == 200
    assert remote.json() == local.json()


def test_remote_transport_tamper_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import dsf_ai_service.app as app_module
    import dsf_ai_service.substrate_runner as runner

    transported = runner._embodied_action_transport(_emitted_result())
    transported["learned_body_act"]["pcm_s16le_base64"] = "AAAA"

    class _Remote:
        async def call(self, operation, **_values):
            assert operation == "embodied_action_experience"
            return transported

    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", API_KEY)
    monkeypatch.setattr(app_module, "_is_remote", lambda: True)
    monkeypatch.setattr(app_module, "_get_substrate_client", _Remote)
    response = TestClient(app_module.app).post(
        "/api/v1/embodiment/action-experience",
        headers={"X-API-Key": API_KEY},
        json=_action_request(),
    )
    assert response.status_code == 409
