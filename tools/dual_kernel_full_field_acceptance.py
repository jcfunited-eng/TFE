"""Independent, lossless dual-kernel full-field acceptance harness.

The harness gives the same authenticated raw binaural pressure and the same
authenticated non-auditory causal grid independently to:

* the canonical production native-sensory L0--L4 transaction builder; and
* the isolated, non-canonical near-v1.3 VTVR side kernel.

The resulting fields remain separate typed objects.  No compatibility vector,
score, field projection, cross-kernel input, identity claim, or learning claim
is created.  The only common downstream authority is an authenticated envelope
that cites both complete branch receipts and their one common raw encounter.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import TypeAlias

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
    NativeSensorySubstreamInput,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
    signed_pcm16_samples,
)
from tools.isolated_vtvr_side_kernel_v2 import (
    JointFieldInput,
    SideKernelExperience,
    run_side_kernel,
)
from tools.isolated_w1_physical_stereo_path import (
    PhysicalStereoAuditAuthority,
    PhysicalStereoCapture,
)


RAW_ENCOUNTER_SCHEMA = "guala.audit.dual_kernel_raw_encounter.v1"
ACCEPTANCE_SCHEMA = "guala.audit.dual_kernel_full_field_acceptance.v1"
CANONICAL_KERNEL_ID = "guala.production.canonical_native_l0_l4"
SIDE_KERNEL_ID = "guala.research.near_v1_3_vtvr_side_kernel.v2"
NO_LEARNING_CLAIM = "evidence_only_no_learning_claim"
_RAW_DOMAIN = b"guala-audit-dual-kernel-raw-encounter-v1\0"
_ACCEPTANCE_DOMAIN = b"guala-audit-dual-kernel-acceptance-v1\0"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    result = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4_096:
        raise ValueError("dual-kernel authority key changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("dual-kernel evidence must remain exact")
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class LivedNonauditoryChannel:
    """One unflattened physical channel on the encounter's causal grid."""

    sense: PhysicalSense
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[NativeAxisCoordinate, ...]
    physical_quantity: str
    physical_unit: str
    source_times: tuple[Fraction, ...]
    signal: tuple[Fraction, ...]
    phase_turns: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sense, PhysicalSense)
            or self.sense is PhysicalSense.SOUND
        ):
            raise ValueError(
                "lived non-auditory channel requires a non-sound sense"
            )
        if (
            not isinstance(self.sensor_id, str)
            or not self.sensor_id
            or not isinstance(self.substream_id, str)
            or not self.substream_id
            or isinstance(self.topology_index, bool)
            or not isinstance(self.topology_index, int)
            or self.topology_index < 0
            or not self.coordinates
            or not all(
                isinstance(value, NativeAxisCoordinate)
                for value in self.coordinates
            )
            or not isinstance(self.physical_quantity, str)
            or not self.physical_quantity
            or not isinstance(self.physical_unit, str)
            or not self.physical_unit
            or not self.source_times
            or len(self.source_times) != len(self.signal)
            or len(self.source_times) != len(self.phase_turns)
        ):
            raise ValueError("lived non-auditory channel is incomplete")
        prior: Fraction | None = None
        for index, (timestamp, signal, phase) in enumerate(zip(
            self.source_times,
            self.signal,
            self.phase_turns,
            strict=True,
        )):
            if (
                not isinstance(timestamp, Fraction)
                or not isinstance(signal, Fraction)
                or not isinstance(phase, Fraction)
            ):
                raise TypeError(
                    f"lived non-auditory sample {index} is not exact"
                )
            if prior is not None and timestamp <= prior:
                raise ValueError(
                    "lived non-auditory causal times must increase"
                )
            prior = timestamp
            if not -1 <= signal <= 1:
                raise ValueError(
                    "lived non-auditory signal left the physical boundary"
                )
            if Fraction.from_float(float(signal)) != signal:
                raise ValueError(
                    "lived non-auditory signal is not lossless at the "
                    "canonical binary64 intake"
                )

    @property
    def vertex_id(self) -> str:
        return (
            f"{self.sense.value}:{self.sensor_id}:"
            f"{self.substream_id}:{self.topology_index}"
        )

    def raw_record(self) -> dict[str, object]:
        return {
            "coordinates": [
                [value.axis_id, value.coordinate_id]
                for value in self.coordinates
            ],
            "phase_turns": [
                _fraction_text(value) for value in self.phase_turns
            ],
            "physical_quantity": self.physical_quantity,
            "physical_unit": self.physical_unit,
            "sense": self.sense.value,
            "sensor_id": self.sensor_id,
            "signal": [_fraction_text(value) for value in self.signal],
            "source_times": [
                _fraction_text(value) for value in self.source_times
            ],
            "substream_id": self.substream_id,
            "topology_index": self.topology_index,
            "vertex_id": self.vertex_id,
        }

    def canonical_input(self) -> NativeSensorySubstreamInput:
        result = NativeSensorySubstreamInput(
            sense=self.sense,
            sensor_id=self.sensor_id,
            substream_id=self.substream_id,
            topology_index=self.topology_index,
            coordinates=self.coordinates,
            physical_quantity=self.physical_quantity,
            physical_unit=self.physical_unit,
            source_times=self.source_times,
            normalized_signal=tuple(float(value) for value in self.signal),
            phase_turns=self.phase_turns,
        )
        if tuple(
            Fraction.from_float(value)
            for value in result.normalized_signal
        ) != self.signal:
            raise RuntimeError(
                "canonical native intake changed non-auditory evidence"
            )
        return result


@dataclass(frozen=True, slots=True)
class AuthenticatedDualKernelEncounter:
    """Authenticated common raw custody; never a kernel interpretation."""

    capture: PhysicalStereoCapture
    world_observation_receipt_sha256: str
    source_time_start: Fraction
    nonauditory_channels: tuple[LivedNonauditoryChannel, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def source_times(self) -> tuple[Fraction, ...]:
        return self.nonauditory_channels[0].source_times

    @property
    def source_time_end(self) -> Fraction:
        return self.source_time_start + Fraction(
            self.capture.capture_sample_count,
            PCM_SAMPLE_RATE_HZ,
        )

    def unsigned_record(self) -> dict[str, object]:
        return {
            "capture_authority_receipt_sha256": (
                self.capture.authority_receipt_sha256
            ),
            "left_pcm_sha256": hashlib.sha256(
                self.capture.left_pcm_s16le
            ).hexdigest(),
            "nonauditory_channels": [
                value.raw_record()
                for value in self.nonauditory_channels
            ],
            "right_pcm_sha256": hashlib.sha256(
                self.capture.right_pcm_s16le
            ).hexdigest(),
            "schema": RAW_ENCOUNTER_SCHEMA,
            "source_time_start": _fraction_text(
                self.source_time_start
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class SideVertexProvenance:
    vertex_id: str
    sense: str
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]
    physical_quantity: str
    physical_unit: str

    def record(self) -> dict[str, object]:
        return {
            "coordinates": [list(value) for value in self.coordinates],
            "physical_quantity": self.physical_quantity,
            "physical_unit": self.physical_unit,
            "sense": self.sense,
            "sensor_id": self.sensor_id,
            "substream_id": self.substream_id,
            "topology_index": self.topology_index,
            "vertex_id": self.vertex_id,
        }


@dataclass(frozen=True, slots=True)
class CanonicalProductionFieldEvidence:
    kernel_id: str
    raw_encounter_receipt_sha256: str
    full_field: BuiltSixSenseFullField

    def verify(self) -> None:
        if self.kernel_id != CANONICAL_KERNEL_ID:
            raise ValueError("canonical production kernel identity changed")
        _sha256(
            self.raw_encounter_receipt_sha256,
            "canonical raw encounter",
        )
        if not isinstance(self.full_field, BuiltSixSenseFullField):
            raise TypeError("canonical evidence is not a typed full field")
        self.full_field.verify_construction()
        self.full_field.boundary.verify(
            self.full_field.receipt_registry
        )

    @property
    def field_receipt_sha256(self) -> str:
        return self.full_field.boundary.authority_receipt_sha256


@dataclass(frozen=True, slots=True)
class NearV13VTVRFieldEvidence:
    kernel_id: str
    raw_encounter_receipt_sha256: str
    vertex_provenance: tuple[SideVertexProvenance, ...]
    full_field: SideKernelExperience

    def verify(self) -> None:
        if self.kernel_id != SIDE_KERNEL_ID:
            raise ValueError("VTVR side-kernel identity changed")
        _sha256(
            self.raw_encounter_receipt_sha256,
            "side-kernel raw encounter",
        )
        if not isinstance(self.full_field, SideKernelExperience):
            raise TypeError("side evidence is not a typed VTVR full field")
        self.full_field.verify()
        if (
            not self.vertex_provenance
            or tuple(
                value.vertex_id for value in self.vertex_provenance
            ) != self.full_field.joint_input.vertex_ids
            or len({
                value.vertex_id for value in self.vertex_provenance
            }) != len(self.vertex_provenance)
        ):
            raise ValueError("VTVR vertex provenance was flattened")

    @property
    def field_receipt_sha256(self) -> str:
        return self.full_field.authority_receipt_sha256


KernelFieldEvidence: TypeAlias = (
    CanonicalProductionFieldEvidence | NearV13VTVRFieldEvidence
)


@dataclass(frozen=True, slots=True)
class DualKernelFullFieldAcceptance:
    """The sole common boundary; its branch fields remain disjoint."""

    raw_encounter: AuthenticatedDualKernelEncounter
    kernel_fields: tuple[KernelFieldEvidence, ...]
    disposition: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def canonical(self) -> CanonicalProductionFieldEvidence:
        value = self.kernel_fields[0]
        if not isinstance(value, CanonicalProductionFieldEvidence):
            raise RuntimeError("canonical branch position changed")
        return value

    @property
    def side(self) -> NearV13VTVRFieldEvidence:
        value = self.kernel_fields[1]
        if not isinstance(value, NearV13VTVRFieldEvidence):
            raise RuntimeError("side branch position changed")
        return value

    def unsigned_record(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "kernel_fields": [
                {
                    "field_receipt_sha256": value.field_receipt_sha256,
                    "kernel_id": value.kernel_id,
                    "raw_encounter_receipt_sha256": (
                        value.raw_encounter_receipt_sha256
                    ),
                    "vertex_provenance": (
                        [
                            provenance.record()
                            for provenance in value.vertex_provenance
                        ]
                        if isinstance(
                            value, NearV13VTVRFieldEvidence
                        )
                        else None
                    ),
                }
                for value in self.kernel_fields
            ],
            "raw_encounter_receipt_sha256": (
                self.raw_encounter.authority_receipt_sha256
            ),
            "schema": ACCEPTANCE_SCHEMA,
        }


class DualKernelFullFieldAcceptanceHarness:
    """Stateless owner of one independent, evidence-only dual execution."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        capture_authority: PhysicalStereoAuditAuthority,
    ) -> None:
        root = hashlib.sha256(_key(authority_key)).digest()
        self._raw_key = hashlib.sha256(_RAW_DOMAIN + root).digest()
        self._acceptance_key = hashlib.sha256(
            _ACCEPTANCE_DOMAIN + root
        ).digest()
        if not isinstance(
            capture_authority, PhysicalStereoAuditAuthority
        ):
            raise TypeError(
                "dual-kernel harness requires a typed capture authority"
            )
        self._capture_authority = capture_authority

    def _authenticate_raw(
        self,
        *,
        capture: PhysicalStereoCapture,
        world_observation_receipt_sha256: str,
        source_time_start: Fraction,
        nonauditory_channels: tuple[LivedNonauditoryChannel, ...],
    ) -> AuthenticatedDualKernelEncounter:
        self._capture_authority.verify_capture(capture)
        _sha256(
            world_observation_receipt_sha256,
            "lived world observation",
        )
        if not isinstance(source_time_start, Fraction):
            raise TypeError("dual-kernel source time must remain exact")
        if (
            not isinstance(nonauditory_channels, tuple)
            or not nonauditory_channels
            or not all(
                isinstance(value, LivedNonauditoryChannel)
                for value in nonauditory_channels
            )
        ):
            raise ValueError(
                "dual-kernel encounter requires typed non-auditory evidence"
            )
        expected_times = tuple(
            source_time_start + Fraction(index, PCM_SAMPLE_RATE_HZ)
            for index in range(capture.capture_sample_count)
        )
        if any(
            value.source_times != expected_times
            for value in nonauditory_channels
        ):
            raise ValueError(
                "dual-kernel branches require one unchanged causal grid"
            )
        identities = tuple(
            (value.sense, value.topology_index)
            for value in nonauditory_channels
        )
        vertex_ids = tuple(
            value.vertex_id for value in nonauditory_channels
        )
        if (
            len(set(identities)) != len(identities)
            or len(set(vertex_ids)) != len(vertex_ids)
        ):
            raise ValueError(
                "dual-kernel non-auditory topology is not unique"
            )
        provisional = AuthenticatedDualKernelEncounter(
            capture=capture,
            world_observation_receipt_sha256=(
                world_observation_receipt_sha256
            ),
            source_time_start=source_time_start,
            nonauditory_channels=nonauditory_channels,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.unsigned_record()
        signature = hmac.new(
            self._raw_key,
            _RAW_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = AuthenticatedDualKernelEncounter(
            capture=capture,
            world_observation_receipt_sha256=(
                world_observation_receipt_sha256
            ),
            source_time_start=source_time_start,
            nonauditory_channels=nonauditory_channels,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self._verify_raw(result)
        return result

    def _verify_raw(
        self,
        value: AuthenticatedDualKernelEncounter,
    ) -> None:
        if not isinstance(value, AuthenticatedDualKernelEncounter):
            raise TypeError("dual-kernel raw encounter is not typed")
        self._capture_authority.verify_capture(value.capture)
        payload = value.unsigned_record()
        expected_hmac = hmac.new(
            self._raw_key,
            _RAW_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        expected_receipt = _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": payload,
        })
        if (
            not hmac.compare_digest(
                expected_hmac, value.authority_hmac_sha256
            )
            or expected_receipt != value.authority_receipt_sha256
        ):
            raise ValueError("dual-kernel raw encounter authority changed")

    @staticmethod
    def _canonical_branch(
        raw: AuthenticatedDualKernelEncounter,
    ) -> CanonicalProductionFieldEvidence:
        observed: dict[
            PhysicalSense,
            tuple[NativeSensorySubstreamInput, ...],
        ] = {
            PhysicalSense.SOUND: (
                *binaural_sound_field_inputs(
                    ear="left",
                    topology_index=0,
                    pcm=raw.capture.left_pcm_s16le,
                    source_time_start=raw.source_time_start,
                ),
                *binaural_sound_field_inputs(
                    ear="right",
                    topology_index=32,
                    pcm=raw.capture.right_pcm_s16le,
                    source_time_start=raw.source_time_start,
                ),
            ),
        }
        for sense in SENSE_ORDER:
            if sense is PhysicalSense.SOUND:
                continue
            channels = tuple(
                value.canonical_input()
                for value in raw.nonauditory_channels
                if value.sense is sense
            )
            if channels:
                observed[sense] = channels
        built = build_transaction_owned_six_sense_full_field(
            assembly_id=(
                "dual-kernel-"
                f"{raw.authority_receipt_sha256}"
            ),
            source_time_start=raw.source_time_start,
            source_time_end=raw.source_time_end,
            observed_substreams=observed,
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense in observed
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        )
        result = CanonicalProductionFieldEvidence(
            kernel_id=CANONICAL_KERNEL_ID,
            raw_encounter_receipt_sha256=(
                raw.authority_receipt_sha256
            ),
            full_field=built,
        )
        result.verify()
        return result

    @staticmethod
    def _side_branch(
        raw: AuthenticatedDualKernelEncounter,
    ) -> NearV13VTVRFieldEvidence:
        left = signed_pcm16_samples(raw.capture.left_pcm_s16le)
        right = signed_pcm16_samples(raw.capture.right_pcm_s16le)
        ordered_channels = tuple(
            channel
            for sense in SENSE_ORDER
            if sense is not PhysicalSense.SOUND
            for channel in raw.nonauditory_channels
            if channel.sense is sense
        )
        provenance = (
            SideVertexProvenance(
                vertex_id="sound:W1:left-ear-pressure:0",
                sense=PhysicalSense.SOUND.value,
                sensor_id="W1-calibrated-left-pressure",
                substream_id="left-ear-pressure",
                topology_index=0,
                coordinates=(("acoustic-receptor", "left"),),
                physical_quantity="signed-acoustic-pressure",
                physical_unit="pcm16-count",
            ),
            SideVertexProvenance(
                vertex_id="sound:W1:right-ear-pressure:1",
                sense=PhysicalSense.SOUND.value,
                sensor_id="W1-calibrated-right-pressure",
                substream_id="right-ear-pressure",
                topology_index=1,
                coordinates=(("acoustic-receptor", "right"),),
                physical_quantity="signed-acoustic-pressure",
                physical_unit="pcm16-count",
            ),
            *(
                SideVertexProvenance(
                    vertex_id=value.vertex_id,
                    sense=value.sense.value,
                    sensor_id=value.sensor_id,
                    substream_id=value.substream_id,
                    topology_index=value.topology_index,
                    coordinates=tuple(
                        (axis.axis_id, axis.coordinate_id)
                        for axis in value.coordinates
                    ),
                    physical_quantity=value.physical_quantity,
                    physical_unit=value.physical_unit,
                )
                for value in ordered_channels
            ),
        )
        vectors = tuple(
            (
                Fraction(left[index]),
                Fraction(right[index]),
                *(
                    value.signal[index]
                    for value in ordered_channels
                ),
            )
            for index in range(raw.capture.capture_sample_count)
        )
        groups: list[tuple[int, ...]] = [(0, 1)]
        for sense in SENSE_ORDER:
            if sense is PhysicalSense.SOUND:
                continue
            indices = tuple(
                index + 2
                for index, value in enumerate(ordered_channels)
                if value.sense is sense
            )
            if indices:
                groups.append(indices)
        joint = JointFieldInput.create(
            vertex_ids=tuple(
                value.vertex_id for value in provenance
            ),
            groups=tuple(groups),
            times=raw.source_times,
            vectors=vectors,
        )
        result = NearV13VTVRFieldEvidence(
            kernel_id=SIDE_KERNEL_ID,
            raw_encounter_receipt_sha256=(
                raw.authority_receipt_sha256
            ),
            vertex_provenance=provenance,
            full_field=run_side_kernel(joint),
        )
        result.verify()
        return result

    def accept(
        self,
        *,
        capture: PhysicalStereoCapture,
        world_observation_receipt_sha256: str,
        source_time_start: Fraction,
        nonauditory_channels: tuple[LivedNonauditoryChannel, ...],
    ) -> DualKernelFullFieldAcceptance:
        raw = self._authenticate_raw(
            capture=capture,
            world_observation_receipt_sha256=(
                world_observation_receipt_sha256
            ),
            source_time_start=source_time_start,
            nonauditory_channels=nonauditory_channels,
        )
        canonical = self._canonical_branch(raw)
        side = self._side_branch(raw)
        provisional = DualKernelFullFieldAcceptance(
            raw_encounter=raw,
            kernel_fields=(canonical, side),
            disposition=NO_LEARNING_CLAIM,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.unsigned_record()
        signature = hmac.new(
            self._acceptance_key,
            _ACCEPTANCE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = DualKernelFullFieldAcceptance(
            raw_encounter=raw,
            kernel_fields=(canonical, side),
            disposition=NO_LEARNING_CLAIM,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self.verify(result, recompute_branches=False)
        return result

    def verify(
        self,
        value: DualKernelFullFieldAcceptance,
        *,
        recompute_branches: bool = True,
    ) -> None:
        if not isinstance(value, DualKernelFullFieldAcceptance):
            raise TypeError("dual-kernel acceptance is not typed")
        self._verify_raw(value.raw_encounter)
        if (
            value.disposition != NO_LEARNING_CLAIM
            or len(value.kernel_fields) != 2
            or not isinstance(
                value.kernel_fields[0],
                CanonicalProductionFieldEvidence,
            )
            or not isinstance(
                value.kernel_fields[1],
                NearV13VTVRFieldEvidence,
            )
            or any(
                branch.raw_encounter_receipt_sha256
                != value.raw_encounter.authority_receipt_sha256
                for branch in value.kernel_fields
            )
        ):
            raise ValueError(
                "dual-kernel common boundary changed its authority"
            )
        for branch in value.kernel_fields:
            branch.verify()
        payload = value.unsigned_record()
        expected_hmac = hmac.new(
            self._acceptance_key,
            _ACCEPTANCE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        expected_receipt = _digest({
            "authority_hmac_sha256": expected_hmac,
            "payload": payload,
        })
        if (
            not hmac.compare_digest(
                expected_hmac, value.authority_hmac_sha256
            )
            or expected_receipt != value.authority_receipt_sha256
        ):
            raise ValueError(
                "dual-kernel acceptance authority changed"
            )
        if recompute_branches:
            expected_canonical = self._canonical_branch(
                value.raw_encounter
            )
            expected_side = self._side_branch(value.raw_encounter)
            if (
                expected_canonical.full_field.boundary
                != value.canonical.full_field.boundary
                or expected_canonical.full_field.receipt_registry
                != value.canonical.full_field.receipt_registry
                or expected_canonical.full_field.source_sample_commitments
                != value.canonical.full_field.source_sample_commitments
                or expected_side != value.side
            ):
                raise ValueError(
                    "dual-kernel branch changed from common raw evidence"
                )


__all__ = (
    "ACCEPTANCE_SCHEMA",
    "AuthenticatedDualKernelEncounter",
    "CANONICAL_KERNEL_ID",
    "CanonicalProductionFieldEvidence",
    "DualKernelFullFieldAcceptance",
    "DualKernelFullFieldAcceptanceHarness",
    "KernelFieldEvidence",
    "LivedNonauditoryChannel",
    "NO_LEARNING_CLAIM",
    "NearV13VTVRFieldEvidence",
    "RAW_ENCOUNTER_SCHEMA",
    "SIDE_KERNEL_ID",
    "SideVertexProvenance",
)
