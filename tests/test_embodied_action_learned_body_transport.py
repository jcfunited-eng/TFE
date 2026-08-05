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


def test_retired_learned_vocal_act_transport_is_refused() -> None:
    """Anti-resurrection guard: results carrying the retired vocal act or
    learned-body-act transport keys are refused, never converted."""

    for retired in (
        _emitted_result(),
        _silent_result(),
        {
            "binding_created": False,
            "learned_body_act": {"state": "emitted"},
            "world_revision_after": 2,
            "world_revision_before": 1,
        },
    ):
        for convert in _converters():
            with pytest.raises(
                RuntimeError,
                match="permanently retired",
            ):
                convert(copy.deepcopy(retired))


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
