"""Atomic companion vocal action preparation inside the bounded W1 world.

The companion port is control topology only.  It never becomes perceptual
identity, a source label, a word, or meaning.  One preparation owns exactly
one authenticated intent, one PCM chunk, one typed vocal world execution, one
authenticated emission, and one reserved anonymous audiovisual settlement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    SECOND_BODY_PORT_ID,
    VocalizeCommand,
    encode_command,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    AuthenticatedW1AcousticEmission,
    MAX_EMITTED_PCM_SAMPLES,
    MIN_EMITTED_PCM_SAMPLES,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
)


INTENT_SCHEMA = "guala.w1.companion_vocal_intent.v2"
INTENT_DOMAIN = b"guala.w1.companion_vocal_intent.v2\0"


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
        value = value.encode("utf-8")
    if not isinstance(value, bytes) or not value:
        raise ValueError("companion vocal authority key is unavailable")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class CompanionVocalIntentReceipt:
    companion_port_id: str
    world_observation_receipt_sha256: str
    pcm_sha256: str
    sample_count: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "companion_port_id": self.companion_port_id,
            "pcm_sha256": self.pcm_sha256,
            "sample_count": self.sample_count,
            "schema": INTENT_SCHEMA,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        if not isinstance(self.companion_port_id, str) or not self.companion_port_id:
            raise ValueError("companion vocal port is unavailable")
        _sha256(self.world_observation_receipt_sha256, "world observation")
        _sha256(self.pcm_sha256, "companion pressure")
        if (
            isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or not MIN_EMITTED_PCM_SAMPLES
            <= self.sample_count
            <= MAX_EMITTED_PCM_SAMPLES
        ):
            raise ValueError("companion vocal sample count changed")
        _sha256(self.authority_hmac_sha256, "companion intent HMAC")
        _sha256(self.authority_receipt_sha256, "companion intent receipt")
        payload = self.payload()
        expected_hmac = hmac.new(
            key,
            INTENT_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                self.authority_hmac_sha256,
                expected_hmac,
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("companion vocal intent authority changed")


@dataclass(frozen=True, slots=True)
class PreparedCompanionVocalExperience:
    epoch_token: str
    world_snapshot: bytes
    intent_receipt: CompanionVocalIntentReceipt
    command_payload: bytes
    execution_receipt: ActionExecutionReceipt
    acoustic_emission: AuthenticatedW1AcousticEmission
    physical_mount: W1PhysicalEvidenceMount


class W1CompanionVocalExperienceAuthority:
    """Own one bounded prepare/commit/discard companion vocal transaction."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        physical_authority: W1AudiovisualPhysicalEvidenceAuthority,
        companion_port_id: str = SECOND_BODY_PORT_ID,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("companion vocal experience requires W1 world authority")
        if not isinstance(
            physical_authority, W1AudiovisualPhysicalEvidenceAuthority
        ):
            raise TypeError(
                "companion vocal experience requires W1 physical authority"
            )
        actor_by_port = {
            item.port_id: item.actor_body_id
            for item in world_authority.actor_ports
        }
        companion_body = actor_by_port.get(companion_port_id)
        if companion_body is None:
            raise ValueError("companion vocal port is not mounted")
        if companion_body == world_authority.observation_snapshot().self_body_id:
            raise ValueError("companion vocal port cannot be the self port")
        self._key = _key(authority_key)
        self._world = world_authority
        self._physical = physical_authority
        self._companion_port_id = companion_port_id
        self._prepared: PreparedCompanionVocalExperience | None = None
        self._lock = threading.RLock()

    @staticmethod
    def _sample_count(pcm_s16le: bytes) -> int:
        if not isinstance(pcm_s16le, bytes) or len(pcm_s16le) % 2:
            raise ValueError("companion pressure must be PCM16 bytes")
        count = len(pcm_s16le) // 2
        if not MIN_EMITTED_PCM_SAMPLES <= count <= MAX_EMITTED_PCM_SAMPLES:
            raise ValueError("companion pressure exceeds its exact sample boundary")
        return count

    def _issue_intent(
        self,
        *,
        pcm_s16le: bytes,
        sample_count: int,
        world_observation_receipt_sha256: str,
    ) -> CompanionVocalIntentReceipt:
        unsigned = CompanionVocalIntentReceipt(
            companion_port_id=self._companion_port_id,
            world_observation_receipt_sha256=(
                world_observation_receipt_sha256
            ),
            pcm_sha256=hashlib.sha256(pcm_s16le).hexdigest(),
            sample_count=sample_count,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = unsigned.payload()
        signature = hmac.new(
            self._key,
            INTENT_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        intent = CompanionVocalIntentReceipt(
            companion_port_id=unsigned.companion_port_id,
            world_observation_receipt_sha256=(
                unsigned.world_observation_receipt_sha256
            ),
            pcm_sha256=unsigned.pcm_sha256,
            sample_count=unsigned.sample_count,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        intent.verify(self._key)
        return intent

    def prepare(
        self,
        *,
        pcm_s16le: bytes,
    ) -> PreparedCompanionVocalExperience:
        sample_count = self._sample_count(pcm_s16le)
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("companion vocal transaction is already prepared")
            world_snapshot = self._world.encoded_snapshot()
            before = self._world.observation_snapshot()
            intent = self._issue_intent(
                pcm_s16le=pcm_s16le,
                sample_count=sample_count,
                world_observation_receipt_sha256=(
                    before.authority_receipt_sha256
                ),
            )
            epoch_token = self._physical.open_epoch()
            mounted: W1PhysicalEvidenceMount | None = None
            try:
                epoch_commitment = hashlib.sha256(
                    epoch_token.encode("utf-8")
                ).hexdigest()
                command_payload = encode_command(VocalizeCommand(
                    epoch_commitment_sha256=epoch_commitment,
                    sequence=0,
                    source_sample_start=0,
                    pcm_sha256=intent.pcm_sha256,
                    sample_count=sample_count,
                ))
                execution = self._world.execute_port_command(
                    port_id=self._companion_port_id,
                    command_payload=command_payload,
                    causal_intent_receipt_sha256=(
                        intent.authority_receipt_sha256
                    ),
                    expected_revision=before.revision,
                )
                if (
                    execution.disposition != "applied"
                    or execution.port_id != self._companion_port_id
                    or execution.before != before
                    or execution.causal_intent_receipt_sha256
                    != intent.authority_receipt_sha256
                ):
                    raise RuntimeError("companion vocal execution was not applied")
                emission = self._physical.emit_acoustic_pressure(
                    epoch_token=epoch_token,
                    sequence=0,
                    source_sample_start=0,
                    observation_snapshot=execution.after,
                    execution_receipt=execution,
                    command_payload=command_payload,
                    emitter_port_id=self._companion_port_id,
                    pcm_s16le=pcm_s16le,
                )
                mounted = self._physical.mount(
                    epoch_token=epoch_token,
                    sequence=0,
                    execution_receipt=execution,
                    acoustic_emission=emission,
                    commit=False,
                )
                if (
                    mounted.state is not W1EvidenceState.OBSERVED
                    or mounted.causal_settlement is None
                    or mounted.evidence_receipt is None
                ):
                    raise RuntimeError(
                        "companion vocal action produced no causal experience"
                    )
                self._physical.verify_mount(mounted)
                prepared = PreparedCompanionVocalExperience(
                    epoch_token=epoch_token,
                    world_snapshot=world_snapshot,
                    intent_receipt=intent,
                    command_payload=command_payload,
                    execution_receipt=execution,
                    acoustic_emission=emission,
                    physical_mount=mounted,
                )
                self._prepared = prepared
                return prepared
            except BaseException:
                if mounted is not None and mounted.causal_settlement is not None:
                    try:
                        self._physical.discard_prepared_multisensory_mount(
                            mounted
                        )
                    except ValueError:
                        pass
                self._world.restore_encoded(world_snapshot)
                self._physical.close_epoch(epoch_token)
                raise

    def _require_prepared(
        self, prepared: PreparedCompanionVocalExperience
    ) -> PreparedCompanionVocalExperience:
        if not isinstance(prepared, PreparedCompanionVocalExperience):
            raise TypeError("typed companion vocal preparation is required")
        current = self._prepared
        if (
            current is None
            or current.physical_mount.causal_settlement is None
            or prepared.physical_mount.causal_settlement is None
            or current.physical_mount.causal_settlement.authority_receipt_sha256
            != prepared.physical_mount.causal_settlement.authority_receipt_sha256
        ):
            raise ValueError("companion vocal preparation changed")
        current.intent_receipt.verify(self._key)
        if (
            current.execution_receipt.causal_intent_receipt_sha256
            != current.intent_receipt.authority_receipt_sha256
        ):
            raise ValueError("companion vocal execution lost its intent")
        return current

    def commit(self, prepared: PreparedCompanionVocalExperience) -> None:
        with self._lock:
            current = self._require_prepared(prepared)
            try:
                self._physical.commit_prepared_multisensory_mount(
                    current.physical_mount,
                    close_epoch=True,
                )
            except BaseException:
                self._world.restore_encoded(current.world_snapshot)
                self._physical.close_epoch(current.epoch_token)
                self._prepared = None
                raise
            self._prepared = None

    def discard(self, prepared: PreparedCompanionVocalExperience) -> None:
        with self._lock:
            current = self._require_prepared(prepared)
            self._physical.discard_prepared_multisensory_mount(
                current.physical_mount,
                close_epoch=True,
            )
            self._world.restore_encoded(current.world_snapshot)
            self._prepared = None

    def status(self) -> dict[str, object]:
        with self._lock:
            retained = 0
            if self._prepared is not None:
                retained = len(self._prepared.acoustic_emission.pcm_s16le)
                binaural = self._prepared.physical_mount.binaural_pcm
                if binaural is not None:
                    retained += (
                        len(binaural.left_pcm_s16le)
                        + len(binaural.right_pcm_s16le)
                    )
            return {
                "companion_port_id": self._companion_port_id,
                "max_pcm_samples_per_experience": MAX_EMITTED_PCM_SAMPLES,
                "max_retained_raw_media_bytes": (
                    3 * MAX_EMITTED_PCM_SAMPLES * 2
                ),
                "prepared": int(self._prepared is not None),
                "retained_raw_media_bytes": retained,
                "schema": "guala.w1.companion_vocal_experience_status.v1",
            }


__all__ = (
    "CompanionVocalIntentReceipt",
    "PreparedCompanionVocalExperience",
    "W1CompanionVocalExperienceAuthority",
)
