"""Durable capacity-one delivery state for one causal speech execution.

The transaction is keyed by the dispatcher's authenticated request and
execution receipts.  It owns only actuator delivery state: the causal action
and the auditory full-field settlement remain owned by their existing
authorities.  Every external operation is preceded by a signed state change,
so a process restart consumes no more than two attempts and never invents a
successful mouth or auditory event.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, replace
from typing import Mapping

from dsf_ai_service.glew_runtime.model import sha256_digest


STATE_SCHEMA = "guala.causal_speech_delivery.state.v1"
ENVELOPE_SCHEMA = "guala.causal_speech_delivery.state.hmac.v1"
STATE_DOMAIN = b"guala-causal-speech-delivery-state-v1\0"
MAX_ATTEMPTS = 2
MAX_WAV_BYTES = 4 * 1024 * 1024
MAX_FAILURE_BYTES = 1024
MAX_ENCODED_STATE_BYTES = 4 * ((MAX_WAV_BYTES + 2) // 3) + 16 * 1024

_LIVE_PHASES = {
    "queued",
    "attempt_started",
    "retryable",
    "wav_ready",
    "observation_started",
}
_TERMINAL_PHASES = {"completed", "exhausted"}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("causal speech delivery key must be bytes or text")
    if not result or len(result) > 4096:
        raise ValueError("causal speech delivery key must be bounded and nonempty")
    return result


def _bounded_text(value: object, name: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > maximum
    ):
        raise ValueError(f"{name} must be bounded canonical text")
    return value


@dataclass(frozen=True, slots=True)
class CausalSpeechDeliveryState:
    request_receipt_sha256: str
    execution_receipt_sha256: str
    action_text_sha256: str
    phase: str
    attempts: int
    wav_sha256: str | None = None
    wav_base64: str | None = None
    failure_stage: str | None = None
    failure_detail: str | None = None

    @classmethod
    def queued(
        cls,
        *,
        request_receipt_sha256: str,
        execution_receipt_sha256: str,
        action_text: str,
    ) -> "CausalSpeechDeliveryState":
        state = cls(
            request_receipt_sha256=request_receipt_sha256,
            execution_receipt_sha256=execution_receipt_sha256,
            action_text_sha256=hashlib.sha256(action_text.encode("utf-8")).hexdigest(),
            phase="queued",
            attempts=0,
        )
        state.verify()
        return state

    def verify(self) -> None:
        sha256_digest(self.request_receipt_sha256, "speech delivery request")
        sha256_digest(self.execution_receipt_sha256, "speech delivery execution")
        sha256_digest(self.action_text_sha256, "speech delivery action text")
        if self.phase not in _LIVE_PHASES | _TERMINAL_PHASES:
            raise ValueError("causal speech delivery phase changed")
        if (
            isinstance(self.attempts, bool)
            or not isinstance(self.attempts, int)
            or not 0 <= self.attempts <= MAX_ATTEMPTS
        ):
            raise ValueError("causal speech delivery attempt count changed")
        if self.phase == "queued" and self.attempts != 0:
            raise ValueError("queued causal speech delivery already consumed an attempt")
        if self.phase != "queued" and self.attempts == 0:
            raise ValueError("causal speech delivery phase lacks an attempt")
        has_wav = self.wav_sha256 is not None or self.wav_base64 is not None
        if has_wav:
            if self.wav_sha256 is None or self.wav_base64 is None:
                raise ValueError("causal speech delivery WAV state is partial")
            sha256_digest(self.wav_sha256, "speech delivery WAV")
            try:
                wav = base64.b64decode(self.wav_base64, validate=True)
            except Exception as error:
                raise ValueError("causal speech delivery WAV is not canonical base64") from error
            if not wav or len(wav) > MAX_WAV_BYTES:
                raise ValueError("causal speech delivery WAV exceeds its boundary")
            if base64.b64encode(wav).decode("ascii") != self.wav_base64:
                raise ValueError("causal speech delivery WAV base64 changed")
            if hashlib.sha256(wav).hexdigest() != self.wav_sha256:
                raise ValueError("causal speech delivery WAV digest changed")
        if self.phase in {"wav_ready", "observation_started", "completed"} and not has_wav:
            raise ValueError("causal speech delivery phase lost its exact WAV")
        if self.phase in {"queued", "attempt_started", "retryable"} and has_wav:
            raise ValueError("causal speech delivery retained WAV before synthesis")
        has_failure = self.failure_stage is not None or self.failure_detail is not None
        if has_failure:
            if self.failure_stage is None or self.failure_detail is None:
                raise ValueError("causal speech delivery failure is partial")
            _bounded_text(self.failure_stage, "speech delivery failure stage", 128)
            _bounded_text(
                self.failure_detail,
                "speech delivery failure detail",
                MAX_FAILURE_BYTES,
            )
        if self.phase in {"retryable", "exhausted"} and not has_failure:
            raise ValueError("failed causal speech delivery lacks failure evidence")
        if self.phase not in {"retryable", "exhausted"} and has_failure:
            raise ValueError("successful causal speech delivery carries failure evidence")
        if self.phase == "retryable" and self.attempts >= MAX_ATTEMPTS:
            raise ValueError("exhausted causal speech delivery remains retryable")
        if self.phase == "completed" and self.attempts > MAX_ATTEMPTS:
            raise ValueError("completed causal speech delivery exceeded attempts")

    @property
    def live(self) -> bool:
        return self.phase in _LIVE_PHASES

    @property
    def wav_bytes(self) -> bytes | None:
        if self.wav_base64 is None:
            return None
        return base64.b64decode(self.wav_base64, validate=True)

    def verify_action_text(self, action_text: str) -> None:
        if hashlib.sha256(action_text.encode("utf-8")).hexdigest() != self.action_text_sha256:
            raise ValueError("causal speech delivery action text changed")

    def begin_attempt(self) -> "CausalSpeechDeliveryState":
        self.verify()
        if self.phase not in {"queued", "retryable"}:
            raise ValueError("causal speech delivery is not ready for synthesis")
        if self.attempts >= MAX_ATTEMPTS:
            raise ValueError("causal speech delivery attempt capacity is exhausted")
        result = replace(
            self,
            phase="attempt_started",
            attempts=self.attempts + 1,
            failure_stage=None,
            failure_detail=None,
        )
        result.verify()
        return result

    def record_wav(self, wav_bytes: bytes) -> "CausalSpeechDeliveryState":
        self.verify()
        if self.phase != "attempt_started":
            raise ValueError("causal speech synthesis has no started attempt")
        if not isinstance(wav_bytes, bytes) or not wav_bytes:
            raise ValueError("causal speech synthesis produced no WAV bytes")
        if len(wav_bytes) > MAX_WAV_BYTES:
            raise ValueError("causal speech synthesis exceeded the WAV boundary")
        if len(wav_bytes) < 12 or wav_bytes[:4] != b"RIFF" or wav_bytes[8:12] != b"WAVE":
            raise ValueError("causal speech synthesis did not produce a WAV container")
        result = replace(
            self,
            phase="wav_ready",
            wav_sha256=hashlib.sha256(wav_bytes).hexdigest(),
            wav_base64=base64.b64encode(wav_bytes).decode("ascii"),
        )
        result.verify()
        return result

    def begin_observation(self) -> "CausalSpeechDeliveryState":
        self.verify()
        if self.phase != "wav_ready":
            raise ValueError("causal speech WAV is not ready for observation")
        result = replace(self, phase="observation_started")
        result.verify()
        return result

    def fail(self, *, stage: str, detail: str, uncertain_observation: bool = False) -> "CausalSpeechDeliveryState":
        self.verify()
        stage = _bounded_text(stage, "speech delivery failure stage", 128)
        detail = _bounded_text(
            detail,
            "speech delivery failure detail",
            MAX_FAILURE_BYTES,
        )
        exhausted = uncertain_observation or self.attempts >= MAX_ATTEMPTS
        result = replace(
            self,
            phase="exhausted" if exhausted else "retryable",
            wav_sha256=self.wav_sha256 if exhausted else None,
            wav_base64=self.wav_base64 if exhausted else None,
            failure_stage=stage,
            failure_detail=detail,
        )
        result.verify()
        return result

    def complete(self) -> "CausalSpeechDeliveryState":
        self.verify()
        if self.phase != "observation_started":
            raise ValueError("causal speech observation has not started")
        result = replace(self, phase="completed")
        result.verify()
        return result

    def recover_after_restart(self) -> "CausalSpeechDeliveryState":
        """Resolve only phases whose interrupted work cannot be replayed safely."""
        self.verify()
        if self.phase == "attempt_started":
            return self.fail(
                stage="process_restart_during_synthesis",
                detail="process restarted after attempt authority was persisted",
            )
        if self.phase == "observation_started":
            return self.fail(
                stage="process_restart_during_observation",
                detail=(
                    "process restarted after observation authority was persisted; "
                    "the waveform will not be re-admitted"
                ),
                uncertain_observation=True,
            )
        return self

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "action_text_sha256": self.action_text_sha256,
            "attempts": self.attempts,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "failure_detail": self.failure_detail,
            "failure_stage": self.failure_stage,
            "phase": self.phase,
            "request_receipt_sha256": self.request_receipt_sha256,
            "schema": STATE_SCHEMA,
            "wav_base64": self.wav_base64,
            "wav_sha256": self.wav_sha256,
        }

    @classmethod
    def from_record(cls, value: Mapping[str, object]) -> "CausalSpeechDeliveryState":
        expected = {
            "action_text_sha256",
            "attempts",
            "execution_receipt_sha256",
            "failure_detail",
            "failure_stage",
            "phase",
            "request_receipt_sha256",
            "schema",
            "wav_base64",
            "wav_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected or value.get("schema") != STATE_SCHEMA:
            raise ValueError("causal speech delivery state fields changed")
        state = cls(
            request_receipt_sha256=value.get("request_receipt_sha256"),
            execution_receipt_sha256=value.get("execution_receipt_sha256"),
            action_text_sha256=value.get("action_text_sha256"),
            phase=value.get("phase"),
            attempts=value.get("attempts"),
            wav_sha256=value.get("wav_sha256"),
            wav_base64=value.get("wav_base64"),
            failure_stage=value.get("failure_stage"),
            failure_detail=value.get("failure_detail"),
        )
        state.verify()
        return state


def encode_state(state: CausalSpeechDeliveryState, *, authority_key: object) -> dict[str, str]:
    state.verify()
    key = _key(authority_key)
    payload = _canonical(state.as_record())
    if len(payload) > MAX_ENCODED_STATE_BYTES:
        raise RuntimeError("causal speech delivery encoded state exceeds its boundary")
    return {
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": ENVELOPE_SCHEMA,
        "state_hmac_sha256": hmac.new(
            key, STATE_DOMAIN + payload, hashlib.sha256
        ).hexdigest(),
    }


def decode_state(value: Mapping[str, object], *, authority_key: object) -> CausalSpeechDeliveryState:
    if not isinstance(value, Mapping) or set(value) != {
        "payload_base64",
        "schema",
        "state_hmac_sha256",
    } or value.get("schema") != ENVELOPE_SCHEMA:
        raise ValueError("causal speech delivery envelope changed")
    try:
        payload = base64.b64decode(value.get("payload_base64"), validate=True)
    except Exception as error:
        raise ValueError("causal speech delivery payload is not canonical base64") from error
    if not payload or len(payload) > MAX_ENCODED_STATE_BYTES:
        raise ValueError("causal speech delivery payload exceeds its boundary")
    signature = value.get("state_hmac_sha256")
    sha256_digest(signature, "causal speech delivery state HMAC")
    expected = hmac.new(_key(authority_key), STATE_DOMAIN + payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("causal speech delivery state HMAC changed")
    try:
        record = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("causal speech delivery payload is not JSON") from error
    if _canonical(record) != payload:
        raise ValueError("causal speech delivery payload is not canonical")
    return CausalSpeechDeliveryState.from_record(record)


__all__ = (
    "CausalSpeechDeliveryState",
    "MAX_ATTEMPTS",
    "MAX_ENCODED_STATE_BYTES",
    "MAX_WAV_BYTES",
    "decode_state",
    "encode_state",
)
