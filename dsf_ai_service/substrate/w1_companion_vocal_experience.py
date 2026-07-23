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
from fractions import Fraction

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
    W1AnonymousAcousticVisualCorrespondence,
    W1AudiovisualPhysicalEvidenceAuthority,
    W1EvidenceState,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
)


INTENT_SCHEMA = "guala.w1.companion_vocal_intent.v2"
INTENT_DOMAIN = b"guala.w1.companion_vocal_intent.v2\0"
EPISODE_INTENT_SCHEMA = "guala.w1.companion_vocal_episode_intent.v1"
EPISODE_INTENT_DOMAIN = b"guala.w1.companion_vocal_episode_intent.v1\0"
EPISODE_SCHEMA = "guala.w1.companion_vocal_episode.v1"
EPISODE_AUTHORITY_SCHEMA = "guala.w1.companion_vocal_episode.authority.v1"
EPISODE_AUTHORITY_DOMAIN = b"guala.w1.companion_vocal_episode.authority.v1\0"
MAX_COMPANION_VOCAL_EPISODE_SAMPLES = 8 * 16_000
MAX_COMPANION_VOCAL_EPISODE_AUTHORITY_BYTES = 8 * 1024 * 1024


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
class CompanionVocalEpisodeIntentReceipt:
    companion_port_id: str
    world_observation_receipt_sha256: str
    pcm_sha256: str
    total_sample_count: int
    block_count: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "block_count": self.block_count,
            "companion_port_id": self.companion_port_id,
            "pcm_sha256": self.pcm_sha256,
            "sample_rate_hz": 16_000,
            "schema": EPISODE_INTENT_SCHEMA,
            "total_sample_count": self.total_sample_count,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        if not isinstance(self.companion_port_id, str) or not self.companion_port_id:
            raise ValueError("companion vocal episode port is unavailable")
        _sha256(self.world_observation_receipt_sha256, "world observation")
        _sha256(self.pcm_sha256, "companion episode pressure")
        expected_blocks = (
            self.total_sample_count + MAX_EMITTED_PCM_SAMPLES - 1
        ) // MAX_EMITTED_PCM_SAMPLES
        if (
            isinstance(self.total_sample_count, bool)
            or not isinstance(self.total_sample_count, int)
            or not MIN_EMITTED_PCM_SAMPLES
            <= self.total_sample_count
            <= MAX_COMPANION_VOCAL_EPISODE_SAMPLES
            or isinstance(self.block_count, bool)
            or not isinstance(self.block_count, int)
            or self.block_count != expected_blocks
        ):
            raise ValueError("companion vocal episode extent changed")
        _sha256(self.authority_hmac_sha256, "companion episode intent HMAC")
        _sha256(self.authority_receipt_sha256, "companion episode intent receipt")
        expected_hmac = hmac.new(
            key,
            EPISODE_INTENT_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(self.authority_hmac_sha256, expected_hmac)
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": self.payload(),
            })
        ):
            raise ValueError("companion vocal episode intent authority changed")


@dataclass(frozen=True, slots=True)
class W1CompanionVocalEpisodeBlock:
    sequence: int
    source_sample_start: int
    source_sample_end: int
    world_execution_receipt_sha256: str
    physical_evidence_receipt_sha256: str
    causal_settlement_receipt_sha256: str
    anonymous_av_continuity_receipt_sha256: str
    anonymous_av_correspondence: W1AnonymousAcousticVisualCorrespondence

    @property
    def binaural_l5(self) -> W1BinauralAuditoryL5Experience:
        return self.anonymous_av_correspondence.auditory_l5

    def structural_payload(self) -> dict[str, object]:
        return {
            "anonymous_av_correspondence": (
                self.anonymous_av_correspondence.structural_payload()
            ),
            "sequence": self.sequence,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
        }

    def authority_payload(self) -> dict[str, object]:
        return {
            "anonymous_av_correspondence_authority": (
                self.anonymous_av_correspondence.authority_record()
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "anonymous_av_continuity_receipt_sha256": (
                self.anonymous_av_continuity_receipt_sha256
            ),
            "physical_evidence_receipt_sha256": (
                self.physical_evidence_receipt_sha256
            ),
            "sequence": self.sequence,
            "source_sample_end": self.source_sample_end,
            "source_sample_start": self.source_sample_start,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def verify(self) -> None:
        self.anonymous_av_correspondence.verify_structure()
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or isinstance(self.source_sample_start, bool)
            or not isinstance(self.source_sample_start, int)
            or self.source_sample_start < 0
            or isinstance(self.source_sample_end, bool)
            or not isinstance(self.source_sample_end, int)
            or not self.source_sample_start < self.source_sample_end
            or self.source_sample_end - self.source_sample_start
            > MAX_EMITTED_PCM_SAMPLES
            or self.source_sample_end - self.source_sample_start
            < MIN_EMITTED_PCM_SAMPLES
        ):
            raise ValueError("companion vocal episode block extent changed")
        for value, name in (
            (self.world_execution_receipt_sha256, "world execution"),
            (self.physical_evidence_receipt_sha256, "physical evidence"),
            (self.causal_settlement_receipt_sha256, "causal settlement"),
            (
                self.anonymous_av_continuity_receipt_sha256,
                "audiovisual continuity",
            ),
        ):
            _sha256(value, f"companion episode {name}")
        if (
            self.anonymous_av_correspondence
            .causal_settlement_receipt_sha256
            != self.causal_settlement_receipt_sha256
            or self.binaural_l5.source_time_start
            != Fraction(self.source_sample_start, 16_000)
            or self.binaural_l5.source_time_end
            != Fraction(self.source_sample_end, 16_000)
        ):
            raise ValueError("companion episode L5 lost its causal interval")


@dataclass(frozen=True, slots=True)
class W1CompanionVocalEpisode:
    episode_id: str
    structural_fingerprint: str
    total_sample_count: int
    blocks: tuple[W1CompanionVocalEpisodeBlock, ...]
    intent_authority_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def structural_payload(self) -> dict[str, object]:
        return {
            "blocks": [value.structural_payload() for value in self.blocks],
            "sample_rate_hz": 16_000,
            "schema": EPISODE_SCHEMA,
            "total_sample_count": self.total_sample_count,
        }

    def authority_payload(self) -> dict[str, object]:
        return {
            "blocks": [value.authority_payload() for value in self.blocks],
            "episode_id": self.episode_id,
            "intent_authority_receipt_sha256": (
                self.intent_authority_receipt_sha256
            ),
            "sample_rate_hz": 16_000,
            "schema": EPISODE_AUTHORITY_SCHEMA,
            "structural_fingerprint": self.structural_fingerprint,
            "total_sample_count": self.total_sample_count,
            "world_after_receipt_sha256": self.world_after_receipt_sha256,
            "world_before_receipt_sha256": self.world_before_receipt_sha256,
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        if not isinstance(self.blocks, tuple) or not self.blocks:
            raise ValueError("companion vocal episode has no blocks")
        next_start = 0
        for sequence, block in enumerate(self.blocks):
            block.verify()
            if (
                block.sequence != sequence
                or block.source_sample_start != next_start
            ):
                raise ValueError("companion vocal episode continuity changed")
            next_start = block.source_sample_end
        if next_start != self.total_sample_count:
            raise ValueError("companion vocal episode extent changed")
        for value, name in (
            (self.intent_authority_receipt_sha256, "intent"),
            (self.world_before_receipt_sha256, "world before"),
            (self.world_after_receipt_sha256, "world after"),
            (self.authority_hmac_sha256, "authority HMAC"),
            (self.authority_receipt_sha256, "authority receipt"),
        ):
            _sha256(value, f"companion episode {name}")
        structural = _digest(self.structural_payload())
        if (
            structural != self.structural_fingerprint
            or self.episode_id
            != _digest({"companion_vocal_structure": structural})
        ):
            raise ValueError("companion vocal episode structure changed")
        payload = self.authority_payload()
        encoded = _canonical(payload)
        expected_hmac = hmac.new(
            key,
            EPISODE_AUTHORITY_DOMAIN + encoded,
            hashlib.sha256,
        ).hexdigest()
        if (
            len(encoded) > MAX_COMPANION_VOCAL_EPISODE_AUTHORITY_BYTES
            or not hmac.compare_digest(self.authority_hmac_sha256, expected_hmac)
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError("companion vocal episode authority changed")

    def persistence_record(self, authority_key: bytes | str) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.authority_payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedCompanionVocalExperience:
    epoch_token: str
    world_snapshot: bytes
    intent_receipt: CompanionVocalIntentReceipt
    command_payload: bytes
    execution_receipt: ActionExecutionReceipt
    acoustic_emission: AuthenticatedW1AcousticEmission
    physical_mount: W1PhysicalEvidenceMount


@dataclass(frozen=True, slots=True)
class PreparedCompanionVocalEpisode:
    epoch_token: str
    world_snapshot: bytes
    intent_receipt: CompanionVocalEpisodeIntentReceipt
    episode: W1CompanionVocalEpisode


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
        self._prepared_episode: PreparedCompanionVocalEpisode | None = None
        self._latest_episode: W1CompanionVocalEpisode | None = None
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

    @staticmethod
    def _episode_blocks(pcm_s16le: bytes) -> tuple[bytes, ...]:
        if not isinstance(pcm_s16le, bytes) or len(pcm_s16le) % 2:
            raise ValueError("companion episode pressure must be PCM16 bytes")
        sample_count = len(pcm_s16le) // 2
        if not MIN_EMITTED_PCM_SAMPLES <= sample_count <= (
            MAX_COMPANION_VOCAL_EPISODE_SAMPLES
        ):
            raise ValueError(
                "companion episode pressure exceeds its exact sample boundary"
            )
        block_count = (
            sample_count + MAX_EMITTED_PCM_SAMPLES - 1
        ) // MAX_EMITTED_PCM_SAMPLES
        base, extra = divmod(sample_count, block_count)
        counts = tuple(
            base + (1 if index < extra else 0)
            for index in range(block_count)
        )
        if any(
            value < MIN_EMITTED_PCM_SAMPLES
            or value > MAX_EMITTED_PCM_SAMPLES
            for value in counts
        ):
            raise RuntimeError("companion episode partition changed")
        result = []
        sample_start = 0
        for count in counts:
            result.append(pcm_s16le[sample_start * 2:(sample_start + count) * 2])
            sample_start += count
        if sample_start != sample_count or b"".join(result) != pcm_s16le:
            raise RuntimeError("companion episode partition lost pressure")
        return tuple(result)

    def _issue_episode_intent(
        self,
        *,
        pcm_s16le: bytes,
        block_count: int,
        world_observation_receipt_sha256: str,
    ) -> CompanionVocalEpisodeIntentReceipt:
        provisional = CompanionVocalEpisodeIntentReceipt(
            companion_port_id=self._companion_port_id,
            world_observation_receipt_sha256=(
                world_observation_receipt_sha256
            ),
            pcm_sha256=hashlib.sha256(pcm_s16le).hexdigest(),
            total_sample_count=len(pcm_s16le) // 2,
            block_count=block_count,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._key,
            EPISODE_INTENT_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = CompanionVocalEpisodeIntentReceipt(
            companion_port_id=provisional.companion_port_id,
            world_observation_receipt_sha256=(
                provisional.world_observation_receipt_sha256
            ),
            pcm_sha256=provisional.pcm_sha256,
            total_sample_count=provisional.total_sample_count,
            block_count=provisional.block_count,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._key)
        return result

    def _build_episode(
        self,
        *,
        intent: CompanionVocalEpisodeIntentReceipt,
        blocks: tuple[W1CompanionVocalEpisodeBlock, ...],
        world_before_receipt_sha256: str,
        world_after_receipt_sha256: str,
    ) -> W1CompanionVocalEpisode:
        structural_payload = {
            "blocks": [value.structural_payload() for value in blocks],
            "sample_rate_hz": 16_000,
            "schema": EPISODE_SCHEMA,
            "total_sample_count": intent.total_sample_count,
        }
        fingerprint = _digest(structural_payload)
        provisional = W1CompanionVocalEpisode(
            episode_id=_digest({"companion_vocal_structure": fingerprint}),
            structural_fingerprint=fingerprint,
            total_sample_count=intent.total_sample_count,
            blocks=blocks,
            intent_authority_receipt_sha256=(
                intent.authority_receipt_sha256
            ),
            world_before_receipt_sha256=world_before_receipt_sha256,
            world_after_receipt_sha256=world_after_receipt_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.authority_payload()
        signature = hmac.new(
            self._key,
            EPISODE_AUTHORITY_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1CompanionVocalEpisode(
            episode_id=provisional.episode_id,
            structural_fingerprint=provisional.structural_fingerprint,
            total_sample_count=provisional.total_sample_count,
            blocks=provisional.blocks,
            intent_authority_receipt_sha256=(
                provisional.intent_authority_receipt_sha256
            ),
            world_before_receipt_sha256=(
                provisional.world_before_receipt_sha256
            ),
            world_after_receipt_sha256=(
                provisional.world_after_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._key)
        return result

    def prepare_episode(
        self,
        *,
        pcm_s16le: bytes,
    ) -> PreparedCompanionVocalEpisode:
        """Prepare one known-length vocal act as an atomic W1 episode."""
        pcm_blocks = self._episode_blocks(pcm_s16le)
        with self._lock:
            if self._prepared is not None or self._prepared_episode is not None:
                raise RuntimeError("companion vocal transaction is already prepared")
            world_snapshot = self._world.encoded_snapshot()
            world_before = self._world.observation_snapshot()
            intent = self._issue_episode_intent(
                pcm_s16le=pcm_s16le,
                block_count=len(pcm_blocks),
                world_observation_receipt_sha256=(
                    world_before.authority_receipt_sha256
                ),
            )
            epoch_token = self._physical.begin_atomic_episode()
            mounted: W1PhysicalEvidenceMount | None = None
            episode_blocks = []
            sample_start = 0
            try:
                epoch_commitment = hashlib.sha256(
                    epoch_token.encode("utf-8")
                ).hexdigest()
                for sequence, pcm_block in enumerate(pcm_blocks):
                    block_count = len(pcm_block) // 2
                    before = self._world.observation_snapshot()
                    command_payload = encode_command(VocalizeCommand(
                        epoch_commitment_sha256=epoch_commitment,
                        sequence=sequence,
                        source_sample_start=sample_start,
                        pcm_sha256=hashlib.sha256(pcm_block).hexdigest(),
                        sample_count=block_count,
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
                        raise RuntimeError(
                            "companion vocal episode execution was not applied"
                        )
                    emission = self._physical.emit_acoustic_pressure(
                        epoch_token=epoch_token,
                        sequence=sequence,
                        source_sample_start=sample_start,
                        observation_snapshot=execution.after,
                        execution_receipt=execution,
                        command_payload=command_payload,
                        emitter_port_id=self._companion_port_id,
                        pcm_s16le=pcm_block,
                    )
                    mounted = self._physical.mount(
                        epoch_token=epoch_token,
                        sequence=sequence,
                        execution_receipt=execution,
                        acoustic_emission=emission,
                        commit=False,
                    )
                    if (
                        mounted.state is not W1EvidenceState.OBSERVED
                        or mounted.evidence_receipt is None
                        or mounted.causal_settlement is None
                        or mounted.binaural_auditory_l5 is None
                        or mounted.anonymous_av_correspondence is None
                        or mounted.anonymous_av_continuity is None
                    ):
                        raise RuntimeError(
                            "companion vocal episode block did not settle"
                        )
                    self._physical.verify_mount(mounted)
                    self._physical.commit_prepared_multisensory_mount(mounted)
                    episode_blocks.append(W1CompanionVocalEpisodeBlock(
                        sequence=sequence,
                        source_sample_start=sample_start,
                        source_sample_end=sample_start + block_count,
                        world_execution_receipt_sha256=(
                            execution.authority_receipt_sha256
                        ),
                        physical_evidence_receipt_sha256=(
                            mounted.evidence_receipt.authority_receipt_sha256
                        ),
                        causal_settlement_receipt_sha256=(
                            mounted.causal_settlement.authority_receipt_sha256
                        ),
                        anonymous_av_continuity_receipt_sha256=(
                            mounted.anonymous_av_continuity
                            .authority_receipt_sha256
                        ),
                        anonymous_av_correspondence=(
                            mounted.anonymous_av_correspondence
                        ),
                    ))
                    mounted = None
                    sample_start += block_count
                episode = self._build_episode(
                    intent=intent,
                    blocks=tuple(episode_blocks),
                    world_before_receipt_sha256=(
                        world_before.authority_receipt_sha256
                    ),
                    world_after_receipt_sha256=(
                        self._world.observation_snapshot()
                        .authority_receipt_sha256
                    ),
                )
                prepared = PreparedCompanionVocalEpisode(
                    epoch_token=epoch_token,
                    world_snapshot=world_snapshot,
                    intent_receipt=intent,
                    episode=episode,
                )
                self._prepared_episode = prepared
                return prepared
            except BaseException:
                try:
                    self._physical.rollback_atomic_episode(epoch_token)
                finally:
                    self._world.restore_encoded(world_snapshot)
                raise

    def _require_prepared_episode(
        self,
        prepared: PreparedCompanionVocalEpisode,
    ) -> PreparedCompanionVocalEpisode:
        if not isinstance(prepared, PreparedCompanionVocalEpisode):
            raise TypeError("typed companion vocal episode is required")
        current = self._prepared_episode
        if (
            current is None
            or current.episode.authority_receipt_sha256
            != prepared.episode.authority_receipt_sha256
        ):
            raise ValueError("companion vocal episode preparation changed")
        current.intent_receipt.verify(self._key)
        current.episode.verify(self._key)
        return current

    def verify_episode(self, episode: W1CompanionVocalEpisode) -> None:
        if not isinstance(episode, W1CompanionVocalEpisode):
            raise TypeError("typed companion vocal episode is required")
        episode.verify(self._key)

    def commit_episode(self, prepared: PreparedCompanionVocalEpisode) -> None:
        with self._lock:
            current = self._require_prepared_episode(prepared)
            self._physical.commit_atomic_episode(current.epoch_token)
            self._latest_episode = current.episode
            self._prepared_episode = None

    def discard_episode(self, prepared: PreparedCompanionVocalEpisode) -> None:
        with self._lock:
            current = self._require_prepared_episode(prepared)
            try:
                self._physical.rollback_atomic_episode(current.epoch_token)
            finally:
                self._world.restore_encoded(current.world_snapshot)
            self._prepared_episode = None

    def prepare(
        self,
        *,
        pcm_s16le: bytes,
    ) -> PreparedCompanionVocalExperience:
        sample_count = self._sample_count(pcm_s16le)
        with self._lock:
            if self._prepared is not None or self._prepared_episode is not None:
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
                "has_latest_episode": self._latest_episode is not None,
                "max_episode_authority_bytes": (
                    MAX_COMPANION_VOCAL_EPISODE_AUTHORITY_BYTES
                ),
                "max_episode_samples": MAX_COMPANION_VOCAL_EPISODE_SAMPLES,
                "max_pcm_samples_per_experience": MAX_EMITTED_PCM_SAMPLES,
                "max_retained_raw_media_bytes": (
                    3 * MAX_EMITTED_PCM_SAMPLES * 2
                ),
                "prepared": int(self._prepared is not None),
                "prepared_episode": int(self._prepared_episode is not None),
                "retained_raw_media_bytes": retained,
                "schema": "guala.w1.companion_vocal_experience_status.v2",
            }


__all__ = (
    "CompanionVocalIntentReceipt",
    "CompanionVocalEpisodeIntentReceipt",
    "MAX_COMPANION_VOCAL_EPISODE_AUTHORITY_BYTES",
    "MAX_COMPANION_VOCAL_EPISODE_SAMPLES",
    "PreparedCompanionVocalExperience",
    "PreparedCompanionVocalEpisode",
    "W1CompanionVocalEpisode",
    "W1CompanionVocalEpisodeBlock",
    "W1CompanionVocalExperienceAuthority",
)
