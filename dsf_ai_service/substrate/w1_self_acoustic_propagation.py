"""Exact durable-program self-acoustic propagation into the W1 binaural field.

This authority is separate from anonymous external audiovisual evidence.
The authenticated self-vocal motor already proves which body produced the
PCM.  This owner therefore renders that exact pressure from the self body's
physical centre to the two calibrated ear positions, mounts both ears through
the complete native L0--L4 field, settles W1 binaural L5 and both receptor
events, and only then presents the atomic two-ear settlement to the recurrent
q owner.

No text, label, source classifier, compatibility vector, weighted score, or
reduced DSF projection is admitted.  Raw PCM and delay-line tails exist only
inside the returned transient mount.  The authenticated receipt commits their
digests and the complete causal authority chain.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import threading
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryBinauralMotifCommitUndo,
    AuditoryBinauralMotifFiring,
    AuditoryBinauralMotifObservation,
    AuditoryMotifObservationState,
    AuditoryRecurrentMotifOwner,
    PreparedAuditoryBinauralMotifObservation,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1BinauralCalibration,
    W1BinauralPCM,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_joint_units,
    binaural_sound_field_inputs,
    body_from_snapshot,
    calibrated_ear_positions,
    render_ear_pressure,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
    settle_w1_binaural_receptors,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    physical_receptor_joint_units,
    physical_receptor_substreams,
)


W1_SELF_ACOUSTIC_RECEIPT_SCHEMA = (
    "guala.w1.self_acoustic_propagation.receipt.v1"
)
W1_SELF_ACOUSTIC_DOMAIN = (
    b"guala-w1-self-acoustic-propagation-v1\0"
)
W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA = (
    "guala.w1.self_acoustic_propagation.prepared_commitment.v1"
)
W1_PREPARED_ARTICULATORY_COMMITMENT_DOMAIN = (
    b"guala-w1-self-acoustic-prepared-articulatory-commitment-v1\0"
)
_HEX = frozenset("0123456789abcdef")


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
        raise TypeError("W1 self-acoustic key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 self-acoustic key has an invalid boundary")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("W1 self-acoustic time must be exact")
    return f"{value.numerator}/{value.denominator}"


class W1SelfAcousticState(str, Enum):
    OBSERVED = "observed"
    INDETERMINATE_RESOURCE = "indeterminate_resource"


@dataclass(frozen=True, slots=True)
class W1SelfAcousticReceipt:
    state: W1SelfAcousticState
    reason: str
    motor_id: str
    self_vocal_emission_receipt_sha256: str
    world_execution_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    self_source_position: tuple[int, int, int]
    left_ear_position: tuple[int, int, int]
    right_ear_position: tuple[int, int, int]
    calibration_ear_separation_mm: int
    calibration_reference_distance_mm: int
    binaural_commitment: dict[str, object]
    left_pending_tail_sha256: str
    right_pending_tail_sha256: str
    causal_settlement_receipt_sha256: str
    binaural_l5_receipt_sha256: str
    receptor_settlement_receipt_sha256: str
    prelearning_firing_receipt_sha256: str
    observation_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binaural_commitment": self.binaural_commitment,
            "binaural_l5_receipt_sha256": (
                self.binaural_l5_receipt_sha256
            ),
            "calibration": {
                "ear_separation_mm": (
                    self.calibration_ear_separation_mm
                ),
                "reference_distance_mm": (
                    self.calibration_reference_distance_mm
                ),
            },
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "left_ear_position_mm": list(self.left_ear_position),
            "left_pending_tail_sha256": (
                self.left_pending_tail_sha256
            ),
            "motor_id": self.motor_id,
            "observation_receipt_sha256": (
                self.observation_receipt_sha256
            ),
            "prelearning_firing_receipt_sha256": (
                self.prelearning_firing_receipt_sha256
            ),
            "reason": self.reason,
            "receptor_settlement_receipt_sha256": (
                self.receptor_settlement_receipt_sha256
            ),
            "right_ear_position_mm": list(self.right_ear_position),
            "right_pending_tail_sha256": (
                self.right_pending_tail_sha256
            ),
            "schema": W1_SELF_ACOUSTIC_RECEIPT_SCHEMA,
            "self_source_position_mm": list(
                self.self_source_position
            ),
            "self_vocal_emission_receipt_sha256": (
                self.self_vocal_emission_receipt_sha256
            ),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(
                self.source_time_start
            ),
            "state": self.state.value,
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(authority_key)
        for value, name in (
            (self.motor_id, "W1 self-acoustic motor"),
            (
                self.self_vocal_emission_receipt_sha256,
                "W1 self-acoustic emission",
            ),
            (
                self.world_execution_receipt_sha256,
                "W1 self-acoustic world execution",
            ),
            (
                self.world_before_receipt_sha256,
                "W1 self-acoustic world before",
            ),
            (
                self.world_after_receipt_sha256,
                "W1 self-acoustic world after",
            ),
            (
                self.left_pending_tail_sha256,
                "W1 self-acoustic left propagation tail",
            ),
            (
                self.right_pending_tail_sha256,
                "W1 self-acoustic right propagation tail",
            ),
            (
                self.causal_settlement_receipt_sha256,
                "W1 self-acoustic causal settlement",
            ),
            (
                self.binaural_l5_receipt_sha256,
                "W1 self-acoustic binaural L5",
            ),
            (
                self.receptor_settlement_receipt_sha256,
                "W1 self-acoustic receptor settlement",
            ),
            (
                self.prelearning_firing_receipt_sha256,
                "W1 self-acoustic prelearning firing",
            ),
            (
                self.observation_receipt_sha256,
                "W1 self-acoustic observation",
            ),
            (
                self.authority_receipt_sha256,
                "W1 self-acoustic receipt",
            ),
        ):
            _sha256(value, name)
        if (
            not isinstance(self.state, W1SelfAcousticState)
            or not isinstance(self.reason, str)
            or not self.reason
            or self.reason != self.reason.strip()
            or not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or any(
                not isinstance(position, tuple)
                or len(position) != 3
                or any(
                    isinstance(coordinate, bool)
                    or not isinstance(coordinate, int)
                    for coordinate in position
                )
                for position in (
                    self.self_source_position,
                    self.left_ear_position,
                    self.right_ear_position,
                )
            )
            or isinstance(self.calibration_ear_separation_mm, bool)
            or not isinstance(
                self.calibration_ear_separation_mm, int
            )
            or isinstance(
                self.calibration_reference_distance_mm, bool
            )
            or not isinstance(
                self.calibration_reference_distance_mm, int
            )
            or not isinstance(self.binaural_commitment, dict)
        ):
            raise ValueError("W1 self-acoustic receipt boundary changed")
        signature = hmac.new(
            key,
            W1_SELF_ACOUSTIC_DOMAIN + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })
        ):
            raise ValueError("W1 self-acoustic receipt authority changed")


@dataclass(frozen=True, slots=True)
class W1SelfAcousticMount:
    receipt: W1SelfAcousticReceipt
    binaural_pcm: W1BinauralPCM
    causal_settlement: CausalExperienceSettlement
    binaural_l5: W1BinauralAuditoryL5Experience
    receptor_settlement: W1BinauralReceptorSettlement
    prelearning_firing: AuditoryBinauralMotifFiring
    observation: AuditoryBinauralMotifObservation
    left_pending_tail: tuple[int, ...]
    right_pending_tail: tuple[int, ...]

    def verify(self, authority_key: bytes | str) -> None:
        self.receipt.verify(authority_key)
        self.binaural_pcm.verify()
        self.causal_settlement.verify()
        self.binaural_l5.verify()
        self.receptor_settlement.verify()
        self.prelearning_firing.verify()
        self.observation.verify()
        if (
            self.receipt.binaural_commitment
            != self.binaural_pcm.commitment_record()
            or self.receipt.causal_settlement_receipt_sha256
            != self.causal_settlement.authority_receipt_sha256
            or self.receipt.binaural_l5_receipt_sha256
            != self.binaural_l5.authority_receipt_sha256
            or self.receipt.receptor_settlement_receipt_sha256
            != self.receptor_settlement.authority_receipt_sha256
            or self.receipt.prelearning_firing_receipt_sha256
            != self.prelearning_firing.authority_receipt_sha256
            or self.receipt.observation_receipt_sha256
            != self.observation.authority_receipt_sha256
            or self.binaural_l5.upstream_causal_settlement_receipt_sha256
            != self.causal_settlement.authority_receipt_sha256
            or self.receptor_settlement.upstream_w1_l5
            != self.binaural_l5
            or self.prelearning_firing.source_settlement_receipt_sha256
            != self.receptor_settlement.authority_receipt_sha256
            or self.observation.source_settlement_receipt_sha256
            != self.receptor_settlement.authority_receipt_sha256
            or hashlib.sha256(
                _tail_bytes(self.left_pending_tail)
            ).hexdigest() != self.receipt.left_pending_tail_sha256
            or hashlib.sha256(
                _tail_bytes(self.right_pending_tail)
            ).hexdigest() != self.receipt.right_pending_tail_sha256
        ):
            raise ValueError("W1 self-acoustic mount authority changed")
        q_states = (
            self.prelearning_firing.firing.state,
            self.observation.observation.state,
        )
        expected_state = (
            W1SelfAcousticState.OBSERVED
            if all(
                value is AuditoryMotifObservationState.OBSERVED
                for value in q_states
            )
            else W1SelfAcousticState.INDETERMINATE_RESOURCE
        )
        if self.receipt.state is not expected_state:
            raise ValueError("W1 self-acoustic q state changed")


@dataclass(frozen=True, slots=True)
class _PreparedW1SelfAcousticSensory:
    mount: W1SelfAcousticMount
    causal_sequence_token: str
    l5_sequence_token: str
    motif_preparation: PreparedAuditoryBinauralMotifObservation


_PREPARED_W1_SELF_ACOUSTIC_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class PreparedW1SelfAcousticMount:
    """One complete self-hearing occurrence held before physical emission."""

    prepared_emission: "PreparedArticulatoryGeneratedEmission"
    _sensory: _PreparedW1SelfAcousticSensory = field(repr=False)
    _articulatory_owner: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(slots=True)
class _W1ArticulatoryCommitUndoState:
    causal_undo: object | None = None
    l5_undo: object | None = None
    motif_undo: AuditoryBinauralMotifCommitUndo | None = None
    sealed: bool = False
    rolled_back: bool = False


_W1_ARTICULATORY_COMMIT_UNDO_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class W1ArticulatorySelfAcousticCommitUndo:
    """Opaque authority to undo one current physical/sensory commit."""

    _prepared_world_action: object = field(repr=False, compare=False)
    _state: _W1ArticulatoryCommitUndoState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class W1PreparedArticulatoryCommitment:
    """Public hash-only view of one live private prepared W1 occurrence."""

    program_id: str
    synthesis_receipt_sha256: str
    pcm_sha256: str
    prospective_emission_receipt_sha256: str
    prospective_mount_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "pcm_sha256": self.pcm_sha256,
            "program_id": self.program_id,
            "prospective_emission_receipt_sha256": (
                self.prospective_emission_receipt_sha256
            ),
            "prospective_mount_receipt_sha256": (
                self.prospective_mount_receipt_sha256
            ),
            "schema": W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA,
            "synthesis_receipt_sha256": (
                self.synthesis_receipt_sha256
            ),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        for value, name in (
            (self.program_id, "prepared W1 articulatory program"),
            (
                self.synthesis_receipt_sha256,
                "prepared W1 articulatory synthesis",
            ),
            (self.pcm_sha256, "prepared W1 articulatory pressure"),
            (
                self.prospective_emission_receipt_sha256,
                "prepared W1 articulatory emission",
            ),
            (
                self.prospective_mount_receipt_sha256,
                "prepared W1 articulatory mount",
            ),
            (
                self.world_before_receipt_sha256,
                "prepared W1 world before",
            ),
            (
                self.world_after_receipt_sha256,
                "prepared W1 world after",
            ),
            (
                self.authority_hmac_sha256,
                "prepared W1 articulatory HMAC",
            ),
            (
                self.authority_receipt_sha256,
                "prepared W1 articulatory authority",
            ),
        ):
            _sha256(value, name)
        signature = hmac.new(
            _key(authority_key),
            W1_PREPARED_ARTICULATORY_COMMITMENT_DOMAIN
            + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })
        ):
            raise ValueError(
                "prepared W1 articulatory commitment changed"
            )


@dataclass(frozen=True, slots=True)
class _EmissionReceiptCommitment:
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class _PreparedEmissionView:
    execution_receipt: object
    pcm_s16le: bytes
    emission_receipt: _EmissionReceiptCommitment


def _tail_bytes(values: tuple[int, ...]) -> bytes:
    return b"".join(
        int(value).to_bytes(2, "little", signed=True)
        for value in values
    )


def _position_tuple(value) -> tuple[int, int, int]:
    return (value.x, value.y, value.z)


class W1SelfAcousticPropagationAuthority:
    """Render and settle authenticated self pressure at two physical ears."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        world_authority: EmbodimentWorldAuthority,
        causal_owner: ExactCausalExperienceOwner,
        binaural_l5_owner: W1BinauralAuditoryL5Owner,
        binaural_motif_owner: AuditoryRecurrentMotifOwner,
        calibration: W1BinauralCalibration | None = None,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 self-acoustic propagation requires its world")
        if not isinstance(causal_owner, ExactCausalExperienceOwner):
            raise TypeError(
                "W1 self-acoustic propagation requires exact causal physics"
            )
        if not isinstance(binaural_l5_owner, W1BinauralAuditoryL5Owner):
            raise TypeError(
                "W1 self-acoustic propagation requires W1 binaural L5"
            )
        if not isinstance(
            binaural_motif_owner, AuditoryRecurrentMotifOwner
        ):
            raise TypeError(
                "W1 self-acoustic propagation requires recurrent q"
            )
        if binaural_motif_owner.resource_profile.ear_count != 2:
            raise ValueError(
                "W1 self-acoustic recurrent q must retain both ears"
            )
        self._key = _key(authority_key)
        self._world = world_authority
        self._causal = causal_owner
        self._l5 = binaural_l5_owner
        self._motif = binaural_motif_owner
        self._calibration = calibration or W1BinauralCalibration()
        self._calibration.verify()
        self._prepared_articulatory: PreparedW1SelfAcousticMount | None = None
        self._articulatory_commit_undo_owner_authority = object()
        self._lock = threading.RLock()

    def verify_mount(self, mount: W1SelfAcousticMount) -> None:
        if not isinstance(mount, W1SelfAcousticMount):
            raise TypeError("W1 self-acoustic mount is not typed")
        mount.verify(self._key)

    def owns_world(
        self,
        world_authority: EmbodimentWorldAuthority,
    ) -> bool:
        """Return exact dependency identity, never structural equivalence."""

        return world_authority is self._world

    def _prepare_verified_sensory(
        self,
        *,
        emission,
        motor_id: str,
        verify,
    ) -> _PreparedW1SelfAcousticSensory:
        with self._lock:
            verify()
            execution = emission.execution_receipt
            before_body = body_from_snapshot(
                execution.before, execution.before.self_body_id
            )
            after_body = body_from_snapshot(
                execution.after, execution.after.self_body_id
            )
            if before_body != after_body:
                raise ValueError(
                    "self body moved during its vocal pressure interval"
                )
            ears = calibrated_ear_positions(
                after_body, self._calibration.ear_separation_mm
            )
            if ears is None:
                raise ValueError(
                    "self head orientation lacks exact W1 ear geometry"
                )
            left_ear, right_ear = ears
            source = after_body.pose.position
            samples = tuple(
                item[0]
                for item in struct.iter_unpack("<h", emission.pcm_s16le)
            )
            rendered = []
            for ear in ears:
                rendered.append(render_ear_pressure(
                    samples,
                    source=source,
                    ear=ear,
                    reference_distance_mm=(
                        self._calibration.reference_distance_mm
                    ),
                    pending_samples=(),
                    pending_receipt_sha256s=(),
                    emission_receipt_sha256=(
                        emission.emission_receipt
                        .authority_receipt_sha256
                    ),
                ))
            (
                left_pcm,
                left_pending,
                _left_pending_receipts,
                left_contributors,
                left_delay,
                left_attenuation,
            ) = rendered[0]
            (
                right_pcm,
                right_pending,
                _right_pending_receipts,
                right_contributors,
                right_delay,
                right_attenuation,
            ) = rendered[1]
            expected_contributor = (
                emission.emission_receipt.authority_receipt_sha256,
            )
            if (
                left_contributors != expected_contributor
                or right_contributors != expected_contributor
            ):
                raise RuntimeError(
                    "self-acoustic path lost motor provenance"
                )
            sample_count = len(samples)
            binaural = W1BinauralPCM(
                left_pcm_s16le=left_pcm,
                right_pcm_s16le=right_pcm,
                emitted_sample_count=sample_count,
                left_sample_count=sample_count,
                right_sample_count=sample_count,
                left_delay_samples=left_delay,
                right_delay_samples=right_delay,
                left_attenuation=left_attenuation,
                right_attenuation=right_attenuation,
            )
            binaural.verify()
            source_time_start = Fraction(
                execution.before.revision * MAX_VOCAL_SAMPLE_COUNT,
                VOCAL_SAMPLE_RATE_HZ,
            )
            source_time_end = source_time_start + Fraction(
                sample_count, VOCAL_SAMPLE_RATE_HZ
            )
            left_sound = binaural_sound_field_inputs(
                ear="left",
                topology_index=0,
                pcm=left_pcm,
                source_time_start=source_time_start,
            )
            right_sound = binaural_sound_field_inputs(
                ear="right",
                topology_index=AUDITORY_KERNEL_COMPONENT_COUNT,
                pcm=right_pcm,
                source_time_start=source_time_start,
            )
            sound = (*left_sound, *right_sound)
            if len(sound) != 2 * AUDITORY_KERNEL_COMPONENT_COUNT:
                raise RuntimeError(
                    "self-acoustic W1 field lost a cochlear component"
                )
            observed = physical_receptor_substreams(
                execution.before,
                execution.after,
                causal_transition=True,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
            observed[PhysicalSense.SOUND] = sound
            required_senses = frozenset({
                PhysicalSense.BODY,
                PhysicalSense.SIGHT,
                PhysicalSense.SOUND,
                PhysicalSense.TOUCH,
            })
            if (
                frozenset(observed) != required_senses
                or any(not observed[sense] for sense in required_senses)
            ):
                raise RuntimeError(
                    "self-acoustic W1 occurrence lost a simultaneous "
                    "physical receptor field"
                )
            assembly_id = "w1-self-acoustic-" + _digest({
                "binaural_commitment": binaural.commitment_record(),
                "motor_id": motor_id,
                "self_vocal_emission_receipt_sha256": (
                    emission.emission_receipt
                    .authority_receipt_sha256
                ),
                "world_execution_receipt_sha256": (
                    execution.authority_receipt_sha256
                ),
            })
            declared_units = (
                *physical_receptor_joint_units({
                    sense: ports
                    for sense, ports in observed.items()
                    if sense is not PhysicalSense.SOUND
                }),
                *binaural_joint_units(left_sound, right_sound),
            )
            built = build_transaction_owned_six_sense_full_field(
                assembly_id=assembly_id,
                source_time_start=source_time_start,
                source_time_end=source_time_end,
                observed_substreams=observed,
                states={
                    sense: (
                        SenseBoundaryState.OBSERVED
                        if sense in required_senses
                        else SenseBoundaryState.SENSOR_UNAVAILABLE
                    )
                    for sense in SENSE_ORDER
                },
                occurrences=declare_joint_source_occurrences(
                    observed_substreams=observed,
                    declared_units=declared_units,
                ),
            )
            causal_token = self._causal.begin_atomic_sequence()
            try:
                l5_token = self._l5.begin_atomic_sequence()
            except BaseException:
                self._causal.rollback_atomic_sequence(causal_token)
                raise
            settlement = None
            binaural_l5 = None
            motif_preparation = None
            causal_staged = False
            l5_staged = False
            try:
                settlement = self._causal.settle(
                    built,
                    routing_chis=(),
                    source_tags=(),
                    commit=False,
                    reserve=True,
                )
                binaural_l5 = self._l5.prepare(settlement)
                receptors = settle_w1_binaural_receptors(
                    left_custody=left_sound,
                    right_custody=right_sound,
                    causal_settlement=settlement,
                    w1_l5=binaural_l5,
                )
                self._causal.commit_prepared(settlement)
                causal_staged = True
                self._l5.commit_prepared(binaural_l5)
                l5_staged = True
                prelearning = self._motif.fire_binaural(receptors)
                motif_preparation = self._motif.prepare_binaural(
                    receptors
                )
                observation = motif_preparation.observation
                mount = self._finish_mount(
                    emission=emission,
                    motor_id=motor_id,
                    execution=execution,
                    binaural=binaural,
                    settlement=settlement,
                    binaural_l5=binaural_l5,
                    receptors=receptors,
                    prelearning=prelearning,
                    observation=observation,
                    source_time_start=source_time_start,
                    source_time_end=source_time_end,
                    source=source,
                    left_ear=left_ear,
                    right_ear=right_ear,
                    left_pending=left_pending,
                    right_pending=right_pending,
                )
            except BaseException:
                if motif_preparation is not None:
                    self._motif.discard_prepared_binaural(
                        motif_preparation
                    )
                if binaural_l5 is not None and not l5_staged:
                    self._l5.discard_prepared(binaural_l5)
                if (
                    settlement is not None
                    and not causal_staged
                ):
                    self._causal.discard_prepared(settlement)
                self._l5.rollback_atomic_sequence(l5_token)
                self._causal.rollback_atomic_sequence(causal_token)
                raise
            return _PreparedW1SelfAcousticSensory(
                mount=mount,
                causal_sequence_token=causal_token,
                l5_sequence_token=l5_token,
                motif_preparation=motif_preparation,
            )

    def _finish_mount(
        self,
        *,
        emission,
        motor_id: str,
        execution,
        binaural: W1BinauralPCM,
        settlement: CausalExperienceSettlement,
        binaural_l5: W1BinauralAuditoryL5Experience,
        receptors: W1BinauralReceptorSettlement,
        prelearning: AuditoryBinauralMotifFiring,
        observation: AuditoryBinauralMotifObservation,
        source_time_start: Fraction,
        source_time_end: Fraction,
        source,
        left_ear,
        right_ear,
        left_pending: tuple[int, ...],
        right_pending: tuple[int, ...],
    ) -> W1SelfAcousticMount:
        q_states = (
            prelearning.firing.state,
            observation.observation.state,
        )
        state = (
            W1SelfAcousticState.OBSERVED
            if all(
                value is AuditoryMotifObservationState.OBSERVED
                for value in q_states
            )
            else W1SelfAcousticState.INDETERMINATE_RESOURCE
        )
        reason = (
            "self_motor_pressure_settled_at_both_physical_ears"
            if state is W1SelfAcousticState.OBSERVED
            else "recurrent_q_resource_authority_exhausted"
        )
        emission_receipt_sha256 = (
            emission.emission_receipt.authority_receipt_sha256
        )
        left_tail_sha256 = hashlib.sha256(
            _tail_bytes(left_pending)
        ).hexdigest()
        right_tail_sha256 = hashlib.sha256(
            _tail_bytes(right_pending)
        ).hexdigest()
        receipt_payload = {
            "binaural_commitment": binaural.commitment_record(),
            "binaural_l5_receipt_sha256": (
                binaural_l5.authority_receipt_sha256
            ),
            "calibration": {
                "ear_separation_mm": (
                    self._calibration.ear_separation_mm
                ),
                "reference_distance_mm": (
                    self._calibration.reference_distance_mm
                ),
            },
            "causal_settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "left_ear_position_mm": list(_position_tuple(left_ear)),
            "left_pending_tail_sha256": left_tail_sha256,
            "motor_id": motor_id,
            "observation_receipt_sha256": (
                observation.authority_receipt_sha256
            ),
            "prelearning_firing_receipt_sha256": (
                prelearning.authority_receipt_sha256
            ),
            "reason": reason,
            "receptor_settlement_receipt_sha256": (
                receptors.authority_receipt_sha256
            ),
            "right_ear_position_mm": list(_position_tuple(right_ear)),
            "right_pending_tail_sha256": right_tail_sha256,
            "schema": W1_SELF_ACOUSTIC_RECEIPT_SCHEMA,
            "self_source_position_mm": list(_position_tuple(source)),
            "self_vocal_emission_receipt_sha256": (
                emission_receipt_sha256
            ),
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
            "state": state.value,
            "world_after_receipt_sha256": (
                execution.after.authority_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                execution.before.authority_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                execution.authority_receipt_sha256
            ),
        }
        signature = hmac.new(
            self._key,
            W1_SELF_ACOUSTIC_DOMAIN + _canonical(receipt_payload),
            hashlib.sha256,
        ).hexdigest()
        receipt = W1SelfAcousticReceipt(
            state=state,
            reason=reason,
            motor_id=motor_id,
            self_vocal_emission_receipt_sha256=(
                emission_receipt_sha256
            ),
            world_execution_receipt_sha256=(
                execution.authority_receipt_sha256
            ),
            world_before_receipt_sha256=(
                execution.before.authority_receipt_sha256
            ),
            world_after_receipt_sha256=(
                execution.after.authority_receipt_sha256
            ),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            self_source_position=_position_tuple(source),
            left_ear_position=_position_tuple(left_ear),
            right_ear_position=_position_tuple(right_ear),
            calibration_ear_separation_mm=(
                self._calibration.ear_separation_mm
            ),
            calibration_reference_distance_mm=(
                self._calibration.reference_distance_mm
            ),
            binaural_commitment=binaural.commitment_record(),
            left_pending_tail_sha256=left_tail_sha256,
            right_pending_tail_sha256=right_tail_sha256,
            causal_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            binaural_l5_receipt_sha256=(
                binaural_l5.authority_receipt_sha256
            ),
            receptor_settlement_receipt_sha256=(
                receptors.authority_receipt_sha256
            ),
            prelearning_firing_receipt_sha256=(
                prelearning.authority_receipt_sha256
            ),
            observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": receipt_payload,
            }),
        )
        mount = W1SelfAcousticMount(
            receipt=receipt,
            binaural_pcm=binaural,
            causal_settlement=settlement,
            binaural_l5=binaural_l5,
            receptor_settlement=receptors,
            prelearning_firing=prelearning,
            observation=observation,
            left_pending_tail=left_pending,
            right_pending_tail=right_pending,
        )
        mount.verify(self._key)
        return mount

    def _discard_unpublished_sensory(
        self,
        prepared: _PreparedW1SelfAcousticSensory,
    ) -> None:
        self._motif.discard_prepared_binaural(
            prepared.motif_preparation
        )
        self._l5.rollback_atomic_sequence(
            prepared.l5_sequence_token
        )
        self._causal.rollback_atomic_sequence(
            prepared.causal_sequence_token
        )

    def _rollback_published_sensory(
        self,
        prepared: _PreparedW1SelfAcousticSensory,
        *,
        causal_undo=None,
        l5_undo=None,
        motif_undo: AuditoryBinauralMotifCommitUndo | None = None,
    ) -> None:
        if motif_undo is not None:
            self._motif.rollback_committed_binaural(motif_undo)
        if l5_undo is not None:
            self._l5.rollback_committed_atomic_sequence(l5_undo)
        if causal_undo is not None:
            self._causal.rollback_committed_atomic_sequence(
                causal_undo
            )
        self._discard_unpublished_sensory(prepared)

    def _require_prepared_articulatory_locked(
        self,
        prepared: PreparedW1SelfAcousticMount,
    ) -> PreparedW1SelfAcousticMount:
        from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
            ArticulatorySelfVocalMotorOwner,
            PreparedArticulatoryGeneratedEmission,
        )

        if (
            not isinstance(prepared, PreparedW1SelfAcousticMount)
            or prepared._construction_authority
            is not _PREPARED_W1_SELF_ACOUSTIC_AUTHORITY
            or self._prepared_articulatory is not prepared
            or not isinstance(
                prepared.prepared_emission,
                PreparedArticulatoryGeneratedEmission,
            )
            or not isinstance(
                prepared._articulatory_owner,
                ArticulatorySelfVocalMotorOwner,
            )
        ):
            raise ValueError(
                "prepared W1 self-acoustic mount changed custody"
            )
        prepared._articulatory_owner.verify_prepared_generated_emission(
            prepared.prepared_emission,
            world_authority=self._world,
        )
        prepared._sensory.mount.verify(self._key)
        if (
            prepared._sensory.mount.receipt
            .self_vocal_emission_receipt_sha256
            != prepared.prepared_emission
            .prospective_emission_receipt_sha256
        ):
            raise ValueError(
                "prepared W1 mount lost prospective emission authority"
            )
        return prepared

    def prepare_articulatory(
        self,
        prepared_emission,
        *,
        articulatory_owner,
    ) -> PreparedW1SelfAcousticMount:
        """Prepare complete self-hearing before generated pressure is emitted."""

        from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
            ArticulatorySelfVocalMotorOwner,
            PreparedArticulatoryGeneratedEmission,
        )

        if not isinstance(
            prepared_emission,
            PreparedArticulatoryGeneratedEmission,
        ):
            raise TypeError(
                "prepared W1 self-acoustic input is not articulatory"
            )
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "prepared W1 self-acoustic owner is not articulatory"
            )
        with self._lock:
            if self._prepared_articulatory is not None:
                raise RuntimeError(
                    "W1 self-acoustic articulatory mount is already prepared"
                )
            emission_view = _PreparedEmissionView(
                execution_receipt=(
                    prepared_emission.prepared_world_action
                    .execution_receipt
                ),
                pcm_s16le=prepared_emission.pcm_s16le,
                emission_receipt=_EmissionReceiptCommitment(
                    prepared_emission
                    .prospective_emission_receipt_sha256
                ),
            )
            sensory = None
            try:
                sensory = self._prepare_verified_sensory(
                    emission=emission_view,
                    motor_id=(
                        prepared_emission.synthesis.program.program_id
                    ),
                    verify=lambda: (
                        articulatory_owner
                        .verify_prepared_generated_emission(
                            prepared_emission,
                            world_authority=self._world,
                        )
                    ),
                )
                prepared = PreparedW1SelfAcousticMount(
                    prepared_emission=prepared_emission,
                    _sensory=sensory,
                    _articulatory_owner=articulatory_owner,
                    _construction_authority=(
                        _PREPARED_W1_SELF_ACOUSTIC_AUTHORITY
                    ),
                )
                self._prepared_articulatory = prepared
                self._require_prepared_articulatory_locked(prepared)
            except BaseException:
                if sensory is not None:
                    self._discard_unpublished_sensory(sensory)
                articulatory_owner.discard_prepared_generated_emission(
                    prepared_emission,
                    world_authority=self._world,
                )
                self._prepared_articulatory = None
                raise
            return prepared

    def prepared_articulatory_commitment(
        self,
        prepared: PreparedW1SelfAcousticMount,
    ) -> W1PreparedArticulatoryCommitment:
        """Return only authenticated hashes for one live prepared occurrence."""

        with self._lock:
            current = self._require_prepared_articulatory_locked(prepared)
            emission = current.prepared_emission
            mount_receipt = current._sensory.mount.receipt
            provisional = W1PreparedArticulatoryCommitment(
                program_id=emission.synthesis.program.program_id,
                synthesis_receipt_sha256=(
                    emission.synthesis.receipt.authority_receipt_sha256
                ),
                pcm_sha256=hashlib.sha256(
                    emission.pcm_s16le
                ).hexdigest(),
                prospective_emission_receipt_sha256=(
                    emission.prospective_emission_receipt_sha256
                ),
                prospective_mount_receipt_sha256=(
                    mount_receipt.authority_receipt_sha256
                ),
                world_before_receipt_sha256=(
                    emission.prepared_world_action.execution_receipt
                    .before.authority_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    emission.prepared_world_action.execution_receipt
                    .after.authority_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._key,
                W1_PREPARED_ARTICULATORY_COMMITMENT_DOMAIN
                + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            result = W1PreparedArticulatoryCommitment(
                **{
                    name: getattr(provisional, name)
                    for name in (
                        "program_id",
                        "synthesis_receipt_sha256",
                        "pcm_sha256",
                        "prospective_emission_receipt_sha256",
                        "prospective_mount_receipt_sha256",
                        "world_before_receipt_sha256",
                        "world_after_receipt_sha256",
                    )
                },
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            result.verify(self._key)
            return result

    def verify_prepared_articulatory_commitment(
        self,
        prepared: PreparedW1SelfAcousticMount,
        commitment: W1PreparedArticulatoryCommitment,
    ) -> None:
        """Prove a hash view belongs to this exact live preparation."""

        if not isinstance(
            commitment,
            W1PreparedArticulatoryCommitment,
        ):
            raise TypeError(
                "prepared W1 articulatory commitment is not typed"
            )
        with self._lock:
            self._require_prepared_articulatory_locked(prepared)
            commitment.verify(self._key)
            expected = self.prepared_articulatory_commitment(prepared)
            if commitment != expected:
                raise ValueError(
                    "prepared W1 articulatory commitment changed custody"
                )

    def commit_prepared_articulatory(
        self,
        prepared: PreparedW1SelfAcousticMount,
    ) -> tuple[
        "ArticulatoryGeneratedEmission",
        W1SelfAcousticMount,
        W1ArticulatorySelfAcousticCommitUndo,
    ]:
        """Commit one atomic event and return its owner-bound exact undo."""

        with self._lock:
            current = self._require_prepared_articulatory_locked(prepared)
            world_committed = False
            undo_state = _W1ArticulatoryCommitUndoState()
            undo = W1ArticulatorySelfAcousticCommitUndo(
                _prepared_world_action=(
                    current.prepared_emission.prepared_world_action
                ),
                _state=undo_state,
                _owner_authority=(
                    self._articulatory_commit_undo_owner_authority
                ),
                _construction_authority=(
                    _W1_ARTICULATORY_COMMIT_UNDO_AUTHORITY
                ),
            )
            try:
                causal_install = (
                    self._causal.preverify_atomic_visibility_install(
                        current._sensory.causal_sequence_token
                    )
                )
                l5_install = (
                    self._l5.preverify_atomic_visibility_install(
                        current._sensory.l5_sequence_token
                    )
                )
                motif_install = (
                    self._motif.preverify_binaural_visibility_install(
                        current._sensory.motif_preparation
                    )
                )
                motor_commit = (
                    current._articulatory_owner
                    .preverify_generated_emission_commit(
                        current.prepared_emission,
                        world_authority=self._world,
                    )
                )
                (
                    current._articulatory_owner
                    .verify_preverified_generated_emission_commit(
                        motor_commit,
                        world_authority=self._world,
                    )
                )
                with (
                    current._articulatory_owner
                    .preverified_generated_emission_transaction(
                        motor_commit,
                        world_authority=self._world,
                    ) as commit_motor,
                    self._world
                    .prepared_action_visibility_transaction(
                        current.prepared_emission
                        .prepared_world_action
                    ),
                    self._causal.atomic_visibility_transaction(
                        causal_install
                    ) as install_causal,
                    self._l5.atomic_visibility_transaction(
                        l5_install
                    ) as install_l5,
                    self._motif.binaural_visibility_transaction(
                        motif_install
                    ) as install_motif,
                ):
                    emission = commit_motor()
                    world_committed = True
                    undo_state.causal_undo = install_causal()
                    undo_state.l5_undo = install_l5()
                    undo_state.motif_undo = install_motif()
                    self._prepared_articulatory = None
                    undo_state.sealed = True
            except BaseException:
                assert not world_committed
                self._discard_unpublished_sensory(current._sensory)
                (
                    current._articulatory_owner
                    .discard_prepared_generated_emission(
                        current.prepared_emission,
                        world_authority=self._world,
                    )
                )
                self._prepared_articulatory = None
                raise
            return emission, current._sensory.mount, undo

    def rollback_committed_articulatory(
        self,
        undo: W1ArticulatorySelfAcousticCommitUndo,
    ) -> None:
        """Undo one still-current world and full sensory commit atomically."""

        with self._lock:
            if (
                not isinstance(
                    undo,
                    W1ArticulatorySelfAcousticCommitUndo,
                )
                or undo._construction_authority
                is not _W1_ARTICULATORY_COMMIT_UNDO_AUTHORITY
                or undo._owner_authority
                is not self._articulatory_commit_undo_owner_authority
                or not undo._state.sealed
                or undo._state.rolled_back
                or undo._state.causal_undo is None
                or undo._state.l5_undo is None
                or undo._state.motif_undo is None
                or self._prepared_articulatory is not None
            ):
                raise ValueError(
                    "W1 articulatory commit undo changed custody"
                )
            state = undo._state
            with (
                self._world
                .committed_prepared_action_rollback_transaction(
                    undo._prepared_world_action
                ) as rollback_world,
                self._causal
                .committed_atomic_sequence_rollback_transaction(
                    state.causal_undo
                ) as rollback_causal,
                self._l5
                .committed_atomic_sequence_rollback_transaction(
                    state.l5_undo
                ) as rollback_l5,
                self._motif.committed_binaural_rollback_transaction(
                    state.motif_undo
                ) as rollback_motif,
            ):
                rollback_motif()
                rollback_l5()
                rollback_causal()
                rollback_world()
                state.rolled_back = True

    def discard_prepared_articulatory(
        self,
        prepared: PreparedW1SelfAcousticMount,
    ) -> None:
        """Discard staged self-hearing and its uncommitted physical pressure."""

        with self._lock:
            current = self._require_prepared_articulatory_locked(prepared)
            self._discard_unpublished_sensory(current._sensory)
            current._articulatory_owner.discard_prepared_generated_emission(
                current.prepared_emission,
                world_authority=self._world,
            )
            self._prepared_articulatory = None


__all__ = [
    "PreparedW1SelfAcousticMount",
    "W1ArticulatorySelfAcousticCommitUndo",
    "W1PreparedArticulatoryCommitment",
    "W1_PREPARED_ARTICULATORY_COMMITMENT_SCHEMA",
    "W1SelfAcousticMount",
    "W1SelfAcousticPropagationAuthority",
    "W1SelfAcousticReceipt",
    "W1SelfAcousticState",
]
