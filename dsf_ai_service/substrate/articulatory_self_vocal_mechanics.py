"""Bounded deterministic physical larynx and vocal-tract authority.

The motor owns only admitted actuator programs and their physical resource
profile.  It deterministically generates laryngeal excitation, propagates
pressure through an eight-section fixed-point tube, exposes the actuator BODY
field, and prepares or commits the generated pressure through the embodiment
world.  It does not own words, THING identities, heard exemplars, acoustic
custody, or an exploration policy.

Generated pressure is transient.  Cold state contains no PCM, cursor, learned
binding, or acoustic record, so repeated vocal action cannot grow motor state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, Iterator, Mapping

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    BuiltSixSenseFullField,
    NativeSensorySubstreamInput,
    build_transaction_owned_six_sense_full_field,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    MIN_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    VOCAL_SAMPLE_RATE_HZ,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    PreparedActionExecution,
    VocalizeCommand,
    encode_command,
)


ARTICULATORY_PROFILE_SCHEMA = "guala.articulatory_motor.profile.v1"
ARTICULATORY_PROGRAM_SCHEMA = "guala.articulatory_motor.program.v2"
ARTICULATORY_SYNTHESIS_SCHEMA = "guala.articulatory_motor.synthesis.v2"
ARTICULATORY_ACTUATOR_FULL_FIELD_ASSEMBLY_SCHEMA = (
    "guala.articulatory_motor.actuator_full_field_assembly.v1"
)
ARTICULATORY_GENERATED_EMISSION_SCHEMA = (
    "guala.articulatory_motor.generated_emission.v1"
)
ARTICULATORY_PREPARED_GENERATED_EMISSION_SCHEMA = (
    "guala.articulatory_motor.prepared_generated_emission.v1"
)
ARTICULATORY_STATE_SCHEMA = "guala.articulatory_motor.state.v2"
ARTICULATORY_ENVELOPE_SCHEMA = "guala.articulatory_motor.state_hmac.v2"

TRACT_SECTION_COUNT = 8
MAX_ARTICULATORY_SAMPLES = MAX_VOCAL_SAMPLE_COUNT
MAX_ARTICULATORY_RELAXATION_SAMPLES = 131_072
MAX_TRACT_AREA_MM2 = 5_000
ACTUATOR_RECEPTOR_SAMPLE_DIVISOR = 2
PPM = 1_000_000
Q31 = 1 << 31

_SYNTHESIS_DOMAIN = b"guala-articulatory-synthesis-v2\0"
_GENERATED_EMISSION_DOMAIN = (
    b"guala-articulatory-generated-emission-v1\0"
)
_PREPARED_GENERATED_EMISSION_DOMAIN = (
    b"guala-articulatory-prepared-generated-emission-v1\0"
)
_STATE_DOMAIN = b"guala-articulatory-state-v2\0"
_HEX = frozenset("0123456789abcdef")
_PREPARED_ARTICULATORY_GENERATED_EMISSION_AUTHORITY = object()
_PREPARED_PROGRAM_ADMISSION_AUTHORITY = object()
_PROGRAM_ADMISSION_UNDO_AUTHORITY = object()


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
        raise TypeError("articulatory authority key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("articulatory authority key has an invalid boundary")
    return result


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(key, domain + _canonical(value), hashlib.sha256).hexdigest()


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _bounded(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"{name} left its exact integer boundary")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("articulatory structural time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _round_div(numerator: int, denominator: int) -> int:
    """Nearest integer, with exact half cases directed away from zero."""

    if denominator <= 0:
        raise ValueError("fixed-point denominator must be positive")
    sign = -1 if numerator < 0 else 1
    magnitude = abs(numerator)
    quotient, remainder = divmod(magnitude, denominator)
    if 2 * remainder >= denominator:
        quotient += 1
    return sign * quotient


def _q31_ratio(numerator: int, denominator: int) -> int:
    return _round_div(numerator * Q31, denominator)


def _q31_mul(value: int, coefficient: int) -> int:
    return _round_div(value * coefficient, Q31)


def signed_magnitude_truncating_wall_loss(
    value: int,
    retention_q31: int,
) -> int:
    """Apply dissipative tube-wall retention without a sub-LSB limit cycle.

    Conservative tube scattering continues to use nearest-integer rounding.
    Loss is different physics: every non-unity application must strictly
    reduce a nonzero magnitude once its retained fraction falls below one
    integer unit.  Signed magnitude truncation supplies that exact property.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("tube-wall pressure must be an exact integer")
    _bounded(
        retention_q31,
        "tube-wall Q31 retention",
        minimum=0,
        maximum=Q31,
    )
    retained_magnitude = abs(value) * retention_q31 // Q31
    return -retained_magnitude if value < 0 else retained_magnitude


def _pcm_bytes(values: tuple[int, ...]) -> bytes:
    return b"".join(
        int(value).to_bytes(2, "little", signed=True) for value in values
    )


def _pcm_tuple(value: bytes, name: str) -> tuple[int, ...]:
    if not isinstance(value, bytes) or len(value) % 2:
        raise ValueError(f"{name} must be immutable PCM16 bytes")
    return tuple(item[0] for item in struct.iter_unpack("<h", value))


def _area_tuple(value: object, name: str) -> tuple[int, ...]:
    if (
        not isinstance(value, tuple)
        or len(value) != TRACT_SECTION_COUNT
        or any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or not 1 <= item <= MAX_TRACT_AREA_MM2
            for item in value
        )
    ):
        raise ValueError(
            f"{name} must contain {TRACT_SECTION_COUNT} physical areas"
        )
    return value


@dataclass(frozen=True, slots=True)
class LaryngealExcitationConfiguration:
    cycle_samples: int
    open_samples: int
    peak_volume_velocity_pcm: int

    def verify(self) -> None:
        _bounded(
            self.cycle_samples,
            "laryngeal cycle",
            minimum=16,
            maximum=800,
        )
        _bounded(
            self.open_samples,
            "laryngeal open interval",
            minimum=2,
            maximum=self.cycle_samples - 1,
        )
        _bounded(
            self.peak_volume_velocity_pcm,
            "laryngeal peak volume velocity",
            minimum=1,
            maximum=16_000,
        )

    def as_record(self) -> dict[str, int]:
        self.verify()
        return {
            "cycle_samples": self.cycle_samples,
            "open_samples": self.open_samples,
            "peak_volume_velocity_pcm": self.peak_volume_velocity_pcm,
        }


@dataclass(frozen=True, slots=True)
class VocalTractConfiguration:
    initial_section_area_mm2: tuple[int, ...]
    apex_section_area_mm2: tuple[int, ...]
    final_section_area_mm2: tuple[int, ...]
    radiation_load_area_mm2: int
    wall_retention_ppm: int

    def verify(self) -> None:
        _area_tuple(
            self.initial_section_area_mm2,
            "initial vocal-tract section areas",
        )
        _area_tuple(
            self.apex_section_area_mm2,
            "apex vocal-tract section areas",
        )
        _area_tuple(
            self.final_section_area_mm2,
            "final vocal-tract section areas",
        )
        _bounded(
            self.radiation_load_area_mm2,
            "vocal-tract radiation load area",
            minimum=1,
            maximum=MAX_TRACT_AREA_MM2,
        )
        _bounded(
            self.wall_retention_ppm,
            "vocal-tract wall retention",
            minimum=1,
            maximum=PPM,
        )

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "apex_section_area_mm2": list(
                self.apex_section_area_mm2
            ),
            "final_section_area_mm2": list(
                self.final_section_area_mm2
            ),
            "initial_section_area_mm2": list(
                self.initial_section_area_mm2
            ),
            "radiation_load_area_mm2": self.radiation_load_area_mm2,
            "wall_retention_ppm": self.wall_retention_ppm,
        }


@dataclass(frozen=True, slots=True)
class ArticulatoryBodyTrajectoryInterval:
    """One exact held body configuration on a half-open sample interval."""

    sample_start: int
    sample_end: int
    glottal_open_samples: int
    section_area_mm2: tuple[int, ...]

    def verify(self, larynx: LaryngealExcitationConfiguration) -> None:
        larynx.verify()
        _bounded(
            self.sample_start,
            "articulatory trajectory sample start",
            minimum=0,
            maximum=MAX_ARTICULATORY_SAMPLES - 1,
        )
        _bounded(
            self.sample_end,
            "articulatory trajectory sample end",
            minimum=1,
            maximum=MAX_ARTICULATORY_SAMPLES,
        )
        if self.sample_start >= self.sample_end:
            raise ValueError(
                "articulatory trajectory interval has no physical extent"
            )
        _bounded(
            self.glottal_open_samples,
            "articulatory trajectory glottal opening",
            minimum=2,
            maximum=larynx.cycle_samples - 1,
        )
        _area_tuple(
            self.section_area_mm2,
            "articulatory trajectory vocal-tract areas",
        )

    def as_record(
        self,
        larynx: LaryngealExcitationConfiguration,
    ) -> dict[str, object]:
        self.verify(larynx)
        return {
            "glottal_open_samples": self.glottal_open_samples,
            "sample_end": self.sample_end,
            "sample_start": self.sample_start,
            "section_area_mm2": list(self.section_area_mm2),
        }


@dataclass(frozen=True, slots=True)
class ArticulatoryProgram:
    sample_count: int
    larynx: LaryngealExcitationConfiguration
    tract: VocalTractConfiguration
    body_trajectory: tuple[ArticulatoryBodyTrajectoryInterval, ...]
    program_id: str
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        sample_count: int,
        larynx: LaryngealExcitationConfiguration,
        tract: VocalTractConfiguration,
        body_trajectory: tuple[
            ArticulatoryBodyTrajectoryInterval, ...
        ] = (),
    ) -> "ArticulatoryProgram":
        if not isinstance(larynx, LaryngealExcitationConfiguration):
            raise TypeError("articulatory program requires a larynx")
        if not isinstance(tract, VocalTractConfiguration):
            raise TypeError("articulatory program requires a vocal tract")
        larynx.verify()
        tract.verify()
        _bounded(
            sample_count,
            "articulatory sample count",
            minimum=MIN_VOCAL_SAMPLE_COUNT,
            maximum=MAX_ARTICULATORY_SAMPLES,
        )
        if not isinstance(body_trajectory, tuple):
            raise TypeError(
                "articulatory body trajectory must be an immutable tuple"
            )
        cursor = 0
        for interval in body_trajectory:
            if not isinstance(
                interval,
                ArticulatoryBodyTrajectoryInterval,
            ):
                raise TypeError(
                    "articulatory body trajectory interval is not typed"
                )
            interval.verify(larynx)
            if interval.sample_start != cursor:
                raise ValueError(
                    "articulatory body trajectory skipped a sample interval"
                )
            cursor = interval.sample_end
        if body_trajectory and cursor != sample_count:
            raise ValueError(
                "articulatory body trajectory did not cover the program"
            )
        record = {
            "body_trajectory": [
                interval.as_record(larynx)
                for interval in body_trajectory
            ],
            "larynx": larynx.as_record(),
            "sample_count": sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_PROGRAM_SCHEMA,
            "tract": tract.as_record(),
        }
        program_id = _digest(record)
        return cls(
            sample_count=sample_count,
            larynx=larynx,
            tract=tract,
            body_trajectory=body_trajectory,
            program_id=program_id,
            authority_receipt_sha256=_digest({
                "program_id": program_id,
                "record": record,
            }),
        )

    def payload(self) -> dict[str, object]:
        return {
            "body_trajectory": [
                interval.as_record(self.larynx)
                for interval in self.body_trajectory
            ],
            "larynx": self.larynx.as_record(),
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_PROGRAM_SCHEMA,
            "tract": self.tract.as_record(),
        }

    def verify(self) -> None:
        expected = ArticulatoryProgram.create(
            sample_count=self.sample_count,
            larynx=self.larynx,
            tract=self.tract,
            body_trajectory=self.body_trajectory,
        )
        if self != expected:
            raise ValueError("articulatory program authority changed")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "program_id": self.program_id,
        }


@dataclass(slots=True)
class _ProgramAdmissionState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class PreparedArticulatoryProgramAdmission:
    program: ArticulatoryProgram
    _prior_programs: Mapping[str, ArticulatoryProgram] = field(
        repr=False,
        compare=False,
    )
    _staged_programs: Mapping[str, ArticulatoryProgram] = field(
        repr=False,
        compare=False,
    )
    _state: _ProgramAdmissionState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class ArticulatoryProgramAdmissionUndo:
    _prepared: PreparedArticulatoryProgramAdmission = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class ArticulatoryMotorResourceProfile:
    profile_id: str
    max_programs: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_programs: int,
        max_state_bytes: int,
    ) -> "ArticulatoryMotorResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("articulatory profile identifier is invalid")
        provisional = cls(
            profile_id=profile_id,
            max_programs=_positive(
                max_programs, "articulatory program capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "articulatory state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_programs=provisional.max_programs,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_programs": self.max_programs,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": ARTICULATORY_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _positive(self.max_programs, "articulatory program capacity")
        _positive(self.max_state_bytes, "articulatory state capacity")
        _sha256(
            self.authority_receipt_sha256,
            "articulatory profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("articulatory resource profile changed")


@dataclass(frozen=True, slots=True)
class ArticulatoryActuatorFullFieldPartition:
    partition_index: int
    sample_start: int
    sample_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    full_field: BuiltSixSenseFullField

    def payload(self) -> dict[str, object]:
        return {
            "full_field_receipt_sha256": (
                self.full_field.boundary.authority_receipt_sha256
            ),
            "partition_index": self.partition_index,
            "sample_end": self.sample_end,
            "sample_start": self.sample_start,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }


@dataclass(frozen=True, slots=True)
class ArticulatoryActuatorFullFieldAssembly:
    program_id: str
    sample_count: int
    source_time_start: Fraction
    source_time_end: Fraction
    partitions: tuple[ArticulatoryActuatorFullFieldPartition, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "partitions": [value.payload() for value in self.partitions],
            "program_id": self.program_id,
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_ACTUATOR_FULL_FIELD_ASSEMBLY_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def verify(self) -> None:
        _sha256(self.program_id, "articulatory actuator program")
        _sha256(
            self.authority_receipt_sha256,
            "articulatory actuator full-field assembly",
        )
        if (
            not isinstance(self.partitions, tuple)
            or not self.partitions
            or not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.sample_count < 1
            or self.source_time_end
            != self.source_time_start
            + Fraction(self.sample_count, VOCAL_SAMPLE_RATE_HZ)
        ):
            raise ValueError(
                "articulatory actuator full-field extent changed"
            )
        cursor = 0
        for partition_index, partition in enumerate(self.partitions):
            if (
                not isinstance(
                    partition,
                    ArticulatoryActuatorFullFieldPartition,
                )
                or partition.partition_index != partition_index
                or partition.sample_start != cursor
                or not partition.sample_start < partition.sample_end
                or partition.sample_end > self.sample_count
                or partition.sample_end - partition.sample_start
                > MAX_NATIVE_SAMPLES_PER_SUBSTREAM
                or partition.source_time_start
                != self.source_time_start
                + Fraction(
                    partition.sample_start,
                    VOCAL_SAMPLE_RATE_HZ,
                )
                or partition.source_time_end
                != self.source_time_start
                + Fraction(
                    partition.sample_end,
                    VOCAL_SAMPLE_RATE_HZ,
                )
            ):
                raise ValueError(
                    "articulatory actuator partition coverage changed"
                )
            partition.full_field.verify_construction()
            if (
                any(
                    boundary.source_time_start
                    != partition.source_time_start
                    or boundary.source_time_end
                    != partition.source_time_end
                    for boundary in partition.full_field.boundary.boundaries
                )
                or len(partition.full_field.source_sample_commitments) != 9
                or any(
                    sample_count
                    != partition.sample_end - partition.sample_start
                    for _digest_value, sample_count, _commitment
                    in partition.full_field.source_sample_commitments
                )
            ):
                raise ValueError(
                    "articulatory actuator partition field changed"
                )
            cursor = partition.sample_end
        if (
            cursor != self.sample_count
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError(
                "articulatory actuator full-field assembly changed"
            )


@dataclass(frozen=True, slots=True)
class ArticulatorySynthesisReceipt:
    program_id: str
    excitation_pcm_sha256: str
    radiated_pcm_sha256: str
    sample_count: int
    source_time_start: Fraction
    source_time_end: Fraction
    actuator_full_field_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "actuator_full_field_receipt_sha256": (
                self.actuator_full_field_receipt_sha256
            ),
            "excitation_pcm_sha256": self.excitation_pcm_sha256,
            "program_id": self.program_id,
            "radiated_pcm_sha256": self.radiated_pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_SYNTHESIS_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def verify(self, key: bytes) -> None:
        for value, name in (
            (self.program_id, "articulatory synthesis program"),
            (
                self.excitation_pcm_sha256,
                "articulatory excitation PCM",
            ),
            (self.radiated_pcm_sha256, "articulatory radiated PCM"),
            (
                self.actuator_full_field_receipt_sha256,
                "articulatory actuator full field",
            ),
            (
                self.authority_receipt_sha256,
                "articulatory synthesis",
            ),
        ):
            _sha256(value, name)
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or not MIN_VOCAL_SAMPLE_COUNT
            <= self.sample_count
            <= MAX_ARTICULATORY_SAMPLES
        ):
            raise ValueError("articulatory synthesis interval changed")
        signature = _sign(key, _SYNTHESIS_DOMAIN, self.payload())
        if (
            not hmac.compare_digest(signature, self.authority_hmac_sha256)
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": self.payload(),
            })
        ):
            raise ValueError("articulatory synthesis authority changed")


@dataclass(frozen=True, slots=True)
class ArticulatorySynthesis:
    program: ArticulatoryProgram
    excitation_pcm_s16le: bytes
    radiated_pcm_s16le: bytes
    actuator_full_field_assembly: ArticulatoryActuatorFullFieldAssembly
    receipt: ArticulatorySynthesisReceipt


@dataclass(frozen=True, slots=True)
class ArticulatoryTravelingWaveState:
    """Exact pressure state retained inside the eight-section tube."""

    right_pressure: tuple[int, ...]
    left_pressure: tuple[int, ...]
    previous_glottal_flow: int

    def verify(self) -> None:
        for values, name in (
            (self.right_pressure, "right-traveling tube pressure"),
            (self.left_pressure, "left-traveling tube pressure"),
        ):
            if (
                not isinstance(values, tuple)
                or len(values) != TRACT_SECTION_COUNT
                or any(
                    isinstance(value, bool) or not isinstance(value, int)
                    for value in values
                )
            ):
                raise ValueError(f"{name} state changed")
        if (
            isinstance(self.previous_glottal_flow, bool)
            or not isinstance(self.previous_glottal_flow, int)
        ):
            raise ValueError("previous glottal flow state changed")

    @property
    def is_quiescent(self) -> bool:
        self.verify()
        return (
            self.previous_glottal_flow == 0
            and not any(self.right_pressure)
            and not any(self.left_pressure)
        )


@dataclass(frozen=True, slots=True)
class ArticulatoryPressureWithQuiescence:
    """Transient active pressure and its exact neutral-tract decay."""

    excitation_pressure_pcm: tuple[int, ...]
    active_radiated_pressure_pcm: tuple[int, ...]
    active_area_trajectories_mm2: tuple[tuple[int, ...], ...]
    active_terminal_state: ArticulatoryTravelingWaveState
    neutral_section_area_mm2: tuple[int, ...]
    relaxation_radiated_pressure_pcm: tuple[int, ...]
    quiescent_terminal_state: ArticulatoryTravelingWaveState

    def verify(self, program: ArticulatoryProgram) -> None:
        program.verify()
        self.active_terminal_state.verify()
        self.quiescent_terminal_state.verify()
        _area_tuple(
            self.neutral_section_area_mm2,
            "neutral vocal-tract section areas",
        )
        if (
            len(self.excitation_pressure_pcm) != program.sample_count
            or len(self.active_radiated_pressure_pcm) != program.sample_count
            or len(self.active_area_trajectories_mm2)
            != TRACT_SECTION_COUNT
            or any(
                len(values) != program.sample_count
                for values in self.active_area_trajectories_mm2
            )
            or len(self.relaxation_radiated_pressure_pcm)
            > MAX_ARTICULATORY_RELAXATION_SAMPLES
            or not self.quiescent_terminal_state.is_quiescent
        ):
            raise ValueError(
                "articulatory active-to-quiescent pressure changed"
            )


@dataclass(frozen=True, slots=True)
class ArticulatoryGeneratedEmissionReceipt:
    program_id: str
    synthesis_receipt_sha256: str
    pcm_sha256: str
    sample_count: int
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    command_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "command_sha256": self.command_sha256,
            "pcm_sha256": self.pcm_sha256,
            "program_id": self.program_id,
            "sample_count": self.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_GENERATED_EMISSION_SCHEMA,
            "self_port_id": PORT_ID,
            "synthesis_receipt_sha256": (
                self.synthesis_receipt_sha256
            ),
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

    def verify(self, key: bytes) -> None:
        for value, label in (
            (self.program_id, "generated emission program"),
            (
                self.synthesis_receipt_sha256,
                "generated emission synthesis",
            ),
            (self.pcm_sha256, "generated emission pressure"),
            (
                self.world_before_receipt_sha256,
                "generated emission world before",
            ),
            (
                self.world_after_receipt_sha256,
                "generated emission world after",
            ),
            (
                self.world_execution_receipt_sha256,
                "generated emission world execution",
            ),
            (self.command_sha256, "generated emission command"),
            (
                self.authority_receipt_sha256,
                "generated emission authority",
            ),
        ):
            _sha256(value, label)
        if not MIN_VOCAL_SAMPLE_COUNT <= self.sample_count <= (
            MAX_ARTICULATORY_SAMPLES
        ):
            raise ValueError("generated emission sample extent changed")
        signature = _sign(
            key, _GENERATED_EMISSION_DOMAIN, self.payload()
        )
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
            raise ValueError("generated emission authority changed")


@dataclass(frozen=True, slots=True)
class ArticulatoryGeneratedEmission:
    synthesis: ArticulatorySynthesis
    pcm_s16le: bytes
    execution_receipt: ActionExecutionReceipt
    emission_receipt: ArticulatoryGeneratedEmissionReceipt


@dataclass(frozen=True, slots=True)
class PreparedArticulatoryGeneratedEmission:
    """One uncommitted physical vocal action held outside live world state.

    This capability is not an emission claim.  It contains no generated
    emission receipt, and it becomes an ``ArticulatoryGeneratedEmission`` only
    after the world accepts its exact prepared action at the final commit
    point.
    """

    synthesis: ArticulatorySynthesis
    pcm_s16le: bytes
    command_payload: bytes
    causal_intent_receipt_sha256: str
    prepared_world_action: PreparedActionExecution
    prospective_emission_receipt_sha256: str
    preparation_hmac_sha256: str
    preparation_receipt_sha256: str
    _prospective_emission_hmac_sha256: str = field(
        repr=False,
        compare=False,
    )
    _world_authority: EmbodimentWorldAuthority = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        execution = self.prepared_world_action.execution_receipt
        return {
            "causal_intent_receipt_sha256": (
                self.causal_intent_receipt_sha256
            ),
            "command_sha256": hashlib.sha256(
                self.command_payload
            ).hexdigest(),
            "pcm_sha256": hashlib.sha256(self.pcm_s16le).hexdigest(),
            "program_id": self.synthesis.program.program_id,
            "prospective_emission_receipt_sha256": (
                self.prospective_emission_receipt_sha256
            ),
            "sample_count": self.synthesis.program.sample_count,
            "schema": ARTICULATORY_PREPARED_GENERATED_EMISSION_SCHEMA,
            "synthesis_receipt_sha256": (
                self.synthesis.receipt.authority_receipt_sha256
            ),
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


_PREVERIFIED_GENERATED_EMISSION_COMMIT_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class PreverifiedArticulatoryGeneratedEmissionCommit:
    _prepared: PreparedArticulatoryGeneratedEmission = field(repr=False)
    _result: ArticulatoryGeneratedEmission = field(repr=False)
    _world_authority: EmbodimentWorldAuthority = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


def _tract_areas(
    tract: VocalTractConfiguration,
    sample_index: int,
    sample_count: int,
) -> tuple[int, ...]:
    final_index = sample_count - 1
    apex_index = final_index // 2
    if sample_index <= apex_index:
        left = tract.initial_section_area_mm2
        right = tract.apex_section_area_mm2
        position = sample_index
        denominator = max(1, apex_index)
    else:
        left = tract.apex_section_area_mm2
        right = tract.final_section_area_mm2
        position = sample_index - apex_index
        denominator = max(1, final_index - apex_index)
    return tuple(
        _round_div(
            initial * (denominator - position)
            + final * position,
            denominator,
        )
        for initial, final in zip(
            left,
            right,
            strict=True,
        )
    )


def _generate_physical_pressure(
    program: ArticulatoryProgram,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[tuple[int, ...], ...]]:
    """Run one ideal-flow larynx into an eight-section loss tube."""

    excitation, radiated, areas, _terminal = (
        _generate_physical_pressure_with_terminal(program)
    )
    return excitation, radiated, areas


def _advance_articulatory_tube(
    *,
    right: tuple[int, ...],
    left: tuple[int, ...],
    areas: tuple[int, ...],
    source_pressure: int,
    radiation_load_area_mm2: int,
    retention_q31: int,
) -> tuple[tuple[int, ...], tuple[int, ...], int]:
    """Advance one conservative scattering step plus physical wall loss."""

    _area_tuple(areas, "instantaneous vocal-tract section areas")
    if (
        len(right) != TRACT_SECTION_COUNT
        or len(left) != TRACT_SECTION_COUNT
    ):
        raise ValueError("articulatory traveling-wave state changed")
    next_right = [0] * TRACT_SECTION_COUNT
    next_left = [0] * TRACT_SECTION_COUNT
    next_right[0] = source_pressure

    for junction in range(TRACT_SECTION_COUNT - 1):
        left_area = areas[junction]
        right_area = areas[junction + 1]
        total_area = left_area + right_area
        incoming_right = right[junction]
        incoming_left = left[junction + 1]
        outgoing_right = _round_div(
            2 * left_area * incoming_right
            + (right_area - left_area) * incoming_left,
            total_area,
        )
        outgoing_left = _round_div(
            (left_area - right_area) * incoming_right
            + 2 * right_area * incoming_left,
            total_area,
        )
        next_right[junction + 1] = (
            signed_magnitude_truncating_wall_loss(
                outgoing_right,
                retention_q31,
            )
        )
        next_left[junction] = signed_magnitude_truncating_wall_loss(
            outgoing_left,
            retention_q31,
        )

    mouth_area = areas[-1]
    mouth_total = mouth_area + radiation_load_area_mm2
    reflected = _round_div(
        (mouth_area - radiation_load_area_mm2) * right[-1],
        mouth_total,
    )
    transmitted = _round_div(
        2 * mouth_area * right[-1],
        mouth_total,
    )
    next_left[-1] = signed_magnitude_truncating_wall_loss(
        reflected,
        retention_q31,
    )
    return (
        tuple(next_right),
        tuple(next_left),
        max(-32_768, min(32_767, transmitted)),
    )


def _generate_physical_pressure_with_terminal(
    program: ArticulatoryProgram,
) -> tuple[
    tuple[int, ...],
    tuple[int, ...],
    tuple[tuple[int, ...], ...],
    ArticulatoryTravelingWaveState,
]:
    """Run active articulation and expose its exact terminal tube state."""

    program.verify()
    count = program.sample_count
    larynx = program.larynx
    tract = program.tract
    right = [0] * TRACT_SECTION_COUNT
    left = [0] * TRACT_SECTION_COUNT
    previous_flow = 0
    excitation: list[int] = []
    radiated: list[int] = []
    area_trajectories = [
        [] for _unused in range(TRACT_SECTION_COUNT)
    ]
    retention_q31 = _q31_ratio(tract.wall_retention_ppm, PPM)
    body_interval_index = 0

    for sample_index in range(count):
        if program.body_trajectory:
            while (
                sample_index
                >= program.body_trajectory[
                    body_interval_index
                ].sample_end
            ):
                body_interval_index += 1
            body_interval = program.body_trajectory[
                body_interval_index
            ]
            open_samples = body_interval.glottal_open_samples
            areas = body_interval.section_area_mm2
        else:
            open_samples = larynx.open_samples
            areas = _tract_areas(tract, sample_index, count)
        phase = sample_index % larynx.cycle_samples
        if phase < open_samples:
            flow = _round_div(
                larynx.peak_volume_velocity_pcm
                * 4
                * phase
                * (open_samples - phase),
                open_samples * open_samples,
            )
        else:
            flow = 0
        source_pressure = flow - previous_flow
        previous_flow = flow
        excitation.append(source_pressure)

        for section_index, area in enumerate(areas):
            area_trajectories[section_index].append(area)

        next_right, next_left, transmitted = _advance_articulatory_tube(
            right=tuple(right),
            left=tuple(left),
            areas=areas,
            source_pressure=source_pressure,
            radiation_load_area_mm2=tract.radiation_load_area_mm2,
            retention_q31=retention_q31,
        )
        radiated.append(transmitted)
        right = next_right
        left = next_left

    return (
        tuple(excitation),
        tuple(radiated),
        tuple(tuple(values) for values in area_trajectories),
        ArticulatoryTravelingWaveState(
            right_pressure=tuple(right),
            left_pressure=tuple(left),
            previous_glottal_flow=previous_flow,
        ),
    )


def generate_articulatory_pressure_with_quiescence(
    *,
    program: ArticulatoryProgram,
    neutral_section_area_mm2: tuple[int, ...],
) -> ArticulatoryPressureWithQuiescence:
    """Continue one active articulation at neutral geometry until exact rest."""

    program.verify()
    neutral = _area_tuple(
        neutral_section_area_mm2,
        "neutral vocal-tract section areas",
    )
    if program.tract.wall_retention_ppm >= PPM:
        raise ValueError(
            "eventual articulatory quiescence requires wall retention below unity"
        )
    excitation, radiated, areas, active_terminal = (
        _generate_physical_pressure_with_terminal(program)
    )
    relaxation, quiescent_terminal = (
        relax_articulatory_traveling_wave_state(
            program=program,
            neutral_section_area_mm2=neutral,
            initial_state=active_terminal,
        )
    )
    result = ArticulatoryPressureWithQuiescence(
        excitation_pressure_pcm=excitation,
        active_radiated_pressure_pcm=radiated,
        active_area_trajectories_mm2=areas,
        active_terminal_state=active_terminal,
        neutral_section_area_mm2=neutral,
        relaxation_radiated_pressure_pcm=relaxation,
        quiescent_terminal_state=quiescent_terminal,
    )
    result.verify(program)
    return result


def relax_articulatory_traveling_wave_state(
    *,
    program: ArticulatoryProgram,
    neutral_section_area_mm2: tuple[int, ...],
    initial_state: ArticulatoryTravelingWaveState,
) -> tuple[tuple[int, ...], ArticulatoryTravelingWaveState]:
    """Advance an authenticated terminal state until every pressure is zero."""

    program.verify()
    neutral = _area_tuple(
        neutral_section_area_mm2,
        "neutral vocal-tract section areas",
    )
    if not isinstance(initial_state, ArticulatoryTravelingWaveState):
        raise TypeError(
            "articulatory relaxation requires a traveling-wave state"
        )
    initial_state.verify()
    if program.tract.wall_retention_ppm >= PPM:
        raise ValueError(
            "eventual articulatory quiescence requires wall retention below unity"
        )
    right = initial_state.right_pressure
    left = initial_state.left_pressure
    previous_flow = initial_state.previous_glottal_flow
    retention_q31 = _q31_ratio(
        program.tract.wall_retention_ppm,
        PPM,
    )
    relaxation: list[int] = []

    while previous_flow or any(right) or any(left):
        if len(relaxation) >= MAX_ARTICULATORY_RELAXATION_SAMPLES:
            raise RuntimeError(
                "articulatory tube did not reach exact quiescence inside "
                "its admitted relaxation boundary"
            )
        source_pressure = -previous_flow
        previous_flow = 0
        right, left, transmitted = _advance_articulatory_tube(
            right=right,
            left=left,
            areas=neutral,
            source_pressure=source_pressure,
            radiation_load_area_mm2=(
                program.tract.radiation_load_area_mm2
            ),
            retention_q31=retention_q31,
        )
        relaxation.append(transmitted)

    terminal = ArticulatoryTravelingWaveState(
        right_pressure=right,
        left_pressure=left,
        previous_glottal_flow=previous_flow,
    )
    terminal.verify()
    if not terminal.is_quiescent:
        raise RuntimeError("articulatory relaxation ended before quiescence")
    return tuple(relaxation), terminal


def _actuator_full_field(
    *,
    program: ArticulatoryProgram,
    excitation: tuple[int, ...],
    area_trajectories: tuple[tuple[int, ...], ...],
    source_time_start: Fraction,
) -> ArticulatoryActuatorFullFieldAssembly:
    count = program.sample_count
    cycle = program.larynx.cycle_samples
    partitions: list[ArticulatoryActuatorFullFieldPartition] = []
    for partition_index, sample_start in enumerate(
        range(0, count, MAX_NATIVE_SAMPLES_PER_SUBSTREAM)
    ):
        sample_end = min(
            count,
            sample_start + MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
        )
        receptor_indices = tuple(range(sample_start, sample_end))
        times = tuple(
            source_time_start + Fraction(index, VOCAL_SAMPLE_RATE_HZ)
            for index in receptor_indices
        )
        excitation_input = NativeSensorySubstreamInput(
            sense=PhysicalSense.BODY,
            sensor_id="self-laryngeal-mechanoreceptor",
            substream_id="glottal-volume-acceleration",
            topology_index=0,
            coordinates=(
                NativeAxisCoordinate("body-region", "larynx"),
                NativeAxisCoordinate("actuator-axis", "glottal-flow"),
            ),
            physical_quantity="glottal-volume-velocity-change",
            physical_unit="pcm16-per-sample",
            source_times=times,
            normalized_signal=tuple(
                excitation[index] / 32_768.0
                for index in receptor_indices
            ),
            phase_turns=tuple(
                Fraction(index, cycle) for index in receptor_indices
            ),
        )
        tract_inputs = tuple(
            NativeSensorySubstreamInput(
                sense=PhysicalSense.BODY,
                sensor_id="self-vocal-tract-proprioceptor",
                substream_id=(
                    f"vocal-tract-section-{section_index:02d}-area"
                ),
                topology_index=section_index + 1,
                coordinates=(
                    NativeAxisCoordinate(
                        "body-region",
                        "vocal-tract",
                    ),
                    NativeAxisCoordinate(
                        "tract-section",
                        f"{section_index:02d}",
                    ),
                ),
                physical_quantity="cross-sectional-area",
                physical_unit="square-millimetres",
                source_times=times,
                normalized_signal=tuple(
                    area_trajectories[section_index][index]
                    / MAX_TRACT_AREA_MM2
                    for index in receptor_indices
                ),
                phase_turns=tuple(
                    Fraction(index, max(1, count - 1))
                    for index in receptor_indices
                ),
            )
            for section_index in range(TRACT_SECTION_COUNT)
        )
        partition_time_start = source_time_start + Fraction(
            sample_start,
            VOCAL_SAMPLE_RATE_HZ,
        )
        partition_time_end = source_time_start + Fraction(
            sample_end,
            VOCAL_SAMPLE_RATE_HZ,
        )
        built = build_transaction_owned_six_sense_full_field(
            assembly_id=(
                "articulatory-actuator-"
                + _digest({
                    "partition_index": partition_index,
                    "program_id": program.program_id,
                    "sample_end": sample_end,
                    "sample_start": sample_start,
                    "source_time_start": _fraction_text(
                        source_time_start
                    ),
                })
            ),
            source_time_start=partition_time_start,
            source_time_end=partition_time_end,
            observed_substreams={
                PhysicalSense.BODY: (excitation_input, *tract_inputs)
            },
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense is PhysicalSense.BODY
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
            # The laryngeal mechanoreceptor and every vocal-tract section
            # proprioceptor report one coupled articulatory mechanism
            # executing one program partition: one joint occurrence.
            occurrences=declare_joint_source_occurrences(
                observed_substreams={
                    PhysicalSense.BODY: (excitation_input, *tract_inputs)
                },
                declared_units=(
                    tuple(
                        (PhysicalSense.BODY, port.topology_index)
                        for port in (excitation_input, *tract_inputs)
                    ),
                ),
            ),
        )
        partitions.append(
            ArticulatoryActuatorFullFieldPartition(
                partition_index=partition_index,
                sample_start=sample_start,
                sample_end=sample_end,
                source_time_start=partition_time_start,
                source_time_end=partition_time_end,
                full_field=built,
            )
        )
    source_time_end = source_time_start + Fraction(
        count,
        VOCAL_SAMPLE_RATE_HZ,
    )
    provisional = ArticulatoryActuatorFullFieldAssembly(
        program_id=program.program_id,
        sample_count=count,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        partitions=tuple(partitions),
        authority_receipt_sha256="0" * 64,
    )
    result = ArticulatoryActuatorFullFieldAssembly(
        program_id=provisional.program_id,
        sample_count=provisional.sample_count,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        partitions=provisional.partitions,
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result.verify()
    return result


class ArticulatorySelfVocalMotorOwner:
    """Own bounded physical programs and transient generated pressure."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: ArticulatoryMotorResourceProfile,
    ) -> None:
        if not isinstance(
            resource_profile, ArticulatoryMotorResourceProfile
        ):
            raise TypeError(
                "articulatory motor requires a resource profile"
            )
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._synthesis_key = hashlib.sha256(
            _SYNTHESIS_DOMAIN + root
        ).digest()
        self._generated_emission_key = hashlib.sha256(
            _GENERATED_EMISSION_DOMAIN + root
        ).digest()
        self._prepared_generated_emission_key = hashlib.sha256(
            _PREPARED_GENERATED_EMISSION_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._programs: dict[str, ArticulatoryProgram] = {}
        self._prepared_program_admission: (
            PreparedArticulatoryProgramAdmission | None
        ) = None
        self._latest_program_admission_undo: (
            ArticulatoryProgramAdmissionUndo | None
        ) = None
        self._program_admission_owner = object()
        self._prepared_generated_emission: (
            PreparedArticulatoryGeneratedEmission | None
        ) = None
        self._prepared_generated_emission_authority = object()
        self._active_preverified_generated_emission_commit: (
            PreverifiedArticulatoryGeneratedEmissionCommit | None
        ) = None
        self._lock = threading.RLock()

    @property
    def programs(self) -> tuple[ArticulatoryProgram, ...]:
        with self._lock:
            return tuple(
                self._programs[key] for key in sorted(self._programs)
            )

    def admit_program(
        self, program: ArticulatoryProgram
    ) -> ArticulatoryProgram:
        if not isinstance(program, ArticulatoryProgram):
            raise TypeError("articulatory program has the wrong type")
        program.verify()
        with self._lock:
            existing = self._programs.get(program.program_id)
            if existing is not None:
                if existing != program:
                    raise ValueError("articulatory program identity conflicted")
                return existing
            if len(self._programs) >= self._profile.max_programs:
                raise ArticulatoryCapacityError(
                    "articulatory program capacity exhausted"
                )
            staged = dict(self._programs)
            staged[program.program_id] = program
            self._encoded(staged)
            self._programs = staged
        return program

    def _verify_prepared_program_admission(
        self,
        prepared: PreparedArticulatoryProgramAdmission,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedArticulatoryProgramAdmission,
            )
            or prepared._construction_authority
            is not _PREPARED_PROGRAM_ADMISSION_AUTHORITY
            or prepared._owner_authority
            is not self._program_admission_owner
            or self._prepared_program_admission is not prepared
            or prepared._state.phase != "prepared"
            or dict(prepared._prior_programs) != self._programs
        ):
            raise ValueError(
                "prepared articulatory program admission changed custody"
            )
        prepared.program.verify()
        staged = dict(prepared._staged_programs)
        if (
            staged.get(prepared.program.program_id)
            != prepared.program
            or len(staged) != len(self._programs) + 1
        ):
            raise ValueError(
                "prepared articulatory program admission changed state"
            )
        self._encoded(staged)

    def prepare_program_admission(
        self,
        program: ArticulatoryProgram,
    ) -> PreparedArticulatoryProgramAdmission:
        if not isinstance(program, ArticulatoryProgram):
            raise TypeError(
                "program admission requires an articulatory program"
            )
        program.verify()
        with self._lock:
            if (
                self._prepared_program_admission is not None
                or self._latest_program_admission_undo is not None
                or self._prepared_generated_emission is not None
            ):
                raise RuntimeError(
                    "articulatory motor already owns a transaction"
                )
            if program.program_id in self._programs:
                raise ValueError(
                    "experience-grown articulatory program already exists"
                )
            if len(self._programs) >= self._profile.max_programs:
                raise ArticulatoryCapacityError(
                    "articulatory program capacity exhausted"
                )
            prior = dict(self._programs)
            staged = {
                **prior,
                program.program_id: program,
            }
            self._encoded(staged)
            prepared = PreparedArticulatoryProgramAdmission(
                program=program,
                _prior_programs=prior,
                _staged_programs=staged,
                _state=_ProgramAdmissionState(),
                _owner_authority=self._program_admission_owner,
                _construction_authority=(
                    _PREPARED_PROGRAM_ADMISSION_AUTHORITY
                ),
            )
            self._prepared_program_admission = prepared
            self._verify_prepared_program_admission(prepared)
            return prepared

    def commit_prepared_program_admission(
        self,
        prepared: PreparedArticulatoryProgramAdmission,
    ) -> ArticulatoryProgramAdmissionUndo:
        with self._lock:
            self._verify_prepared_program_admission(prepared)
            self._programs = dict(prepared._staged_programs)
            self._prepared_program_admission = None
            prepared._state.phase = "committed"
            undo = ArticulatoryProgramAdmissionUndo(
                _prepared=prepared,
                _owner_authority=self._program_admission_owner,
                _construction_authority=(
                    _PROGRAM_ADMISSION_UNDO_AUTHORITY
                ),
            )
            self._latest_program_admission_undo = undo
            return undo

    def discard_prepared_program_admission(
        self,
        prepared: PreparedArticulatoryProgramAdmission,
    ) -> None:
        with self._lock:
            self._verify_prepared_program_admission(prepared)
            self._prepared_program_admission = None
            prepared._state.phase = "discarded"

    def finalize_program_admission(
        self,
        undo: ArticulatoryProgramAdmissionUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(
                    undo,
                    ArticulatoryProgramAdmissionUndo,
                )
                or undo._construction_authority
                is not _PROGRAM_ADMISSION_UNDO_AUTHORITY
                or undo._owner_authority
                is not self._program_admission_owner
                or self._latest_program_admission_undo is not undo
                or undo._prepared._state.phase != "committed"
            ):
                raise ValueError(
                    "articulatory program admission finalization changed"
                )
            self._latest_program_admission_undo = None
            undo._prepared._state.phase = "finalized"

    def rollback_program_admission(
        self,
        undo: ArticulatoryProgramAdmissionUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(
                    undo,
                    ArticulatoryProgramAdmissionUndo,
                )
                or undo._construction_authority
                is not _PROGRAM_ADMISSION_UNDO_AUTHORITY
                or undo._owner_authority
                is not self._program_admission_owner
                or self._latest_program_admission_undo is not undo
                or undo._prepared._state.phase != "committed"
                or self._programs
                != dict(undo._prepared._staged_programs)
            ):
                raise ValueError(
                    "articulatory program admission rollback changed"
                )
            self._programs = dict(
                undo._prepared._prior_programs
            )
            self._latest_program_admission_undo = None
            undo._prepared._state.phase = "rolled_back"

    def synthesize(
        self,
        *,
        program_id: str,
        source_time_start: Fraction,
    ) -> ArticulatorySynthesis:
        if not isinstance(source_time_start, Fraction):
            raise TypeError("articulatory source time must be exact")
        with self._lock:
            program = self._programs.get(program_id)
        if program is None:
            raise KeyError("articulatory program is unavailable")
        excitation, radiated, areas = _generate_physical_pressure(program)
        excitation_pcm = _pcm_bytes(excitation)
        radiated_pcm = _pcm_bytes(radiated)
        actuator_full_field_assembly = _actuator_full_field(
            program=program,
            excitation=excitation,
            area_trajectories=areas,
            source_time_start=source_time_start,
        )
        source_time_end = source_time_start + Fraction(
            program.sample_count, VOCAL_SAMPLE_RATE_HZ
        )
        payload = {
            "actuator_full_field_receipt_sha256": (
                actuator_full_field_assembly.authority_receipt_sha256
            ),
            "excitation_pcm_sha256": hashlib.sha256(
                excitation_pcm
            ).hexdigest(),
            "program_id": program.program_id,
            "radiated_pcm_sha256": hashlib.sha256(
                radiated_pcm
            ).hexdigest(),
            "sample_count": program.sample_count,
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_SYNTHESIS_SCHEMA,
            "source_time_end": _fraction_text(source_time_end),
            "source_time_start": _fraction_text(source_time_start),
        }
        signature = _sign(
            self._synthesis_key, _SYNTHESIS_DOMAIN, payload
        )
        receipt = ArticulatorySynthesisReceipt(
            program_id=program.program_id,
            excitation_pcm_sha256=payload["excitation_pcm_sha256"],
            radiated_pcm_sha256=payload["radiated_pcm_sha256"],
            sample_count=program.sample_count,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            actuator_full_field_receipt_sha256=(
                actuator_full_field_assembly.authority_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result = ArticulatorySynthesis(
            program=program,
            excitation_pcm_s16le=excitation_pcm,
            radiated_pcm_s16le=radiated_pcm,
            actuator_full_field_assembly=actuator_full_field_assembly,
            receipt=receipt,
        )
        self.verify_synthesis(result)
        return result

    def verify_synthesis(self, value: ArticulatorySynthesis) -> None:
        if not isinstance(value, ArticulatorySynthesis):
            raise TypeError("articulatory synthesis has the wrong type")
        value.program.verify()
        value.receipt.verify(self._synthesis_key)
        value.actuator_full_field_assembly.verify()
        with self._lock:
            owned = self._programs.get(value.program.program_id)
        excitation, radiated, _areas = _generate_physical_pressure(
            value.program
        )
        if (
            owned != value.program
            or _pcm_tuple(
                value.excitation_pcm_s16le,
                "articulatory excitation",
            )
            != excitation
            or _pcm_tuple(
                value.radiated_pcm_s16le,
                "articulatory radiated pressure",
            )
            != radiated
            or value.receipt.program_id != value.program.program_id
            or value.receipt.sample_count != value.program.sample_count
            or value.receipt.excitation_pcm_sha256
            != hashlib.sha256(value.excitation_pcm_s16le).hexdigest()
            or value.receipt.radiated_pcm_sha256
            != hashlib.sha256(value.radiated_pcm_s16le).hexdigest()
            or value.actuator_full_field_assembly.program_id
            != value.program.program_id
            or value.actuator_full_field_assembly.sample_count
            != value.program.sample_count
            or value.actuator_full_field_assembly.source_time_start
            != value.receipt.source_time_start
            or value.actuator_full_field_assembly.source_time_end
            != value.receipt.source_time_end
            or value.receipt.actuator_full_field_receipt_sha256
            != value.actuator_full_field_assembly.authority_receipt_sha256
        ):
            raise ValueError("articulatory synthesis changed physical state")

    def _prospective_generated_emission_receipt(
        self,
        *,
        synthesis: ArticulatorySynthesis,
        pcm_s16le: bytes,
        execution: ActionExecutionReceipt,
    ) -> ArticulatoryGeneratedEmissionReceipt:
        """Build and verify the exact receipt that a successful commit returns."""

        receipt_fields = {
            "program_id": synthesis.program.program_id,
            "synthesis_receipt_sha256": (
                synthesis.receipt.authority_receipt_sha256
            ),
            "pcm_sha256": hashlib.sha256(pcm_s16le).hexdigest(),
            "sample_count": synthesis.program.sample_count,
            "world_before_receipt_sha256": (
                execution.before.authority_receipt_sha256
            ),
            "world_after_receipt_sha256": (
                execution.after.authority_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                execution.authority_receipt_sha256
            ),
            "command_sha256": execution.command_sha256,
        }
        receipt_payload = {
            "command_sha256": receipt_fields["command_sha256"],
            "pcm_sha256": receipt_fields["pcm_sha256"],
            "program_id": receipt_fields["program_id"],
            "sample_count": receipt_fields["sample_count"],
            "sample_rate_hz": VOCAL_SAMPLE_RATE_HZ,
            "schema": ARTICULATORY_GENERATED_EMISSION_SCHEMA,
            "self_port_id": PORT_ID,
            "synthesis_receipt_sha256": (
                receipt_fields["synthesis_receipt_sha256"]
            ),
            "world_after_receipt_sha256": (
                receipt_fields["world_after_receipt_sha256"]
            ),
            "world_before_receipt_sha256": (
                receipt_fields["world_before_receipt_sha256"]
            ),
            "world_execution_receipt_sha256": (
                receipt_fields["world_execution_receipt_sha256"]
            ),
        }
        signature = _sign(
            self._generated_emission_key,
            _GENERATED_EMISSION_DOMAIN,
            receipt_payload,
        )
        receipt = ArticulatoryGeneratedEmissionReceipt(
            program_id=receipt_fields["program_id"],
            synthesis_receipt_sha256=(
                receipt_fields["synthesis_receipt_sha256"]
            ),
            pcm_sha256=receipt_fields["pcm_sha256"],
            sample_count=receipt_fields["sample_count"],
            world_before_receipt_sha256=(
                receipt_fields["world_before_receipt_sha256"]
            ),
            world_after_receipt_sha256=(
                receipt_fields["world_after_receipt_sha256"]
            ),
            world_execution_receipt_sha256=(
                receipt_fields["world_execution_receipt_sha256"]
            ),
            command_sha256=receipt_fields["command_sha256"],
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": receipt_payload,
            }),
        )
        receipt.verify(self._generated_emission_key)
        return receipt

    def _require_prepared_generated_emission_locked(
        self,
        prepared: PreparedArticulatoryGeneratedEmission,
        *,
        world_authority: EmbodimentWorldAuthority,
        require_live: bool = True,
    ) -> PreparedArticulatoryGeneratedEmission:
        if (
            not isinstance(
                prepared,
                PreparedArticulatoryGeneratedEmission,
            )
            or prepared._construction_authority
            is not _PREPARED_ARTICULATORY_GENERATED_EMISSION_AUTHORITY
            or prepared._owner_authority
            is not self._prepared_generated_emission_authority
            or prepared._world_authority is not world_authority
            or (
                require_live
                and self._prepared_generated_emission is not prepared
            )
        ):
            raise ValueError(
                "prepared articulatory generated emission changed custody"
            )
        self.verify_synthesis(prepared.synthesis)
        execution = prepared.prepared_world_action.execution_receipt
        world_authority.verify_execution_receipt(execution)
        prospective = self._prospective_generated_emission_receipt(
            synthesis=prepared.synthesis,
            pcm_s16le=prepared.pcm_s16le,
            execution=execution,
        )
        payload = prepared.payload()
        signature = _sign(
            self._prepared_generated_emission_key,
            _PREPARED_GENERATED_EMISSION_DOMAIN,
            payload,
        )
        current = world_authority.observation_snapshot()
        if (
            not hmac.compare_digest(
                signature,
                prepared.preparation_hmac_sha256,
            )
            or prepared.preparation_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
            or prepared.pcm_s16le
            != prepared.synthesis.radiated_pcm_s16le
            or prepared.prospective_emission_receipt_sha256
            != prospective.authority_receipt_sha256
            or prepared._prospective_emission_hmac_sha256
            != prospective.authority_hmac_sha256
            or execution.disposition != "applied"
            or execution.port_id != PORT_ID
            or execution.actor_body_id != execution.before.self_body_id
            or execution.causal_intent_receipt_sha256
            != prepared.causal_intent_receipt_sha256
            or execution.command_sha256
            != hashlib.sha256(prepared.command_payload).hexdigest()
            or execution.before != current
            or execution.after.revision != execution.before.revision + 1
        ):
            raise ValueError(
                "prepared articulatory generated emission changed state"
            )
        return prepared

    def verify_prepared_generated_emission(
        self,
        prepared: PreparedArticulatoryGeneratedEmission,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Verify one live prepared capability without committing the world."""

        with self._lock:
            self._require_prepared_generated_emission_locked(
                prepared,
                world_authority=world_authority,
            )

    def prepare_generated_emission(
        self,
        *,
        synthesis: ArticulatorySynthesis,
        world_authority: EmbodimentWorldAuthority,
        causal_intent_receipt_sha256: str,
    ) -> PreparedArticulatoryGeneratedEmission:
        """Prepare fresh pressure without changing live physical world state."""

        self.verify_synthesis(synthesis)
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError(
                "articulatory execution requires W1 world authority"
            )
        _sha256(
            causal_intent_receipt_sha256,
            "articulatory causal intent",
        )
        with self._lock:
            if self._prepared_generated_emission is not None:
                raise RuntimeError(
                    "articulatory generated emission is already prepared"
                )
            before = world_authority.observation_snapshot()
            pcm = synthesis.radiated_pcm_s16le
            command = VocalizeCommand(
                epoch_commitment_sha256=_digest({
                    "program_id": synthesis.program.program_id,
                    "synthesis_receipt_sha256": (
                        synthesis.receipt.authority_receipt_sha256
                    ),
                    "world_before_receipt_sha256": (
                        before.authority_receipt_sha256
                    ),
                }),
                sequence=before.revision,
                source_sample_start=0,
                pcm_sha256=hashlib.sha256(pcm).hexdigest(),
                sample_count=synthesis.program.sample_count,
            )
            command_payload = encode_command(command)
            prepared_world = world_authority.prepare_port_command(
                port_id=PORT_ID,
                command_payload=command_payload,
                causal_intent_receipt_sha256=(
                    causal_intent_receipt_sha256
                ),
                expected_revision=before.revision,
            )
            if isinstance(prepared_world, ActionExecutionReceipt):
                world_authority.verify_execution_receipt(prepared_world)
                raise ValueError(
                    "articulatory self-body preparation was rejected: "
                    f"{prepared_world.reason}"
                )
            prospective = self._prospective_generated_emission_receipt(
                synthesis=synthesis,
                pcm_s16le=pcm,
                execution=prepared_world.execution_receipt,
            )
            provisional = PreparedArticulatoryGeneratedEmission(
                synthesis=synthesis,
                pcm_s16le=pcm,
                command_payload=command_payload,
                causal_intent_receipt_sha256=(
                    causal_intent_receipt_sha256
                ),
                prepared_world_action=prepared_world,
                prospective_emission_receipt_sha256=(
                    prospective.authority_receipt_sha256
                ),
                preparation_hmac_sha256="0" * 64,
                preparation_receipt_sha256="0" * 64,
                _prospective_emission_hmac_sha256=(
                    prospective.authority_hmac_sha256
                ),
                _world_authority=world_authority,
                _owner_authority=(
                    self._prepared_generated_emission_authority
                ),
                _construction_authority=(
                    _PREPARED_ARTICULATORY_GENERATED_EMISSION_AUTHORITY
                ),
            )
            signature = _sign(
                self._prepared_generated_emission_key,
                _PREPARED_GENERATED_EMISSION_DOMAIN,
                provisional.payload(),
            )
            prepared = PreparedArticulatoryGeneratedEmission(
                synthesis=provisional.synthesis,
                pcm_s16le=provisional.pcm_s16le,
                command_payload=provisional.command_payload,
                causal_intent_receipt_sha256=(
                    provisional.causal_intent_receipt_sha256
                ),
                prepared_world_action=(
                    provisional.prepared_world_action
                ),
                prospective_emission_receipt_sha256=(
                    provisional.prospective_emission_receipt_sha256
                ),
                preparation_hmac_sha256=signature,
                preparation_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
                _prospective_emission_hmac_sha256=(
                    provisional._prospective_emission_hmac_sha256
                ),
                _world_authority=world_authority,
                _owner_authority=(
                    self._prepared_generated_emission_authority
                ),
                _construction_authority=(
                    _PREPARED_ARTICULATORY_GENERATED_EMISSION_AUTHORITY
                ),
            )
            self._prepared_generated_emission = prepared
            try:
                self._require_prepared_generated_emission_locked(
                    prepared,
                    world_authority=world_authority,
                )
            except BaseException:
                world_authority.discard_prepared_action(prepared_world)
                self._prepared_generated_emission = None
                raise
            return prepared

    def preverify_generated_emission_commit(
        self,
        prepared: PreparedArticulatoryGeneratedEmission,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> PreverifiedArticulatoryGeneratedEmissionCommit:
        """Build and verify the complete result before visibility closes."""

        with self._lock:
            current = self._require_prepared_generated_emission_locked(
                prepared,
                world_authority=world_authority,
            )
            execution = current.prepared_world_action.execution_receipt
            receipt = self._prospective_generated_emission_receipt(
                synthesis=current.synthesis,
                pcm_s16le=current.pcm_s16le,
                execution=execution,
            )
            if receipt.authority_receipt_sha256 != (
                current.prospective_emission_receipt_sha256
            ):
                raise ValueError(
                    "prepared prospective emission commitment changed"
                )
            staged_result = ArticulatoryGeneratedEmission(
                synthesis=current.synthesis,
                pcm_s16le=current.pcm_s16le,
                execution_receipt=execution,
                emission_receipt=receipt,
            )
            self.verify_generated_emission(
                staged_result,
                world_authority=world_authority,
            )
            return PreverifiedArticulatoryGeneratedEmissionCommit(
                _prepared=current,
                _result=staged_result,
                _world_authority=world_authority,
                _owner_authority=(
                    self._prepared_generated_emission_authority
                ),
                _construction_authority=(
                    _PREVERIFIED_GENERATED_EMISSION_COMMIT_AUTHORITY
                ),
            )

    @contextmanager
    def preverified_generated_emission_transaction(
        self,
        preverified: PreverifiedArticulatoryGeneratedEmissionCommit,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> Iterator[Callable[[], ArticulatoryGeneratedEmission]]:
        """Yield one owner-bound physical commit while retaining motor custody."""

        with self._lock:
            self.verify_preverified_generated_emission_commit(
                preverified,
                world_authority=world_authority,
            )
            if self._active_preverified_generated_emission_commit is not None:
                raise RuntimeError(
                    "generated emission commit transaction already active"
                )
            current = preverified._prepared
            self._active_preverified_generated_emission_commit = preverified
            committed = False

            def commit() -> ArticulatoryGeneratedEmission:
                nonlocal committed
                if (
                    self._active_preverified_generated_emission_commit
                    is not preverified
                    or committed
                ):
                    raise AssertionError(
                        "generated emission commit capability is not live"
                    )
                world_authority.commit_prepared_action(
                    current.prepared_world_action
                )
                committed = True
                self._prepared_generated_emission = None
                return preverified._result

            try:
                yield commit
            finally:
                if (
                    self._active_preverified_generated_emission_commit
                    is preverified
                ):
                    self._active_preverified_generated_emission_commit = None

    def verify_preverified_generated_emission_commit(
        self,
        preverified: PreverifiedArticulatoryGeneratedEmissionCommit,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Verify exact owner/world/live custody before visibility closes."""

        if (
            not isinstance(
                preverified,
                PreverifiedArticulatoryGeneratedEmissionCommit,
            )
            or preverified._construction_authority
            is not _PREVERIFIED_GENERATED_EMISSION_COMMIT_AUTHORITY
            or preverified._owner_authority
            is not self._prepared_generated_emission_authority
            or preverified._world_authority is not world_authority
        ):
            raise ValueError(
                "preverified generated emission changed custody"
            )
        with self._lock:
            current = self._require_prepared_generated_emission_locked(
                preverified._prepared,
                world_authority=world_authority,
            )
            if (
                preverified._result.synthesis is not current.synthesis
                or preverified._result.pcm_s16le
                is not current.pcm_s16le
                or preverified._result.execution_receipt
                is not current.prepared_world_action.execution_receipt
                or preverified._result.emission_receipt
                .authority_receipt_sha256
                != current.prospective_emission_receipt_sha256
            ):
                raise ValueError(
                    "preverified generated emission result changed"
                )

    def discard_prepared_generated_emission(
        self,
        prepared: PreparedArticulatoryGeneratedEmission,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        """Discard one prepared vocal action without physical mutation."""

        with self._lock:
            current = self._require_prepared_generated_emission_locked(
                prepared,
                world_authority=world_authority,
            )
            world_authority.discard_prepared_action(
                current.prepared_world_action
            )
            self._prepared_generated_emission = None

    def verify_generated_emission(
        self,
        value: ArticulatoryGeneratedEmission,
        *,
        world_authority: EmbodimentWorldAuthority,
    ) -> None:
        if not isinstance(value, ArticulatoryGeneratedEmission):
            raise TypeError(
                "articulatory generated emission is not typed"
            )
        self.verify_synthesis(value.synthesis)
        value.emission_receipt.verify(
            self._generated_emission_key
        )
        world_authority.verify_execution_receipt(
            value.execution_receipt
        )
        receipt = value.emission_receipt
        execution = value.execution_receipt
        if (
            value.pcm_s16le
            != value.synthesis.radiated_pcm_s16le
            or receipt.program_id
            != value.synthesis.program.program_id
            or receipt.synthesis_receipt_sha256
            != value.synthesis.receipt.authority_receipt_sha256
            or receipt.pcm_sha256
            != hashlib.sha256(value.pcm_s16le).hexdigest()
            or receipt.sample_count
            != value.synthesis.program.sample_count
            or receipt.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or receipt.world_before_receipt_sha256
            != execution.before.authority_receipt_sha256
            or receipt.world_after_receipt_sha256
            != execution.after.authority_receipt_sha256
            or receipt.command_sha256 != execution.command_sha256
            or execution.disposition != "applied"
        ):
            raise ValueError(
                "generated pressure diverged from articulatory synthesis"
            )

    def status(self) -> dict[str, int | bool | str]:
        with self._lock:
            encoded = self._encoded(self._programs)
            return {
                "program_count": len(self._programs),
                "program_capacity": self._profile.max_programs,
                "program_capacity_exhausted": (
                    len(self._programs) >= self._profile.max_programs
                ),
                "retained_pcm_bytes": 0,
                "retained_cursor_bytes": 0,
                "retained_binding_count": 0,
                "encoded_state_bytes": len(encoded),
                "state_byte_capacity": self._profile.max_state_bytes,
                "state_schema": ARTICULATORY_STATE_SCHEMA,
            }

    def _encoded(
        self,
        programs: Mapping[str, ArticulatoryProgram],
    ) -> bytes:
        body = {
            "programs": [
                programs[key].as_record() for key in sorted(programs)
            ],
            "resource_profile": (
                self._profile.payload()
                | {
                    "authority_receipt_sha256": (
                        self._profile.authority_receipt_sha256
                    )
                }
            ),
            "schema": ARTICULATORY_STATE_SCHEMA,
        }
        envelope = {
            "body": body,
            "schema": ARTICULATORY_ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(
                self._state_key, _STATE_DOMAIN, body
            ),
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._profile.max_state_bytes:
            raise ArticulatoryCapacityError(
                "articulatory state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if (
                self._prepared_program_admission is not None
                or self._latest_program_admission_undo is not None
            ):
                raise RuntimeError(
                    "articulatory program transaction cannot persist"
                )
            return self._encoded(self._programs)

    def restore_current_encoded(self, encoded: bytes) -> None:
        """Restore exact authenticated current-schema state in place."""

        if not isinstance(encoded, bytes):
            raise TypeError("articulatory state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "articulatory state is not canonical JSON"
            ) from exc
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ARTICULATORY_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("articulatory state envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"programs", "resource_profile", "schema"}
            or body.get("schema") != ARTICULATORY_STATE_SCHEMA
            or not isinstance(body.get("programs"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("articulatory state body changed")
        raw_profile = body["resource_profile"]
        expected_profile = (
            self._profile.payload()
            | {
                "authority_receipt_sha256": (
                    self._profile.authority_receipt_sha256
                )
            }
        )
        if raw_profile != expected_profile:
            raise ValueError(
                "articulatory restored resource profile changed"
            )
        signature = envelope.get("state_hmac_sha256")
        _sha256(signature, "articulatory state HMAC")
        expected = _sign(self._state_key, _STATE_DOMAIN, body)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("articulatory state HMAC changed")
        restored: dict[str, ArticulatoryProgram] = {}
        for raw in body["programs"]:
            program = self._program_from_record(raw)
            if program.program_id in restored:
                raise ValueError("articulatory program was duplicated")
            restored[program.program_id] = program
        if len(restored) > self._profile.max_programs:
            raise ValueError(
                "articulatory restored state exceeds capacity"
            )
        with self._lock:
            if (
                self._prepared_program_admission is not None
                or self._latest_program_admission_undo is not None
                or self._prepared_generated_emission is not None
                or self._active_preverified_generated_emission_commit
                is not None
            ):
                raise RuntimeError(
                    "cannot restore across articulatory transaction"
                )
            prior = self._programs
            self._programs = restored
            try:
                if self._encoded(restored) != encoded:
                    raise ValueError(
                        "articulatory restored state changed"
                    )
            except BaseException:
                self._programs = prior
                raise

    @staticmethod
    def _program_from_record(raw: object) -> ArticulatoryProgram:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "authority_receipt_sha256",
                "body_trajectory",
                "larynx",
                "program_id",
                "sample_count",
                "sample_rate_hz",
                "schema",
                "tract",
            }
            or raw.get("schema") != ARTICULATORY_PROGRAM_SCHEMA
            or raw.get("sample_rate_hz") != VOCAL_SAMPLE_RATE_HZ
            or not isinstance(raw.get("larynx"), Mapping)
            or not isinstance(raw.get("tract"), Mapping)
            or not isinstance(raw.get("body_trajectory"), list)
        ):
            raise ValueError("articulatory program record changed")
        raw_larynx = raw["larynx"]
        raw_tract = raw["tract"]
        if set(raw_larynx) != {
            "cycle_samples",
            "open_samples",
            "peak_volume_velocity_pcm",
        } or set(raw_tract) != {
            "apex_section_area_mm2",
            "final_section_area_mm2",
            "initial_section_area_mm2",
            "radiation_load_area_mm2",
            "wall_retention_ppm",
        }:
            raise ValueError(
                "articulatory physical configuration changed"
            )
        try:
            body_trajectory = tuple(
                ArticulatoryBodyTrajectoryInterval(
                    sample_start=item["sample_start"],
                    sample_end=item["sample_end"],
                    glottal_open_samples=item[
                        "glottal_open_samples"
                    ],
                    section_area_mm2=tuple(
                        item["section_area_mm2"]
                    ),
                )
                for item in raw["body_trajectory"]
                if (
                    isinstance(item, Mapping)
                    and set(item)
                    == {
                        "glottal_open_samples",
                        "sample_end",
                        "sample_start",
                        "section_area_mm2",
                    }
                )
            )
            if len(body_trajectory) != len(raw["body_trajectory"]):
                raise ValueError(
                    "articulatory body trajectory is malformed"
                )
            program = ArticulatoryProgram(
                sample_count=raw.get("sample_count"),
                larynx=LaryngealExcitationConfiguration(
                    cycle_samples=raw_larynx.get("cycle_samples"),
                    open_samples=raw_larynx.get("open_samples"),
                    peak_volume_velocity_pcm=raw_larynx.get(
                        "peak_volume_velocity_pcm"
                    ),
                ),
                tract=VocalTractConfiguration(
                    initial_section_area_mm2=tuple(
                        raw_tract["initial_section_area_mm2"]
                    ),
                    apex_section_area_mm2=tuple(
                        raw_tract["apex_section_area_mm2"]
                    ),
                    final_section_area_mm2=tuple(
                        raw_tract["final_section_area_mm2"]
                    ),
                    radiation_load_area_mm2=raw_tract.get(
                        "radiation_load_area_mm2"
                    ),
                    wall_retention_ppm=raw_tract.get(
                        "wall_retention_ppm"
                    ),
                ),
                body_trajectory=body_trajectory,
                program_id=raw.get("program_id"),
                authority_receipt_sha256=raw.get(
                    "authority_receipt_sha256"
                ),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "articulatory program configuration is malformed"
            ) from exc
        program.verify()
        if program.as_record() != dict(raw):
            raise ValueError("articulatory program is noncanonical")
        return program

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
    ) -> "ArticulatorySelfVocalMotorOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("articulatory state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("articulatory state is not canonical JSON") from exc
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("articulatory state envelope changed")
        body = envelope["body"]
        envelope_schema = envelope.get("schema")
        is_current = (
            envelope_schema == ARTICULATORY_ENVELOPE_SCHEMA
            and body.get("schema") == ARTICULATORY_STATE_SCHEMA
            and set(body) == {"programs", "resource_profile", "schema"}
        )
        if (
            not is_current
            or not isinstance(body.get("programs"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("articulatory state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_programs",
            "max_state_bytes",
            "profile_id",
            "schema",
        }:
            raise ValueError("articulatory resource profile record changed")
        profile = ArticulatoryMotorResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_programs=raw_profile.get("max_programs"),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
        )
        signature = envelope.get("state_hmac_sha256")
        _sha256(signature, "articulatory state HMAC")
        expected = _sign(
            owner._state_key,
            _STATE_DOMAIN,
            body,
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError("articulatory state HMAC changed")
        for raw in body["programs"]:
            program = cls._program_from_record(raw)
            if program.program_id in owner._programs:
                raise ValueError("articulatory program was duplicated")
            owner._programs[program.program_id] = program
        if len(owner._programs) > profile.max_programs:
            raise ValueError("articulatory restored state exceeds capacity")
        if owner.snapshot_encoded() != encoded:
            raise ValueError("articulatory restored state changed")
        return owner


class ArticulatoryCapacityError(RuntimeError):
    pass


__all__ = (
    "ACTUATOR_RECEPTOR_SAMPLE_DIVISOR",
    "ARTICULATORY_ACTUATOR_FULL_FIELD_ASSEMBLY_SCHEMA",
    "ARTICULATORY_ENVELOPE_SCHEMA",
    "ARTICULATORY_GENERATED_EMISSION_SCHEMA",
    "ARTICULATORY_PREPARED_GENERATED_EMISSION_SCHEMA",
    "ARTICULATORY_PROGRAM_SCHEMA",
    "ARTICULATORY_STATE_SCHEMA",
    "ARTICULATORY_SYNTHESIS_SCHEMA",
    "ArticulatoryCapacityError",
    "ArticulatoryActuatorFullFieldAssembly",
    "ArticulatoryActuatorFullFieldPartition",
    "ArticulatoryBodyTrajectoryInterval",
    "ArticulatoryGeneratedEmission",
    "ArticulatoryGeneratedEmissionReceipt",
    "ArticulatoryMotorResourceProfile",
    "ArticulatoryPressureWithQuiescence",
    "ArticulatoryProgram",
    "ArticulatoryProgramAdmissionUndo",
    "ArticulatorySelfVocalMotorOwner",
    "ArticulatorySynthesis",
    "ArticulatorySynthesisReceipt",
    "ArticulatoryTravelingWaveState",
    "LaryngealExcitationConfiguration",
    "MAX_ARTICULATORY_RELAXATION_SAMPLES",
    "MAX_ARTICULATORY_SAMPLES",
    "MAX_TRACT_AREA_MM2",
    "PPM",
    "PreparedArticulatoryGeneratedEmission",
    "PreparedArticulatoryProgramAdmission",
    "PreverifiedArticulatoryGeneratedEmissionCommit",
    "Q31",
    "TRACT_SECTION_COUNT",
    "VocalTractConfiguration",
    "generate_articulatory_pressure_with_quiescence",
    "relax_articulatory_traveling_wave_state",
    "signed_magnitude_truncating_wall_loss",
)
