from __future__ import annotations

import base64
import hashlib
import wave
from io import BytesIO

import pytest

from dsf_ai_service.physical_surface_lesson_http_contract import (
    PLAN_REQUEST_SCHEMA,
    PLAN_RESPONSE_SCHEMA,
    ROUTE_PATH,
    STEP_REQUEST_SCHEMA,
    STEP_RESPONSE_SCHEMA,
    PhysicalSurfaceTutoringPlanHTTPRequest,
    PhysicalSurfaceTutoringStepHTTPRequest,
    physical_surface_tutoring_http_response,
)


def _wav() -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16_000)
        writer.writeframes(b"\x00\x00" * 320)
    return output.getvalue()


def _plan_payload() -> dict[str, object]:
    return {
        "prior_progression_receipt_sha256": None,
        "schema": PLAN_REQUEST_SCHEMA,
        "steps": [{
            "source_media_receipt_sha256": hashlib.sha256(_wav()).hexdigest(),
            "target_object_id": "W1-optical-surface-01",
        }],
    }


def _step_payload() -> dict[str, object]:
    wav = _wav()
    return {
        "plan_receipt_sha256": "a" * 64,
        "prior_progression_receipt_sha256": None,
        "schema": STEP_REQUEST_SCHEMA,
        "source_media_receipt_sha256": hashlib.sha256(wav).hexdigest(),
        "step_index": 0,
        "wav_base64": base64.b64encode(wav).decode("ascii"),
    }


def test_plan_carries_only_opaque_surfaces_and_media_receipts() -> None:
    decoded = PhysicalSurfaceTutoringPlanHTTPRequest.decode(_plan_payload())
    arguments = decoded.runtime_arguments(state_dir="/tmp/state")

    assert ROUTE_PATH == "/api/v1/embodiment/physical-surface-lesson"
    assert set(arguments) == {
        "prior_progression_receipt_sha256",
        "state_dir",
        "steps",
    }
    assert arguments["steps"][0].target_object_id == (
        "W1-optical-surface-01"
    )
    assert "apple" not in repr(decoded).lower()
    assert "letter" not in repr(decoded).lower()


def test_step_is_prior_bound_and_carries_only_exact_physical_audio() -> None:
    decoded = PhysicalSurfaceTutoringStepHTTPRequest.decode(_step_payload())
    arguments = decoded.runtime_arguments(state_dir="/tmp/state")
    assert set(arguments) == {
        "plan_receipt_sha256",
        "prior_progression_receipt_sha256",
        "state_dir",
        "step_index",
        "wav_bytes",
    }
    assert arguments["wav_bytes"] == _wav()
    assert arguments["prior_progression_receipt_sha256"] is None

    labelled = _step_payload()
    labelled["meaning"] = "A is for apple"
    with pytest.raises(ValueError, match="request changed"):
        PhysicalSurfaceTutoringStepHTTPRequest.decode(labelled)
    crossed = _step_payload()
    crossed["source_media_receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs"):
        PhysicalSurfaceTutoringStepHTTPRequest.decode(crossed)


def test_plan_and_step_responses_are_receipts_only() -> None:
    plan_request = PhysicalSurfaceTutoringPlanHTTPRequest.decode(
        _plan_payload()
    )
    plan_response = physical_surface_tutoring_http_response(
        request_sha256=plan_request.request_sha256,
        operation="plan",
        result={"authority_receipt_sha256": "1" * 64},
    )
    assert plan_response["schema"] == PLAN_RESPONSE_SCHEMA
    assert not any(plan_response["claims"].values())

    step_request = PhysicalSurfaceTutoringStepHTTPRequest.decode(
        _step_payload()
    )
    step_response = physical_surface_tutoring_http_response(
        request_sha256=step_request.request_sha256,
        operation="step",
        result={"retained_pcm_bytes": 0},
    )
    assert step_response["schema"] == STEP_RESPONSE_SCHEMA
    assert step_response["retained_pcm_bytes"] == 0
    assert not any(step_response["claims"].values())
    with pytest.raises(ValueError, match="retained audio"):
        physical_surface_tutoring_http_response(
            request_sha256=step_request.request_sha256,
            operation="step",
            result={"retained_pcm_bytes": 1},
        )
