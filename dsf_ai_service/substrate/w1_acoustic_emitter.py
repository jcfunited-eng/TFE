"""Authenticated transient acoustic emission inside the W1 environment.

This authority is the virtual physical emitter.  It binds exact PCM16 bytes to
one authenticated W1 world transition, one external actor control port, one
causal sample interval, and one capture epoch.  The signed control receipt is
consumed transiently by the audiovisual perception authority; emitter identity
and raw PCM are never copied into perceptual identity or persisted evidence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
from dataclasses import dataclass

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
)


EMISSION_SCHEMA = "guala.w1.authenticated_acoustic_emission.v1"
AUTHORITY_DOMAIN = b"guala-w1-authenticated-acoustic-emitter-v1\0"
PCM_SAMPLE_RATE_HZ = 16_000
PCM_SAMPLE_WIDTH_BYTES = 2
MIN_EMITTED_PCM_SAMPLES = 160
MAX_EMITTED_PCM_SAMPLES = MAX_NATIVE_SAMPLES_PER_SUBSTREAM
MAX_SOURCE_SAMPLE_INDEX = (1 << 63) - 1


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("W1 acoustic emitter key must be bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError("W1 acoustic emitter key has an invalid boundary")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _pcm_sample_count(value: bytes) -> int:
    if not isinstance(value, bytes) or len(value) % PCM_SAMPLE_WIDTH_BYTES:
        raise ValueError("W1 emission must be signed little-endian PCM16")
    count = len(value) // PCM_SAMPLE_WIDTH_BYTES
    if not MIN_EMITTED_PCM_SAMPLES <= count <= MAX_EMITTED_PCM_SAMPLES:
        raise ValueError("W1 emission exceeds its exact sample boundary")
    tuple(struct.iter_unpack("<h", value))
    return count


@dataclass(frozen=True, slots=True)
class W1AcousticEmissionReceipt:
    epoch_commitment_sha256: str
    sequence: int
    source_sample_start: int
    source_sample_end: int
    emitter_port_id: str
    execution_receipt_sha256: str
    pcm_sha256: str
    sample_count: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "emitter_port_id": self.emitter_port_id,
            "epoch_commitment_sha256": self.epoch_commitment_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "pcm_sha256": self.pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": EMISSION_SCHEMA,
            "sequence": self.sequence,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        _sha256(self.epoch_commitment_sha256, "W1 emission epoch")
        _sha256(self.execution_receipt_sha256, "W1 execution receipt")
        _sha256(self.pcm_sha256, "W1 emitted PCM")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or not 0 <= self.sequence <= MAX_SOURCE_SAMPLE_INDEX
            or isinstance(self.source_sample_start, bool)
            or not isinstance(self.source_sample_start, int)
            or not 0 <= self.source_sample_start <= MAX_SOURCE_SAMPLE_INDEX
            or isinstance(self.source_sample_end, bool)
            or not isinstance(self.source_sample_end, int)
            or not self.source_sample_start
            < self.source_sample_end
            <= MAX_SOURCE_SAMPLE_INDEX
            or self.source_sample_end - self.source_sample_start
            != self.sample_count
            or not MIN_EMITTED_PCM_SAMPLES
            <= self.sample_count
            <= MAX_EMITTED_PCM_SAMPLES
            or not isinstance(self.emitter_port_id, str)
            or not self.emitter_port_id
        ):
            raise ValueError("W1 acoustic emission boundary changed")
        expected_hmac = hmac.new(
            key,
            AUTHORITY_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac, self.authority_hmac_sha256
        ):
            raise ValueError("W1 acoustic emission HMAC changed")
        expected_receipt = _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": self.payload(),
        })
        if expected_receipt != self.authority_receipt_sha256:
            raise ValueError("W1 acoustic emission receipt changed")


@dataclass(frozen=True, slots=True)
class AuthenticatedW1AcousticEmission:
    receipt: W1AcousticEmissionReceipt
    pcm_s16le: bytes

    def verify(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        execution_receipt: ActionExecutionReceipt,
    ) -> None:
        self.receipt.verify(authority_key)
        world_authority.verify_execution_receipt(execution_receipt)
        current = world_authority.observation_snapshot()
        count = _pcm_sample_count(self.pcm_s16le)
        if (
            count != self.receipt.sample_count
            or hashlib.sha256(self.pcm_s16le).hexdigest()
            != self.receipt.pcm_sha256
            or execution_receipt.authority_receipt_sha256
            != self.receipt.execution_receipt_sha256
            or execution_receipt.disposition != "applied"
            or execution_receipt.observed_revision
            != execution_receipt.before.revision
            or execution_receipt.after.revision
            != execution_receipt.before.revision + 1
            or current.authority_receipt_sha256
            != execution_receipt.after.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 acoustic pressure differs from its authenticated emission"
            )
        actor_by_port = {
            item.port_id: item.actor_body_id
            for item in world_authority.actor_ports
        }
        emitter_body_id = actor_by_port.get(self.receipt.emitter_port_id)
        if emitter_body_id is None:
            raise ValueError("W1 acoustic emitter port is not mounted")
        if emitter_body_id == execution_receipt.after.self_body_id:
            raise ValueError("W1 external emission used the self port")
        if (
            execution_receipt.port_id != self.receipt.emitter_port_id
            or execution_receipt.actor_body_id != emitter_body_id
        ):
            raise ValueError(
                "W1 acoustic emission is not bound to its acting emitter"
            )


class W1AcousticEmitterAuthority:
    """Issue authenticated transient pressure from a mounted W1 actor."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 acoustic emitter requires the world authority")
        self._key = _key(authority_key)
        self._world = world_authority

    def owns_world(self, world_authority: EmbodimentWorldAuthority) -> bool:
        return self._world is world_authority

    def verify_emission(
        self,
        emission: AuthenticatedW1AcousticEmission,
        *,
        execution_receipt: ActionExecutionReceipt,
    ) -> None:
        if not isinstance(emission, AuthenticatedW1AcousticEmission):
            raise TypeError("W1 authenticated acoustic emission is required")
        emission.verify(
            authority_key=self._key,
            world_authority=self._world,
            execution_receipt=execution_receipt,
        )

    def emit(
        self,
        *,
        epoch_token: str,
        sequence: int,
        source_sample_start: int,
        execution_receipt: ActionExecutionReceipt,
        emitter_port_id: str,
        pcm_s16le: bytes,
    ) -> AuthenticatedW1AcousticEmission:
        if (
            not isinstance(epoch_token, str)
            or not epoch_token
            or len(epoch_token.encode("utf-8")) > 256
        ):
            raise ValueError("W1 acoustic emission epoch is required")
        self._world.verify_execution_receipt(execution_receipt)
        if execution_receipt.disposition != "applied":
            raise ValueError("W1 acoustic emission requires an applied transition")
        count = _pcm_sample_count(pcm_s16le)
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or not 0 <= sequence <= MAX_SOURCE_SAMPLE_INDEX
            or isinstance(source_sample_start, bool)
            or not isinstance(source_sample_start, int)
            or not 0 <= source_sample_start
            <= MAX_SOURCE_SAMPLE_INDEX - count
        ):
            raise ValueError("W1 acoustic emission clock is invalid")
        payload = {
            "emitter_port_id": emitter_port_id,
            "epoch_commitment_sha256": hashlib.sha256(
                epoch_token.encode("utf-8")
            ).hexdigest(),
            "execution_receipt_sha256": (
                execution_receipt.authority_receipt_sha256
            ),
            "pcm_sha256": hashlib.sha256(pcm_s16le).hexdigest(),
            "sample_count": count,
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": EMISSION_SCHEMA,
            "sequence": sequence,
            "source_sample_end": source_sample_start + count,
            "source_sample_start": source_sample_start,
        }
        signature = hmac.new(
            self._key,
            AUTHORITY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        receipt = W1AcousticEmissionReceipt(
            epoch_commitment_sha256=payload["epoch_commitment_sha256"],
            sequence=sequence,
            source_sample_start=source_sample_start,
            source_sample_end=source_sample_start + count,
            emitter_port_id=emitter_port_id,
            execution_receipt_sha256=(
                execution_receipt.authority_receipt_sha256
            ),
            pcm_sha256=payload["pcm_sha256"],
            sample_count=count,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result = AuthenticatedW1AcousticEmission(
            receipt=receipt,
            pcm_s16le=pcm_s16le,
        )
        self.verify_emission(result, execution_receipt=execution_receipt)
        return result

    @staticmethod
    def status() -> dict[str, object]:
        return {
            "max_pcm_samples_per_emission": MAX_EMITTED_PCM_SAMPLES,
            "retained_raw_media_bytes": 0,
            "schema": "guala.w1.acoustic_emitter_status.v1",
        }


__all__ = (
    "AuthenticatedW1AcousticEmission",
    "MAX_EMITTED_PCM_SAMPLES",
    "MIN_EMITTED_PCM_SAMPLES",
    "PCM_SAMPLE_RATE_HZ",
    "W1AcousticEmissionReceipt",
    "W1AcousticEmitterAuthority",
)
