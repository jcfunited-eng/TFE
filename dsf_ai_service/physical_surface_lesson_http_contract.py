"""Protected transport for ordered tutor-mounted physical-surface lessons.

The plan carries only opaque mounted-object identities and exact WAV digests.
The step carries one WAV and the prior progression receipt.  Source time,
context identity, sight, settlement, and learning receipts are derived by the
runtime; no label, word, transcript, pronunciation, or meaning is admitted.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.substrate.embodied_glyph_tutoring import MAX_PCM_SAMPLES
from dsf_ai_service.substrate.physical_surface_tutoring_conductor import (
    APPROVED_PHYSICAL_SURFACE_IDS,
    MAX_PLAN_STEPS,
    PhysicalSurfaceTutoringPlanStep,
)


ROUTE_PATH = "/api/v1/embodiment/physical-surface-lesson"
PLAN_REQUEST_SCHEMA = "guala.physical_surface_tutoring.plan_http_request.v1"
STEP_REQUEST_SCHEMA = "guala.physical_surface_tutoring.step_http_request.v1"
PLAN_RESPONSE_SCHEMA = "guala.physical_surface_tutoring.plan_http_response.v1"
STEP_RESPONSE_SCHEMA = "guala.physical_surface_tutoring.step_http_response.v1"
MAX_WAV_BYTES = MAX_PCM_SAMPLES * 2 + 4_096
MAX_REQUEST_BYTES = 512 * 1024
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _uint63(value: object, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= 2**63 - 1
    ):
        raise ValueError(f"{name} changed")
    return value


def _decode_wav(value: object) -> bytes:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 4 * ((MAX_WAV_BYTES + 2) // 3)
    ):
        raise ValueError("tutor WAV exceeds its byte boundary")
    try:
        wav = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("tutor WAV is not canonical base64") from error
    if (
        not wav
        or len(wav) > MAX_WAV_BYTES
        or base64.b64encode(wav).decode("ascii") != value
    ):
        raise ValueError("tutor WAV is not canonical base64")
    return wav


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceTutoringPlanHTTPRequest:
    prior_progression_receipt_sha256: str | None
    steps: tuple[PhysicalSurfaceTutoringPlanStep, ...]
    request_sha256: str

    @classmethod
    def decode(
        cls,
        value: Mapping[str, object],
    ) -> "PhysicalSurfaceTutoringPlanHTTPRequest":
        if (
            not isinstance(value, Mapping)
            or set(value)
            != {
                "prior_progression_receipt_sha256",
                "schema",
                "steps",
            }
            or value.get("schema") != PLAN_REQUEST_SCHEMA
            or len(_canonical(value)) > MAX_REQUEST_BYTES
        ):
            raise ValueError("physical tutoring plan HTTP request changed")
        raw_steps = value.get("steps")
        if (
            not isinstance(raw_steps, list)
            or not 1 <= len(raw_steps) <= MAX_PLAN_STEPS
        ):
            raise ValueError("physical tutoring plan extent changed")
        steps = []
        for item in raw_steps:
            if (
                not isinstance(item, Mapping)
                or set(item)
                != {"source_media_receipt_sha256", "target_object_id"}
            ):
                raise ValueError("physical tutoring plan step changed")
            step = PhysicalSurfaceTutoringPlanStep.create(
                target_object_id=item["target_object_id"],
                source_media_receipt_sha256=item[
                    "source_media_receipt_sha256"
                ],
            )
            if step.target_object_id not in APPROVED_PHYSICAL_SURFACE_IDS:
                raise ValueError("physical tutoring target is not approved")
            steps.append(step)
        prior = value["prior_progression_receipt_sha256"]
        if prior is not None:
            prior = _sha(prior, "physical tutoring prior progression")
        return cls(
            prior_progression_receipt_sha256=prior,
            steps=tuple(steps),
            request_sha256=hashlib.sha256(_canonical(value)).hexdigest(),
        )

    def runtime_arguments(self, *, state_dir: object) -> dict[str, object]:
        return {
            "prior_progression_receipt_sha256": (
                self.prior_progression_receipt_sha256
            ),
            "state_dir": state_dir,
            "steps": self.steps,
        }


@dataclass(frozen=True, slots=True)
class PhysicalSurfaceTutoringStepHTTPRequest:
    plan_receipt_sha256: str
    step_index: int
    prior_progression_receipt_sha256: str | None
    source_media_receipt_sha256: str
    wav_bytes: bytes = field(repr=False)
    request_sha256: str

    @classmethod
    def decode(
        cls,
        value: Mapping[str, object],
    ) -> "PhysicalSurfaceTutoringStepHTTPRequest":
        if (
            not isinstance(value, Mapping)
            or set(value)
            != {
                "plan_receipt_sha256",
                "prior_progression_receipt_sha256",
                "schema",
                "source_media_receipt_sha256",
                "step_index",
                "wav_base64",
            }
            or value.get("schema") != STEP_REQUEST_SCHEMA
            or len(_canonical(value)) > MAX_REQUEST_BYTES
        ):
            raise ValueError("physical tutoring step HTTP request changed")
        prior = value.get("prior_progression_receipt_sha256")
        if prior is not None:
            prior = _sha(prior, "physical tutoring prior progression")
        wav = _decode_wav(value.get("wav_base64"))
        media = _sha(
            value.get("source_media_receipt_sha256"),
            "physical tutoring source media",
        )
        if hashlib.sha256(wav).hexdigest() != media:
            raise ValueError("tutor WAV differs from its source media receipt")
        step_index = _uint63(value.get("step_index"), "physical tutoring step")
        if step_index >= MAX_PLAN_STEPS:
            raise ValueError("physical tutoring step exceeds its boundary")
        return cls(
            plan_receipt_sha256=_sha(
                value.get("plan_receipt_sha256"),
                "physical tutoring plan",
            ),
            step_index=step_index,
            prior_progression_receipt_sha256=prior,
            source_media_receipt_sha256=media,
            wav_bytes=wav,
            request_sha256=hashlib.sha256(_canonical(value)).hexdigest(),
        )

    def runtime_arguments(self, *, state_dir: object) -> dict[str, object]:
        return {
            "plan_receipt_sha256": self.plan_receipt_sha256,
            "prior_progression_receipt_sha256": (
                self.prior_progression_receipt_sha256
            ),
            "state_dir": state_dir,
            "step_index": self.step_index,
            "wav_bytes": self.wav_bytes,
        }


def physical_surface_tutoring_http_response(
    *,
    request_sha256: str,
    result: Mapping[str, object],
    operation: str,
) -> dict[str, object]:
    _sha(request_sha256, "physical tutoring request")
    if operation not in {"plan", "step"} or not isinstance(result, Mapping):
        raise ValueError("physical tutoring response changed")
    if operation == "step" and (
        result.get("retained_pcm_bytes") != 0
        or "wav_bytes" in result
        or "pcm_s16le" in result
    ):
        raise ValueError("physical tutoring response retained audio")
    return {
        "claims": {
            "hidden_visual_identity_authority": False,
            "meaning_authority": False,
            "pronunciation_authority": False,
            "recognition_authority": False,
            "word_authority": False,
        },
        "operation": operation,
        "request_sha256": request_sha256,
        "result": dict(result),
        "retained_pcm_bytes": 0,
        "schema": (
            PLAN_RESPONSE_SCHEMA
            if operation == "plan"
            else STEP_RESPONSE_SCHEMA
        ),
    }


__all__ = (
    "MAX_REQUEST_BYTES",
    "PLAN_REQUEST_SCHEMA",
    "PLAN_RESPONSE_SCHEMA",
    "PhysicalSurfaceTutoringPlanHTTPRequest",
    "PhysicalSurfaceTutoringStepHTTPRequest",
    "ROUTE_PATH",
    "STEP_REQUEST_SCHEMA",
    "STEP_RESPONSE_SCHEMA",
    "physical_surface_tutoring_http_response",
)
